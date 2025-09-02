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
from sqlalchemy import delete, text, func, case
from sqlalchemy.orm import selectinload, joinedload
from sqlalchemy.exc import IntegrityError, NoResultFound
from fastapi import HTTPException, UploadFile, status
from passlib.context import CryptContext
import redis
import asyncio
import aiohttp
import hashlib
import hmac
from typing import Optional, Dict, Any
import json

from src.api.model import (
    Adresse, Utilisateur, CentreFormation, Formation, SessionFormation,
    Module, Ressource, DossierCandidature, PieceJointe, Reclamation,
    InformationDescriptive,
    Evaluation, QuestionEvaluation, ResultatEvaluation, ReponseCandidat, Certificat,
    PaiementCinetPay, PaiementQueue
)
from src.util.helper.enum import (
    CiviliteEnum, DeviseEnum, MethodePaiementEnum, ModaliteEnum,
    RoleEnum, SpecialiteEnum, StatutCandidatureEnum, StatutReclamationEnum,
    TimestampMixin, TypeFormationEnum, TypePaiementEnum, TypeRessourceEnum, StatutSessionEnum,
    TypeEvaluationEnum, StatutEvaluationEnum, StatutResultatEnum, TypeCorrectionEnum
)
from src.api.schema import (
    AdresseCreate, AdresseUpdate, AdresseResponse, AdresseLight, LoginResponse, PieceJointeLight,
    UtilisateurCreate, UtilisateurUpdate, UtilisateurResponse, UtilisateurLight,
    CentreFormationCreate, CentreFormationUpdate, CentreFormationResponse, CentreFormationLight,
    FormationCreate, FormationUpdate, FormationResponse, FormationLight,
    SessionFormationCreate, SessionFormationUpdate, SessionFormationResponse, SessionFormationLight,
    SessionFormationDossierLight, SessionStatutUpdate, SessionModaliteUpdate,
    ModuleCreate, ModuleUpdate, ModuleResponse, ModuleLight, DossierStatutUpdate,
    RessourceCreate, RessourceUpdate, RessourceResponse, RessourceLight,
    DossierCandidatureCreate, DossierCandidatureUpdate, DossierCandidatureResponse, DossierCandidatureLight,
    PieceJointeCreate, PieceJointeUpdate, PieceJointeResponse, PieceJointeLight,
    ReclamationCreate, ReclamationUpdate, ReclamationResponse, ReclamationLight,
    InformationDescriptiveCreate, InformationDescriptiveUpdate, InformationDescriptiveResponse,
    # Nouveaux schémas pour l'évaluation
    EvaluationCreate, EvaluationUpdate, EvaluationResponse, EvaluationLight,
    QuestionEvaluationCreate, QuestionEvaluationUpdate, QuestionEvaluationResponse, QuestionEvaluationLight,
    ResultatEvaluationCreate, ResultatEvaluationUpdate, ResultatEvaluationResponse, ResultatEvaluationLight,
    ReponseCandidatCreate, ReponseCandidatUpdate, ReponseCandidatResponse, 
    CertificatCreate, CertificatUpdate, CertificatResponse, CertificatLight, DossierStatutResponse,
    PaiementCreate, PaiementResponse, PaiementStats
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
            error_msg = str(e)
            logger.error(f"Erreur d'intégrité lors du commit : {error_msg}")
            
            # Détecter les erreurs spécifiques
            if "ix_utilisateurs_email" in error_msg and "dupliquée" in error_msg:
                raise HTTPException(
                    status_code=status.HTTP_409_CONFLICT, 
                    detail="Un utilisateur avec cet email existe déjà. Veuillez utiliser un email différent."
                )
            elif "dupliquée" in error_msg:
                raise HTTPException(
                    status_code=status.HTTP_409_CONFLICT, 
                    detail="Une entrée avec ces informations existe déjà dans la base de données."
                )
            else:
                raise HTTPException(
                    status_code=status.HTTP_409_CONFLICT, 
                    detail="Violation d'intégrité : Entrée dupliquée ou contrainte échouée."
                )
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

    async def create_with_password(self, data: UtilisateurCreate, password: str) -> UtilisateurResponse:
        logger.info("Création d'un utilisateur avec mot de passe spécifique")
        
        # Hacher le mot de passe fourni
        hashed_password = hash_password(password)
        
        # Créer l'utilisateur avec le mot de passe haché
        user_data = data.model_dump()
        user_data["password"] = hashed_password
        
        user = Utilisateur(**user_data)
        
        self.session.add(user)
        await self.commit()
        await self.refresh(user)
        
        logger.info(f"Utilisateur créé avec ID {user.id} et mot de passe personnalisé")
        
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

    async def create_with_password_detailed(self, user_data: dict, password: str) -> UtilisateurResponse:
        logger.info("Création d'un utilisateur avec tous les champs détaillés")
        
        # Hacher le mot de passe fourni
        hashed_password = hash_password(password)
        user_data["password"] = hashed_password
        
        # Créer l'utilisateur avec tous les champs
        user = Utilisateur(**user_data)
        
        self.session.add(user)
        await self.commit()
        await self.refresh(user)
        
        logger.info(f"Utilisateur créé avec ID {user.id} et tous les champs détaillés")
        
        # Créer manuellement la réponse pour éviter les erreurs de greenlet avec les relations
        response_data = {
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
        
        return UtilisateurResponse(**response_data)

    async def get_by_id(self, user_id: int, load_relations: bool = True) -> Optional[UtilisateurResponse]:
        query = select(Utilisateur).where(Utilisateur.id == user_id)
        try:
            logger.info(f"Récupération de l'utilisateur ID {user_id}")
            result = await self.session.execute(query)
            user = result.scalar_one()
            
            # Créer manuellement la réponse avec des listes vides pour les relations
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
                "adresses": [],  # Liste vide pour éviter les erreurs
                "dossiers": [],  # Liste vide pour éviter les erreurs
                "reclamations": []  # Liste vide pour éviter les erreurs
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
        try:
            logger.info(f"Récupération de la formation ID {formation_id}")
            result = await self.session.execute(query)
            formation = result.scalar_one()
            
            # Créer manuellement la réponse avec des listes vides pour les relations
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
                "sessions": [],  # Liste vide pour éviter les erreurs
                "modules": [],   # Liste vide pour éviter les erreurs
                "dossiers": [],  # Liste vide pour éviter les erreurs
                "information_descriptive": None  # None pour éviter les erreurs
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
                            "information_descriptive": InformationDescriptiveResponse.model_validate(formation.information_descriptive, from_attributes=True) if formation.information_descriptive else None
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
        
        # Charger les formations AVEC leurs relations
        query = select(Formation).options(
            selectinload(Formation.sessions),
            selectinload(Formation.modules),
            selectinload(Formation.dossiers),
            joinedload(Formation.information_descriptive)
        ).offset(skip).limit(limit)
        
        result = await self.session.execute(query)
        formations = result.scalars().all()
        
        # Créer les réponses avec toutes les informations chargées
        formation_responses = []
        for formation in formations:
            # Convertir les sessions en SessionFormationLight
            sessions_light = []
            for session in formation.sessions:
                try:
                    sessions_light.append(SessionFormationLight.model_validate(session, from_attributes=True))
                except Exception as e:
                    logger.warning(f"Erreur lors de la conversion de session {session.id}: {e}")
                    continue
            
            # Convertir les modules en ModuleResponse
            modules_response = []
            for module in formation.modules:
                try:
                    # Créer un ModuleResponse avec les données de base
                    module_data = {
                        "id": module.id,
                        "titre": module.titre,
                        "ordre": module.ordre,
                        "formation_id": module.formation_id,
                        "description": module.description,
                        "created_at": module.created_at,
                        "updated_at": module.updated_at,
                        "formation": FormationLight.model_validate(formation, from_attributes=True),
                        "ressources": []  # Liste vide pour éviter les erreurs
                    }
                    modules_response.append(ModuleResponse(**module_data))
                except Exception as e:
                    logger.warning(f"Erreur lors de la conversion de module {module.id}: {e}")
                    continue
            
            # Convertir les dossiers en DossierCandidatureLight
            dossiers_light = []
            for dossier in formation.dossiers:
                try:
                    dossiers_light.append(DossierCandidatureLight.model_validate(dossier, from_attributes=True))
                except Exception as e:
                    logger.warning(f"Erreur lors de la conversion de dossier {dossier.id}: {e}")
                    continue
            
            # Créer manuellement la réponse avec toutes les relations
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
                "sessions": sessions_light,
                "modules": modules_response,
                "dossiers": dossiers_light,
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
        # Charger explicitement la relation dossiers
        await self.session.refresh(session_form, ["dossiers"])
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

    async def get_all(self, skip: int = 0, limit: int = 100) -> List[SessionFormationResponse]:
        """Récupère toutes les sessions de formation avec pagination et relations"""
        logger.info(f"Récupération des sessions de formation (skip: {skip}, limit: {limit})")
        
        try:
            query = select(SessionFormation).options(
                joinedload(SessionFormation.formation),
                joinedload(SessionFormation.centre),
                selectinload(SessionFormation.dossiers).joinedload(DossierCandidature.utilisateur)
            ).offset(skip).limit(limit)
            
            result = await self.session.execute(query)
            sessions = result.scalars().all()
            
            # Convertir en SessionFormationResponse
            sessions_response = []
            for session in sessions:
                session_data = {
                    "id": session.id,
                    "formation_id": session.formation_id,
                    "centre_id": session.centre_id,
                    "date_debut": session.date_debut,
                    "date_fin": session.date_fin,
                    "date_limite_inscription": session.date_limite_inscription,
                    "statut": session.statut,
                    "modalite": session.modalite,
                    "nombre_places": session.nombre_places,
                    "nombre_inscrits": session.nombre_inscrits,
                    "prix": session.prix,
                    "description": session.description,
                    "created_at": session.created_at,
                    "updated_at": session.updated_at,
                    "formation": session.formation,
                    "centre": session.centre,
                    "dossiers": session.dossiers
                }
                sessions_response.append(SessionFormationResponse.model_validate(session_data, from_attributes=True))
            
            logger.info(f"{len(sessions_response)} sessions récupérées")
            return sessions_response
            
        except Exception as e:
            logger.error(f"Erreur lors de la récupération des sessions: {str(e)}")
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Erreur lors de la récupération des sessions de formation"
            )

    async def change_modalite(self, session_id: int, data: SessionModaliteUpdate) -> SessionFormationResponse:
        """Change la modalité d'une session de formation avec validation métier"""
        logger.info(f"Changement de modalité de la session ID {session_id} vers {data.modalite}")
        
        # Récupérer la session avec ses relations
        result = await self.session.execute(
            select(SessionFormation).options(
                selectinload(SessionFormation.dossiers),
                selectinload(SessionFormation.paiements_cinetpay)
            ).where(SessionFormation.id == session_id)
        )
        session_form = result.scalar_one_or_none()
        
        if not session_form:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Session de formation avec ID {session_id} non trouvée"
            )
        
        # Validation métier : vérifier s'il y a des paiements effectués
        if session_form.paiements_cinetpay:
            # Vérifier s'il y a des paiements réussis
            successful_payments = [
                p for p in session_form.paiements_cinetpay 
                if p.statut == "ACCEPTED"
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
        
        # Attribuer automatiquement l'ordre si non fourni
        if data.ordre is None:
            # Récupérer le dernier ordre pour cette formation
            result = await self.session.execute(
                select(Module.ordre).where(Module.formation_id == data.formation_id).order_by(Module.ordre.desc()).limit(1)
            )
            max_ordre_result = result.scalar_one_or_none()
            data.ordre = (max_ordre_result or 0) + 1
            logger.info(f"Ordre automatiquement attribué: {data.ordre}")
        
        # Créer le module
        module_data = data.model_dump()
        module = Module(**module_data)
        self.session.add(module)
        
        try:
            await self.session.commit()
            await self.session.refresh(module, ["formation", "ressources"])
            logger.info(f"Module créé avec ID {module.id} et ordre {module.ordre}")
            return ModuleResponse.model_validate(module, from_attributes=True)
        except Exception as e:
            await self.session.rollback()
            logger.error(f"Erreur lors de la création du module: {str(e)}")
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"Erreur lors de la création du module: {str(e)}"
            )

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
        
        # Mettre à jour les champs du module
        update_data = data.model_dump(exclude_unset=True)
        for key, value in update_data.items():
            setattr(module, key, value)
        
        try:
            await self.commit()
            logger.info(f"Module ID {module_id} mis à jour")
            # Récupérer le module mis à jour avec toutes les relations
            return await self.get_by_id(module_id)
        except Exception as e:
            await self.session.rollback()
            logger.error(f"Erreur lors de la mise à jour du module {module_id}: {str(e)}")
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"Erreur lors de la mise à jour du module: {str(e)}"
            )

    async def get_all(self, skip: int = 0, limit: int = 100) -> List[ModuleResponse]:
        """Récupère tous les modules avec pagination"""
        logger.info(f"Récupération des modules (skip: {skip}, limit: {limit})")
        
        query = select(Module).options(
            joinedload(Module.formation),
            selectinload(Module.ressources)
        ).offset(skip).limit(limit).order_by(Module.formation_id, Module.ordre)
        
        result = await self.session.execute(query)
        modules = result.scalars().all()
        
        # Convertir en ModuleResponse
        modules_response = []
        for module in modules:
            modules_response.append(ModuleResponse.model_validate(module, from_attributes=True))
        
        logger.info(f"{len(modules_response)} modules récupérés")
        return modules_response

    async def get_modules_by_formation(self, formation_id: int) -> List[ModuleResponse]:
        """Récupère tous les modules d'une formation classés par ordre"""
        logger.info(f"Récupération des modules de la formation {formation_id}")
        
        # Vérifier que la formation existe
        formation_query = select(Formation).where(Formation.id == formation_id)
        formation_result = await self.session.execute(formation_query)
        formation = formation_result.scalar_one_or_none()
        
        if not formation:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Formation avec l'ID {formation_id} non trouvée"
            )
        
        # Récupérer tous les modules de la formation classés par ordre
        query = select(Module).options(
            joinedload(Module.formation),
            selectinload(Module.ressources)
        ).where(Module.formation_id == formation_id).order_by(Module.ordre)
        
        result = await self.session.execute(query)
        modules = result.scalars().all()
        
        # Convertir en ModuleResponse
        modules_response = []
        for module in modules:
            modules_response.append(ModuleResponse.model_validate(module, from_attributes=True))
        
        logger.info(f"{len(modules_response)} modules récupérés pour la formation {formation_id}")
        return modules_response

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
        logger.info("Création d'une ressource")
        
        # Créer un dictionnaire avec les données
        ressource_data = data.model_dump()
        if module_id:
            ressource_data["module_id"] = module_id
            
        ressource = Ressource(**ressource_data)
        self.session.add(ressource)
        await self.commit()
        
        # Récupérer la ressource créée avec ses relations
        return await self.get_by_id(ressource.id)

    async def get_by_id(self, ressource_id: int, load_relations: bool = True) -> Optional[RessourceResponse]:
        query = select(Ressource).where(Ressource.id == ressource_id)
        if load_relations:
            query = query.options(joinedload(Ressource.module).joinedload(Module.formation))
        try:
            logger.info(f"Récupération de la ressource ID {ressource_id}")
            result = await self.session.execute(query)
            ressource = result.scalar_one_or_none()
            if not ressource:
                raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"Ressource avec ID {ressource_id} non trouvée.")
            return RessourceResponse.model_validate(ressource, from_attributes=True)
        except HTTPException:
            raise
        except Exception as e:
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
        
        # Récupérer la ressource mise à jour avec ses relations
        return await self.get_by_id(ressource_id)

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

    async def get_all(self, skip: int = 0, limit: int = 100) -> List[RessourceLight]:
        """Récupère toutes les ressources avec pagination"""
        logger.info(f"Récupération des ressources (skip: {skip}, limit: {limit})")
        
        query = select(Ressource).options(
            joinedload(Ressource.module)
        ).offset(skip).limit(limit).order_by(Ressource.id)
        
        result = await self.session.execute(query)
        ressources = result.scalars().all()
        
        # Convertir en RessourceLight
        ressources_response = []
        for ressource in ressources:
            ressources_response.append(RessourceLight.model_validate(ressource, from_attributes=True))
        
        logger.info(f"{len(ressources_response)} ressources récupérées")
        return ressources_response

    async def get_ressources_by_module(self, module_id: int) -> List[RessourceResponse]:
        """Récupère toutes les ressources d'un module spécifique"""
        logger.info(f"Récupération des ressources du module {module_id}")
        
        # Vérifier que le module existe
        module_query = select(Module).where(Module.id == module_id)
        module_result = await self.session.execute(module_query)
        module = module_result.scalar_one_or_none()
        
        if not module:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Module avec l'ID {module_id} non trouvé"
            )
        
        # Récupérer toutes les ressources du module
        query = select(Ressource).options(
            joinedload(Ressource.module).joinedload(Module.formation)
        ).where(Ressource.module_id == module_id).order_by(Ressource.id)
        
        result = await self.session.execute(query)
        ressources = result.scalars().all()
        
        # Convertir en RessourceResponse
        ressources_response = []
        for ressource in ressources:
            ressources_response.append(RessourceResponse.model_validate(ressource, from_attributes=True))
        
        logger.info(f"{len(ressources_response)} ressources récupérées pour le module {module_id}")
        return ressources_response

