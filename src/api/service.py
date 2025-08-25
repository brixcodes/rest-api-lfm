from datetime import datetime, timedelta, date
import logging
import os
import uuid
import secrets
import string
import aiofiles
from pathlib import Path as PathLib
from typing import List, Optional, Dict
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from sqlalchemy.orm import selectinload, joinedload
from sqlalchemy.exc import IntegrityError, NoResultFound
from fastapi import HTTPException, UploadFile, status
from passlib.context import CryptContext

from src.api.model import (
    Adresse, Utilisateur, CentreFormation, Formation, SessionFormation,
    Module, Ressource, DossierCandidature, PieceJointe, Reclamation, Paiement,
    InformationDescriptive,
    Evaluation, QuestionEvaluation, ResultatEvaluation, ReponseCandidat, Certificat,
)
from src.util.helper.enum import (
    StatutSessionEnum, StatutCandidatureEnum, StatutPaiementEnum, ModaliteEnum,
    StatutEvaluationEnum, StatutResultatEnum, TypeCorrectionEnum
)
from src.api.schema import (
    AdresseCreate, AdresseUpdate, AdresseResponse, AdresseLight, LoginResponse, PieceJointeLight,
    UtilisateurCreate, UtilisateurUpdate, UtilisateurResponse, UtilisateurLight,
    CentreFormationCreate, CentreFormationUpdate, CentreFormationResponse, CentreFormationLight,
    FormationCreate, FormationUpdate, FormationResponse, FormationLight,
    SessionFormationCreate, SessionFormationUpdate, SessionFormationResponse, SessionFormationLight,
    SessionStatutUpdate, SessionModaliteUpdate,
    ModuleCreate, ModuleUpdate, ModuleResponse, ModuleLight,
    RessourceCreate, RessourceUpdate, RessourceResponse, RessourceLight,
    DossierCandidatureCreate, DossierCandidatureUpdate, DossierCandidatureResponse, DossierCandidatureLight,
    PieceJointeCreate, PieceJointeUpdate, PieceJointeResponse, PieceJointeLight,
    ReclamationCreate, ReclamationUpdate, ReclamationResponse, ReclamationLight,
    PaiementCreate, PaiementUpdate, PaiementResponse, PaiementLight,
    InformationDescriptiveCreate, InformationDescriptiveUpdate, InformationDescriptiveResponse,
    # Nouveaux schémas pour l'évaluation
    EvaluationCreate, EvaluationUpdate, EvaluationResponse, EvaluationLight,
    QuestionEvaluationCreate, QuestionEvaluationUpdate, QuestionEvaluationResponse, QuestionEvaluationLight,
    ResultatEvaluationCreate, ResultatEvaluationUpdate, ResultatEvaluationResponse, ResultatEvaluationLight,
    ReponseCandidatCreate, ReponseCandidatUpdate, ReponseCandidatResponse, 
    CertificatCreate, CertificatUpdate, CertificatResponse, CertificatLight,
)

from src.util.db.setting import settings
logger = logging.getLogger(__name__)

# Configuration du contexte de hachage des mots de passe
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

def generate_secure_password(length: int = 12) -> str:
    """Génère un mot de passe sécurisé avec des caractères aléatoires"""
    alphabet = string.ascii_letters + string.digits + "!@#$%^&*"
    while True:
        password = ''.join(secrets.choice(alphabet) for i in range(length))
        # Vérifier que le mot de passe contient au moins une lettre majuscule, une minuscule et un chiffre
        if (any(c.islower() for c in password)
                and any(c.isupper() for c in password)
                and any(c.isdigit() for c in password)
                and any(c in "!@#$%^&*" for c in password)):
            return password

def hash_password(password: str) -> str:
    """Hache un mot de passe avec bcrypt"""
    return pwd_context.hash(password)

def verify_password(plain_password: str, hashed_password: str) -> bool:
    """Vérifie un mot de passe contre son hash"""
    return pwd_context.verify(plain_password, hashed_password)

class BaseService:
    def __init__(self, session: AsyncSession):
        self.session = session

    async def commit(self):
        try:
            await self.session.commit()
        except IntegrityError as e:
            await self.session.rollback()
            logger.error(f"Erreur d'intégrité lors du commit : {str(e)}")
            raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Violation d'intégrité : Entrée dupliquée ou contrainte échouée.")
        except Exception as e:
            await self.session.rollback()
            logger.error(f"Erreur inattendue lors du commit : {str(e)}")
            raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Erreur inattendue de base de données lors du commit.")

    async def refresh(self, instance):
        await self.session.refresh(instance)
        
# ────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────
# Service Fichier
# ────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────

class FileUploadException(HTTPException):
    pass

class FileStorageException(HTTPException):
    pass

class FileService:
    def __init__(self):
        # Récupère la racine du projet (là où le script est lancé)
        project_root = PathLib(os.getcwd())

        # Use settings from setting.py for storage path
        self.storage_path = project_root / "upload"
        self.storage_path.mkdir(parents=True, exist_ok=True)  # crée le dossier si absent
        logger.info(f"Chemin de stockage configuré : {self.storage_path.absolute()}")

        # Allowed file extensions
        self.allowed_extensions = {
            # Images
            '.jpg', '.jpeg', '.png', 
            # Documents
            '.pdf', '.doc', '.docx',
            # Vidéos
            '.mp4', '.avi', '.mkv',
            # Audio
            '.mp3', '.wav', '.opus'
        }
        self.max_file_size = 254 * 1024 * 1024  # 254 MB

    async def upload_file(self, file: UploadFile, base_url: str) -> dict[str, str]:
        try:
            # Validate file extension
            file_extension = PathLib(file.filename).suffix.lower()
            if file_extension not in self.allowed_extensions:
                logger.warning(f"Tentative de téléversement avec extension non autorisée : {file_extension}")
                raise FileUploadException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail=f"Extension de fichier non autorisée : {file_extension}. Extensions autorisées : {', '.join(sorted(self.allowed_extensions))}"
                )

            # Validate file size before reading
            if file.size and file.size > self.max_file_size:
                logger.warning(f"Taille du fichier trop grande : {file.size} octets")
                raise FileUploadException(
                    status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
                    detail=f"La taille du fichier ({file.size} octets) dépasse la limite de {self.max_file_size} octets."
                )

            # Generate unique filename
            unique_filename = f"{uuid.uuid4()}{file_extension}"
            file_path = self.storage_path / unique_filename
            logger.info(f"Chemin de fichier généré : {file_path.absolute()}")

            # Ensure storage directory exists
            self.storage_path.mkdir(parents=True, exist_ok=True)
            logger.debug(f"Répertoire de stockage vérifié : {self.storage_path.absolute()}")

            # Save file
            async with aiofiles.open(file_path, 'wb') as out_file:
                content = await file.read()
                await out_file.write(content)
            logger.info(f"Fichier écrit avec succès : {file_path} (Taille : {len(content)} octets)")

            # Verify file exists and size matches
            if not file_path.exists():
                logger.error(f"Le fichier n'existe pas après écriture : {file_path}")
                raise FileStorageException(
                    status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                    detail="Erreur lors de l'enregistrement du fichier."
                )

            file_size = file_path.stat().st_size
            if file_size != len(content):
                logger.error(f"Incohérence de taille : {file_size} (disque) vs {len(content)} (mémoire)")
                file_path.unlink()
                raise FileStorageException(
                    status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                    detail="Incohérence dans la taille du fichier enregistré."
                )

            # Construct full URL
            relative_path = f"{self.storage_path.name}/{unique_filename}"
            full_url = f"{base_url.rstrip('/')}/{relative_path}"
            logger.info(f"Fichier téléversé avec succès : {unique_filename}")

            return {
                "filename": unique_filename,
                "path": str(file_path),
                "url": full_url,
                "original_filename": file.filename,
                "size": str(file_size)
            }

        except FileUploadException:
            raise
        except Exception as e:
            logger.error(f"Erreur inattendue lors du téléversement : {str(e)}", exc_info=True)
            raise FileStorageException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"Erreur lors de l'enregistrement du fichier : {str(e)}"
            )

    async def delete_file(self, file_path: str) -> None:
        try:
            # If full URL is provided, extract filename
            if file_path.startswith('http'):
                file_path = PathLib(file_path).name

            # Construct full file path
            full_path = self.storage_path / file_path
            logger.info(f"Tentative de suppression du fichier : {full_path.absolute()}")

            # Verify file exists
            if not full_path.exists():
                logger.warning(f"Le fichier n'existe pas : {full_path}")
                raise FileUploadException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail=f"Le fichier {file_path} n'existe pas."
                )

            # Verify file is within storage directory
            try:
                full_path.relative_to(self.storage_path)
            except ValueError:
                logger.warning(f"Chemin non autorisé : {full_path}")
                raise FileUploadException(
                    status_code=status.HTTP_403_FORBIDDEN,
                    detail="Chemin de fichier non autorisé : hors du répertoire de stockage."
                )

            # Delete file
            full_path.unlink()
            logger.info(f"Fichier supprimé avec succès : {full_path}")

        except FileUploadException:
            raise
        except Exception as e:
            logger.error(f"Erreur inattendue lors de la suppression : {str(e)}", exc_info=True)
            raise FileStorageException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"Erreur lors de la suppression du fichier : {str(e)}"
            )

# ────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────
# ADRESSE (Nouvelle table pour normaliser les adresses et éviter la duplication)
# ────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────
class AddressService(BaseService):
    async def create(self, data: AdresseCreate, user_id: int) -> AdresseResponse:
        logger.info(f"Création d'une adresse pour l'utilisateur {user_id}")
        address = Adresse(**data.model_dump(), utilisateur_id=user_id)
        self.session.add(address)
        await self.commit()
        await self.refresh(address)
        logger.info(f"Adresse créée avec ID {address.id}")
        return AdresseResponse.model_validate(address, from_attributes=True)

    async def get_by_id(self, address_id: int) -> Optional[AdresseResponse]:
        try:
            logger.info(f"Récupération de l'adresse ID {address_id}")
            result = await self.session.execute(select(Adresse).options(joinedload(Adresse.utilisateur)).where(Adresse.id == address_id))
            address = result.scalar_one()
            return AdresseResponse.model_validate(address, from_attributes=True)
        except NoResultFound:
            logger.warning(f"Adresse ID {address_id} non trouvée")
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"Adresse avec ID {address_id} non trouvée.")

    async def update(self, address_id: int, data: AdresseUpdate) -> AdresseResponse:
        # Récupérer directement l'adresse depuis la base de données
        result = await self.session.execute(select(Adresse).where(Adresse.id == address_id))
        address = result.scalar_one_or_none()
        
        if not address:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"Adresse avec ID {address_id} non trouvée.")
        
        logger.info(f"Mise à jour de l'adresse ID {address_id}")
        update_data = data.model_dump(exclude_unset=True)
        for key, value in update_data.items():
            setattr(address, key, value)
        await self.commit()
        await self.refresh(address)
        logger.info(f"Adresse ID {address_id} mise à jour")
        return AdresseResponse.model_validate(address, from_attributes=True)

    async def delete(self, address_id: int):
        # Récupérer directement l'adresse depuis la base de données
        result = await self.session.execute(select(Adresse).where(Adresse.id == address_id))
        address = result.scalar_one_or_none()
        
        if not address:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"Adresse avec ID {address_id} non trouvée.")
        
        logger.info(f"Suppression de l'adresse ID {address_id}")
        await self.session.delete(address)
        await self.commit()
        logger.info(f"Adresse ID {address_id} supprimée")