# ────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────
# DOSSIER CANDIDATURE (Optimisé: Ajout de date_soumission, motif_refus; frais hérités mais surchargables)
# ────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────
class DossierService(BaseService):
    """Service optimisé pour la gestion des dossiers de candidature"""

    async def create(self, data: DossierCandidatureCreate) -> DossierCandidatureResponse:
        logger.info("Création d'un dossier de candidature")
        
        # Récupérer la session de formation
        session_result = await self.session.execute(select(SessionFormation).where(SessionFormation.id == data.session_id))
        session = session_result.scalar_one_or_none()
        if not session:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"La session de formation avec ID {data.session_id} n'existe pas."
            )
        
        # Récupérer la formation associée à la session
        formation_result = await self.session.execute(select(Formation).where(Formation.id == session.formation_id))
        formation = formation_result.scalar_one_or_none()
        if not formation:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"La formation associée à la session ID {session.formation_id} n'existe pas."
            )
        
        # Récupérer l'utilisateur pour vérifier son rôle
        user_result = await self.session.execute(
            select(Utilisateur).where(Utilisateur.id == data.utilisateur_id)
        )
        user = user_result.scalar_one_or_none()
        
        if not user:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Utilisateur avec ID {data.utilisateur_id} non trouvé"
            )
        
        # Générer automatiquement le numéro de candidature
        numero_candidature = await self._generate_unique_numero_candidature()
        
        # Créer le dossier avec les champs automatiques
        dossier_data = data.model_dump(exclude={"pieces_jointes", "reclamations", "numero_candidature", "date_soumission"})
        dossier_data["numero_candidature"] = numero_candidature
        dossier_data["date_soumission"] = datetime.now()
        dossier_data["formation_id"] = session.formation_id
        
        # Appliquer les règles spéciales pour les formateurs
        if user.role.value == RoleEnum.FORMATEUR.value:
            logger.info(f"Application des règles spéciales pour le formateur {user.id}")
            dossier_data["frais_formation_montant"] = 0.0
            dossier_data["frais_inscription_montant"] = 21000.0
            dossier_data["devise"] = DeviseEnum.XOF
            dossier_data["objet"] = data.objet
            
        if user.role.value == RoleEnum.CANDIDAT.value:
            logger.info(f"Application des règles spéciales pour le candidat {user.id}")
            dossier_data["frais_formation_montant"] = formation.frais_formation
            dossier_data["frais_inscription_montant"] = formation.frais_inscription
            dossier_data["devise"] = formation.devise
            dossier_data["objet"] = data.objet
       
        # Nettoyer les valeurs None
        dossier_data = {k: v for k, v in dossier_data.items() if v is not None}
        logger.info(f"Données du dossier avant création: {dossier_data}")
        dossier = DossierCandidature(**dossier_data)
        
        self.session.add(dossier)
        await self.commit()
        await self.refresh(dossier)
        
        # Créer manuellement la réponse pour éviter les erreurs de greenlet
        formation_light = None
        if formation:
            formation_light = {
                "id": formation.id,
                "titre": formation.titre,
                "specialite": formation.specialite,
                "modalite": formation.modalite
            }
        
        session_light = None
        if session:
            session_light = {
                "id": session.id,
                "formation_id": session.formation_id,
                "centre_id": session.centre_id,
                "date_debut": session.date_debut,
                "date_fin": session.date_fin,
                "date_limite_inscription": session.date_limite_inscription,
                "places_disponibles": session.places_disponibles,
                "statut": session.statut,
                "modalite": session.modalite,
                "centre": None
            }
        
        response_data = {
            "id": dossier.id,
            "utilisateur_id": dossier.utilisateur_id,
            "formation_id": dossier.formation_id,
            "numero_candidature": dossier.numero_candidature,
            "statut": dossier.statut,
            "session_id": dossier.session_id,
            "date_soumission": dossier.date_soumission,
            "objet": dossier.objet,
            "motif_refus": dossier.motif_refus,
            "frais_inscription_montant": float(dossier.frais_inscription_montant) if dossier.frais_inscription_montant else None,
            "frais_formation_montant": float(dossier.frais_formation_montant) if dossier.frais_formation_montant else None,
            "devise": dossier.devise,
            "created_at": dossier.created_at,
            "updated_at": dossier.updated_at,
            "utilisateur": UtilisateurLight.model_validate(user, from_attributes=True),
            "formation": FormationLight(**formation_light) if formation_light else None,
            "session": SessionFormationDossierLight(**session_light) if session_light else None,
            "reclamations": [],
            "pieces_jointes": [],
            "total_paye": 0.0,
            "reste_a_payer_inscription": float(dossier.frais_inscription_montant) if dossier.frais_inscription_montant else 0.0,
            "reste_a_payer_formation": float(dossier.frais_formation_montant) if dossier.frais_formation_montant else 0.0
        }
        
        response = DossierCandidatureResponse(**response_data)
        logger.info(f"Dossier créé avec ID {dossier.id} et numéro {numero_candidature}")
        return response

    async def _generate_unique_numero_candidature(self) -> str:
        """Génère un numéro de candidature unique de 10 caractères"""
        while True:
            alphabet = string.digits + string.ascii_uppercase
            numero = ''.join(secrets.choice(alphabet) for _ in range(10))
            result = await self.session.execute(
                select(DossierCandidature).where(DossierCandidature.numero_candidature == numero)
            )
            if not result.scalar_one_or_none():
                return numero

    async def get_by_id(self, dossier_id: int, load_relations: bool = True) -> Optional[DossierCandidatureResponse]:
        query = select(DossierCandidature).where(DossierCandidature.id == dossier_id)
        if load_relations:
            query = query.options(
                joinedload(DossierCandidature.utilisateur),
                joinedload(DossierCandidature.formation),
                joinedload(DossierCandidature.session).joinedload(SessionFormation.centre),
                selectinload(DossierCandidature.reclamations).joinedload(Reclamation.auteur),
                selectinload(DossierCandidature.pieces_jointes)
            )
        try:
            logger.info(f"Récupération du dossier ID {dossier_id}")
            result = await self.session.execute(query)
            dossier = result.scalar_one()
            response = DossierCandidatureResponse.model_validate(dossier, from_attributes=True)
            # Calculer le total payé en utilisant les paiements CinetPay
            total_paye = sum(p.montant for p in dossier.session.paiements_cinetpay 
                           if p.utilisateur_id == dossier.utilisateur_id and p.statut == "ACCEPTED")
            response.total_paye = total_paye
            response.reste_a_payer_inscription = (dossier.frais_inscription_montant or 0) - total_paye
            response.reste_a_payer_formation = (dossier.frais_formation_montant or 0) - total_paye
            return response
        except NoResultFound:
            logger.warning(f"Dossier ID {dossier_id} non trouvé")
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"Dossier avec ID {dossier_id} non trouvé.")

    async def update(self, dossier_id: int, data: DossierCandidatureUpdate) -> DossierCandidatureResponse:
        result = await self.session.execute(
            select(DossierCandidature).where(DossierCandidature.id == dossier_id)
            .options(
                joinedload(DossierCandidature.utilisateur),
                joinedload(DossierCandidature.formation),
                joinedload(DossierCandidature.session)
            )
        )
        dossier = result.scalar_one_or_none()
        
        if not dossier:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"Dossier avec ID {dossier_id} non trouvé.")
        
        logger.info(f"Mise à jour du dossier ID {dossier_id}")
        update_data = data.model_dump(exclude_unset=True, exclude={"pieces_jointes", "reclamations"})
        for key, value in update_data.items():
            setattr(dossier, key, value)
        if data.pieces_jointes:
            dossier.pieces_jointes = [PieceJointe(**pj.model_dump(), dossier=dossier) for pj in data.pieces_jointes]
        if data.reclamations:
            dossier.reclamations = [Reclamation(**rec.model_dump(), dossier=dossier) for rec in data.reclamations]
        await self.commit()
        await self.refresh(dossier)
        response = DossierCandidatureResponse.model_validate(dossier, from_attributes=True)
        # Calculer le total payé en utilisant les paiements CinetPay
        total_paye = sum(p.montant for p in dossier.session.paiements_cinetpay 
                       if p.utilisateur_id == dossier.utilisateur_id and p.statut == "ACCEPTED")
        response.total_paye = total_paye
        response.reste_a_payer_inscription = (dossier.frais_inscription_montant or 0) - total_paye
        response.reste_a_payer_formation = (dossier.frais_formation_montant or 0) - total_paye
        logger.info(f"Dossier ID {dossier_id} mis à jour")
        return response

    async def delete(self, dossier_id: int):
        result = await self.session.execute(select(DossierCandidature).where(DossierCandidature.id == dossier_id))
        dossier = result.scalar_one_or_none()
        
        if not dossier:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"Dossier avec ID {dossier_id} non trouvé.")
        
        logger.info(f"Suppression du dossier ID {dossier_id}")
        await self.session.delete(dossier)
        await self.commit()
        logger.info(f"Dossier ID {dossier_id} supprimé")

    async def get_all(self, skip: int = 0, limit: int = 100) -> List[DossierCandidatureResponse]:
        logger.info(f"Récupération des dossiers de candidature (skip: {skip}, limit: {limit})")
        
        query = select(DossierCandidature).options(
            joinedload(DossierCandidature.utilisateur),
            joinedload(DossierCandidature.formation),
            joinedload(DossierCandidature.session).joinedload(SessionFormation.centre),
            selectinload(DossierCandidature.reclamations).joinedload(Reclamation.auteur),
            selectinload(DossierCandidature.pieces_jointes)
        ).offset(skip).limit(limit)
        
        result = await self.session.execute(query)
        dossiers = result.scalars().all()
        
        return await self._format_dossiers_response(dossiers)

    async def get_by_candidat(self, candidat_id: int, skip: int = 0, limit: int = 100) -> List[DossierCandidatureResponse]:
        logger.info(f"Récupération des candidatures du candidat ID {candidat_id} (skip: {skip}, limit: {limit})")
        
        query = select(DossierCandidature).where(DossierCandidature.utilisateur_id == candidat_id).options(
            joinedload(DossierCandidature.utilisateur),
            joinedload(DossierCandidature.formation),
            joinedload(DossierCandidature.session).joinedload(SessionFormation.centre),
            selectinload(DossierCandidature.reclamations).joinedload(Reclamation.auteur),
            selectinload(DossierCandidature.pieces_jointes)
        ).offset(skip).limit(limit)
        
        result = await self.session.execute(query)
        dossiers = result.scalars().all()
        
        return await self._format_dossiers_response(dossiers)

    async def _format_dossiers_response(self, dossiers: List[DossierCandidature]) -> List[DossierCandidatureResponse]:
        """Formate une liste de dossiers en réponse optimisée"""
        responses = []
        for dossier in dossiers:
            try:
                # Gestion des cas où formation_id est None
                if dossier.formation_id is None and dossier.session and hasattr(dossier.session, 'formation_id'):
                    dossier.formation_id = dossier.session.formation_id
                
                # S'assurer que formation n'est pas None si formation_id existe
                if dossier.formation_id and not dossier.formation and dossier.session and hasattr(dossier.session, 'formation'):
                    dossier.formation = dossier.session.formation
                
                response = DossierCandidatureResponse.model_validate(dossier, from_attributes=True)
                
                # Calcul optimisé des montants avec gestion des statuts de paiement corrects
                total_paye = sum(float(p.montant) for p in dossier.session.paiements_cinetpay 
                               if p.utilisateur_id == dossier.utilisateur_id and p.statut == "ACCEPTED")
                response.total_paye = total_paye
                
                # Calcul des restes à payer avec gestion des valeurs None
                frais_inscription = float(dossier.frais_inscription_montant) if dossier.frais_inscription_montant else 0.0
                frais_formation = float(dossier.frais_formation_montant) if dossier.frais_formation_montant else 0.0
                
                response.reste_a_payer_inscription = max(frais_inscription - total_paye, 0.0)
                response.reste_a_payer_formation = max(frais_formation - total_paye, 0.0)
                
                responses.append(response)
                
            except Exception as e:
                logger.error(f"Erreur lors du formatage du dossier {dossier.id}: {e}")
                logger.error(f"formation_id: {dossier.formation_id}, formation: {dossier.formation}")
                # Créer une réponse minimale plutôt que d'ignorer le dossier
                try:
                    response_dict = {
                        "id": dossier.id,
                        "utilisateur_id": dossier.utilisateur_id,
                        "formation_id": dossier.formation_id,
                        "session_id": getattr(dossier, 'session_id', None),
                        "numero_candidature": dossier.numero_candidature,
                        "statut": dossier.statut,
                        "date_soumission": dossier.date_soumission,
                        "objet": getattr(dossier, 'objet', None),
                        "motif_refus": getattr(dossier, 'motif_refus', None),
                        "frais_inscription_montant": float(dossier.frais_inscription_montant) if dossier.frais_inscription_montant else None,
                        "frais_formation_montant": float(dossier.frais_formation_montant) if dossier.frais_formation_montant else None,
                        "devise": getattr(dossier, 'devise', None),
                        "created_at": getattr(dossier, 'created_at', None),
                        "updated_at": getattr(dossier, 'updated_at', None),
                        "utilisateur": UtilisateurLight.model_validate(dossier.utilisateur, from_attributes=True) if dossier.utilisateur else None,
                        "formation": FormationLight.model_validate(dossier.formation, from_attributes=True) if dossier.formation else None,
                        "session": None,
                        "pieces_jointes": [],
                        "reclamations": [],
                        "total_paye": 0.0,
                        "reste_a_payer_inscription": 0.0,
                        "reste_a_payer_formation": 0.0
                    }
                    response = DossierCandidatureResponse(**response_dict)
                    responses.append(response)
                except Exception as e2:
                    logger.error(f"Impossible de créer une réponse minimale pour le dossier {dossier.id}: {e2}")
                    continue
                    
        return responses



    async def changer_statut(self, dossier_id: int, statut_data: DossierStatutUpdate) -> DossierStatutResponse:
        """Méthode optimisée pour changer le statut avec validation améliorée"""
        # Définir les transitions de statut valides
        VALID_TRANSITIONS = {
            StatutCandidatureEnum.RECUE: {StatutCandidatureEnum.EN_ETUDE, StatutCandidatureEnum.ANNULEE},
            StatutCandidatureEnum.EN_ETUDE: {StatutCandidatureEnum.ACCEPTÉE, StatutCandidatureEnum.REFUSÉE, StatutCandidatureEnum.ANNULEE},
            StatutCandidatureEnum.ACCEPTÉE: {StatutCandidatureEnum.ANNULEE},
            StatutCandidatureEnum.REFUSÉE: {StatutCandidatureEnum.ANNULEE},
            StatutCandidatureEnum.ANNULEE: set()  # Aucune transition possible depuis ANNULEE
        }

        # Récupérer le dossier avec les relations nécessaires
        query = select(DossierCandidature).where(DossierCandidature.id == dossier_id).options(
            joinedload(DossierCandidature.utilisateur),
            joinedload(DossierCandidature.formation),
            joinedload(DossierCandidature.session)
        )
        result = await self.session.execute(query)
        dossier = result.scalar_one_or_none()

        if not dossier:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"Dossier avec ID {dossier_id} non trouvé.")

        # Vérifier la transition de statut
        if statut_data.statut == dossier.statut:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Le dossier est déjà dans l'état {statut_data.statut.value}."
            )

        if statut_data.statut not in VALID_TRANSITIONS[dossier.statut]:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Transition de {dossier.statut.value} à {statut_data.statut.value} non autorisée."
            )

        # Vérifier le motif_refus pour REFUSÉE
        if statut_data.statut == StatutCandidatureEnum.REFUSÉE and not statut_data.motif_refus:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Un motif de refus est requis pour refuser une candidature."
            )

        # Mettre à jour le dossier
        logger.info(f"Changement de statut du dossier ID {dossier_id} de {dossier.statut.value} à {statut_data.statut.value}")
        ancien_statut = dossier.statut
        dossier.statut = statut_data.statut
        if statut_data.motif_refus:
            dossier.motif_refus = statut_data.motif_refus
        if statut_data.date_soumission:
            dossier.date_soumission = statut_data.date_soumission
            
        await self.commit()
        await self.refresh(dossier)

        return DossierStatutResponse(
            id=dossier.id,
            numero_candidature=dossier.numero_candidature,
            ancien_statut=ancien_statut,
            nouveau_statut=dossier.statut,
            motif_refus=dossier.motif_refus,
            date_soumission=dossier.date_soumission,
            commentaire=statut_data.commentaire,
            date_modification=datetime.now()
        )


    
# ────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────
#  PIECES JOINTES (Optimisé: Ajout de date_soumission, motif_refus; frais hérités mais surchargables)
# ────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────

class PieceJointeService(BaseService):
    async def create(self, data: PieceJointeCreate, dossier_id: Optional[int] = None) -> PieceJointeLight:
        if dossier_id:
            data.dossier_id = dossier_id
        logger.info("Création d'une pièce jointe")
        piece = PieceJointe(**data.model_dump())
        self.session.add(piece)
        await self.commit()
        await self.refresh(piece)
        logger.info(f"Pièce jointe créée avec ID {piece.id}")
        
        # Retourner un schéma simple pour éviter les erreurs de validation
        return PieceJointeLight(
            id=piece.id,
            type_document=piece.type_document,
            chemin_fichier=piece.chemin_fichier
        )

    async def get_by_id(self, piece_id: int, load_relations: bool = True) -> Optional[PieceJointeLight]:
        query = select(PieceJointe).where(PieceJointe.id == piece_id)
        try:
            logger.info(f"Récupération de la pièce jointe ID {piece_id}")
            result = await self.session.execute(query)
            piece = result.scalar_one()
            
            # Retourner un schéma simple pour éviter les erreurs de validation
            return PieceJointeLight(
                id=piece.id,
                type_document=piece.type_document,
                chemin_fichier=piece.chemin_fichier
            )
        except NoResultFound:
            logger.warning(f"Pièce jointe ID {piece_id} non trouvée")
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"Pièce jointe avec ID {piece_id} non trouvée.")

    async def update(self, piece_id: int, data: PieceJointeUpdate) -> PieceJointeLight:
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
        
        # Retourner un schéma simple pour éviter les erreurs de validation
        return PieceJointeLight(
            id=piece.id,
            type_document=piece.type_document,
            chemin_fichier=piece.chemin_fichier
        )

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
    async def _generate_unique_numero_reclamation(self) -> str:
        """Génère un numéro de réclamation unique de 10 caractères"""
        while True:
            alphabet = string.digits + string.ascii_uppercase
            numero = ''.join(secrets.choice(alphabet) for _ in range(10))
            result = await self.session.execute(
                select(Reclamation).where(Reclamation.numero_reclamation == numero)
            )
            if not result.scalar_one_or_none():
                return numero
    
    async def create(self, data: ReclamationCreate, dossier_id: Optional[int] = None) -> ReclamationResponse:
        if dossier_id:
            data.dossier_id = dossier_id
        
        logger.info("Création d'une réclamation")
        
        # Récupérer automatiquement l'auteur_id à partir du dossier_id
        auteur_id = None
        if hasattr(data, 'auteur_id') and data.auteur_id:
            auteur_id = data.auteur_id
        else:
            # Récupérer automatiquement depuis le dossier
            dossier_query = select(DossierCandidature).where(DossierCandidature.id == data.dossier_id)
            result = await self.session.execute(dossier_query)
            dossier = result.scalar_one_or_none()
            
            if not dossier:
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND, 
                    detail=f"Dossier de candidature avec ID {data.dossier_id} non trouvé"
                )
            
            auteur_id = dossier.utilisateur_id
            logger.info(f"Auteur ID {auteur_id} récupéré automatiquement depuis le dossier {data.dossier_id}")
        
        # Générer automatiquement le numéro de réclamation
        numero_reclamation = await self._generate_unique_numero_reclamation()
        
        # Préparer les données avec les valeurs automatiques
        reclamation_data = data.model_dump(exclude={"numero_reclamation", "statut", "date_cloture"})
        reclamation_data["numero_reclamation"] = numero_reclamation
        reclamation_data["statut"] = StatutReclamationEnum.NOUVEAU.value
        reclamation_data["date_cloture"] = None  # Sera définie lors de la clôture
        reclamation_data["auteur_id"] = auteur_id  # Ajouter l'auteur_id récupéré
        
        reclamation = Reclamation(**reclamation_data)
        self.session.add(reclamation)
        await self.commit()
        await self.refresh(reclamation)
        
        logger.info(f"Réclamation créée avec ID {reclamation.id} et numéro {numero_reclamation}")
        
        # Créer manuellement la réponse pour éviter les erreurs de greenlet
        response_data = {
            "id": reclamation.id,
            "dossier_id": reclamation.dossier_id,
            "auteur_id": reclamation.auteur_id,
            "numero_reclamation": reclamation.numero_reclamation,
            "objet": reclamation.objet,
            "type_reclamation": reclamation.type_reclamation,
            "priorite": reclamation.priorite,
            "statut": reclamation.statut,
            "description": reclamation.description,
            "date_cloture": reclamation.date_cloture,
            "created_at": reclamation.created_at,
            "updated_at": reclamation.updated_at,
            "dossier": None,  # Pas de relation chargée
            "auteur": None     # Pas de relation chargée
        }
        
        return ReclamationResponse(**response_data)

    async def get_all(self, skip: int = 0, limit: int = 100) -> List[ReclamationResponse]:
        """Récupère toutes les réclamations avec pagination"""
        query = select(Reclamation).offset(skip).limit(limit)
        logger.info(f"Récupération de toutes les réclamations (skip: {skip}, limit: {limit})")
        result = await self.session.execute(query)
        reclamations_list = result.scalars().all()
        
        # Créer manuellement les réponses pour éviter les erreurs de greenlet
        responses = []
        for rec in reclamations_list:
            response_data = {
                "id": rec.id,
                "dossier_id": rec.dossier_id,
                "auteur_id": rec.auteur_id,
                "numero_reclamation": rec.numero_reclamation,
                "objet": rec.objet,
                "type_reclamation": rec.type_reclamation,
                "priorite": rec.priorite,
                "statut": rec.statut,
                "description": rec.description,
                "date_cloture": rec.date_cloture,
                "created_at": rec.created_at,
                "updated_at": rec.updated_at,
                "dossier": None,  # Pas de relation chargée
                "auteur": None     # Pas de relation chargée
            }
            responses.append(ReclamationResponse(**response_data))
        
        return responses

    async def get_by_id(self, reclamation_id: int, load_relations: bool = True) -> Optional[ReclamationResponse]:
        query = select(Reclamation).where(Reclamation.id == reclamation_id)
        try:
            logger.info(f"Récupération de la réclamation ID {reclamation_id}")
            result = await self.session.execute(query)
            reclamation = result.scalar_one()
            
            # Créer manuellement la réponse pour éviter les erreurs de greenlet
            response_data = {
                "id": reclamation.id,
                "dossier_id": reclamation.dossier_id,
                "auteur_id": reclamation.auteur_id,
                "numero_reclamation": reclamation.numero_reclamation,
                "objet": reclamation.objet,
                "type_reclamation": reclamation.type_reclamation,
                "priorite": reclamation.priorite,
                "statut": reclamation.statut,
                "description": reclamation.description,
                "date_cloture": reclamation.date_cloture,
                "created_at": reclamation.created_at,
                "updated_at": reclamation.updated_at,
                "dossier": None,  # Pas de relation chargée
                "auteur": None     # Pas de relation chargée
            }
            
            return ReclamationResponse(**response_data)
        except NoResultFound:
            logger.warning(f"Réclamation ID {reclamation_id} non trouvée")
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"Réclamation avec ID {reclamation_id} non trouvée.")

    async def update(self, reclamation_id: int, data: ReclamationUpdate) -> ReclamationResponse:
        # Récupérer directement la réclamation depuis la base de données
        result = await self.session.execute(select(Reclamation).where(Reclamation.id == reclamation_id))
        reclamation = result.scalar_one_or_none()
        
        if not reclamation:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"Réclamation avec ID {reclamation_id} non trouvée.")
        
        # Vérifier que la réclamation n'est pas clôturée
        if reclamation.statut == StatutReclamationEnum.CLOTURE.value:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST, 
                detail="Impossible de modifier une réclamation clôturée. Le statut est définitif."
            )
        
        logger.info(f"Mise à jour de la réclamation ID {reclamation_id}")
        
        # Exclure les champs gérés par le système
        update_data = data.model_dump(exclude_unset=True, exclude={"statut", "date_cloture", "numero_reclamation"})
        
        for key, value in update_data.items():
            setattr(reclamation, key, value)
        
        await self.commit()
        await self.refresh(reclamation)
        logger.info(f"Réclamation ID {reclamation_id} mise à jour")
        
        # Créer manuellement la réponse pour éviter les erreurs de greenlet
        response_data = {
            "id": reclamation.id,
            "dossier_id": reclamation.dossier_id,
            "auteur_id": reclamation.auteur_id,
            "numero_reclamation": reclamation.numero_reclamation,
            "objet": reclamation.objet,
            "type_reclamation": reclamation.type_reclamation,
            "priorite": reclamation.priorite,
            "statut": reclamation.statut,
            "description": reclamation.description,
            "date_cloture": reclamation.date_cloture,
            "created_at": reclamation.created_at,
            "updated_at": reclamation.updated_at,
            "dossier": None,  # Pas de relation chargée
            "auteur": None     # Pas de relation chargée
        }
        
        return ReclamationResponse(**response_data)

    async def change_status(self, reclamation_id: int, new_status: str, commentaire: Optional[str] = None) -> ReclamationResponse:
        """Change le statut d'une réclamation selon les règles de transition"""
        result = await self.session.execute(select(Reclamation).where(Reclamation.id == reclamation_id))
        reclamation = result.scalar_one_or_none()
        
        if not reclamation:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"Réclamation avec ID {reclamation_id} non trouvée.")
        
        # Vérifier que la réclamation n'est pas clôturée
        if reclamation.statut == StatutReclamationEnum.CLOTURE.value:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST, 
                detail="Impossible de modifier le statut d'une réclamation clôturée. Le statut est définitif."
            )
        
        # Validation du statut
        valid_statuses = [StatutReclamationEnum.NOUVEAU, StatutReclamationEnum.EN_COURS, StatutReclamationEnum.CLOTURE]
        if new_status not in [s.value for s in valid_statuses]:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=f"Statut invalide. Statuts autorisés: {[s.value for s in valid_statuses]}")
        
        # Règles de transition de statut
        current_status = reclamation.statut
        
        # Règle 1: Pour passer à EN_COURS, la réclamation doit être NOUVEAU
        if new_status == StatutReclamationEnum.EN_COURS.value and current_status != StatutReclamationEnum.NOUVEAU.value:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST, 
                detail=f"Impossible de passer au statut 'EN_COURS'. La réclamation doit d'abord être au statut 'NOUVEAU'. Statut actuel: {current_status}"
            )
        
        # Règle 2: Pour passer à CLOTURE, la réclamation doit être EN_COURS
        if new_status == StatutReclamationEnum.CLOTURE.value and current_status != StatutReclamationEnum.EN_COURS.value:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST, 
                detail=f"Impossible de clôturer la réclamation. Elle doit d'abord être au statut 'EN_COURS'. Statut actuel: {current_status}"
            )
        
        # Règle 3: Pas de retour en arrière (NOUVEAU -> EN_COURS -> CLOTURE uniquement)
        if current_status == StatutReclamationEnum.EN_COURS.value and new_status == StatutReclamationEnum.NOUVEAU.value:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST, 
                detail="Impossible de revenir au statut 'NOUVEAU' depuis 'EN_COURS'. Seule la progression vers 'CLOTURE' est autorisée."
            )
        
        logger.info(f"Changement de statut de la réclamation ID {reclamation_id} de '{current_status}' vers '{new_status}'")
        
        # Mise à jour du statut
        reclamation.statut = new_status
        
        # Si le statut est 'clôturé', ajouter la date de clôture automatiquement
        if new_status == StatutReclamationEnum.CLOTURE.value:
            reclamation.date_cloture = datetime.utcnow()
            logger.info(f"Date de clôture automatiquement définie pour la réclamation ID {reclamation_id}")
        
        # Ajouter le commentaire si fourni
        if commentaire:
            # Ici vous pourriez ajouter le commentaire dans un champ approprié
            # ou créer une table de commentaires séparée
            pass
        
        await self.commit()
        await self.refresh(reclamation)
        logger.info(f"Statut de la réclamation ID {reclamation_id} changé vers '{new_status}'")
        
        # Créer manuellement la réponse pour éviter les erreurs de greenlet
        response_data = {
            "id": reclamation.id,
            "dossier_id": reclamation.dossier_id,
            "auteur_id": reclamation.auteur_id,
            "numero_reclamation": reclamation.numero_reclamation,
            "objet": reclamation.objet,
            "type_reclamation": reclamation.type_reclamation,
            "priorite": reclamation.priorite,
            "statut": reclamation.statut,
            "description": reclamation.description,
            "date_cloture": reclamation.date_cloture,
            "created_at": reclamation.created_at,
            "updated_at": reclamation.updated_at,
            "dossier": None,  # Pas de relation chargée
            "auteur": None     # Pas de relation chargée
        }
        
        return ReclamationResponse(**response_data)

    async def delete(self, reclamation_id: int):
        # Récupérer directement la réclamation depuis la base de données
        result = await self.session.execute(select(Reclamation).where(Reclamation.id == reclamation_id))
        reclamation = result.scalar_one_or_none()
        
        if not reclamation:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"Réclamation avec ID {reclamation_id} non trouvée.")
        
        # Vérifier que la réclamation n'est pas clôturée
        if reclamation.statut == StatutReclamationEnum.CLOTURE.value:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST, 
                detail="Impossible de supprimer une réclamation clôturée. Le statut est définitif."
            )
        
        logger.info(f"Suppression de la réclamation ID {reclamation_id}")
        await self.session.delete(reclamation)
        await self.commit()
        logger.info(f"Réclamation ID {reclamation_id} supprimée")

    async def get_by_user(self, user_id: int, skip: int = 0, limit: int = 100) -> List[ReclamationResponse]:
        """Récupère toutes les réclamations d'un utilisateur spécifique"""
        query = select(Reclamation).where(Reclamation.auteur_id == user_id).offset(skip).limit(limit)
        logger.info(f"Récupération des réclamations de l'utilisateur ID {user_id} (skip: {skip}, limit: {limit})")
        result = await self.session.execute(query)
        reclamations_list = result.scalars().all()
        
        # Créer manuellement les réponses pour éviter les erreurs de greenlet
        responses = []
        for rec in reclamations_list:
            response_data = {
                "id": rec.id,
                "dossier_id": rec.dossier_id,
                "auteur_id": rec.auteur_id,
                "numero_reclamation": rec.numero_reclamation,
                "objet": rec.objet,
                "type_reclamation": rec.type_reclamation,
                "priorite": rec.priorite,
                "statut": rec.statut,
                "description": rec.description,
                "date_cloture": rec.date_cloture,
                "created_at": rec.created_at,
                "updated_at": rec.updated_at,
                "dossier": None,  # Pas de relation chargée
                "auteur": None     # Pas de relation chargée
            }
            responses.append(ReclamationResponse(**response_data))
        
        return responses