# ────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────
# UTILISATEUR (Optimisé: Adresses externalisées, ajout de champs pour traçabilité et sécurité, suppression de redondances)
# ────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────
class UserService(BaseService):
    async def create(self, data: UtilisateurCreate) -> UtilisateurResponse:
        logger.info("Création d'un utilisateur")
        
        # Générer un mot de passe sécurisé automatiquement
        plain_password = generate_secure_password()
        hashed_password = hash_password(plain_password)
        
        # Créer l'utilisateur avec le mot de passe haché
        user_data = data.model_dump()
        user_data["password"] = hashed_password
        
        user = Utilisateur(**user_data)
        
        self.session.add(user)
        await self.commit()
        await self.refresh(user)
        
        # Pour l'instant, on le log (à supprimer en production)
        logger.info(f"Utilisateur créé avec ID {user.id} - Mot de passe temporaire: {plain_password}")
        
        # Créer manuellement la réponse pour éviter les erreurs de greenlet avec les relations
        user_data = {
            "id": user.id,
            "nom": user.nom,
            "prenom": user.prenom,
            "email": user.email,
            "role": user.role,
            "civilite": user.civilite,
            "date_naissance": user.date_naissance,
            "telephone_mobile": user.telephone_mobile,
            "telephone": user.telephone,
            "nationalite": user.nationalite,
            "actif": user.actif,
            "email_verified": user.email_verified,
            "last_login": user.last_login,
            "situation_professionnelle": user.situation_professionnelle,
            "experience_professionnelle_en_mois": user.experience_professionnelle_en_mois,
            "employeur": user.employeur,
            "categorie_socio_professionnelle": user.categorie_socio_professionnelle,
            "fonction": user.fonction,
            "dernier_diplome_obtenu": user.dernier_diplome_obtenu,
            "date_obtention_dernier_diplome": user.date_obtention_dernier_diplome,
            "created_at": user.created_at,
            "updated_at": user.updated_at,
            "adresses": None,  # Pas encore d'adresses pour un nouvel utilisateur
            "dossiers": None,  # Pas encore de dossiers pour un nouvel utilisateur
            "reclamations": None  # Pas encore de réclamations pour un nouvel utilisateur
        }
        
        return UtilisateurResponse(**user_data)

    async def get_by_id(self, user_id: int, load_relations: bool = True) -> Optional[UtilisateurResponse]:
        query = select(Utilisateur).where(Utilisateur.id == user_id)
        if load_relations:
            query = query.options(
                selectinload(Utilisateur.adresses),
                selectinload(Utilisateur.dossiers).selectinload(DossierCandidature.formation),
                selectinload(Utilisateur.dossiers).selectinload(DossierCandidature.session),
                selectinload(Utilisateur.reclamations).joinedload(Reclamation.dossier)
            )
        try:
            logger.info(f"Récupération de l'utilisateur ID {user_id}")
            result = await self.session.execute(query)
            user = result.scalar_one()
            
            # Créer manuellement la réponse pour éviter les erreurs de greenlet
            user_data = {
                "id": user.id,
                "nom": user.nom,
                "prenom": user.prenom,
                "email": user.email,
                "role": user.role,
                "civilite": user.civilite,
                "date_naissance": user.date_naissance,
                "telephone_mobile": user.telephone_mobile,
                "telephone": user.telephone,
                "nationalite": user.nationalite,
                "actif": user.actif,
                "email_verified": user.email_verified,
                "last_login": user.last_login,
                "situation_professionnelle": user.situation_professionnelle,
                "experience_professionnelle_en_mois": user.experience_professionnelle_en_mois,
                "employeur": user.employeur,
                "categorie_socio_professionnelle": user.categorie_socio_professionnelle,
                "fonction": user.fonction,
                "dernier_diplome_obtenu": user.dernier_diplome_obtenu,
                "date_obtention_dernier_diplome": user.date_obtention_dernier_diplome,
                "created_at": user.created_at,
                "updated_at": user.updated_at,
                "adresses": user.adresses if load_relations else None,
                "dossiers": user.dossiers if load_relations else None,
                "reclamations": user.reclamations if load_relations else None
            }
            
            return UtilisateurResponse(**user_data)
        except NoResultFound:
            logger.warning(f"Utilisateur ID {user_id} non trouvé")
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"Utilisateur avec ID {user_id} non trouvé.")

    async def update(self, user_id: int, data: UtilisateurUpdate) -> UtilisateurResponse:
        # Récupérer directement l'utilisateur depuis la base de données
        result = await self.session.execute(select(Utilisateur).where(Utilisateur.id == user_id))
        user = result.scalar_one_or_none()
        
        if not user:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"Utilisateur avec ID {user_id} non trouvé.")
        
        logger.info(f"Mise à jour de l'utilisateur ID {user_id}")
        update_data = data.model_dump(exclude_unset=True)
        for key, value in update_data.items():
            setattr(user, key, value)
        await self.commit()
        await self.refresh(user)
        logger.info(f"Utilisateur ID {user_id} mis à jour")
        
        # Créer manuellement la réponse pour éviter les erreurs de greenlet
        user_data = {
            "id": user.id,
            "nom": user.nom,
            "prenom": user.prenom,
            "email": user.email,
            "role": user.role,
            "civilite": user.civilite,
            "date_naissance": user.date_naissance,
            "telephone_mobile": user.telephone_mobile,
            "telephone": user.telephone,
            "nationalite": user.nationalite,
            "actif": user.actif,
            "email_verified": user.email_verified,
            "last_login": user.last_login,
            "situation_professionnelle": user.situation_professionnelle,
            "experience_professionnelle_en_mois": user.experience_professionnelle_en_mois,
            "employeur": user.employeur,
            "categorie_socio_professionnelle": user.categorie_socio_professionnelle,
            "fonction": user.fonction,
            "dernier_diplome_obtenu": user.dernier_diplome_obtenu,
            "date_obtention_dernier_diplome": user.date_obtention_dernier_diplome,
            "created_at": user.created_at,
            "updated_at": user.updated_at,
            "adresses": None,  # Pas chargé pour la mise à jour
            "dossiers": None,  # Pas chargé pour la mise à jour
            "reclamations": None  # Pas chargé pour la mise à jour
        }
        
        return UtilisateurResponse(**user_data)

    async def delete(self, user_id: int):
        # Récupérer directement l'utilisateur depuis la base de données
        result = await self.session.execute(select(Utilisateur).where(Utilisateur.id == user_id))
        user = result.scalar_one_or_none()
        
        if not user:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"Utilisateur avec ID {user_id} non trouvé.")
        
        logger.info(f"Suppression de l'utilisateur ID {user_id}")
        await self.session.delete(user)
        await self.commit()
        logger.info(f"Utilisateur ID {user_id} supprimé")

    async def get_all(self, skip: int = 0, limit: int = 100) -> List[UtilisateurResponse]:
        logger.info(f"Récupération de tous les utilisateurs (skip={skip}, limit={limit})")
        result = await self.session.execute(select(Utilisateur).offset(skip).limit(limit))
        users = result.scalars().all()
        
        # Pour la liste, on ne charge que les informations de base sans les relations
        # pour éviter les erreurs de greenlet
        user_responses = []
        for user in users:
            user_data = {
                "id": user.id,
                "nom": user.nom,
                "prenom": user.prenom,
                "email": user.email,
                "role": user.role,
                "civilite": user.civilite,
                "date_naissance": user.date_naissance,
                "telephone_mobile": user.telephone_mobile,
                "telephone": user.telephone,
                "nationalite": user.nationalite,
                "actif": user.actif,
                "email_verified": user.email_verified,
                "last_login": user.last_login,
                "situation_professionnelle": user.situation_professionnelle,
                "experience_professionnelle_en_mois": user.experience_professionnelle_en_mois,
                "employeur": user.employeur,
                "categorie_socio_professionnelle": user.categorie_socio_professionnelle,
                "fonction": user.fonction,
                "dernier_diplome_obtenu": user.dernier_diplome_obtenu,
                "date_obtention_dernier_diplome": user.date_obtention_dernier_diplome,
                "created_at": user.created_at,
                "updated_at": user.updated_at,
                "adresses": None,  # Pas chargé pour la liste
                "dossiers": None,  # Pas chargé pour la liste
                "reclamations": None  # Pas chargé pour la liste
            }
            user_responses.append(UtilisateurResponse(**user_data))
        
        return user_responses
    
    async def change_password(self, user_id: int, current_password: str, new_password: str) -> bool:
        """Permet à un utilisateur de changer son mot de passe"""
        # Récupérer directement l'utilisateur sans passer par get_by_id
        result = await self.session.execute(select(Utilisateur).where(Utilisateur.id == user_id))
        user = result.scalar_one_or_none()
        
        if not user:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Utilisateur non trouvé"
            )
        
        # Vérifier l'ancien mot de passe
        if not verify_password(current_password, user.password):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Mot de passe actuel incorrect"
            )
        
        # Hacher et sauvegarder le nouveau mot de passe
        hashed_new_password = hash_password(new_password)
        user.password = hashed_new_password
        await self.commit()
        await self.refresh(user)
        
        logger.info(f"Mot de passe changé pour l'utilisateur ID {user_id}")
        return True
    
    async def reset_password_by_email(self, email: str) -> str:
        """Réinitialise le mot de passe d'un utilisateur par email et retourne le nouveau mot de passe"""
        # Rechercher l'utilisateur par email
        query = select(Utilisateur).where(Utilisateur.email == email)
        result = await self.session.execute(query)
        user = result.scalar_one_or_none()
        
        if not user:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Aucun utilisateur trouvé avec cet email"
            )
        
        # Générer un nouveau mot de passe sécurisé
        new_password = generate_secure_password()
        hashed_password = hash_password(new_password)
        
        # Mettre à jour le mot de passe
        user.password = hashed_password
        await self.commit()
        await self.refresh(user)
        
        logger.info(f"Mot de passe réinitialisé pour l'utilisateur {email} (ID: {user.id}, mot de pass : {new_password})")
        
        # Pour l'instant, on le retourne (à supprimer en production)
        return new_password
    
    async def authenticate_user(self, email: str, password: str) -> Optional[Utilisateur]:
        """Authentifie un utilisateur avec son email et mot de passe"""
        logger.info(f"Tentative d'authentification pour l'email: {email}")
        
        # Rechercher l'utilisateur par email
        query = select(Utilisateur).where(Utilisateur.email == email)
        result = await self.session.execute(query)
        user = result.scalar_one_or_none()
        
        if not user:
            logger.warning(f"Tentative d'authentification avec un email inexistant: {email}")
            return None
        
        # Vérifier le mot de passe
        if not verify_password(password, user.password):
            logger.warning(f"Mot de passe incorrect pour l'utilisateur: {email}")
            return None
        
        # Vérifier que le compte est actif
        if not user.actif:
            logger.warning(f"Tentative d'authentification avec un compte inactif: {email}")
            return None
        
        # Mettre à jour la dernière connexion
        user.last_login = datetime.utcnow()
        await self.commit()
        await self.refresh(user)
        
        logger.info(f"Authentification réussie pour l'utilisateur: {email}")
        return user
    
    async def login_user(self, email: str, password: str) -> LoginResponse:
        """Authentifie un utilisateur et retourne une réponse de connexion complète"""
        from src.api.schema import LoginResponse, UtilisateurLight
        from src.api.security import create_access_token
        
        # Authentifier l'utilisateur
        user = await self.authenticate_user(email, password)
        
        if not user:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Email ou mot de passe incorrect",
                headers={"WWW-Authenticate": "Bearer"},
            )
        
        # Créer le token d'accès
        access_token_expires = timedelta(minutes=30)
        access_token = create_access_token(
            data={"sub": user.email, "user_id": user.id, "role": user.role.value},
            expires_delta=access_token_expires
        )
        
        # Créer la réponse utilisateur
        user_response = UtilisateurLight(
            id=user.id,
            nom=user.nom,
            prenom=user.prenom,
            email=user.email,
            nationalite=user.nationalite,
            role=user.role
        )
        
        # Retourner la réponse de connexion
        return LoginResponse(
            access_token=access_token,
            token_type="bearer",
            user=user_response,
            message="Connexion réussie"
        )