# ────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────
# PAIEMENTS (Optimisé: Ajout de date_echeance, index sur reference_externe)
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
        
        # Charger la relation formation pour la réponse
        await self.session.refresh(info_desc, ['formation'])
        logger.info(f"Informations descriptives créées avec ID {info_desc.id}")
        return InformationDescriptiveResponse.model_validate(info_desc, from_attributes=True)

    async def get_by_formation_id(self, formation_id: int) -> Optional[InformationDescriptiveResponse]:
        try:
            logger.info(f"Récupération des informations descriptives pour la formation {formation_id}")
            result = await self.session.execute(
                select(InformationDescriptive)
                .options(selectinload(InformationDescriptive.formation))
                .where(InformationDescriptive.formation_id == formation_id)
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
        
        # Charger la relation formation pour la réponse
        await self.session.refresh(info_obj, ['formation'])
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
        """Crée une nouvelle évaluation"""
        
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
        
        # Créer manuellement la réponse pour éviter les erreurs de greenlet
        response_data = {
            "id": evaluation.id,
            "session_id": evaluation.session_id,
            "formateur_id": evaluation.formateur_id,
            "titre": evaluation.titre,
            "description": evaluation.description,
            "type_evaluation": evaluation.type_evaluation,
            "statut": evaluation.statut,
            "date_ouverture": evaluation.date_ouverture,
            "date_fermeture": evaluation.date_fermeture,
            "duree_minutes": evaluation.duree_minutes,
            "ponderation": evaluation.ponderation,
            "note_minimale": evaluation.note_minimale,
            "nombre_tentatives_max": evaluation.nombre_tentatives_max,
            "type_correction": evaluation.type_correction,
            "instructions": evaluation.instructions,
            "consignes_correction": evaluation.consignes_correction,
            "questions": [],
            "created_at": evaluation.created_at,
            "updated_at": evaluation.updated_at
        }
        
        return EvaluationResponse(**response_data)

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
        
        # Créer manuellement la réponse pour éviter les erreurs de greenlet
        response_data = {
            "id": evaluation.id,
            "session_id": evaluation.session_id,
            "formateur_id": evaluation.formateur_id,
            "titre": evaluation.titre,
            "description": evaluation.description,
            "type_evaluation": evaluation.type_evaluation,
            "statut": evaluation.statut,
            "date_ouverture": evaluation.date_ouverture,
            "date_fermeture": evaluation.date_fermeture,
            "duree_minutes": evaluation.duree_minutes,
            "ponderation": evaluation.ponderation,
            "note_minimale": evaluation.note_minimale,
            "nombre_tentatives_max": evaluation.nombre_tentatives_max,
            "type_correction": evaluation.type_correction,
            "instructions": evaluation.instructions,
            "consignes_correction": evaluation.consignes_correction,
            "questions": [],
            "created_at": evaluation.created_at,
            "updated_at": evaluation.updated_at
        }
        
        return EvaluationResponse(**response_data)

    async def get_by_session(self, session_id: int) -> List[EvaluationResponse]:
        """Récupère toutes les évaluations d'une session"""
        
        query = select(Evaluation).where(Evaluation.session_id == session_id)
        result = await self.session.execute(query)
        evaluations = result.scalars().all()
        
        responses = []
        for evaluation in evaluations:
            response_data = {
                "id": evaluation.id,
                "session_id": evaluation.session_id,
                "formateur_id": evaluation.formateur_id,
                "titre": evaluation.titre,
                "description": evaluation.description,
                "type_evaluation": evaluation.type_evaluation,
                "statut": evaluation.statut,
                "date_ouverture": evaluation.date_ouverture,
                "date_fermeture": evaluation.date_fermeture,
                "duree_minutes": evaluation.duree_minutes,
                "ponderation": evaluation.ponderation,
                "note_minimale": evaluation.note_minimale,
                "nombre_tentatives_max": evaluation.nombre_tentatives_max,
                "type_correction": evaluation.type_correction,
                "instructions": evaluation.instructions,
                "consignes_correction": evaluation.consignes_correction,
                "questions": [],
                "created_at": evaluation.created_at,
                "updated_at": evaluation.updated_at
            }
            responses.append(EvaluationResponse(**response_data))
        
        return responses

    async def update(self, evaluation_id: int, evaluation_data: EvaluationUpdate) -> EvaluationResponse:
        """Met à jour une évaluation"""
        
        evaluation = await self._get_evaluation_or_404(evaluation_id)
        
        # Mettre à jour les champs
        for field, value in evaluation_data.model_dump(exclude_unset=True).items():
            setattr(evaluation, field, value)
        
        await self.commit()
        await self.refresh(evaluation)
        
        # Créer manuellement la réponse pour éviter les erreurs de greenlet
        response_data = {
            "id": evaluation.id,
            "session_id": evaluation.session_id,
            "formateur_id": evaluation.formateur_id,
            "titre": evaluation.titre,
            "description": evaluation.description,
            "type_evaluation": evaluation.type_evaluation,
            "statut": evaluation.statut,
            "date_ouverture": evaluation.date_ouverture,
            "date_fermeture": evaluation.date_fermeture,
            "duree_minutes": evaluation.duree_minutes,
            "ponderation": evaluation.ponderation,
            "note_minimale": evaluation.note_minimale,
            "nombre_tentatives_max": evaluation.nombre_tentatives_max,
            "type_correction": evaluation.type_correction,
            "instructions": evaluation.instructions,
            "consignes_correction": evaluation.consignes_correction,
            "questions": [],
            "created_at": evaluation.created_at,
            "updated_at": evaluation.updated_at
        }
        
        return EvaluationResponse(**response_data)

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
        
        # Créer manuellement la réponse pour éviter les erreurs de greenlet
        response_data = {
            "id": question.id,
            "evaluation_id": question.evaluation_id,
            "question": question.question,
            "type_question": question.type_question,
            "ordre": question.ordre,
            "reponses_possibles": question.reponses_possibles,
            "reponse_correcte": question.reponse_correcte,
            "points": question.points,
            "created_at": question.created_at,
            "updated_at": question.updated_at
        }
        
        return QuestionEvaluationResponse(**response_data)

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
        
        # Créer manuellement la réponse pour éviter les erreurs de greenlet
        response_data = {
            "id": question.id,
            "evaluation_id": question.evaluation_id,
            "question": question.question,
            "type_question": question.type_question,
            "ordre": question.ordre,
            "reponses_possibles": question.reponses_possibles,
            "reponse_correcte": question.reponse_correcte,
            "points": question.points,
            "created_at": question.created_at,
            "updated_at": question.updated_at
        }
        
        return QuestionEvaluationResponse(**response_data)

    async def get_by_evaluation(self, evaluation_id: int) -> List[QuestionEvaluationResponse]:
        """Récupère toutes les questions d'une évaluation"""
        
        query = select(QuestionEvaluation).where(QuestionEvaluation.evaluation_id == evaluation_id).order_by(QuestionEvaluation.ordre)
        result = await self.session.execute(query)
        questions = result.scalars().all()
        
        responses = []
        for question in questions:
            response_data = {
                "id": question.id,
                "evaluation_id": question.evaluation_id,
                "question": question.question,
                "type_question": question.type_question,
                "ordre": question.ordre,
                "reponses_possibles": question.reponses_possibles,
                "reponse_correcte": question.reponse_correcte,
                "points": question.points,
                "created_at": question.created_at,
                "updated_at": question.updated_at
            }
            responses.append(QuestionEvaluationResponse(**response_data))
        
        return responses

    async def update(self, question_id: int, question_data: QuestionEvaluationUpdate) -> QuestionEvaluationResponse:
        """Met à jour une question"""
        
        question = await self._get_question_or_404(question_id)
        
        # Mettre à jour les champs
        for field, value in question_data.model_dump(exclude_unset=True).items():
            setattr(question, field, value)
        
        await self.commit()
        await self.refresh(question)
        
        # Créer manuellement la réponse pour éviter les erreurs de greenlet
        response_data = {
            "id": question.id,
            "evaluation_id": question.evaluation_id,
            "question": question.question,
            "type_question": question.type_question,
            "ordre": question.ordre,
            "reponses_possibles": question.reponses_possibles,
            "reponse_correcte": question.reponse_correcte,
            "points": question.points,
            "created_at": question.created_at,
            "updated_at": question.updated_at
        }
        
        return QuestionEvaluationResponse(**response_data)

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

    async def get_by_resultat_evaluation(self, resultat_id: int) -> List[ReponseCandidatResponse]:
        """Récupère toutes les réponses d'un résultat d'évaluation"""
        
        query = select(ReponseCandidat).where(ReponseCandidat.resultat_id == resultat_id)
        result = await self.session.execute(query)
        reponses = result.scalars().all()
        
        return [ReponseCandidatResponse.model_validate(r, from_attributes=True) for r in reponses]

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
        
        # Créer manuellement la réponse pour éviter les erreurs de greenlet
        response_data = {
            "id": resultat.id,
            "evaluation_id": resultat.evaluation_id,
            "candidat_id": resultat.candidat_id,
            "tentative_numero": resultat.tentative_numero,
            "statut": resultat.statut,
            "date_debut": resultat.date_debut,
            "date_fin": resultat.date_fin,
            "note_obtenue": resultat.note_obtenue,
            "note_maximale": resultat.note_maximale,
            "pourcentage_reussite": resultat.pourcentage_reussite,
            "commentaire_formateur": resultat.commentaire_formateur,
            "commentaire_candidat": resultat.commentaire_candidat,
            "reponses": [],
            "created_at": resultat.created_at,
            "updated_at": resultat.updated_at
        }
        
        return ResultatEvaluationResponse(**response_data)

    async def soumettre_evaluation(self, resultat_id: int, candidat_id: int) -> ResultatEvaluationResponse:
        """Soumet une évaluation (marque comme terminée)"""
        
        # Récupérer le résultat
        resultat_query = select(ResultatEvaluation).where(ResultatEvaluation.id == resultat_id)
        resultat_result = await self.session.execute(resultat_query)
        resultat = resultat_result.scalar_one_or_none()
        
        if not resultat:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Résultat d'évaluation non trouvé"
            )
        
        # Vérifier que le candidat correspond
        if resultat.candidat_id != candidat_id:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Vous ne pouvez pas soumettre cette évaluation"
            )
        
        # Marquer comme terminé
        resultat.date_fin = datetime.now()
        resultat.statut = StatutResultatEnum.EN_ATTENTE
        
        await self.commit()
        await self.refresh(resultat)
        
        # Créer manuellement la réponse pour éviter les erreurs de greenlet
        response_data = {
            "id": resultat.id,
            "evaluation_id": resultat.evaluation_id,
            "candidat_id": resultat.candidat_id,
            "tentative_numero": resultat.tentative_numero,
            "statut": resultat.statut,
            "date_debut": resultat.date_debut,
            "date_fin": resultat.date_fin,
            "note_obtenue": resultat.note_obtenue,
            "note_maximale": resultat.note_maximale,
            "pourcentage_reussite": resultat.pourcentage_reussite,
            "commentaire_formateur": resultat.commentaire_formateur,
            "commentaire_candidat": resultat.commentaire_candidat,
            "reponses": [],
            "created_at": resultat.created_at,
            "updated_at": resultat.updated_at
        }
        
        return ResultatEvaluationResponse(**response_data)

    async def corriger_evaluation(self, resultat_id: int, candidat_id: int, note_obtenue: float, note_maximale: float, commentaire_formateur: str = None, commentaire_candidat: str = None) -> ResultatEvaluationResponse:
        """Corrige manuellement une évaluation"""
        
        resultat = await self._get_resultat_or_404(resultat_id)
        
        # Vérifier que le candidat correspond
        if resultat.candidat_id != candidat_id:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Vous ne pouvez pas corriger cette évaluation"
            )
        
        # Mettre à jour les résultats
        resultat.note_obtenue = note_obtenue
        resultat.note_maximale = note_maximale
        resultat.pourcentage_reussite = (note_obtenue / note_maximale * 100) if note_maximale > 0 else 0
        resultat.commentaire_formateur = commentaire_formateur
        resultat.commentaire_candidat = commentaire_candidat
        resultat.statut = StatutResultatEnum.SUCCES
        
        await self.commit()
        await self.refresh(resultat)
        
        # Créer manuellement la réponse pour éviter les erreurs de greenlet
        response_data = {
            "id": resultat.id,
            "evaluation_id": resultat.evaluation_id,
            "candidat_id": resultat.candidat_id,
            "tentative_numero": resultat.tentative_numero,
            "statut": resultat.statut,
            "date_debut": resultat.date_debut,
            "date_fin": resultat.date_fin,
            "note_obtenue": resultat.note_obtenue,
            "note_maximale": resultat.note_maximale,
            "pourcentage_reussite": resultat.pourcentage_reussite,
            "commentaire_formateur": resultat.commentaire_formateur,
            "commentaire_candidat": resultat.commentaire_candidat,
            "reponses": [],
            "created_at": resultat.created_at,
            "updated_at": resultat.updated_at
        }
        
        return ResultatEvaluationResponse(**response_data)

    async def get_by_id(self, resultat_id: int) -> ResultatEvaluationResponse:
        """Récupère un résultat par son ID"""
        """Récupère un résultat par son ID"""
        
        resultat = await self._get_resultat_or_404(resultat_id)
        
        # Créer manuellement la réponse pour éviter les erreurs de greenlet
        response_data = {
            "id": resultat.id,
            "evaluation_id": resultat.evaluation_id,
            "candidat_id": resultat.candidat_id,
            "tentative_numero": resultat.tentative_numero,
            "statut": resultat.statut,
            "date_debut": resultat.date_debut,
            "date_fin": resultat.date_fin,
            "note_obtenue": resultat.note_obtenue,
            "note_maximale": resultat.note_maximale,
            "pourcentage_reussite": resultat.pourcentage_reussite,
            "commentaire_formateur": resultat.commentaire_formateur,
            "commentaire_candidat": resultat.commentaire_candidat,
            "reponses": [],
            "created_at": resultat.created_at,
            "updated_at": resultat.updated_at
        }
        
        return ResultatEvaluationResponse(**response_data)

    async def get_by_evaluation(self, evaluation_id: int) -> List[ResultatEvaluationResponse]:
        """Récupère tous les résultats d'une évaluation"""
        
        query = select(ResultatEvaluation).where(ResultatEvaluation.evaluation_id == evaluation_id)
        result = await self.session.execute(query)
        resultats = result.scalars().all()
        
        responses = []
        for resultat in resultats:
            response_data = {
                "id": resultat.id,
                "evaluation_id": resultat.evaluation_id,
                "candidat_id": resultat.candidat_id,
                "tentative_numero": resultat.tentative_numero,
                "statut": resultat.statut,
                "date_debut": resultat.date_debut,
                "date_fin": resultat.date_fin,
                "note_obtenue": resultat.note_obtenue,
                "note_maximale": resultat.note_maximale,
                "pourcentage_reussite": resultat.pourcentage_reussite,
                "commentaire_formateur": resultat.commentaire_formateur,
                "commentaire_candidat": resultat.commentaire_candidat,
                "reponses": [],
                "created_at": resultat.created_at,
                "updated_at": resultat.updated_at
            }
            responses.append(ResultatEvaluationResponse(**response_data))
        
        return responses

    async def get_by_candidat(self, candidat_id: int) -> List[ResultatEvaluationResponse]:
        """Récupère tous les résultats d'un candidat"""
        
        query = select(ResultatEvaluation).where(ResultatEvaluation.candidat_id == candidat_id)
        result = await self.session.execute(query)
        resultats = result.scalars().all()
        
        responses = []
        for resultat in resultats:
            response_data = {
                "id": resultat.id,
                "evaluation_id": resultat.evaluation_id,
                "candidat_id": resultat.candidat_id,
                "tentative_numero": resultat.tentative_numero,
                "statut": resultat.statut,
                "date_debut": resultat.date_debut,
                "date_fin": resultat.date_fin,
                "note_obtenue": resultat.note_obtenue,
                "note_maximale": resultat.note_maximale,
                "pourcentage_reussite": resultat.pourcentage_reussite,
                "commentaire_formateur": resultat.commentaire_formateur,
                "commentaire_candidat": resultat.commentaire_candidat,
                "reponses": [],
                "created_at": resultat.created_at,
                "updated_at": resultat.updated_at
            }
            responses.append(ResultatEvaluationResponse(**response_data))
        
        return responses

    async def update(self, resultat_id: int, resultat_data: dict) -> ResultatEvaluationResponse:
        """Met à jour un résultat d'évaluation"""
        
        resultat = await self._get_resultat_or_404(resultat_id)
        
        # Mettre à jour les champs
        for field, value in resultat_data.items():
            if hasattr(resultat, field):
                setattr(resultat, field, value)
        
        await self.commit()
        await self.refresh(resultat)
        
        # Créer manuellement la réponse pour éviter les erreurs de greenlet
        response_data = {
            "id": resultat.id,
            "evaluation_id": resultat.evaluation_id,
            "candidat_id": resultat.candidat_id,
            "tentative_numero": resultat.tentative_numero,
            "statut": resultat.statut,
            "date_debut": resultat.date_debut,
            "date_fin": resultat.date_fin,
            "note_obtenue": resultat.note_obtenue,
            "note_maximale": resultat.note_maximale,
            "pourcentage_reussite": resultat.pourcentage_reussite,
            "commentaire_formateur": resultat.commentaire_formateur,
            "commentaire_candidat": resultat.commentaire_candidat,
            "reponses": [],
            "created_at": resultat.created_at,
            "updated_at": resultat.updated_at
        }
        
        return ResultatEvaluationResponse(**response_data)

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

# Configuration Redis optimisée
REDIS_CONFIG = {
    "host": "172.19.0.76",
    "port": 6379,
    "db": 0,
    "decode_responses": True,
    "retry_on_timeout": True,
    "socket_keepalive": True,
    "socket_keepalive_options": {},
    "health_check_interval": 30
}

# Configuration des opérateurs de paiement
PAYMENT_OPERATORS = {
    "cinetpay": {
        "name": "CinetPay",
        "api_key": "1234567890abcdef1234567890abcdef12345678",
        "site_id": "123456",
        "secret_key": "abcdef1234567890abcdef1234567890abcdef12",
        "api_url": "https://api-checkout.cinetpay.com/v2/payment",
        "verify_url": "https://api-checkout.cinetpay.com/v2/payment/check",
        "supported_currencies": ["XAF", "XOF", "EUR", "USD"],
        "supported_methods": ["MOBILE_MONEY", "CARD", "WALLET"]
    }
    # Ajouter d'autres opérateurs ici
}

class PaymentService:
    """Service unifié pour la gestion des paiements avec support multi-opérateurs"""
    
    def __init__(self, session: AsyncSession):
        self.session = session
        self.redis_client = None
        self._init_redis()
    
    def _init_redis(self):
        """Initialiser la connexion Redis avec gestion d'erreurs"""
        try:
            import redis
            self.redis_client = redis.Redis(**REDIS_CONFIG)
            # Test de connexion
            self.redis_client.ping()
            logging.info("✅ Connexion Redis établie")
        except Exception as e:
            logging.warning(f"⚠️ Redis non disponible: {e}")
            self.redis_client = None
    
    def _generate_transaction_id(self, utilisateur_id: int, session_id: int, operator: str = "cinetpay") -> str:
        """Générer un ID de transaction unique avec préfixe opérateur"""
        timestamp = datetime.now().strftime("%Y%m%d%H%M%S%f")[:-3]
        return f"{operator.upper()}_{utilisateur_id}_{session_id}_{timestamp}"
    
    def _get_default_urls(self, transaction_id: str) -> tuple[str, str]:
        """Générer les URLs par défaut pour les notifications et retours"""
        base_url = "https://api.lafaom.com"  # À configurer selon l'environnement
        notify_url = f"{base_url}/api/v1/paiements/notification"
        return_url = f"{base_url}/api/v1/paiements/retour/{transaction_id}"
        return notify_url, return_url
    
    async def create_payment(self, paiement_data: PaiementCreate, operator: str = "cinetpay") -> PaiementResponse:
        """Créer un nouveau paiement avec gestion automatique des champs système"""
        try:
            # Validation des données
            if paiement_data.montant <= 0:
                raise HTTPException(status_code=400, detail="Le montant doit être positif")
            
            # Générer les champs système
            transaction_id = self._generate_transaction_id(
                paiement_data.utilisateur_id, 
                paiement_data.session_id, 
                operator
            )
            
            # URLs par défaut si non fournies
            notify_url = paiement_data.notify_url or self._get_default_urls(transaction_id)[0]
            return_url = paiement_data.return_url or self._get_default_urls(transaction_id)[1]
            
            # Créer l'enregistrement en base
            paiement = PaiementCinetPay(
                transaction_id=transaction_id,
                utilisateur_id=paiement_data.utilisateur_id,
                session_id=paiement_data.session_id,
                montant=paiement_data.montant,
                devise=paiement_data.devise,
                description=paiement_data.description,
                type_paiement=paiement_data.type_paiement,
                statut="EN_ATTENTE",
                notify_url=notify_url,
                return_url=return_url,
                metadata_paiement=paiement_data.metadata_paiement
            )
            
            self.session.add(paiement)
            await self.session.commit()
            await self.session.refresh(paiement)
            
            # Initier le paiement avec l'opérateur
            payment_result = await self._initiate_payment_with_operator(paiement, operator)
            
            # Ajouter à la queue de vérification
            await self._add_to_verification_queue(paiement.transaction_id)
            
            return PaiementResponse.model_validate(paiement, from_attributes=True)
            
        except Exception as e:
            await self.session.rollback()
            logging.error(f"Erreur lors de la création du paiement: {e}")
            raise HTTPException(status_code=500, detail=str(e))
    
    async def _initiate_payment_with_operator(self, paiement: PaiementCinetPay, operator: str) -> dict:
        """Initier le paiement avec l'opérateur spécifié"""
        if operator == "cinetpay":
            return await self._initiate_cinetpay_payment(paiement)
        else:
            raise HTTPException(status_code=400, detail=f"Opérateur {operator} non supporté")
    
    async def _initiate_cinetpay_payment(self, paiement: PaiementCinetPay) -> dict:
        """Initier un paiement CinetPay"""
        try:
            import aiohttp
            
            operator_config = PAYMENT_OPERATORS["cinetpay"]
            
            # Préparer les données pour CinetPay
            payment_data = {
                "apikey": operator_config["api_key"],
                "site_id": operator_config["site_id"],
                "transaction_id": paiement.transaction_id,
                "amount": paiement.montant,
                "currency": paiement.devise,
                "description": paiement.description,
                "notify_url": paiement.notify_url,
                "return_url": paiement.return_url,
                "channels": "ALL",
                "lang": "fr",
                "customer_name": f"Client {paiement.utilisateur_id}",  # Ajouté
                "customer_email": f"client{paiement.utilisateur_id}@test.com",  # Ajouté
                "customer_phone_number": "+1234567890",  # Ajouté
                "customer_address": "Adresse test",  # Ajouté
                "customer_city": "Ville test",  # Ajouté
                "customer_country": "CM",  # Ajouté
                "customer_zip_code": "00000"  # Ajouté
            }
            
            async with aiohttp.ClientSession() as session:
                async with session.post(operator_config["api_url"], json=payment_data) as response:
                    result = await response.json()
                    
                    if result.get("code") == "201":
                        # Mettre à jour le paiement avec les données de CinetPay
                        paiement.payment_url = result["data"]["payment_url"]
                        paiement.payment_token = result["data"]["payment_token"]
                        await self.session.commit()
                        
                        return result
                    else:
                        error_msg = result.get("message", "Erreur inconnue")
                        paiement.error_message = error_msg
                        paiement.statut = "ECHEC"
                        await self.session.commit()
                        
                        raise HTTPException(status_code=400, detail=error_msg)
                        
        except Exception as e:
            logging.error(f"Erreur lors de l'initiation CinetPay: {e}")
            raise HTTPException(status_code=500, detail=str(e))
    
    async def _add_to_verification_queue(self, transaction_id: str):
        """Ajouter un paiement à la queue de vérification Redis"""
        if not self.redis_client:
            logging.warning("Redis non disponible - queue de vérification ignorée")
            return
        
        try:
            # Ajouter à la queue Redis
            queue_data = {
                "transaction_id": transaction_id,
                "next_check": datetime.now().isoformat(),
                "attempts": 0,
                "max_attempts": 20
            }
            
            self.redis_client.hset(
                f"payment_queue:{transaction_id}",
                mapping=queue_data
            )
            
            # Ajouter à la liste des transactions à vérifier
            self.redis_client.zadd(
                "pending_payments",
                {transaction_id: datetime.now().timestamp()}
            )
            
            logging.info(f"✅ Paiement {transaction_id} ajouté à la queue de vérification")
            
        except Exception as e:
            logging.error(f"Erreur lors de l'ajout à la queue Redis: {e}")
    
    async def get_payment_by_id(self, payment_id: int) -> PaiementResponse:
        """Récupérer un paiement par ID"""
        result = await self.session.execute(
            select(PaiementCinetPay).where(PaiementCinetPay.id == payment_id)
        )
        paiement = result.scalar_one_or_none()
        
        if not paiement:
            raise HTTPException(status_code=404, detail="Paiement non trouvé")
        
        return PaiementResponse.model_validate(paiement, from_attributes=True)
    
    async def get_payment_by_transaction_id(self, transaction_id: str) -> PaiementResponse:
        """Récupérer un paiement par transaction_id"""
        result = await self.session.execute(
            select(PaiementCinetPay).where(PaiementCinetPay.transaction_id == transaction_id)
        )
        paiement = result.scalar_one_or_none()
        
        if not paiement:
            raise HTTPException(status_code=404, detail="Paiement non trouvé")
        
        return PaiementResponse.model_validate(paiement, from_attributes=True)
    
    async def get_payments_by_user(self, utilisateur_id: int) -> List[PaiementResponse]:
        """Récupérer tous les paiements d'un utilisateur"""
        result = await self.session.execute(
            select(PaiementCinetPay)
            .where(PaiementCinetPay.utilisateur_id == utilisateur_id)
            .order_by(PaiementCinetPay.date_creation.desc())
        )
        paiements = result.scalars().all()
        
        return [PaiementResponse.model_validate(p, from_attributes=True) for p in paiements]
    
    async def verify_payment_status(self, transaction_id: str) -> dict:
        """Vérifier le statut d'un paiement auprès de l'opérateur"""
        try:
            # Récupérer le paiement
            paiement = await self.get_payment_by_transaction_id(transaction_id)
            
            # Déterminer l'opérateur à partir du transaction_id
            operator = "cinetpay"  # Par défaut, à améliorer selon le préfixe
            
            if operator == "cinetpay":
                return await self._verify_cinetpay_payment(transaction_id)
            else:
                raise HTTPException(status_code=400, detail=f"Opérateur {operator} non supporté")
                
        except Exception as e:
            logging.error(f"Erreur lors de la vérification: {e}")
            raise HTTPException(status_code=500, detail=str(e))
    
    async def _verify_cinetpay_payment(self, transaction_id: str) -> dict:
        """Vérifier le statut d'un paiement CinetPay"""
        try:
            import aiohttp
            
            operator_config = PAYMENT_OPERATORS["cinetpay"]
            
            # Préparer les données pour la vérification
            verify_data = {
                "apikey": operator_config["api_key"],
                "site_id": operator_config["site_id"],
                "transaction_id": transaction_id
            }
            
            async with aiohttp.ClientSession() as session:
                async with session.post(operator_config["verify_url"], json=verify_data) as response:
                    result = await response.json()
                    
                    if result.get("code") == "00":
                        return result
                    else:
                        raise HTTPException(status_code=400, detail=result.get("message", "Erreur de vérification"))
                        
        except Exception as e:
            logging.error(f"Erreur lors de la vérification CinetPay: {e}")
            raise HTTPException(status_code=500, detail=str(e))
    
    async def update_payment_status(self, transaction_id: str, verify_result: dict):
        """Mettre à jour le statut d'un paiement basé sur la vérification"""
        try:
            result = await self.session.execute(
                select(PaiementCinetPay).where(PaiementCinetPay.transaction_id == transaction_id)
            )
            paiement = result.scalar_one_or_none()
            
            if not paiement:
                raise HTTPException(status_code=404, detail="Paiement non trouvé")
            
            # Mettre à jour le statut selon la réponse de l'opérateur
            status = verify_result.get("status", "UNKNOWN")
            
            if status == "ACCEPTED":
                paiement.statut = "ACCEPTE"
                paiement.payment_date = datetime.now()
                paiement.payment_method = verify_result.get("payment_method")
                paiement.operator_id = verify_result.get("operator_id")
            elif status == "REFUSED":
                paiement.statut = "REFUSE"
                paiement.error_message = verify_result.get("message", "Paiement refusé")
            elif status == "PENDING":
                paiement.statut = "EN_ATTENTE"
            else:
                paiement.statut = "ECHEC"
                paiement.error_message = f"Statut inconnu: {status}"
            
            await self.session.commit()
            
            # Retirer de la queue si statut final
            if paiement.statut in ["ACCEPTE", "REFUSE", "ECHEC"]:
                await self._remove_from_verification_queue(transaction_id)
            
            logging.info(f"✅ Statut du paiement {transaction_id} mis à jour: {paiement.statut}")
            
        except Exception as e:
            await self.session.rollback()
            logging.error(f"Erreur lors de la mise à jour du statut: {e}")
            raise HTTPException(status_code=500, detail=str(e))
    
    async def _remove_from_verification_queue(self, transaction_id: str):
        """Retirer un paiement de la queue de vérification"""
        if not self.redis_client:
            return
        
        try:
            # Supprimer de Redis
            self.redis_client.delete(f"payment_queue:{transaction_id}")
            self.redis_client.zrem("pending_payments", transaction_id)
            
            logging.info(f"✅ Paiement {transaction_id} retiré de la queue")
            
        except Exception as e:
            logging.error(f"Erreur lors de la suppression de la queue: {e}")
    
    async def get_payment_statistics(self) -> PaiementStats:
        """Récupérer les statistiques des paiements"""
        try:
            # Compter les paiements par statut
            result = await self.session.execute(
                select(
                    func.count(PaiementCinetPay.id).label("total"),
                    func.sum(case((PaiementCinetPay.statut == "ACCEPTE", 1), else_=0)).label("acceptes"),
                    func.sum(case((PaiementCinetPay.statut == "REFUSE", 1), else_=0)).label("refuses"),
                    func.sum(case((PaiementCinetPay.statut == "EN_ATTENTE", 1), else_=0)).label("en_attente"),
                    func.sum(case((PaiementCinetPay.statut == "ECHEC", 1), else_=0)).label("echec"),
                    func.sum(case((PaiementCinetPay.statut == "ACCEPTE", PaiementCinetPay.montant), else_=0)).label("montant_total")
                )
            )
            
            stats = result.fetchone()
            
            return PaiementStats(
                total_paiements=stats.total or 0,
                paiements_acceptes=stats.acceptes or 0,
                paiements_refuses=stats.refuses or 0,
                paiements_en_attente=stats.en_attente or 0,
                paiements_echec=stats.echec or 0,
                montant_total=stats.montant_total or 0,
                devise="XAF"
            )
            
        except Exception as e:
            logging.error(f"Erreur lors du calcul des statistiques: {e}")
            raise HTTPException(status_code=500, detail=str(e))