# ────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────
# CENTRE (Optimisé: Ajout de champs pour gestion des places, prérequis, durée en Integer)
# ────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────
class CentreService(BaseService):
    async def create(self, data: CentreFormationCreate) -> CentreFormationResponse:
        logger.info("Création d'un centre de formation")
        centre = CentreFormation(**data.model_dump())
        self.session.add(centre)
        await self.commit()
        await self.refresh(centre)
        logger.info(f"Centre créé avec ID {centre.id}")
        
        # Créer manuellement la réponse pour éviter les erreurs de greenlet avec les relations
        centre_data = {
            "id": centre.id,
            "nom": centre.nom,
            "adresse": centre.adresse,
            "ville": centre.ville,
            "code_postal": centre.code_postal,
            "pays": centre.pays,
            "created_at": centre.created_at,
            "updated_at": centre.updated_at,
            "sessions": []  # Pas encore de sessions pour un nouveau centre
        }
        
        return CentreFormationResponse(**centre_data)

    async def get_by_id(self, centre_id: int, load_relations: bool = True) -> Optional[CentreFormationResponse]:
        query = select(CentreFormation).where(CentreFormation.id == centre_id)
        if load_relations:
            query = query.options(selectinload(CentreFormation.sessions).joinedload(SessionFormation.formation))
        try:
            logger.info(f"Récupération du centre ID {centre_id}")
            result = await self.session.execute(query)
            centre = result.scalar_one()
            
            # Créer manuellement la réponse pour éviter les erreurs de greenlet
            centre_data = {
                "id": centre.id,
                "nom": centre.nom,
                "adresse": centre.adresse,
                "ville": centre.ville,
                "code_postal": centre.code_postal,
                "pays": centre.pays,
                "created_at": centre.created_at,
                "updated_at": centre.updated_at,
                "sessions": centre.sessions if load_relations else []
            }
            
            return CentreFormationResponse(**centre_data)
        except NoResultFound:
            logger.warning(f"Centre ID {centre_id} non trouvé")
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"Centre avec ID {centre_id} non trouvé.")

    async def update(self, centre_id: int, data: CentreFormationUpdate) -> CentreFormationResponse:
        # Récupérer directement le centre depuis la base de données
        result = await self.session.execute(select(CentreFormation).where(CentreFormation.id == centre_id))
        centre = result.scalar_one_or_none()
        
        if not centre:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"Centre avec ID {centre_id} non trouvé.")
        
        logger.info(f"Mise à jour du centre ID {centre_id}")
        update_data = data.model_dump(exclude_unset=True)
        for key, value in update_data.items():
            setattr(centre, key, value)
        await self.commit()
        await self.refresh(centre)
        logger.info(f"Centre ID {centre_id} mis à jour")
        
        # Créer manuellement la réponse pour éviter les erreurs de greenlet
        centre_data = {
            "id": centre.id,
            "nom": centre.nom,
            "adresse": centre.adresse,
            "ville": centre.ville,
            "code_postal": centre.code_postal,
            "pays": centre.pays,
            "created_at": centre.created_at,
            "updated_at": centre.updated_at,
            "sessions": []  # Pas chargé pour la mise à jour
        }
        
        return CentreFormationResponse(**centre_data)

    async def delete(self, centre_id: int):
        # Récupérer directement le centre depuis la base de données
        result = await self.session.execute(select(CentreFormation).where(CentreFormation.id == centre_id))
        centre = result.scalar_one_or_none()
        
        if not centre:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"Centre avec ID {centre_id} non trouvé.")
        
        logger.info(f"Suppression du centre ID {centre_id}")
        await self.session.delete(centre)
        await self.commit()
        logger.info(f"Centre ID {centre_id} supprimé")

    async def get_all(self, skip: int = 0, limit: int = 100) -> List[CentreFormationResponse]:
        logger.info(f"Récupération de tous les centres (skip={skip}, limit={limit})")
        
        # Charger les centres avec leurs relations (sessions et formations)
        query = select(CentreFormation).options(
            selectinload(CentreFormation.sessions).joinedload(SessionFormation.formation)
        ).offset(skip).limit(limit)
        
        result = await self.session.execute(query)
        centres = result.scalars().all()
        
        # Créer les réponses avec toutes les informations chargées
        centre_responses = []
        for centre in centres:
            # Debug: afficher les valeurs récupérées
            logger.info(f"Centre {centre.id}: adresse={centre.adresse}, ville={centre.ville}, code_postal={centre.code_postal}, pays={centre.pays}")
            
            centre_data = {
                "id": centre.id,
                "nom": centre.nom,
                "adresse": centre.adresse,
                "ville": centre.ville,
                "code_postal": centre.code_postal,
                "pays": centre.pays,
                "created_at": centre.created_at,
                "updated_at": centre.updated_at,
                "sessions": centre.sessions  # Maintenant chargé avec les relations
            }
            
            # Debug: afficher le dictionnaire créé
            logger.info(f"Centre data créé: {centre_data}")
            
            centre_response = CentreFormationResponse(**centre_data)
            centre_responses.append(centre_response)
        
        return centre_responses



# ────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────
# FORMATION  (Optimisé: Ajout de champs pour gestion des places, prérequis, durée en Integer)
# ────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────

class FormationService(BaseService):
    async def create(self, data: FormationCreate) -> FormationResponse:
        logger.info("Création d'une formation")
        # FormationCreate n'a pas de modules ni information_descriptive, donc on utilise directement model_dump()
        formation = Formation(**data.model_dump())
        
        self.session.add(formation)
        await self.commit()
        await self.refresh(formation)
        logger.info(f"Formation créée avec ID {formation.id}")
        
        # Créer manuellement la réponse pour éviter les erreurs de greenlet avec les relations
        formation_data = {
            "id": formation.id,
            "titre": formation.titre,
            "specialite": formation.specialite,
            "fiche_info": formation.fiche_info,
            "description": formation.description,
            "duree_heures": formation.duree_heures,
            "type_formation": formation.type_formation,
            "modalite": formation.modalite,
            "pre_requis": formation.pre_requis,
            "frais_inscription": formation.frais_inscription,
            "frais_formation": formation.frais_formation,
            "devise": formation.devise,
            "created_at": formation.created_at,
            "updated_at": formation.updated_at,
            "sessions": [],  # Pas encore de sessions pour une nouvelle formation
            "modules": [],   # Pas encore de modules pour une nouvelle formation
            "dossiers": [],  # Pas encore de dossiers pour une nouvelle formation
            "information_descriptive": None  # Pas encore d'informations descriptives
        }
        
        return FormationResponse(**formation_data)

    async def get_by_id(self, formation_id: int, load_relations: bool = True) -> Optional[FormationResponse]:
        query = select(Formation).where(Formation.id == formation_id)
        if load_relations:
            query = query.options(
                selectinload(Formation.sessions).joinedload(SessionFormation.centre),
                selectinload(Formation.modules).selectinload(Module.ressources),
                selectinload(Formation.dossiers).joinedload(DossierCandidature.utilisateur),
                joinedload(Formation.information_descriptive)  # Use joinedload for one-to-one relationship
            )
        try:
            logger.info(f"Récupération de la formation ID {formation_id}")
            result = await self.session.execute(query)
            formation = result.scalar_one()
            
            # Créer manuellement la réponse pour éviter les erreurs de greenlet avec les relations
            formation_data = {
                "id": formation.id,
                "titre": formation.titre,
                "specialite": formation.specialite,
                "fiche_info": formation.fiche_info,
                "description": formation.description,
                "duree_heures": formation.duree_heures,
                "type_formation": formation.type_formation,
                "modalite": formation.modalite,
                "pre_requis": formation.pre_requis,
                "frais_inscription": formation.frais_inscription,
                "frais_formation": formation.frais_formation,
                "devise": formation.devise,
                "created_at": formation.created_at,
                "updated_at": formation.updated_at,
                "sessions": formation.sessions if load_relations else [],
                "modules": formation.modules if load_relations else [],
                "dossiers": formation.dossiers if load_relations else [],
                "information_descriptive": formation.information_descriptive if load_relations else None
            }
            
            return FormationResponse(**formation_data)
        except NoResultFound:
            logger.warning(f"Formation ID {formation_id} non trouvée")
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"Formation avec ID {formation_id} non trouvée.")

    async def update(self, formation_id: int, data: FormationUpdate) -> FormationResponse:
        # Récupérer la formation avec ses relations pour éviter les erreurs de greenlet
        query = select(Formation).where(Formation.id == formation_id).options(
            selectinload(Formation.sessions),
            selectinload(Formation.modules),
            selectinload(Formation.dossiers),
            joinedload(Formation.information_descriptive)
        )
        result = await self.session.execute(query)
        formation = result.scalar_one_or_none()
        
        if not formation:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"Formation avec ID {formation_id} non trouvée.")
        
        logger.info(f"Mise à jour de la formation ID {formation_id}")
        update_data = data.model_dump(exclude_unset=True)
        for key, value in update_data.items():
            setattr(formation, key, value)
        
        await self.commit()
        await self.refresh(formation)
        logger.info(f"Formation ID {formation_id} mise à jour")
        
        # Créer manuellement la réponse pour éviter les erreurs de greenlet avec les relations
        formation_data = {
            "id": formation.id,
            "titre": formation.titre,
            "specialite": formation.specialite,
            "fiche_info": formation.fiche_info,
            "description": formation.description,
            "duree_heures": formation.duree_heures,
            "type_formation": formation.type_formation,
            "modalite": formation.modalite,
            "pre_requis": formation.pre_requis,
            "frais_inscription": formation.frais_inscription,
            "frais_formation": formation.frais_formation,
            "devise": formation.devise,
            "created_at": formation.created_at,
            "updated_at": formation.updated_at,
            "sessions": formation.sessions,
            "modules": formation.modules,
            "dossiers": formation.dossiers,
            "information_descriptive": formation.information_descriptive
        }
        
        return FormationResponse(**formation_data)

    async def delete(self, formation_id: int):
        # Récupérer directement la formation depuis la base de données
        result = await self.session.execute(select(Formation).where(Formation.id == formation_id))
        formation = result.scalar_one_or_none()
        
        if not formation:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"Formation avec ID {formation_id} non trouvée.")
        
        logger.info(f"Suppression de la formation ID {formation_id}")
        await self.session.delete(formation)
        await self.commit()
        logger.info(f"Formation ID {formation_id} supprimée")

    async def get_all(self, skip: int = 0, limit: int = 100) -> List[FormationResponse]:
        logger.info(f"Récupération de toutes les formations (skip={skip}, limit={limit})")
        
        # Charger les formations avec leurs relations de base
        query = select(Formation).options(
            selectinload(Formation.sessions),
            selectinload(Formation.modules),
            selectinload(Formation.dossiers),
            joinedload(Formation.information_descriptive)  # Use joinedload for one-to-one relationship
        ).offset(skip).limit(limit)
        
        result = await self.session.execute(query)
        formations = result.scalars().all()
        
        # Créer les réponses avec toutes les informations chargées
        formation_responses = []
        for formation in formations:
            # Créer manuellement la réponse pour éviter les erreurs de greenlet
            formation_data = {
                "id": formation.id,
                "titre": formation.titre,
                "specialite": formation.specialite,
                "fiche_info": formation.fiche_info,
                "description": formation.description,
                "duree_heures": formation.duree_heures,
                "type_formation": formation.type_formation,
                "modalite": formation.modalite,
                "pre_requis": formation.pre_requis,
                "frais_inscription": formation.frais_inscription,
                "frais_formation": formation.frais_formation,
                "devise": formation.devise,
                "created_at": formation.created_at,
                "updated_at": formation.updated_at,
                "sessions": formation.sessions,
                "modules": formation.modules,
                "dossiers": formation.dossiers,
                "information_descriptive": InformationDescriptiveResponse.model_validate(formation.information_descriptive, from_attributes=True) if formation.information_descriptive else None
            }
            
            formation_response = FormationResponse(**formation_data)
            formation_responses.append(formation_response)
        
        return formation_responses