class PaymentBackgroundWorker:
    """Worker en arrière-plan pour la vérification des paiements avec Redis optimisé"""
    
    def __init__(self, session_factory):
        self.session_factory = session_factory
        self.redis_client = None
        self.running = False
        self._init_redis()
    
    def _init_redis(self):
        """Initialiser Redis avec gestion d'erreurs robuste"""
        try:
            import redis
            self.redis_client = redis.Redis(**REDIS_CONFIG)
            self.redis_client.ping()
            logging.info("✅ Worker Redis connecté")
        except Exception as e:
            logging.error(f"❌ Impossible de connecter Redis au worker: {e}")
            self.redis_client = None
    
    async def start(self):
        """Démarrer le worker"""
        if not self.redis_client:
            logging.error("❌ Redis non disponible - worker non démarré")
            return
        
        self.running = True
        logging.info("🚀 Worker de paiement démarré")
        
        while self.running:
            try:
                await self._process_verification_queue()
                await asyncio.sleep(15)  # Vérifier toutes les 15 secondes
            except Exception as e:
                logging.error(f"Erreur dans le worker: {e}")
                await asyncio.sleep(30)  # Attendre plus longtemps en cas d'erreur
    
    async def stop(self):
        """Arrêter le worker"""
        self.running = False
        logging.info("🛑 Worker de paiement arrêté")
    
    async def _process_verification_queue(self):
        """Traiter la queue de vérification des paiements"""
        try:
            # Récupérer les paiements à vérifier
            pending_payments = self.redis_client.zrangebyscore(
                "pending_payments",
                0,
                datetime.now().timestamp(),
                start=0,
                num=10  # Traiter 10 paiements à la fois
            )
            
            if not pending_payments:
                return
            
            async with self.session_factory() as session:
                payment_service = PaymentService(session)
                
                for transaction_id in pending_payments:
                    try:
                        await self._verify_payment_status(payment_service, transaction_id)
                    except Exception as e:
                        logging.error(f"Erreur lors de la vérification de {transaction_id}: {e}")
                        
        except Exception as e:
            logging.error(f"Erreur lors du traitement de la queue: {e}")
    
    async def _verify_payment_status(self, payment_service: PaymentService, transaction_id: str):
        """Vérifier le statut d'un paiement spécifique"""
        try:
            # Récupérer les informations de la queue
            queue_data = self.redis_client.hgetall(f"payment_queue:{transaction_id}")
            
            if not queue_data:
                # Paiement déjà traité ou supprimé
                return
            
            attempts = int(queue_data.get("attempts", 0))
            max_attempts = int(queue_data.get("max_attempts", 20))
            
            if attempts >= max_attempts:
                # Marquer comme échec et retirer de la queue
                await payment_service.update_payment_status(transaction_id, {"status": "ECHEC"})
                return
            
            # Vérifier le statut
            verify_result = await payment_service.verify_payment_status(transaction_id)
            
            # Mettre à jour les tentatives
            attempts += 1
            next_check = datetime.now() + timedelta(seconds=15)
            
            self.redis_client.hset(
                f"payment_queue:{transaction_id}",
                mapping={
                    "attempts": attempts,
                    "next_check": next_check.isoformat()
                }
            )
            
            # Mettre à jour la prochaine vérification
            self.redis_client.zadd(
                "pending_payments",
                {transaction_id: next_check.timestamp()}
            )
            
            # Mettre à jour le statut si final
            if verify_result.get("status") in ["ACCEPTED", "REFUSED"]:
                await payment_service.update_payment_status(transaction_id, verify_result)
            
        except Exception as e:
            logging.error(f"Erreur lors de la vérification de {transaction_id}: {e}")

# Alias pour compatibilité
CinetPayService = PaymentService
CinetPayBackgroundWorker = PaymentBackgroundWorker