# ────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────
# SESSION  (Optimisé: Ajout de champs pour gestion des places, prérequis, durée en Integer)
# ────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────

class SessionFormationService(BaseService):
    async def create(self, data: SessionFormationCreate) -> SessionFormationResponse:
        """Crée une nouvelle session de formation avec validation des données"""
        logger.info("Création d'une session de formation")
        
        # Validation des données d'entrée
        if data.date_debut and data.date_fin and data.date_debut > data.date_fin:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="La date de début ne peut pas être postérieure à la date de fin"
            )
        
        if data.date_limite_inscription and data.date_debut:
            if data.date_limite_inscription > data.date_debut:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="La date limite d'inscription ne peut pas être postérieure à la date de début"
                )
        
        # Vérifier que la formation existe
        formation_result = await self.session.execute(
            select(Formation).where(Formation.id == data.formation_id)
        )
        formation = formation_result.scalar_one_or_none()
        if not formation:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Formation avec ID {data.formation_id} non trouvée"
            )
        
        # Vérifier que le centre existe si spécifié
        if data.centre_id:
            centre_result = await self.session.execute(
                select(CentreFormation).where(CentreFormation.id == data.centre_id)
            )
            centre = centre_result.scalar_one_or_none()
            if not centre:
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail=f"Centre avec ID {data.centre_id} non trouvé"
                )
        
        # Créer la session avec les données validées
        session_data = data.model_dump()
        
        # Convertir les enums vers les valeurs de la base de données
        if 'statut' in session_data and session_data['statut']:
            if session_data['statut'] == StatutSessionEnum.OUVERTE:
                session_data['statut'] = 'ouverte'
            elif session_data['statut'] == StatutSessionEnum.FERMEE:
                session_data['statut'] = 'fermée'
            elif session_data['statut'] == StatutSessionEnum.ANNULEE:
                session_data['statut'] = 'annulée'
        
        if 'modalite' in session_data and session_data['modalite']:
            if session_data['modalite'] == ModaliteEnum.PRESENTIEL:
                session_data['modalite'] = 'PRESENTIEL'
            elif session_data['modalite'] == ModaliteEnum.EN_LIGNE:
                session_data['modalite'] = 'EN_LIGNE'
        
        session_form = SessionFormation(**session_data)
        
        self.session.add(session_form)
        await self.commit()
        await self.refresh(session_form)
        
        logger.info(f"Session créée avec ID {session_form.id}")
        
        # Retourner la réponse avec les relations chargées
        return await self.get_by_id(session_form.id, load_relations=True)

    async def get_by_id(self, session_id: int, load_relations: bool = True) -> Optional[SessionFormationResponse]:
        """Récupère une session de formation par son ID avec option de chargement des relations"""
        query = select(SessionFormation).where(SessionFormation.id == session_id)
        
        if load_relations:
            query = query.options(
                joinedload(SessionFormation.formation),
                joinedload(SessionFormation.centre),
                selectinload(SessionFormation.dossiers).joinedload(DossierCandidature.utilisateur)
            )
        
        try:
            logger.info(f"Récupération de la session ID {session_id}")
            result = await self.session.execute(query)
            session_form = result.scalar_one()
            
            if not session_form:
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail=f"Session de formation avec ID {session_id} non trouvée"
                )
            
            return SessionFormationResponse.model_validate(session_form, from_attributes=True)
            
        except HTTPException:
            raise
        except Exception as e:
            logger.error(f"Erreur lors de la récupération de la session {session_id}: {str(e)}")
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Erreur lors de la récupération de la session"
            )

    async def update(self, session_id: int, data: SessionFormationUpdate) -> SessionFormationResponse:
        """Met à jour une session de formation existante"""
        logger.info(f"Mise à jour de la session ID {session_id}")
        
        # Récupérer la session existante
        result = await self.session.execute(
            select(SessionFormation).where(SessionFormation.id == session_id)
        )
        session_form = result.scalar_one_or_none()
        
        if not session_form:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Session de formation avec ID {session_id} non trouvée"
            )
        
        # Validation des données de mise à jour
        update_data = data.model_dump(exclude_unset=True)
        
        # Validation des dates si elles sont fournies
        if 'date_debut' in update_data and 'date_fin' in update_data:
            if update_data['date_debut'] and update_data['date_fin']:
                if update_data['date_debut'] > update_data['date_fin']:
                    raise HTTPException(
                        status_code=status.HTTP_400_BAD_REQUEST,
                        detail="La date de début ne peut pas être postérieure à la date de fin"
                    )
        
        if 'date_limite_inscription' in update_data and 'date_debut' in update_data:
            if update_data['date_limite_inscription'] and update_data['date_debut']:
                if update_data['date_limite_inscription'] > update_data['date_debut']:
                    raise HTTPException(
                        status_code=status.HTTP_400_BAD_REQUEST,
                        detail="La date limite d'inscription ne peut pas être postérieure à la date de début"
                    )
        
        # Vérifier que la formation existe si elle est mise à jour
        if 'formation_id' in update_data:
            formation_result = await self.session.execute(
                select(Formation).where(Formation.id == update_data['formation_id'])
            )
            formation = formation_result.scalar_one_or_none()
            if not formation:
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail=f"Formation avec ID {update_data['formation_id']} non trouvée"
                )
        
        # Vérifier que le centre existe si il est mis à jour
        if 'centre_id' in update_data and update_data['centre_id']:
            centre_result = await self.session.execute(
                select(CentreFormation).where(CentreFormation.id == update_data['centre_id'])
            )
            centre = centre_result.scalar_one_or_none()
            if not centre:
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail=f"Centre avec ID {update_data['centre_id']} non trouvé"
                )
        
        # Appliquer les mises à jour
        for key, value in update_data.items():
            setattr(session_form, key, value)
        
        await self.commit()
        await self.refresh(session_form)
        
        logger.info(f"Session ID {session_id} mise à jour")
        
        # Retourner la réponse mise à jour avec les relations
        return await self.get_by_id(session_id, load_relations=True)

    async def delete(self, session_id: int):
        """Supprime une session de formation"""
        logger.info(f"Suppression de la session ID {session_id}")
        
        # Récupérer la session
        result = await self.session.execute(
            select(SessionFormation).where(SessionFormation.id == session_id)
        )
        session_form = result.scalar_one_or_none()
        
        if not session_form:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Session de formation avec ID {session_id} non trouvée"
            )
        
        # Vérifier s'il y a des dossiers de candidature
        if session_form.dossiers:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Impossible de supprimer une session avec des dossiers de candidature"
            )
        
        await self.session.delete(session_form)
        await self.commit()
        
        logger.info(f"Session ID {session_id} supprimée")

    async def change_statut(self, session_id: int, data: SessionStatutUpdate) -> SessionFormationResponse:
        """Change le statut d'une session de formation avec validation métier"""
        logger.info(f"Changement de statut de la session ID {session_id} vers {data.statut}")
        
        # Récupérer la session avec ses relations
        result = await self.session.execute(
            select(SessionFormation).options(
                selectinload(SessionFormation.dossiers)
            ).where(SessionFormation.id == session_id)
        )
        session_form = result.scalar_one_or_none()
        
        if not session_form:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Session de formation avec ID {session_id} non trouvée"
            )
        
        # Validation métier selon le nouveau statut
        if data.statut == StatutSessionEnum.ANNULEE:
            # Vérifier s'il y a des dossiers acceptés
            if session_form.dossiers:
                accepted_dossiers = [
                    d for d in session_form.dossiers 
                    if d.statut == StatutCandidatureEnum.ACCEPTÉE
                ]
                if accepted_dossiers:
                    raise HTTPException(
                        status_code=status.HTTP_400_BAD_REQUEST,
                        detail="Impossible d'annuler une session avec des candidatures acceptées"
                    )
        
        elif data.statut == StatutSessionEnum.FERMEE:
            # Vérifier si la date limite d'inscription est dépassée
            if session_form.date_limite_inscription:
                from datetime import date
                if session_form.date_limite_inscription > date.today():
                    raise HTTPException(
                        status_code=status.HTTP_400_BAD_REQUEST,
                        detail="Impossible de fermer une session avant la date limite d'inscription"
                    )
        
        # Mettre à jour le statut
        session_form.statut = data.statut
        await self.commit()
        await self.refresh(session_form)
        
        logger.info(f"Statut de la session ID {session_id} changé vers {data.statut}")
        
        # Retourner la session mise à jour
        return await self.get_by_id(session_id, load_relations=True)

    async def change_modalite(self, session_id: int, data: SessionModaliteUpdate) -> SessionFormationResponse:
        """Change la modalité d'une session de formation avec validation métier"""
        logger.info(f"Changement de modalité de la session ID {session_id} vers {data.modalite}")
        
        # Récupérer la session avec ses relations
        result = await self.session.execute(
            select(SessionFormation).options(
                selectinload(SessionFormation.dossiers).selectinload(DossierCandidature.paiements)
            ).where(SessionFormation.id == session_id)
        )
        session_form = result.scalar_one_or_none()
        
        if not session_form:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Session de formation avec ID {session_id} non trouvée"
            )
        
        # Validation métier : vérifier s'il y a des paiements effectués
        if session_form.dossiers:
            for dossier in session_form.dossiers:
                if dossier.paiements:
                    # Vérifier s'il y a des paiements réussis
                    successful_payments = [
                        p for p in dossier.paiements 
                        if p.statut == StatutPaiementEnum.ACCEPTED
                    ]
                    if successful_payments:
                        raise HTTPException(
                            status_code=status.HTTP_400_BAD_REQUEST,
                            detail="Impossible de changer la modalité d'une session avec des paiements effectués"
                        )
        
        # Mettre à jour la modalité
        session_form.modalite = data.modalite
        await self.commit()
        await self.refresh(session_form)
        
        logger.info(f"Modalité de la session ID {session_id} changée vers {data.modalite}")
        
        # Retourner la session mise à jour
        return await self.get_by_id(session_id, load_relations=True)

    async def get_all(self, skip: int = 0, limit: int = 100, 
                     formation_id: Optional[int] = None,
                     centre_id: Optional[int] = None,
                     statut: Optional[StatutSessionEnum] = None) -> List[SessionFormationResponse]:
        """Récupère toutes les sessions de formation avec filtres et pagination"""
        logger.info(f"Récupération de toutes les sessions (skip: {skip}, limit: {limit})")
        
        # Construire la requête de base
        query = select(SessionFormation).options(
            joinedload(SessionFormation.formation),
            joinedload(SessionFormation.centre),
            selectinload(SessionFormation.dossiers)
        )
        
        # Appliquer les filtres
        if formation_id:
            query = query.where(SessionFormation.formation_id == formation_id)
        
        if centre_id:
            query = query.where(SessionFormation.centre_id == centre_id)
        
        if statut:
            query = query.where(SessionFormation.statut == statut)
        
        # Appliquer la pagination
        query = query.offset(skip).limit(limit)
        
        # Exécuter la requête
        result = await self.session.execute(query)
        sessions = result.scalars().all()
        
        # Créer les réponses
        session_responses = []
        for session in sessions:
            try:
                session_response = SessionFormationResponse.model_validate(session, from_attributes=True)
                session_responses.append(session_response)
            except Exception as e:
                logger.error(f"Erreur lors de la validation de la session {session.id}: {str(e)}")
                continue
        
        logger.info(f"Récupération de {len(session_responses)} sessions")
        return session_responses

    async def get_sessions_by_formation(self, formation_id: int) -> List[SessionFormationResponse]:
        """Récupère toutes les sessions d'une formation spécifique"""
        logger.info(f"Récupération des sessions pour la formation {formation_id}")
        
        query = select(SessionFormation).options(
            joinedload(SessionFormation.centre),
            selectinload(SessionFormation.dossiers)
        ).where(SessionFormation.formation_id == formation_id)
        
        result = await self.session.execute(query)
        sessions = result.scalars().all()
        
        session_responses = []
        for session in sessions:
            try:
                session_response = SessionFormationResponse.model_validate(session, from_attributes=True)
                session_responses.append(session_response)
            except Exception as e:
                logger.error(f"Erreur lors de la validation de la session {session.id}: {str(e)}")
                continue
        
        return session_responses

    async def get_sessions_by_centre(self, centre_id: int) -> List[SessionFormationResponse]:
        """Récupère toutes les sessions d'un centre spécifique"""
        logger.info(f"Récupération des sessions pour le centre {centre_id}")
        
        query = select(SessionFormation).options(
            joinedload(SessionFormation.formation),
            selectinload(SessionFormation.dossiers)
        ).where(SessionFormation.centre_id == centre_id)
        
        result = await self.session.execute(query)
        sessions = result.scalars().all()
        
        session_responses = []
        for session in sessions:
            try:
                session_response = SessionFormationResponse.model_validate(session, from_attributes=True)
                session_responses.append(session_response)
            except Exception as e:
                logger.error(f"Erreur lors de la validation de la session {session.id}: {str(e)}")
                continue
        
        return session_responses

    async def check_availability(self, session_id: int) -> dict:
        """Vérifie la disponibilité d'une session (places disponibles, dates, etc.)"""
        logger.info(f"Vérification de la disponibilité de la session {session_id}")
        
        result = await self.session.execute(
            select(SessionFormation).options(
                selectinload(SessionFormation.dossiers)
            ).where(SessionFormation.id == session_id)
        )
        session = result.scalar_one_or_none()
        
        if not session:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Session de formation avec ID {session_id} non trouvée"
            )
        
        # Calculer les places occupées
        places_occupees = len(session.dossiers) if session.dossiers else 0
        places_disponibles = session.places_disponibles or 0
        places_restantes = max(0, places_disponibles - places_occupees)
        
        # Vérifier les dates
        from datetime import date
        aujourd_hui = date.today()
        
        inscriptions_ouvertes = True
        if session.date_limite_inscription:
            inscriptions_ouvertes = aujourd_hui <= session.date_limite_inscription
        
        session_commencee = False
        if session.date_debut:
            session_commencee = aujourd_hui >= session.date_debut
        
        return {
            "session_id": session_id,
            "places_disponibles": places_disponibles,
            "places_occupees": places_occupees,
            "places_restantes": places_restantes,
            "inscriptions_ouvertes": inscriptions_ouvertes,
            "session_commencee": session_commencee,
            "statut": session.statut,
            "date_limite_inscription": session.date_limite_inscription,
            "date_debut": session.date_debut,
            "date_fin": session.date_fin
        }

# ────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────
# MODULE  (Optimisé: Ajout d'index sur ordre, suppression de titre redondant si URL suffit)
# ────────────────────────────────────────────────────────────────────────────
class ModuleService(BaseService):
    async def create(self, data: ModuleCreate, formation_id: Optional[int] = None) -> ModuleResponse:
        if formation_id:
            data.formation_id = formation_id
        logger.info("Création d'un module")
        module = Module(**data.model_dump(exclude={"ressources"}))
        if data.ressources:
            for res_data in data.ressources:
                res = Ressource(**res_data.model_dump(), module=module)
                module.ressources.append(res)
        self.session.add(module)
        await self.commit()
        await self.refresh(module)
        logger.info(f"Module créé avec ID {module.id}")
        return ModuleResponse.model_validate(module, from_attributes=True)

    async def get_by_id(self, module_id: int, load_relations: bool = True) -> Optional[ModuleResponse]:
        query = select(Module).where(Module.id == module_id)
        if load_relations:
            query = query.options(
                joinedload(Module.formation).selectinload(Formation.sessions),
                selectinload(Module.ressources)
            )
        try:
            logger.info(f"Récupération du module ID {module_id}")
            result = await self.session.execute(query)
            module = result.scalar_one()
            return ModuleResponse.model_validate(module, from_attributes=True)
        except NoResultFound:
            logger.warning(f"Module ID {module_id} non trouvé")
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"Module avec ID {module_id} non trouvé.")

    async def update(self, module_id: int, data: ModuleUpdate) -> ModuleResponse:
        # Récupérer directement le module depuis la base de données
        result = await self.session.execute(select(Module).where(Module.id == module_id))
        module = result.scalar_one_or_none()
        
        if not module:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"Module avec ID {module_id} non trouvé.")
        
        logger.info(f"Mise à jour du module ID {module_id}")
        update_data = data.model_dump(exclude_unset=True, exclude={"ressources"})
        for key, value in update_data.items():
            setattr(module, key, value)
        if data.ressources:
            module.ressources = [Ressource(**res.model_dump(), module=module) for res in data.ressources]
        await self.commit()
        await self.refresh(module)
        logger.info(f"Module ID {module_id} mis à jour")
        return ModuleResponse.model_validate(module, from_attributes=True)

    async def delete(self, module_id: int):
        # Récupérer directement le module depuis la base de données
        result = await self.session.execute(select(Module).where(Module.id == module_id))
        module = result.scalar_one_or_none()
        
        if not module:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"Module avec ID {module_id} non trouvé.")
        
        logger.info(f"Suppression du module ID {module_id}")
        await self.session.delete(module)
        await self.commit()
        logger.info(f"Module ID {module_id} supprimé")

# ────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────
# RESSOURCE  (Optimisé: Ajout d'index sur ordre, suppression de titre redondant si URL suffit)
# ────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────

class RessourceService(BaseService):
    async def create(self, data: RessourceCreate, module_id: Optional[int] = None) -> RessourceResponse:
        if module_id:
            data.module_id = module_id
        logger.info("Création d'une ressource")
        ressource = Ressource(**data.model_dump())
        self.session.add(ressource)
        await self.commit()
        await self.refresh(ressource)
        logger.info(f"Ressource créée avec ID {ressource.id}")
        return RessourceResponse.model_validate(ressource, from_attributes=True)

    async def get_by_id(self, ressource_id: int, load_relations: bool = True) -> Optional[RessourceResponse]:
        query = select(Ressource).where(Ressource.id == ressource_id)
        if load_relations:
            query = query.options(joinedload(Ressource.module).joinedload(Module.formation))
        try:
            logger.info(f"Récupération de la ressource ID {ressource_id}")
            result = await self.session.execute(query)
            ressource = result.scalar_one()
            return RessourceResponse.model_validate(ressource, from_attributes=True)
        except NoResultFound:
            logger.warning(f"Ressource ID {ressource_id} non trouvée")
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"Ressource avec ID {ressource_id} non trouvée.")

    async def update(self, ressource_id: int, data: RessourceUpdate) -> RessourceResponse:
        # Récupérer directement la ressource depuis la base de données
        result = await self.session.execute(select(Ressource).where(Ressource.id == ressource_id))
        ressource = result.scalar_one_or_none()
        
        if not ressource:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"Ressource avec ID {ressource_id} non trouvée.")
        
        logger.info(f"Mise à jour de la ressource ID {ressource_id}")
        update_data = data.model_dump(exclude_unset=True)
        for key, value in update_data.items():
            setattr(ressource, key, value)
        await self.commit()
        await self.refresh(ressource)
        logger.info(f"Ressource ID {ressource_id} mise à jour")
        return RessourceResponse.model_validate(ressource, from_attributes=True)

    async def delete(self, ressource_id: int):
        # Récupérer directement la ressource depuis la base de données
        result = await self.session.execute(select(Ressource).where(Ressource.id == ressource_id))
        ressource = result.scalar_one_or_none()
        
        if not ressource:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"Ressource avec ID {ressource_id} non trouvée.")
        
        logger.info(f"Suppression de la ressource ID {ressource_id}")
        await self.session.delete(ressource)
        await self.commit()
        logger.info(f"Ressource ID {ressource_id} supprimée")

# ────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────
# DOSSIER CANDIDATURE (Optimisé: Ajout de date_soumission, motif_refus; frais hérités mais surchargables)
# ────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────
class DossierService(BaseService):
    async def create(self, data: DossierCandidatureCreate) -> DossierCandidatureResponse:
        logger.info("Création d'un dossier de candidature")
        dossier = DossierCandidature(**data.model_dump(exclude={"pieces_jointes", "paiements", "reclamations"}))
        if data.pieces_jointes:
            for pj_data in data.pieces_jointes:
                pj = PieceJointe(**pj_data.model_dump(), dossier=dossier)
                dossier.pieces_jointes.append(pj)
        if data.paiements:
            for pay_data in data.paiements:
                pay = Paiement(**pay_data.model_dump(), dossier=dossier)
                dossier.paiements.append(pay)
        if data.reclamations:
            for rec_data in data.reclamations:
                rec = Reclamation(**rec_data.model_dump(), dossier=dossier)
                dossier.reclamations.append(rec)
        self.session.add(dossier)
        await self.commit()
        await self.refresh(dossier)
        response = DossierCandidatureResponse.model_validate(dossier, from_attributes=True)
        response.total_paye = dossier.total_paye
        response.reste_a_payer_inscription = dossier.reste_a_payer_inscription
        response.reste_a_payer_formation = dossier.reste_a_payer_formation
        logger.info(f"Dossier créé avec ID {dossier.id}")
        return response

    async def get_by_id(self, dossier_id: int, load_relations: bool = True) -> Optional[DossierCandidatureResponse]:
        query = select(DossierCandidature).where(DossierCandidature.id == dossier_id)
        if load_relations:
            query = query.options(
                joinedload(DossierCandidature.utilisateur),
                joinedload(DossierCandidature.formation).selectinload(Formation.modules),
                joinedload(DossierCandidature.session).joinedload(SessionFormation.centre),
                selectinload(DossierCandidature.reclamations).joinedload(Reclamation.auteur),
                selectinload(DossierCandidature.paiements),
                selectinload(DossierCandidature.pieces_jointes)
            )
        try:
            logger.info(f"Récupération du dossier ID {dossier_id}")
            result = await self.session.execute(query)
            dossier = result.scalar_one()
            response = DossierCandidatureResponse.model_validate(dossier, from_attributes=True)
            response.total_paye = dossier.total_paye
            response.reste_a_payer_inscription = dossier.reste_a_payer_inscription
            response.reste_a_payer_formation = dossier.reste_a_payer_formation
            return response
        except NoResultFound:
            logger.warning(f"Dossier ID {dossier_id} non trouvé")
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"Dossier avec ID {dossier_id} non trouvé.")

    async def update(self, dossier_id: int, data: DossierCandidatureUpdate) -> DossierCandidatureResponse:
        # Récupérer directement le dossier depuis la base de données
        result = await self.session.execute(select(DossierCandidature).where(DossierCandidature.id == dossier_id))
        dossier = result.scalar_one_or_none()
        
        if not dossier:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"Dossier avec ID {dossier_id} non trouvé.")
        
        logger.info(f"Mise à jour du dossier ID {dossier_id}")
        update_data = data.model_dump(exclude_unset=True, exclude={"pieces_jointes", "paiements", "reclamations"})
        for key, value in update_data.items():
            setattr(dossier, key, value)
        if data.pieces_jointes:
            dossier.pieces_jointes = [PieceJointe(**pj.model_dump(), dossier=dossier) for pj in data.pieces_jointes]
        if data.paiements:
            dossier.paiements = [Paiement(**pay.model_dump(), dossier=dossier) for pay in data.paiements]
        if data.reclamations:
            dossier.reclamations = [Reclamation(**rec.model_dump(), dossier=dossier) for rec in data.reclamations]
        await self.commit()
        await self.refresh(dossier)
        response = DossierCandidatureResponse.model_validate(dossier, from_attributes=True)
        response.total_paye = dossier.total_paye
        response.reste_a_payer_inscription = dossier.reste_a_payer_inscription
        response.reste_a_payer_formation = dossier.reste_a_payer_formation
        logger.info(f"Dossier ID {dossier_id} mis à jour")
        return response

    async def delete(self, dossier_id: int):
        # Récupérer directement le dossier depuis la base de données
        result = await self.session.execute(select(DossierCandidature).where(DossierCandidature.id == dossier_id))
        dossier = result.scalar_one_or_none()
        
        if not dossier:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"Dossier avec ID {dossier_id} non trouvé.")
        
        logger.info(f"Suppression du dossier ID {dossier_id}")
        await self.session.delete(dossier)
        await self.commit()
        logger.info(f"Dossier ID {dossier_id} supprimé")




# ────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────
#  PIECES JOINTES (Optimisé: Ajout de date_soumission, motif_refus; frais hérités mais surchargables)
# ────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────

class PieceJointeService(BaseService):
    async def create(self, data: PieceJointeCreate, dossier_id: Optional[int] = None) -> PieceJointeResponse:
        if dossier_id:
            data.dossier_id = dossier_id
        logger.info("Création d'une pièce jointe")
        piece = PieceJointe(**data.model_dump())
        self.session.add(piece)
        await self.commit()
        await self.refresh(piece)
        logger.info(f"Pièce jointe créée avec ID {piece.id}")
        return PieceJointeResponse.model_validate(piece, from_attributes=True)

    async def get_by_id(self, piece_id: int, load_relations: bool = True) -> Optional[PieceJointeResponse]:
        query = select(PieceJointe).where(PieceJointe.id == piece_id)
        if load_relations:
            query = query.options(joinedload(PieceJointe.dossier).joinedload(DossierCandidature.utilisateur))
        try:
            logger.info(f"Récupération de la pièce jointe ID {piece_id}")
            result = await self.session.execute(query)
            piece = result.scalar_one()
            return PieceJointeResponse.model_validate(piece, from_attributes=True)
        except NoResultFound:
            logger.warning(f"Pièce jointe ID {piece_id} non trouvée")
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"Pièce jointe avec ID {piece_id} non trouvée.")

    async def update(self, piece_id: int, data: PieceJointeUpdate) -> PieceJointeResponse:
        # Récupérer directement la pièce jointe depuis la base de données
        result = await self.session.execute(select(PieceJointe).where(PieceJointe.id == piece_id))
        piece = result.scalar_one_or_none()
        
        if not piece:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"Pièce jointe avec ID {piece_id} non trouvée.")
        
        logger.info(f"Mise à jour de la pièce jointe ID {piece_id}")
        update_data = data.model_dump(exclude_unset=True)
        for key, value in update_data.items():
            setattr(piece, key, value)
        await self.commit()
        await self.refresh(piece)
        logger.info(f"Pièce jointe ID {piece_id} mise à jour")
        return PieceJointeResponse.model_validate(piece, from_attributes=True)

    async def get_all(self, skip: int = 0, limit: int = 100) -> List[PieceJointeLight]:
        """Récupère toutes les pièces jointes avec pagination"""
        logger.info(f"Récupération de toutes les pièces jointes (skip: {skip}, limit: {limit})")
        query = select(PieceJointe).offset(skip).limit(limit)
        result = await self.session.execute(query)
        pieces = result.scalars().all()
        return [PieceJointeLight.model_validate(piece, from_attributes=True) for piece in pieces]

    async def delete(self, piece_id: int):
        # Récupérer directement la pièce jointe depuis la base de données
        result = await self.session.execute(select(PieceJointe).where(PieceJointe.id == piece_id))
        piece = result.scalar_one_or_none()
        
        if not piece:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"Pièce jointe avec ID {piece_id} non trouvée.")
        
        logger.info(f"Suppression de la pièce jointe ID {piece_id}")
        await self.session.delete(piece)
        await self.commit()
        logger.info(f"Pièce jointe ID {piece_id} supprimée")

# ────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────
# RECLAMATIONS (Optimisé: Ajout de date_cloture, index sur statut)
# ────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────
class ReclamationService(BaseService):
    async def create(self, data: ReclamationCreate, dossier_id: Optional[int] = None) -> ReclamationResponse:
        if dossier_id:
            data.dossier_id = dossier_id
        logger.info("Création d'une réclamation")
        reclamation = Reclamation(**data.model_dump())
        self.session.add(reclamation)
        await self.commit()
        await self.refresh(reclamation)
        logger.info(f"Réclamation créée avec ID {reclamation.id}")
        return ReclamationResponse.model_validate(reclamation, from_attributes=True)

    async def get_by_id(self, reclamation_id: int, load_relations: bool = True) -> Optional[ReclamationResponse]:
        query = select(Reclamation).where(Reclamation.id == reclamation_id)
        if load_relations:
            query = query.options(
                joinedload(Reclamation.dossier).joinedload(DossierCandidature.formation),
                joinedload(Reclamation.auteur)
            )
        try:
            logger.info(f"Récupération de la réclamation ID {reclamation_id}")
            result = await self.session.execute(query)
            reclamation = result.scalar_one()
            return ReclamationResponse.model_validate(reclamation, from_attributes=True)
        except NoResultFound:
            logger.warning(f"Réclamation ID {reclamation_id} non trouvée")
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"Réclamation avec ID {reclamation_id} non trouvée.")

    async def update(self, reclamation_id: int, data: ReclamationUpdate) -> ReclamationResponse:
        # Récupérer directement la réclamation depuis la base de données
        result = await self.session.execute(select(Reclamation).where(Reclamation.id == reclamation_id))
        reclamation = result.scalar_one_or_none()
        
        if not reclamation:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"Réclamation avec ID {reclamation_id} non trouvée.")
        
        logger.info(f"Mise à jour de la réclamation ID {reclamation_id}")
        update_data = data.model_dump(exclude_unset=True)
        for key, value in update_data.items():
            setattr(reclamation, key, value)
        await self.commit()
        await self.refresh(reclamation)
        logger.info(f"Réclamation ID {reclamation_id} mise à jour")
        return ReclamationResponse.model_validate(reclamation, from_attributes=True)

    async def delete(self, reclamation_id: int):
        # Récupérer directement la réclamation depuis la base de données
        result = await self.session.execute(select(Reclamation).where(Reclamation.id == reclamation_id))
        reclamation = result.scalar_one_or_none()
        
        if not reclamation:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"Réclamation avec ID {reclamation_id} non trouvée.")
        
        logger.info(f"Suppression de la réclamation ID {reclamation_id}")
        await self.session.delete(reclamation)
        await self.commit()
        logger.info(f"Réclamation ID {reclamation_id} supprimée")

# ────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────
# PAIEMENTS (Optimisé: Ajout de date_echeance, index sur reference_externe)
# ────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────
class PaiementService(BaseService):
    async def create(self, data: PaiementCreate, dossier_id: Optional[int] = None) -> PaiementResponse:
        if dossier_id:
            data.dossier_id = dossier_id
        logger.info("Création d'un paiement")
        paiement = Paiement(**data.model_dump())
        self.session.add(paiement)
        await self.commit()
        await self.refresh(paiement)
        logger.info(f"Paiement créé avec ID {paiement.id}")
        return PaiementResponse.model_validate(paiement, from_attributes=True)

    async def get_by_id(self, paiement_id: int, load_relations: bool = True) -> Optional[PaiementResponse]:
        query = select(Paiement).where(Paiement.id == paiement_id)
        if load_relations:
            query = query.options(joinedload(Paiement.dossier).joinedload(DossierCandidature.utilisateur))
        try:
            logger.info(f"Récupération du paiement ID {paiement_id}")
            result = await self.session.execute(query)
            paiement = result.scalar_one()
            return PaiementResponse.model_validate(paiement, from_attributes=True)
        except NoResultFound:
            logger.warning(f"Paiement ID {paiement_id} non trouvé")
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"Paiement avec ID {paiement_id} non trouvé.")

    async def update(self, paiement_id: int, data: PaiementUpdate) -> PaiementResponse:
        # Récupérer directement le paiement depuis la base de données
        result = await self.session.execute(select(Paiement).where(Paiement.id == paiement_id))
        paiement = result.scalar_one_or_none()
        
        if not paiement:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"Paiement avec ID {paiement_id} non trouvé.")
        
        logger.info(f"Mise à jour du paiement ID {paiement_id}")
        update_data = data.model_dump(exclude_unset=True)
        for key, value in update_data.items():
            setattr(paiement, key, value)
        await self.commit()
        await self.refresh(paiement)
        logger.info(f"Paiement ID {paiement_id} mis à jour")
        return PaiementResponse.model_validate(paiement, from_attributes=True)

    async def delete(self, paiement_id: int):
        # Récupérer directement le paiement depuis la base de données
        result = await self.session.execute(select(Paiement).where(Paiement.id == paiement_id))
        paiement = result.scalar_one_or_none()
        
        if not paiement:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"Paiement avec ID {paiement_id} non trouvé.")
        
        logger.info(f"Suppression du paiement ID {paiement_id}")
        await self.session.delete(paiement)
        await self.commit()
        logger.info(f"Paiement ID {paiement_id} supprimé")


# ────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────
# INFORMATIONS DESCRIPTIVES (Relation one-to-one avec Formation)
# ────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────

class InformationDescriptiveService(BaseService):
    async def create(self, data: InformationDescriptiveCreate, formation_id: int) -> InformationDescriptiveResponse:
        logger.info(f"Création d'informations descriptives pour la formation {formation_id}")
        
        # Vérifier si des informations descriptives existent déjà pour cette formation
        existing_info = await self.get_by_formation_id(formation_id)
        if existing_info:
            logger.info(f"Informations descriptives existent déjà pour la formation {formation_id}, mise à jour en cours...")
            return await self.update(formation_id, data)
        
        # Créer de nouvelles informations descriptives
        info_desc = InformationDescriptive(**data.model_dump(), formation_id=formation_id)
        self.session.add(info_desc)
        await self.commit()
        await self.refresh(info_desc)
        logger.info(f"Informations descriptives créées avec ID {info_desc.id}")
        return InformationDescriptiveResponse.model_validate(info_desc, from_attributes=True)

    async def get_by_formation_id(self, formation_id: int) -> Optional[InformationDescriptiveResponse]:
        try:
            logger.info(f"Récupération des informations descriptives pour la formation {formation_id}")
            result = await self.session.execute(
                select(InformationDescriptive).where(InformationDescriptive.formation_id == formation_id)
            )
            info_desc = result.scalar_one_or_none()
            if info_desc:
                return InformationDescriptiveResponse.model_validate(info_desc, from_attributes=True)
            return None
        except Exception as e:
            logger.error(f"Erreur lors de la récupération des informations descriptives : {str(e)}")
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Erreur lors de la récupération des informations descriptives"
            )

    async def update(self, formation_id: int, data: InformationDescriptiveUpdate) -> InformationDescriptiveResponse:
        logger.info(f"Mise à jour des informations descriptives pour la formation {formation_id}")
        
        # Récupérer les informations existantes
        existing_info = await self.get_by_formation_id(formation_id)
        if not existing_info:
            # Créer si elles n'existent pas
            return await self.create(data, formation_id)
        
        # Récupérer directement l'objet depuis la base de données pour la mise à jour
        result = await self.session.execute(select(InformationDescriptive).where(InformationDescriptive.formation_id == formation_id))
        info_obj = result.scalar_one_or_none()
        
        if not info_obj:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"Informations descriptives pour la formation {formation_id} non trouvées.")
        
        # Mettre à jour l'existant
        update_data = data.model_dump(exclude_unset=True)
        for key, value in update_data.items():
            setattr(info_obj, key, value)
        
        await self.commit()
        await self.refresh(info_obj)
        logger.info(f"Informations descriptives mises à jour pour la formation {formation_id}")
        return InformationDescriptiveResponse.model_validate(info_obj, from_attributes=True)

    async def delete(self, formation_id: int):
        logger.info(f"Suppression des informations descriptives pour la formation {formation_id}")
        result = await self.session.execute(
            select(InformationDescriptive).where(InformationDescriptive.formation_id == formation_id)
        )
        info_desc = result.scalar_one_or_none()
        if info_desc:
            await self.session.delete(info_desc)
            await self.commit()
            logger.info(f"Informations descriptives supprimées pour la formation {formation_id}")
        else:
            logger.warning(f"Aucune information descriptive trouvée pour la formation {formation_id}")


# ──────────────────────────────────────────────────────────────
# Services pour le système d'évaluation et de certification
# ──────────────────────────────────────────────────────────────

class EvaluationService(BaseService):
    """Service pour la gestion des évaluations"""

    async def create(self, evaluation_data: EvaluationCreate, formateur_id: int) -> EvaluationResponse:
        """Crée une nouvelle évaluation avec ses questions"""
        
        # Créer l'évaluation
        evaluation = Evaluation(
            session_id=evaluation_data.session_id,
            formateur_id=formateur_id,
            titre=evaluation_data.titre,
            description=evaluation_data.description,
            type_evaluation=evaluation_data.type_evaluation,
            date_ouverture=evaluation_data.date_ouverture,
            date_fermeture=evaluation_data.date_fermeture,
            duree_minutes=evaluation_data.duree_minutes,
            ponderation=evaluation_data.ponderation,
            note_minimale=evaluation_data.note_minimale,
            nombre_tentatives_max=evaluation_data.nombre_tentatives_max,
            type_correction=evaluation_data.type_correction,
            instructions=evaluation_data.instructions,
            consignes_correction=evaluation_data.consignes_correction
        )
        
        self.session.add(evaluation)
        await self.commit()
        await self.refresh(evaluation)
        
        # Créer les questions si fournies
        if evaluation_data.questions:
            for question_data in evaluation_data.questions:
                question = QuestionEvaluation(
                    evaluation_id=evaluation.id,
                    question=question_data.question,
                    type_question=question_data.type_question,
                    ordre=question_data.ordre,
                    reponses_possibles=question_data.reponses_possibles,
                    reponse_correcte=question_data.reponse_correcte,
                    points=question_data.points
                )
                self.session.add(question)
            
            await self.commit()
            await self.refresh(evaluation)
        
        return EvaluationResponse.model_validate(evaluation, from_attributes=True)

    async def get_by_id(self, evaluation_id: int, load_questions: bool = False) -> EvaluationResponse:
        """Récupère une évaluation par son ID"""
        
        query = select(Evaluation).where(Evaluation.id == evaluation_id)
        result = await self.session.execute(query)
        evaluation = result.scalar_one_or_none()
        
        if not evaluation:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Évaluation non trouvée"
            )
        
        return EvaluationResponse.model_validate(evaluation, from_attributes=True)

    async def get_by_session(self, session_id: int) -> List[EvaluationResponse]:
        """Récupère toutes les évaluations d'une session"""
        
        query = select(Evaluation).where(Evaluation.session_id == session_id)
        result = await self.session.execute(query)
        evaluations = result.scalars().all()
        
        return [EvaluationResponse.model_validate(eval, from_attributes=True) for eval in evaluations]

    async def update(self, evaluation_id: int, evaluation_data: EvaluationUpdate) -> EvaluationResponse:
        """Met à jour une évaluation"""
        
        evaluation = await self._get_evaluation_or_404(evaluation_id)
        
        # Mettre à jour les champs
        for field, value in evaluation_data.model_dump(exclude_unset=True).items():
            setattr(evaluation, field, value)
        
        await self.commit()
        await self.refresh(evaluation)
        
        return EvaluationResponse.model_validate(evaluation, from_attributes=True)

    async def delete(self, evaluation_id: int):
        """Supprime une évaluation"""
        
        evaluation = await self._get_evaluation_or_404(evaluation_id)
        await self.session.delete(evaluation)
        await self.commit()

    async def _get_evaluation_or_404(self, evaluation_id: int):
        """Récupère une évaluation ou lève une 404"""
        
        query = select(Evaluation).where(Evaluation.id == evaluation_id)
        result = await self.session.execute(query)
        evaluation = result.scalar_one_or_none()
        
        if not evaluation:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Évaluation non trouvée"
            )
        
        return evaluation


class QuestionEvaluationService(BaseService):
    """Service pour la gestion des questions d'évaluation"""

    async def create(self, question_data: QuestionEvaluationCreate) -> QuestionEvaluationResponse:
        """Crée une nouvelle question d'évaluation"""
        
        question = QuestionEvaluation(
            evaluation_id=question_data.evaluation_id,
            question=question_data.question,
            type_question=question_data.type_question,
            ordre=question_data.ordre,
            reponses_possibles=question_data.reponses_possibles,
            reponse_correcte=question_data.reponse_correcte,
            points=question_data.points
        )
        
        self.session.add(question)
        await self.commit()
        await self.refresh(question)
        
        return QuestionEvaluationResponse.model_validate(question, from_attributes=True)

    async def get_by_id(self, question_id: int) -> QuestionEvaluationResponse:
        """Récupère une question par son ID"""
        
        query = select(QuestionEvaluation).where(QuestionEvaluation.id == question_id)
        result = await self.session.execute(query)
        question = result.scalar_one_or_none()
        
        if not question:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Question non trouvée"
            )
        
        return QuestionEvaluationResponse.model_validate(question, from_attributes=True)

    async def get_by_evaluation(self, evaluation_id: int) -> List[QuestionEvaluationResponse]:
        """Récupère toutes les questions d'une évaluation"""
        
        query = select(QuestionEvaluation).where(QuestionEvaluation.evaluation_id == evaluation_id).order_by(QuestionEvaluation.ordre)
        result = await self.session.execute(query)
        questions = result.scalars().all()
        
        return [QuestionEvaluationResponse.model_validate(q, from_attributes=True) for q in questions]

    async def update(self, question_id: int, question_data: QuestionEvaluationUpdate) -> QuestionEvaluationResponse:
        """Met à jour une question"""
        
        question = await self._get_question_or_404(question_id)
        
        # Mettre à jour les champs
        for field, value in question_data.model_dump(exclude_unset=True).items():
            setattr(question, field, value)
        
        await self.commit()
        await self.refresh(question)
        
        return QuestionEvaluationResponse.model_validate(question, from_attributes=True)

    async def delete(self, question_id: int):
        """Supprime une question"""
        
        question = await self._get_question_or_404(question_id)
        await self.session.delete(question)
        await self.commit()

    async def reorder_questions(self, evaluation_id: int, question_orders: List[Dict[str, int]]):
        """Réordonne les questions d'une évaluation"""
        
        for order_data in question_orders:
            question_id = order_data.get("question_id")
            new_order = order_data.get("ordre")
            
            if question_id and new_order is not None:
                query = select(QuestionEvaluation).where(
                    QuestionEvaluation.id == question_id,
                    QuestionEvaluation.evaluation_id == evaluation_id
                )
                result = await self.session.execute(query)
                question = result.scalar_one_or_none()
                
                if question:
                    question.ordre = new_order
        
        await self.commit()

    async def _get_question_or_404(self, question_id: int):
        """Récupère une question ou lève une 404"""
        
        query = select(QuestionEvaluation).where(QuestionEvaluation.id == question_id)
        result = await self.session.execute(query)
        question = result.scalar_one_or_none()
        
        if not question:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Question non trouvée"
            )
        
        return question


class ReponseCandidatService(BaseService):
    """Service pour la gestion des réponses des candidats"""

    async def create(self, reponse_data: ReponseCandidatCreate) -> ReponseCandidatResponse:
        """Crée une nouvelle réponse de candidat"""
        
        reponse = ReponseCandidat(
            resultat_id=reponse_data.resultat_id,
            question_id=reponse_data.question_id,
            reponse_texte=reponse_data.reponse_texte,
            reponse_fichier_url=reponse_data.reponse_fichier_url,
            reponse_json=reponse_data.reponse_json
        )
        
        self.session.add(reponse)
        await self.commit()
        await self.refresh(reponse)
        
        return ReponseCandidatResponse.model_validate(reponse, from_attributes=True)

    async def get_by_id(self, reponse_id: int) -> ReponseCandidatResponse:
        """Récupère une réponse par son ID"""
        
        query = select(ReponseCandidat).where(ReponseCandidat.id == reponse_id)
        result = await self.session.execute(query)
        reponse = result.scalar_one_or_none()
        
        if not reponse:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Réponse non trouvée"
            )
        
        return ReponseCandidatResponse.model_validate(reponse, from_attributes=True)

    async def get_by_resultat(self, resultat_id: int) -> List[ReponseCandidatResponse]:
        """Récupère toutes les réponses d'un résultat d'évaluation"""
        
        query = select(ReponseCandidat).where(ReponseCandidat.resultat_id == resultat_id)
        result = await self.session.execute(query)
        reponses = result.scalars().all()
        
        return [ReponseCandidatResponse.model_validate(r, from_attributes=True) for r in reponses]

    async def update(self, reponse_id: int, reponse_data: ReponseCandidatCreate) -> ReponseCandidatResponse:
        """Met à jour une réponse"""
        
        reponse = await self._get_reponse_or_404(reponse_id)
        
        # Mettre à jour les champs
        for field, value in reponse_data.model_dump(exclude_unset=True).items():
            setattr(reponse, field, value)
        
        await self.commit()
        await self.refresh(reponse)
        
        return ReponseCandidatResponse.model_validate(reponse, from_attributes=True)

    async def delete(self, reponse_id: int):
        """Supprime une réponse"""
        
        reponse = await self._get_reponse_or_404(reponse_id)
        await self.session.delete(reponse)
        await self.commit()

    async def corriger_reponse(self, reponse_id: int, points_obtenus: float, commentaire: str = None):
        """Corrige une réponse de candidat"""
        
        reponse = await self._get_reponse_or_404(reponse_id)
        
        # Récupérer la question pour obtenir les points maximaux
        question_query = select(QuestionEvaluation).where(QuestionEvaluation.id == reponse.question_id)
        question_result = await self.session.execute(question_query)
        question = question_result.scalar_one_or_none()
        
        if question:
            reponse.points_obtenus = points_obtenus
            reponse.points_maximaux = question.points
            reponse.commentaire_correction = commentaire
            
            await self.commit()
            await self.refresh(reponse)

    async def _get_reponse_or_404(self, reponse_id: int):
        """Récupère une réponse ou lève une 404"""
        
        query = select(ReponseCandidat).where(ReponseCandidat.id == reponse_id)
        result = await self.session.execute(query)
        reponse = result.scalar_one_or_none()
        
        if not reponse:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Réponse non trouvée"
            )
        
        return reponse


class ResultatEvaluationService(BaseService):
    """Service pour la gestion des résultats d'évaluation"""

    async def commencer_evaluation(self, evaluation_id: int, candidat_id: int) -> ResultatEvaluationResponse:
        """Commence une évaluation pour un candidat"""
        
        # Vérifier que l'évaluation existe et est ouverte
        eval_query = select(Evaluation).where(Evaluation.id == evaluation_id)
        eval_result = await self.session.execute(eval_query)
        evaluation = eval_result.scalar_one_or_none()
        
        if not evaluation:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Évaluation non trouvée"
            )
        
        # Vérifier le nombre de tentatives
        tentative_query = select(ResultatEvaluation).where(
            ResultatEvaluation.evaluation_id == evaluation_id,
            ResultatEvaluation.candidat_id == candidat_id
        )
        tentative_result = await self.session.execute(tentative_query)
        tentatives_existantes = tentative_result.scalars().all()
        
        if len(tentatives_existantes) >= evaluation.nombre_tentatives_max:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Nombre maximum de tentatives atteint"
            )
        
        # Créer un nouveau résultat
        tentative_numero = len(tentatives_existantes) + 1
        resultat = ResultatEvaluation(
            evaluation_id=evaluation_id,
            candidat_id=candidat_id,
            tentative_numero=tentative_numero,
            date_debut=datetime.now()
        )
        
        self.session.add(resultat)
        await self.commit()
        await self.refresh(resultat)
        
        return ResultatEvaluationResponse.model_validate(resultat, from_attributes=True)

    async def soumettre_evaluation(self, resultat_id: int, reponses: List[ReponseCandidatCreate]) -> ResultatEvaluationResponse:
        """Soumet les réponses d'un candidat pour une évaluation"""
        
        # Récupérer le résultat
        resultat_query = select(ResultatEvaluation).where(ResultatEvaluation.id == resultat_id)
        resultat_result = await self.session.execute(resultat_query)
        resultat = resultat_result.scalar_one_or_none()
        
        if not resultat:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Résultat d'évaluation non trouvé"
            )
        
        # Créer les réponses
        for reponse_data in reponses:
            reponse = ReponseCandidat(
                resultat_id=resultat_id,
                question_id=reponse_data.question_id,
                reponse_texte=reponse_data.reponse_texte,
                reponse_fichier_url=reponse_data.reponse_fichier_url,
                reponse_json=reponse_data.reponse_json
            )
            self.session.add(reponse)
        
        # Marquer comme terminé
        resultat.date_fin = datetime.now()
        resultat.statut = StatutResultatEnum.SOUMIS
        
        await self.commit()
        await self.refresh(resultat)
        
        return ResultatEvaluationResponse.model_validate(resultat, from_attributes=True)

    async def corriger_evaluation(self, resultat_id: int) -> ResultatEvaluationResponse:
        """Corrige automatiquement une évaluation"""
        
        resultat = await self._get_resultat_or_404(resultat_id)
        
        # Récupérer toutes les réponses
        reponses_query = select(ReponseCandidat).where(ReponseCandidat.resultat_id == resultat_id)
        reponses_result = await self.session.execute(reponses_query)
        reponses = reponses_result.scalars().all()
        
        total_points = 0
        points_maximaux = 0
        
        # Corriger chaque réponse
        for reponse in reponses:
            question_query = select(QuestionEvaluation).where(QuestionEvaluation.id == reponse.question_id)
            question_result = await self.session.execute(question_query)
            question = question_result.scalar_one_or_none()
            
            if question:
                points_maximaux += question.points
                
                # Logique de correction basique (à adapter selon le type de question)
                if question.type_question == "choix_multiple":
                    if reponse.reponse_json == question.reponse_correcte:
                        reponse.points_obtenus = question.points
                        total_points += question.points
                    else:
                        reponse.points_obtenus = 0
                elif question.type_question == "texte_libre":
                    # Pour les questions à développement, pas de correction automatique
                    reponse.points_obtenus = 0
                else:
                    reponse.points_obtenus = 0
                
                reponse.points_maximaux = question.points
        
        # Calculer les résultats
        resultat.note_obtenue = total_points
        resultat.note_maximale = points_maximaux
        resultat.pourcentage_reussite = (total_points / points_maximaux * 100) if points_maximaux > 0 else 0
        resultat.statut = StatutResultatEnum.CORRIGÉ
        
        await self.commit()
        await self.refresh(resultat)
        
        return ResultatEvaluationResponse.model_validate(resultat, from_attributes=True)

    async def get_by_id(self, resultat_id: int) -> ResultatEvaluationResponse:
        """Récupère un résultat par son ID"""
        
        resultat = await self._get_resultat_or_404(resultat_id)
        return ResultatEvaluationResponse.model_validate(resultat, from_attributes=True)

    async def get_by_evaluation(self, evaluation_id: int) -> List[ResultatEvaluationResponse]:
        """Récupère tous les résultats d'une évaluation"""
        
        query = select(ResultatEvaluation).where(ResultatEvaluation.evaluation_id == evaluation_id)
        result = await self.session.execute(query)
        resultats = result.scalars().all()
        
        return [ResultatEvaluationResponse.model_validate(r, from_attributes=True) for r in resultats]

    async def get_by_candidat(self, candidat_id: int) -> List[ResultatEvaluationResponse]:
        """Récupère tous les résultats d'un candidat"""
        
        query = select(ResultatEvaluation).where(ResultatEvaluation.candidat_id == candidat_id)
        result = await self.session.execute(query)
        resultats = result.scalars().all()
        
        return [ResultatEvaluationResponse.model_validate(r, from_attributes=True) for r in resultats]

    async def update(self, resultat_id: int, resultat_data: dict) -> ResultatEvaluationResponse:
        """Met à jour un résultat d'évaluation"""
        
        resultat = await self._get_resultat_or_404(resultat_id)
        
        # Mettre à jour les champs
        for field, value in resultat_data.items():
            if hasattr(resultat, field):
                setattr(resultat, field, value)
        
        await self.commit()
        await self.refresh(resultat)
        
        return ResultatEvaluationResponse.model_validate(resultat, from_attributes=True)

    async def delete(self, resultat_id: int):
        """Supprime un résultat d'évaluation"""
        
        resultat = await self._get_resultat_or_404(resultat_id)
        await self.session.delete(resultat)
        await self.commit()

    async def _get_resultat_or_404(self, resultat_id: int):
        """Récupère un résultat ou lève une 404"""
        
        query = select(ResultatEvaluation).where(ResultatEvaluation.id == resultat_id)
        result = await self.session.execute(query)
        resultat = result.scalar_one_or_none()
        
        if not resultat:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Résultat d'évaluation non trouvé"
            )
        
        return resultat


class CertificatService(BaseService):
    """Service pour la gestion des certificats"""

    async def generer_certificat(self, candidat_id: int, session_id: int) -> CertificatResponse:
        """Génère un certificat pour un candidat ayant terminé une session"""
        
        # Vérifier que la session est terminée
        session_query = select(SessionFormation).where(SessionFormation.id == session_id)
        session_result = await self.session.execute(session_query)
        session = session_result.scalar_one_or_none()
        
        if not session:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Session non trouvée"
            )
        
        # Vérifier que le candidat a terminé toutes les évaluations
        resultats = await self._get_resultats_session(candidat_id, session_id)
        if not resultats:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Aucun résultat d'évaluation trouvé pour cette session"
            )
        
        # Calculer la note finale
        note_finale = await self._calculer_note_finale(resultats)
        
        # Déterminer la mention
        mention = self._determiner_mention(note_finale)
        
        # Générer le numéro de certificat
        numero_certificat = f"CERT-{session_id:04d}-{candidat_id:04d}-{datetime.now().strftime('%Y%m%d')}"
        
        # Créer le certificat
        certificat = Certificat(
            candidat_id=candidat_id,
            session_id=session_id,
            numero_certificat=numero_certificat,
            titre_formation=session.formation.titre,
            date_obtention=date.today(),
            note_finale=note_finale,
            mention=mention,
            statut_validation="Validé" if note_finale >= 10.0 else "Non validé"
        )
        
        self.session.add(certificat)
        await self.commit()
        await self.refresh(certificat)
        
        return CertificatResponse.model_validate(certificat, from_attributes=True)

    async def _get_resultats_session(self, candidat_id: int, session_id: int) -> List[ResultatEvaluation]:
        """Récupère tous les résultats d'évaluation d'un candidat pour une session"""
        
        query = select(ResultatEvaluation).join(Evaluation).where(
            ResultatEvaluation.candidat_id == candidat_id,
            Evaluation.session_id == session_id
        )
        result = await self.session.execute(query)
        return result.scalars().all()

    async def _calculer_note_finale(self, resultats: List[ResultatEvaluation]) -> float:
        """Calcule la note finale pondérée"""
        if not resultats:
            return 0.0
        
        total_pondere = 0
        total_ponderation = 0
        
        for resultat in resultats:
            if resultat.note_obtenue is not None and resultat.evaluation.ponderation:
                total_pondere += resultat.note_obtenue * resultat.evaluation.ponderation
                total_ponderation += resultat.evaluation.ponderation
        
        return total_pondere / total_ponderation if total_ponderation > 0 else 0.0

    def _determiner_mention(self, note: float) -> str:
        """Détermine la mention selon la note"""
        if note >= 16.0:
            return "Très bien"
        elif note >= 14.0:
            return "Bien"
        elif note >= 12.0:
            return "Assez bien"
        elif note >= 10.0:
            return "Passable"
        else:
            return "Insuffisant"