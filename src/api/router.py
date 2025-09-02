from fastapi import APIRouter, Depends, File, HTTPException, Request, UploadFile, status, Form, Query, Path
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from typing import Dict, List, Optional
from datetime import datetime, timedelta

from src.api.model import Adresse, PieceJointe, Reclamation, Utilisateur
from src.api.schema import (
    AdresseCreate, AdresseUpdate, AdresseResponse, AdresseLight,
    UtilisateurCreate, UtilisateurUpdate, UtilisateurResponse, UtilisateurLight,
    CandidatCreate, FormateurCreate, AdministrateurCreate,
    CentreFormationCreate, CentreFormationUpdate, CentreFormationResponse, CentreFormationLight,
    FormationCreate, FormationUpdate, FormationResponse, FormationLight,
    SessionFormationCreate, SessionFormationUpdate, SessionFormationResponse, SessionFormationLight,
    SessionStatutUpdate, SessionModaliteUpdate,
    ModuleCreate, ModuleUpdate, ModuleResponse, ModuleLight,
    RessourceCreate, RessourceUpdate, RessourceResponse, RessourceLight,
    DossierCandidatureCreate, DossierCandidatureUpdate, DossierCandidatureResponse, DossierCandidatureLight,
    DossierStatutUpdate, DossierStatutResponse,
    PieceJointeCreate, PieceJointeUpdate, PieceJointeResponse, PieceJointeLight,
    ReclamationCreate, ReclamationUpdate, ReclamationResponse, ReclamationLight,
    PasswordChangeRequest, PasswordChangeResponse, PasswordResetByEmailResponse,
    InformationDescriptiveCreate, InformationDescriptiveUpdate, InformationDescriptiveResponse,
    LoginRequest, LoginResponse,
    EvaluationCreate, EvaluationUpdate, EvaluationResponse, EvaluationLight,
    ReponseCandidatCreate, ReponseCandidatResponse,
    ResultatEvaluationResponse, ResultatEvaluationLight,
    CertificatResponse, CertificatLight,
    QuestionEvaluationCreate, QuestionEvaluationUpdate, QuestionEvaluationResponse,
    ReponseCandidatCreate, ReponseCandidatResponse,
    PaiementCinetPayCreate, PaiementCinetPayResponse
)
from src.api.service import (
    AddressService, FileService, UserService, CentreService, FormationService,
    SessionFormationService, ModuleService, RessourceService,
    DossierService, PieceJointeService, ReclamationService,
    InformationDescriptiveService, EvaluationService, ResultatEvaluationService, CertificatService,
    QuestionEvaluationService, ReponseCandidatService, CinetPayService
)
from src.api.security import create_access_token, get_current_active_user
from src.util.db.database import get_async_db
from src.util.helper.enum import StatutCandidatureEnum, RoleEnum, StatutReclamationEnum


# ============================
# Router Fichiers
# ============================
fichiers = APIRouter(
    prefix="/files",
    tags=["files"],
)

@fichiers.post(
    "",
    response_model=Dict[str, str],
    status_code=status.HTTP_201_CREATED,
    summary="Téléverser un fichier",
    description="Téléverse un fichier dans le répertoire de stockage configuré. Retourne l'URL complète du fichier. Formats supportés : Images (.jpg, .jpeg, .png), Documents (.pdf, .doc, .docx), Vidéos (.mp4, .avi, .mkv), Audio (.mp3, .opus). La taille maximale est de 254 Mo."
)
async def upload_file(
    file: UploadFile = File(...),
    request: Request = None
):
    service = FileService()
    base_url = str(request.base_url)
    return await service.upload_file(file, base_url)

@fichiers.delete(
    "/{file_path:path}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Supprimer un fichier",
    description="Supprime un fichier spécifié par son chemin ou nom dans le répertoire de stockage."
)
async def delete_file(
    file_path: str
):
    service = FileService()
    await service.delete_file(file_path)
    
    
# ============================
# Router Adresses
# ============================
adresses = APIRouter(
    prefix="/adresses",
    tags=["adresses"],
)

@adresses.post(
    "",
    response_model=AdresseResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Créer une nouvelle adresse",
    description="Crée une nouvelle adresse pour un utilisateur avec les données fournies, incluant le type d'adresse et les détails géographiques."
)
async def create_adresse(
    adresse_data: AdresseCreate,
    user_id: int,
    db: AsyncSession = Depends(get_async_db)
):
    service = AddressService(db)
    return await service.create(adresse_data, user_id)

@adresses.get(
    "/{adresse_id}",
    response_model=AdresseResponse,
    status_code=status.HTTP_200_OK,
    summary="Récupérer une adresse par ID",
    description="Récupère les détails complets d'une adresse spécifiée par son ID."
)
async def get_adresse(
    adresse_id: int,
    db: AsyncSession = Depends(get_async_db)
):
    service = AddressService(db)
    return await service.get_by_id(adresse_id)

@adresses.get(
    "",
    response_model=List[AdresseLight],
    status_code=status.HTTP_200_OK,
    summary="Lister toutes les adresses",
    description="Récupère une liste paginée de toutes les adresses avec leurs informations de base."
)
async def get_all_adresses(
    skip: int = 0,
    limit: int = 100,
    db: AsyncSession = Depends(get_async_db)
):
    service = AddressService(db)
    result = await service.session.execute(select(Adresse).offset(skip).limit(limit))
    adresses = result.scalars().all()
    return [AdresseLight.model_validate(adr, from_attributes=True) for adr in adresses]

@adresses.put(
    "/{adresse_id}",
    response_model=AdresseResponse,
    status_code=status.HTTP_200_OK,
    summary="Mettre à jour une adresse",
    description="Met à jour les informations d'une adresse existante, incluant le type ou les détails géographiques."
)
async def update_adresse(
    adresse_id: int,
    adresse_data: AdresseUpdate,
    db: AsyncSession = Depends(get_async_db)
):
    service = AddressService(db)
    return await service.update(adresse_id, adresse_data)

@adresses.delete(
    "/{adresse_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Supprimer une adresse",
    description="Supprime une adresse spécifiée par son ID."
)
async def delete_adresse(
    adresse_id: int,
    db: AsyncSession = Depends(get_async_db)
):
    service = AddressService(db)
    await service.delete(adresse_id)

# ============================
# Router Utilisateurs
# ============================
utilisateurs = APIRouter(
    prefix="/utilisateurs",
    tags=["utilisateurs"],
)

@utilisateurs.post(
    "",
    response_model=UtilisateurResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Créer un nouvel utilisateur",
    description="Crée un nouvel utilisateur avec les données fournies, incluant informations personnelles, compte et adresses."
)
async def create_utilisateur(
    utilisateur_data: UtilisateurCreate,
    db: AsyncSession = Depends(get_async_db)
):
    service = UserService(db)
    return await service.create(utilisateur_data)

@utilisateurs.get(
    "/{utilisateur_id}",
    response_model=UtilisateurResponse,
    status_code=status.HTTP_200_OK,
    summary="Récupérer un utilisateur par ID",
    description="Récupère les détails complets d'un utilisateur spécifié par son ID, incluant adresses et relations."
)
async def get_utilisateur(
    utilisateur_id: int,
    db: AsyncSession = Depends(get_async_db)
):
    service = UserService(db)
    return await service.get_by_id(utilisateur_id)

@utilisateurs.get(
    "",
    response_model=List[UtilisateurLight],
    status_code=status.HTTP_200_OK,
    summary="Lister tous les utilisateurs",
    description="Récupère une liste paginée de tous les utilisateurs avec leurs informations de base."
)
async def get_all_utilisateurs(
    skip: int = 0,
    limit: int = 100,
    db: AsyncSession = Depends(get_async_db)
):
    service = UserService(db)
    return await service.get_all(skip, limit)

@utilisateurs.put(
    "/{utilisateur_id}",
    response_model=UtilisateurResponse,
    status_code=status.HTTP_200_OK,
    summary="Mettre à jour un utilisateur",
    description="Met à jour les informations d'un utilisateur existant, incluant informations personnelles ou adresses."
)
async def update_utilisateur(
    utilisateur_id: int,
    utilisateur_data: UtilisateurUpdate,
    db: AsyncSession = Depends(get_async_db)
):
    service = UserService(db)
    return await service.update(utilisateur_id, utilisateur_data)

@utilisateurs.delete(
    "/{utilisateur_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Supprimer un utilisateur",
    description="Supprime un utilisateur spécifié par son ID, incluant ses données associées en cascade."
)
async def delete_utilisateur(
    utilisateur_id: int,
    db: AsyncSession = Depends(get_async_db)
):
    service = UserService(db)
    await service.delete(utilisateur_id)

@utilisateurs.post(
    "/reset-password",
    response_model=PasswordResetByEmailResponse,
    status_code=status.HTTP_200_OK,
    summary="Réinitialiser le mot de passe par email",
    description="Génère un nouveau mot de passe sécurisé et l'envoie par email à l'utilisateur."
)
async def reset_password_by_email(
    email: str,
    db: AsyncSession = Depends(get_async_db)
):
    service = UserService(db)
    new_password = await service.reset_password_by_email(email)
    return {
        "message": "Mot de passe réinitialisé avec succès. Vérifiez votre email.",
        "email": email,
        "new_password": new_password  # À supprimer en production
    }

@utilisateurs.post(
    "/{utilisateur_id}/change-password",
    response_model=PasswordChangeResponse,
    status_code=status.HTTP_200_OK,
    summary="Changer le mot de passe d'un utilisateur",
    description="Permet à un utilisateur de changer son mot de passe en fournissant l'ancien et le nouveau."
)
async def change_utilisateur_password(
    utilisateur_id: int,
    password_data: PasswordChangeRequest,
    db: AsyncSession = Depends(get_async_db)
):
    service = UserService(db)
    await service.change_password(utilisateur_id, password_data.current_password, password_data.new_password)
    return {
        "message": "Mot de passe changé avec succès",
        "user_id": utilisateur_id
    }

@utilisateurs.post(
    "/login",
    response_model=LoginResponse,
    status_code=status.HTTP_200_OK,
    summary="Authentifier un utilisateur",
    description="Authentifie un utilisateur avec son email et mot de passe, retourne un token JWT."
)
async def login(
    login_data: LoginRequest,
    db: AsyncSession = Depends(get_async_db)
):
    service = UserService(db)
    return await service.login_user(login_data.email, login_data.password)

@utilisateurs.get(
    "/me",
    response_model=UtilisateurResponse,
    status_code=status.HTTP_200_OK,
    summary="Récupérer le profil de l'utilisateur connecté",
    description="Récupère les informations du profil de l'utilisateur actuellement authentifié."
)
async def get_my_profile(
    current_user: Utilisateur = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_async_db)
):
    service = UserService(db)
    return await service.get_by_id(current_user.id, load_relations=True)

@utilisateurs.get(
    "/profile",
    response_model=UtilisateurResponse,
    status_code=status.HTTP_200_OK,
    summary="Récupérer le profil de l'utilisateur à partir du token",
    description="Récupère les informations du profil de l'utilisateur à partir de son token JWT."
)
async def get_user_profile_from_token(
    current_user: Utilisateur = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_async_db)
):
    """Route alternative pour récupérer le profil utilisateur à partir du token"""
    service = UserService(db)
    return await service.get_by_id(current_user.id, load_relations=True)

# ============================
# Routes spécifiques pour chaque type d'utilisateur
# ============================

@utilisateurs.post(
    "/candidat",
    response_model=UtilisateurResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Créer un nouveau candidat",
    description="Crée un nouveau candidat avec les données fournies. Le champ 'actif' est automatiquement défini à True."
)
async def create_candidat(
    candidat_data: CandidatCreate,
    db: AsyncSession = Depends(get_async_db)
):
    service = UserService(db)
    # Créer directement l'utilisateur avec tous les champs du schéma CandidatCreate
    user_data = candidat_data.model_dump()
    user_data["role"] = RoleEnum.CANDIDAT
    user_data["actif"] = True
    
    # Supprimer le mot de passe du dictionnaire pour le traiter séparément
    password = user_data.pop("password")
    
    # Créer l'utilisateur avec tous les champs
    return await service.create_with_password_detailed(user_data, password)

@utilisateurs.post(
    "/formateur",
    response_model=UtilisateurResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Créer un nouveau formateur",
    description="Crée un nouveau formateur avec les données fournies. Le champ 'actif' est automatiquement défini à True."
)
async def create_formateur(
    formateur_data: FormateurCreate,
    db: AsyncSession = Depends(get_async_db)
):
    service = UserService(db)
    # Créer directement l'utilisateur avec tous les champs du schéma FormateurCreate
    user_data = formateur_data.model_dump()
    user_data["role"] = RoleEnum.FORMATEUR
    user_data["actif"] = True
    
    # Supprimer le mot de passe du dictionnaire pour le traiter séparément
    password = user_data.pop("password")
    
    # Créer l'utilisateur avec tous les champs
    return await service.create_with_password_detailed(user_data, password)

@utilisateurs.post(
    "/administrateur",
    response_model=UtilisateurResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Créer un nouvel administrateur",
    description="Crée un nouvel administrateur avec les données fournies. Le champ 'actif' est automatiquement défini à True."
)
async def create_administrateur(
    admin_data: AdministrateurCreate,
    db: AsyncSession = Depends(get_async_db)
):
    service = UserService(db)
    # Créer directement l'utilisateur avec tous les champs du schéma AdministrateurCreate
    user_data = admin_data.model_dump()
    user_data["role"] = RoleEnum.ADMIN
    user_data["actif"] = True
    
    # Supprimer le mot de passe du dictionnaire pour le traiter séparément
    password = user_data.pop("password")
    
    # Créer l'utilisateur avec tous les champs
    return await service.create_with_password_detailed(user_data, password)

# ============================
# Router Centres Formations
# ============================
centres_formations = APIRouter(
    prefix="/centres-formations",
    tags=["centres-formations"],
)

@centres_formations.post(
    "",
    response_model=CentreFormationResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Créer un nouveau centre de formation",
    description="Crée un nouveau centre de formation avec les données fournies, incluant nom et adresse."
)
async def create_centre_formation(
    centre_data: CentreFormationCreate,
    db: AsyncSession = Depends(get_async_db)
):
    service = CentreService(db)
    return await service.create(centre_data)

@centres_formations.get(
    "/{centre_id}",
    response_model=CentreFormationResponse,
    status_code=status.HTTP_200_OK,
    summary="Récupérer un centre de formation par ID",
    description="Récupère les détails complets d'un centre de formation spécifié par son ID."
)
async def get_centre_formation(
    centre_id: int,
    db: AsyncSession = Depends(get_async_db)
):
    service = CentreService(db)
    return await service.get_by_id(centre_id)

@centres_formations.get(
    "",
    response_model=List[CentreFormationResponse],
    status_code=status.HTTP_200_OK,
    summary="Lister tous les centres de formation",
    description="Récupère une liste paginée de tous les centres de formation avec leurs informations de base."
)
async def get_all_centres_formations(
    skip: int = 0,
    limit: int = 100,
    db: AsyncSession = Depends(get_async_db)
):
    service = CentreService(db)
    return await service.get_all(skip, limit)

@centres_formations.put(
    "/{centre_id}",
    response_model=CentreFormationResponse,
    status_code=status.HTTP_200_OK,
    summary="Mettre à jour un centre de formation",
    description="Met à jour les informations d'un centre de formation existant."
)
async def update_centre_formation(
    centre_id: int,
    centre_data: CentreFormationUpdate,
    db: AsyncSession = Depends(get_async_db)
):
    service = CentreService(db)
    return await service.update(centre_id, centre_data)

@centres_formations.delete(
    "/{centre_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Supprimer un centre de formation",
    description="Supprime un centre de formation spécifié par son ID."
)
async def delete_centre_formation(
    centre_id: int,
    db: AsyncSession = Depends(get_async_db)
):
    service = CentreService(db)
    await service.delete(centre_id)

# ============================
# Router Formations
# ============================
formations = APIRouter(
    prefix="/formations",
    tags=["formations"],
)

@formations.post(
    "",
    response_model=FormationResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Créer une nouvelle formation",
    description="Crée une nouvelle formation avec les données fournies, incluant titre, description et modules."
)
async def create_formation(
    formation_data: FormationCreate,
    db: AsyncSession = Depends(get_async_db)
):
    service = FormationService(db)
    return await service.create(formation_data)

@formations.get(
    "/{formation_id}",
    response_model=FormationResponse,
    status_code=status.HTTP_200_OK,
    summary="Récupérer une formation par ID",
    description="Récupère les détails complets d'une formation spécifiée par son ID, incluant sessions et modules."
)
async def get_formation(
    formation_id: int,
    db: AsyncSession = Depends(get_async_db)
):
    service = FormationService(db)
    return await service.get_by_id(formation_id)

@formations.get(
    "",
    response_model=List[FormationResponse],
    status_code=status.HTTP_200_OK,
    summary="Lister toutes les formations",
    description="Récupère une liste paginée de toutes les formations avec leurs informations de base."
)
async def get_all_formations(
    skip: int = 0,
    limit: int = 100,
    db: AsyncSession = Depends(get_async_db)
):
    service = FormationService(db)
    return await service.get_all(skip, limit)

@formations.put(
    "/{formation_id}",
    response_model=FormationResponse,
    status_code=status.HTTP_200_OK,
    summary="Mettre à jour une formation",
    description="Met à jour les informations d'une formation existante, incluant modules."
)
async def update_formation(
    formation_id: int,
    formation_data: FormationUpdate,
    db: AsyncSession = Depends(get_async_db)
):
    service = FormationService(db)
    return await service.update(formation_id, formation_data)

@formations.delete(
    "/{formation_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Supprimer une formation",
    description="Supprime une formation spécifiée par son ID, incluant ses données associées en cascade."
)
async def delete_formation(
    formation_id: int,
    db: AsyncSession = Depends(get_async_db)
):
    service = FormationService(db)
    await service.delete(formation_id)


# ============================
# Router Informations Descriptives
# ============================
informations_descriptives = APIRouter(
    prefix="/informations-descriptives",
    tags=["informations-descriptives"],
)

@informations_descriptives.post(
    "/{formation_id}",
    response_model=InformationDescriptiveResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Créer des informations descriptives pour une formation",
    description="Crée ou met à jour les informations descriptives détaillées d'une formation."
)
async def create_information_descriptive(
    formation_id: int,
    info_data: InformationDescriptiveCreate,
    db: AsyncSession = Depends(get_async_db)
):
    service = InformationDescriptiveService(db)
    return await service.create(info_data, formation_id)

@informations_descriptives.get(
    "/{formation_id}",
    response_model=InformationDescriptiveResponse,
    status_code=status.HTTP_200_OK,
    summary="Récupérer les informations descriptives d'une formation",
    description="Récupère les informations descriptives détaillées d'une formation spécifique."
)
async def get_information_descriptive(
    formation_id: int,
    db: AsyncSession = Depends(get_async_db)
):
    service = InformationDescriptiveService(db)
    info_desc = await service.get_by_formation_id(formation_id)
    if not info_desc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Aucune information descriptive trouvée pour cette formation"
        )
    return info_desc

@informations_descriptives.put(
    "/{formation_id}",
    response_model=InformationDescriptiveResponse,
    status_code=status.HTTP_200_OK,
    summary="Mettre à jour les informations descriptives d'une formation",
    description="Met à jour les informations descriptives d'une formation existante."
)
async def update_information_descriptive(
    formation_id: int,
    info_data: InformationDescriptiveUpdate,
    db: AsyncSession = Depends(get_async_db)
):
    service = InformationDescriptiveService(db)
    return await service.update(formation_id, info_data)

@informations_descriptives.delete(
    "/{formation_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Supprimer les informations descriptives d'une formation",
    description="Supprime les informations descriptives d'une formation."
)
async def delete_information_descriptive(
    formation_id: int,
    db: AsyncSession = Depends(get_async_db)
):
    service = InformationDescriptiveService(db)
    await service.delete(formation_id)

# ============================
# Router Sessions Formations
# ============================
sessions_formations = APIRouter(
    prefix="/sessions-formations",
    tags=["sessions-formations"],
)

@sessions_formations.post(
    "",
    response_model=SessionFormationResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Créer une nouvelle session de formation",
    description="Crée une nouvelle session de formation avec les données fournies, incluant dates et centre."
)
async def create_session_formation(
    session_data: SessionFormationCreate,
    db: AsyncSession = Depends(get_async_db)
):
    service = SessionFormationService(db)
    return await service.create(session_data)

@sessions_formations.get(
    "/{session_id}",
    response_model=SessionFormationResponse,
    status_code=status.HTTP_200_OK,
    summary="Récupérer une session de formation par ID",
    description="Récupère les détails complets d'une session de formation spécifiée par son ID."
)
async def get_session_formation(
    session_id: int,
    db: AsyncSession = Depends(get_async_db)
):
    service = SessionFormationService(db)
    return await service.get_by_id(session_id)

@sessions_formations.get(
    "",
    response_model=List[SessionFormationResponse],
    status_code=status.HTTP_200_OK,
    summary="Lister toutes les sessions de formation",
    description="Récupère une liste paginée de toutes les sessions de formation avec leurs informations complètes."
)
async def get_all_sessions_formations(
    skip: int = 0,
    limit: int = 100,
    db: AsyncSession = Depends(get_async_db)
):
    service = SessionFormationService(db)
    return await service.get_all(skip, limit)

@sessions_formations.put(
    "/{session_id}",
    response_model=SessionFormationResponse,
    status_code=status.HTTP_200_OK,
    summary="Mettre à jour une session de formation",
    description="Met à jour les informations d'une session de formation existante."
)
async def update_session_formation(
    session_id: int,
    session_data: SessionFormationUpdate,
    db: AsyncSession = Depends(get_async_db)
):
    service = SessionFormationService(db)
    return await service.update(session_id, session_data)

@sessions_formations.delete(
    "/{session_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Supprimer une session de formation",
    description="Supprime une session de formation spécifiée par son ID."
)
async def delete_session_formation(
    session_id: int,
    db: AsyncSession = Depends(get_async_db)
):
    service = SessionFormationService(db)
    await service.delete(session_id)

@sessions_formations.patch(
    "/{session_id}/statut",
    response_model=SessionFormationResponse,
    status_code=status.HTTP_200_OK,
    summary="Changer le statut d'une session de formation",
    description="Change le statut d'une session de formation (ouverte, fermée, annulée) avec vérifications métier."
)
async def change_session_statut(
    session_id: int,
    statut_data: SessionStatutUpdate,
    db: AsyncSession = Depends(get_async_db)
):
    service = SessionFormationService(db)
    return await service.change_statut(session_id, statut_data)

@sessions_formations.patch(
    "/{session_id}/modalite",
    response_model=SessionFormationResponse,
    status_code=status.HTTP_200_OK,
    summary="Changer la modalité d'une session de formation",
    description="Change la modalité d'une session de formation (présentiel, en ligne) avec vérifications métier."
)
async def change_session_modalite(
    session_id: int,
    modalite_data: SessionModaliteUpdate,
    db: AsyncSession = Depends(get_async_db)
):
    service = SessionFormationService(db)
    return await service.change_modalite(session_id, modalite_data)

# ============================
# Router Modules
# ============================
modules = APIRouter(
    prefix="/modules",
    tags=["modules"],
)

@modules.post(
    "",
    response_model=ModuleResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Créer un nouveau module",
    description="Crée un nouveau module pour une formation avec les données fournies."
)
async def create_module(
    module_data: ModuleCreate,
    db: AsyncSession = Depends(get_async_db)
):
    service = ModuleService(db)
    return await service.create(module_data)

@modules.get(
    "/{module_id}",
    response_model=ModuleResponse,
    status_code=status.HTTP_200_OK,
    summary="Récupérer un module par ID",
    description="Récupère les détails complets d'un module spécifié par son ID, incluant ressources."
)
async def get_module(
    module_id: int,
    db: AsyncSession = Depends(get_async_db)
):
    service = ModuleService(db)
    return await service.get_by_id(module_id)

@modules.get(
    "",
    response_model=List[ModuleResponse],
    status_code=status.HTTP_200_OK,
    summary="Lister tous les modules",
    description="Récupère une liste paginée de tous les modules avec leurs informations complètes."
)
async def get_all_modules(
    skip: int = 0,
    limit: int = 100,
    db: AsyncSession = Depends(get_async_db)
):
    service = ModuleService(db)
    return await service.get_all(skip, limit)

@modules.get(
    "/formation/{formation_id}",
    response_model=List[ModuleResponse],
    status_code=status.HTTP_200_OK,
    summary="Lister les modules d'une formation",
    description="Récupère tous les modules d'une formation spécifique classés automatiquement par ordre."
)
async def get_modules_by_formation(
    formation_id: int,
    db: AsyncSession = Depends(get_async_db)
):
    """Récupère tous les modules d'une formation classés par ordre"""
    service = ModuleService(db)
    return await service.get_modules_by_formation(formation_id)

@modules.put(
    "/{module_id}",
    response_model=ModuleResponse,
    status_code=status.HTTP_200_OK,
    summary="Mettre à jour un module",
    description="Met à jour les informations d'un module existant."
)
async def update_module(
    module_id: int,
    module_data: ModuleUpdate,
    db: AsyncSession = Depends(get_async_db)
):
    service = ModuleService(db)
    return await service.update(module_id, module_data)

@modules.delete(
    "/{module_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Supprimer un module",
    description="Supprime un module spécifié par son ID, incluant ses ressources en cascade."
)
async def delete_module(
    module_id: int,
    db: AsyncSession = Depends(get_async_db)
):
    service = ModuleService(db)
    await service.delete(module_id)

# ============================
# Router Ressources
# ============================
ressources = APIRouter(
    prefix="/ressources",
    tags=["ressources"],
)

@ressources.post(
    "",
    response_model=RessourceResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Créer une nouvelle ressource",
    description="Crée une nouvelle ressource pour un module avec les données fournies."
)
async def create_ressource(
    ressource_data: RessourceCreate,
    db: AsyncSession = Depends(get_async_db)
):
    service = RessourceService(db)
    return await service.create(ressource_data)

@ressources.get(
    "/{ressource_id}",
    response_model=RessourceResponse,
    status_code=status.HTTP_200_OK,
    summary="Récupérer une ressource par ID",
    description="Récupère les détails complets d'une ressource spécifiée par son ID."
)
async def get_ressource(
    ressource_id: int,
    db: AsyncSession = Depends(get_async_db)
):
    service = RessourceService(db)
    return await service.get_by_id(ressource_id)

@ressources.get(
    "",
    response_model=List[RessourceLight],
    status_code=status.HTTP_200_OK,
    summary="Lister toutes les ressources",
    description="Récupère une liste paginée de toutes les ressources avec leurs informations de base."
)
async def get_all_ressources(
    skip: int = 0,
    limit: int = 100,
    db: AsyncSession = Depends(get_async_db)
):
    service = RessourceService(db)
    return await service.get_all(skip, limit)

@ressources.get(
    "/module/{module_id}",
    response_model=List[RessourceResponse],
    status_code=status.HTTP_200_OK,
    summary="Lister les ressources d'un module",
    description="Récupère toutes les ressources d'un module spécifique avec leurs détails complets."
)
async def get_ressources_by_module(
    module_id: int,
    db: AsyncSession = Depends(get_async_db)
):
    """Récupère toutes les ressources d'un module spécifique"""
    service = RessourceService(db)
    return await service.get_ressources_by_module(module_id)

@ressources.put(
    "/{ressource_id}",
    response_model=RessourceResponse,
    status_code=status.HTTP_200_OK,
    summary="Mettre à jour une ressource",
    description="Met à jour les informations d'une ressource existante."
)
async def update_ressource(
    ressource_id: int,
    ressource_data: RessourceUpdate,
    db: AsyncSession = Depends(get_async_db)
):
    service = RessourceService(db)
    return await service.update(ressource_id, ressource_data)

@ressources.delete(
    "/{ressource_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Supprimer une ressource",
    description="Supprime une ressource spécifiée par son ID."
)
async def delete_ressource(
    ressource_id: int,
    db: AsyncSession = Depends(get_async_db)
):
    service = RessourceService(db)
    await service.delete(ressource_id)

# ============================
# Router Dossiers Candidatures
# ============================
dossiers_candidatures = APIRouter(
    prefix="/dossiers-candidatures",
    tags=["dossiers-candidatures"],
)

@dossiers_candidatures.post(
    "",
    response_model=DossierCandidatureResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Créer un nouveau dossier de candidature",
    description="Crée un nouveau dossier de candidature avec les données fournies, incluant pièces jointes et paiements."
)
async def create_dossier_candidature(
    dossier_data: DossierCandidatureCreate,
    db: AsyncSession = Depends(get_async_db)
):
    service = DossierService(db)
    return await service.create(dossier_data)

@dossiers_candidatures.get(
    "/{dossier_id}",
    response_model=DossierCandidatureResponse,
    status_code=status.HTTP_200_OK,
    summary="Récupérer un dossier de candidature par ID",
    description="Récupère les détails complets d'un dossier de candidature spécifié par son ID, incluant relations."
)
async def get_dossier_candidature(
    dossier_id: int,
    db: AsyncSession = Depends(get_async_db)
):
    service = DossierService(db)
    return await service.get_by_id(dossier_id)

@dossiers_candidatures.get(
    "",
    response_model=List[DossierCandidatureResponse],
    status_code=status.HTTP_200_OK,
    summary="Lister tous les dossiers de candidature",
    description="Récupère une liste paginée de tous les dossiers de candidature avec leurs informations de base."
)
async def get_all_dossiers_candidatures(
    skip: int = Query(0, ge=0, description="Nombre d'éléments à ignorer"),
    limit: int = Query(100, ge=1, le=1000, description="Nombre maximum d'éléments à retourner"),
    db: AsyncSession = Depends(get_async_db)
):
    service = DossierService(db)
    return await service.get_all(skip, limit)

@dossiers_candidatures.get(
    "/candidat/{candidat_id}",
    response_model=List[DossierCandidatureResponse],
    status_code=status.HTTP_200_OK,
    summary="Lister les candidatures d'un candidat",
    description="Récupère une liste paginée de toutes les candidatures d'un candidat spécifique avec leurs informations complètes."
)
async def get_candidatures_by_candidat(
    candidat_id: int = Path(..., description="ID du candidat"),
    skip: int = Query(0, ge=0, description="Nombre d'éléments à ignorer"),
    limit: int = Query(100, ge=1, le=1000, description="Nombre maximum d'éléments à retourner"),
    db: AsyncSession = Depends(get_async_db)
):
    service = DossierService(db)
    return await service.get_by_candidat(candidat_id, skip, limit)

@dossiers_candidatures.put(
    "/{dossier_id}",
    response_model=DossierCandidatureResponse,
    status_code=status.HTTP_200_OK,
    summary="Mettre à jour un dossier de candidature",
    description="Met à jour les informations d'un dossier de candidature existant."
)
async def update_dossier_candidature(
    dossier_id: int,
    dossier_data: DossierCandidatureUpdate,
    db: AsyncSession = Depends(get_async_db)
):
    service = DossierService(db)
    return await service.update(dossier_id, dossier_data)

@dossiers_candidatures.delete(
    "/{dossier_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Supprimer un dossier de candidature",
    description="Supprime un dossier de candidature spécifié par son ID, incluant ses données associées en cascade."
)
async def delete_dossier_candidature(
    dossier_id: int,
    db: AsyncSession = Depends(get_async_db)
):
    service = DossierService(db)
    await service.delete(dossier_id)

# ============================
# Routes pour le changement de statut
# ============================

@dossiers_candidatures.patch(
    "/{dossier_id}/statut",
    response_model=DossierStatutResponse,
    status_code=status.HTTP_200_OK,
    summary="Changer le statut d'un dossier de candidature",
    description="Change le statut d'un dossier de candidature avec validation des règles métier."
)
async def changer_statut_dossier(
    dossier_id: int,
    statut_data: DossierStatutUpdate,
    db: AsyncSession = Depends(get_async_db)
):
    service = DossierService(db)
    return await service.changer_statut(dossier_id, statut_data)

@dossiers_candidatures.patch(
    "/{dossier_id}/accepter",
    response_model=DossierStatutResponse,
    status_code=status.HTTP_200_OK,
    summary="Accepter un dossier de candidature",
    description="Accepte un dossier de candidature (statut RECUE ou EN_ETUDE → ACCEPTÉE)."
)
async def accepter_dossier(
    dossier_id: int,
    commentaire: Optional[str] = Form(None, description="Commentaire administratif"),
    db: AsyncSession = Depends(get_async_db)
):
    service = DossierService(db)
    statut_data = DossierStatutUpdate(
        statut=StatutCandidatureEnum.ACCEPTÉE,
        date_soumission=datetime.now(),
        commentaire=commentaire
    )
    return await service.changer_statut(dossier_id, statut_data)

@dossiers_candidatures.patch(
    "/{dossier_id}/refuser",
    response_model=DossierStatutResponse,
    status_code=status.HTTP_200_OK,
    summary="Refuser un dossier de candidature",
    description="Refuse un dossier de candidature avec motif obligatoire."
)
async def refuser_dossier(
    dossier_id: int,
    motif_refus: str = Form(..., description="Motif obligatoire du refus"),
    commentaire: Optional[str] = Form(None, description="Commentaire administratif"),
    db: AsyncSession = Depends(get_async_db)
):
    service = DossierService(db)
    statut_data = DossierStatutUpdate(
        statut=StatutCandidatureEnum.REFUSÉE,
        motif_refus=motif_refus,
        commentaire=commentaire
    )
    return await service.changer_statut(dossier_id, statut_data)

@dossiers_candidatures.patch(
    "/{dossier_id}/mettre-en-etude",
    response_model=DossierStatutResponse,
    status_code=status.HTTP_200_OK,
    summary="Mettre un dossier en étude",
    description="Met un dossier de candidature en étude (statut RECUE → EN_ETUDE)."
)
async def mettre_en_etude_dossier(
    dossier_id: int,
    commentaire: Optional[str] = Form(None, description="Commentaire administratif"),
    db: AsyncSession = Depends(get_async_db)
):
    service = DossierService(db)
    statut_data = DossierStatutUpdate(
        statut=StatutCandidatureEnum.EN_ETUDE,
        date_soumission=datetime.now(),
        commentaire=commentaire
    )
    return await service.changer_statut(dossier_id, statut_data)

@dossiers_candidatures.patch(
    "/{dossier_id}/annuler",
    response_model=DossierStatutResponse,
    status_code=status.HTTP_200_OK,
    summary="Annuler un dossier de candidature",
    description="Annule un dossier de candidature (statut → ANNULEE)."
)
async def annuler_dossier(
    dossier_id: int,
    motif_refus: str = Form(..., description="Motif de l'annulation"),
    commentaire: Optional[str] = Form(None, description="Commentaire administratif"),
    db: AsyncSession = Depends(get_async_db)
):
    service = DossierService(db)
    statut_data = DossierStatutUpdate(
        statut=StatutCandidatureEnum.ANNULEE,
        motif_refus=motif_refus,
        commentaire=commentaire
    )
    return await service.changer_statut(dossier_id, statut_data)



# ============================
# Router Pieces Jointes
# ============================
pieces_jointes = APIRouter(
    prefix="/pieces-jointes",
    tags=["pieces-jointes"],
)

@pieces_jointes.post(
    "",
    response_model=PieceJointeResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Créer une nouvelle pièce jointe",
    description="Crée une nouvelle pièce jointe pour un dossier avec les données fournies."
)
async def create_piece_jointe(
    piece_data: PieceJointeCreate,
    db: AsyncSession = Depends(get_async_db)
):
    service = PieceJointeService(db)
    return await service.create(piece_data)

@pieces_jointes.get(
    "/{piece_id}",
    response_model=PieceJointeResponse,
    status_code=status.HTTP_200_OK,
    summary="Récupérer une pièce jointe par ID",
    description="Récupère les détails complets d'une pièce jointe spécifiée par son ID."
)
async def get_piece_jointe(
    piece_id: int,
    db: AsyncSession = Depends(get_async_db)
):
    service = PieceJointeService(db)
    return await service.get_by_id(piece_id)

@pieces_jointes.get(
    "",
    response_model=List[PieceJointeLight],
    status_code=status.HTTP_200_OK,
    summary="Lister toutes les pièces jointes",
    description="Récupère une liste paginée de toutes les pièces jointes avec leurs informations de base."
)
async def get_all_pieces_jointes(
    skip: int = 0,
    limit: int = 100,
    db: AsyncSession = Depends(get_async_db)
):
    service = PieceJointeService(db)
    return await service.get_all(skip, limit)

@pieces_jointes.put(
    "/{piece_id}",
    response_model=PieceJointeResponse,
    status_code=status.HTTP_200_OK,
    summary="Mettre à jour une pièce jointe",
    description="Met à jour les informations d'une pièce jointe existante."
)
async def update_piece_jointe(
    piece_id: int,
    piece_data: PieceJointeUpdate,
    db: AsyncSession = Depends(get_async_db)
):
    service = PieceJointeService(db)
    return await service.update(piece_id, piece_data)

@pieces_jointes.delete(
    "/{piece_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Supprimer une pièce jointe",
    description="Supprime une pièce jointe spécifiée par son ID."
)
async def delete_piece_jointe(
    piece_id: int,
    db: AsyncSession = Depends(get_async_db)
):
    service = PieceJointeService(db)
    await service.delete(piece_id)

# ============================
# Router Reclamations
# ============================
reclamations = APIRouter(
    prefix="/reclamations",
    tags=["reclamations"],
)

@reclamations.post(
    "",
    response_model=ReclamationResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Créer une nouvelle réclamation",
    description="Crée une nouvelle réclamation pour un dossier avec les données fournies."
)
async def create_reclamation(
    reclamation_data: ReclamationCreate,
    db: AsyncSession = Depends(get_async_db)
):
    service = ReclamationService(db)
    return await service.create(reclamation_data)

@reclamations.get(
    "/{reclamation_id}",
    response_model=ReclamationResponse,
    status_code=status.HTTP_200_OK,
    summary="Récupérer une réclamation par ID",
    description="Récupère les détails complets d'une réclamation spécifiée par son ID."
)
async def get_reclamation(
    reclamation_id: int,
    db: AsyncSession = Depends(get_async_db)
):
    service = ReclamationService(db)
    return await service.get_by_id(reclamation_id)

@reclamations.get(
    "",
    response_model=List[ReclamationResponse],
    status_code=status.HTTP_200_OK,
    summary="Lister toutes les réclamations",
    description="Récupère une liste paginée de toutes les réclamations avec leurs informations complètes."
)
async def get_all_reclamations(
    skip: int = Query(0, ge=0, description="Nombre d'éléments à ignorer"),
    limit: int = Query(100, ge=1, le=1000, description="Nombre maximum d'éléments à retourner"),
    db: AsyncSession = Depends(get_async_db)
):
    service = ReclamationService(db)
    return await service.get_all(skip=skip, limit=limit)

@reclamations.get(
    "/user/{user_id}",
    response_model=List[ReclamationResponse],
    status_code=status.HTTP_200_OK,
    summary="Lister les réclamations d'un utilisateur",
    description="Récupère une liste paginée de toutes les réclamations d'un utilisateur spécifique."
)
async def get_reclamations_by_user(
    user_id: int = Path(..., description="ID de l'utilisateur"),
    skip: int = Query(0, ge=0, description="Nombre d'éléments à ignorer"),
    limit: int = Query(100, ge=1, le=1000, description="Nombre maximum d'éléments à retourner"),
    db: AsyncSession = Depends(get_async_db)
):
    service = ReclamationService(db)
    return await service.get_by_user(user_id, skip=skip, limit=limit)

@reclamations.put(
    "/{reclamation_id}",
    response_model=ReclamationResponse,
    status_code=status.HTTP_200_OK,
    summary="Mettre à jour une réclamation",
    description="Met à jour les informations d'une réclamation existante."
)
async def update_reclamation(
    reclamation_id: int,
    reclamation_data: ReclamationUpdate,
    db: AsyncSession = Depends(get_async_db)
):
    service = ReclamationService(db)
    return await service.update(reclamation_id, reclamation_data)

@reclamations.delete(
    "/{reclamation_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Supprimer une réclamation",
    description="Supprime une réclamation spécifiée par son ID."
)
async def delete_reclamation(
    reclamation_id: int,
    db: AsyncSession = Depends(get_async_db)
):
    service = ReclamationService(db)
    await service.delete(reclamation_id)

@reclamations.patch(
    "/{reclamation_id}/status",
    response_model=ReclamationResponse,
    status_code=status.HTTP_200_OK,
    summary="Changer le statut d'une réclamation",
    description="Change le statut d'une réclamation (nouveau, en cours, clôturé)."
)
async def change_reclamation_status(
    reclamation_id: int,
    status_update: dict,
    db: AsyncSession = Depends(get_async_db)
):
    service = ReclamationService(db)
    new_status = status_update.get("statut")
    commentaire = status_update.get("commentaire")
    
    if not new_status:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Le champ 'statut' est requis")
    
    return await service.change_status(reclamation_id, new_status, commentaire)

@reclamations.patch(
    "/{reclamation_id}/en-cours",
    response_model=ReclamationResponse,
    status_code=status.HTTP_200_OK,
    summary="Mettre une réclamation en cours",
    description="Met le statut d'une réclamation à 'en cours'."
)
async def set_reclamation_en_cours(
    reclamation_id: int,
    db: AsyncSession = Depends(get_async_db)
):
    service = ReclamationService(db)
    return await service.change_status(reclamation_id, StatutReclamationEnum.EN_COURS.value)

@reclamations.patch(
    "/{reclamation_id}/cloture",
    response_model=ReclamationResponse,
    status_code=status.HTTP_200_OK,
    summary="Clôturer une réclamation",
    description="Met le statut d'une réclamation à 'clôturé'."
)
async def set_reclamation_cloture(
    reclamation_id: int,
    db: AsyncSession = Depends(get_async_db)
):
    service = ReclamationService(db)
    return await service.change_status(reclamation_id, StatutReclamationEnum.CLOTURE.value)

# ============================
# Router Paiements
# ============================
paiements = APIRouter(
    prefix="/paiements",
    tags=["paiements"],
)


    
# Routes pour les paiements CinetPay
@paiements.post("/initier", response_model=PaiementCinetPayResponse)
async def initier_paiement(
    paiement_data: PaiementCinetPayCreate,
    db: AsyncSession = Depends(get_async_db)
):
    """Initier un nouveau paiement CinetPay"""
    cinetpay_service = CinetPayService(db)
    return await cinetpay_service.create_payment(paiement_data)

@paiements.get("/cinetpay/{payment_id}", response_model=PaiementCinetPayResponse)
async def get_paiement_cinetpay(
    payment_id: int,
    db: AsyncSession = Depends(get_async_db)
):
    """Récupérer un paiement CinetPay par ID"""
    cinetpay_service = CinetPayService(db)
    return await cinetpay_service.get_payment_by_id(payment_id)

@paiements.get("/transaction/{transaction_id}", response_model=PaiementCinetPayResponse)
async def get_paiement_by_transaction(
    transaction_id: str,
    db: AsyncSession = Depends(get_async_db)
):
    """Récupérer un paiement par transaction_id"""
    cinetpay_service = CinetPayService(db)
    return await cinetpay_service.get_payment_by_transaction_id(transaction_id)

@paiements.get("/utilisateur/{utilisateur_id}", response_model=List[PaiementCinetPayResponse])
async def get_paiements_utilisateur(
    utilisateur_id: int,
    db: AsyncSession = Depends(get_async_db)
):
    """Récupérer tous les paiements d'un utilisateur"""
    cinetpay_service = CinetPayService(db)
    return await cinetpay_service.get_payments_by_user(utilisateur_id)

@paiements.post("/notification")
async def notification_paiement(
    request: Request,
    db: AsyncSession = Depends(get_async_db)
):
    """Endpoint de notification CinetPay"""
    try:
        # Récupérer les données de la notification
        form_data = await request.form()
        data = dict(form_data)
        
        # Récupérer le token HMAC de l'en-tête
        x_token = request.headers.get("x-token")
        
        # Vérifier le token HMAC
        cinetpay_service = CinetPayService(db)
        if not cinetpay_service._verify_hmac_token(data, x_token):
            raise HTTPException(status_code=400, detail="Token HMAC invalide")
        
        # Traiter la notification
        transaction_id = data.get("cpm_trans_id")
        if transaction_id:
            # Vérifier le statut auprès de CinetPay
            verify_result = await cinetpay_service.verify_payment(transaction_id)
            
            # Mettre à jour le statut
            await cinetpay_service.update_payment_status(transaction_id, verify_result)
            
            logging.info(f"✅ Notification traitée pour {transaction_id}")
        
        return {"status": "success"}
        
    except Exception as e:
        logging.error(f"Erreur lors du traitement de la notification: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@paiements.post("/retour")
async def retour_paiement(
    request: Request,
    db: AsyncSession = Depends(get_async_db)
):
    """Endpoint de retour après paiement"""
    try:
        # Récupérer les données de retour
        form_data = await request.form()
        data = dict(form_data)
        
        transaction_id = data.get("transaction_id")
        if transaction_id:
            # Récupérer le paiement
            cinetpay_service = CinetPayService(db)
            paiement = await cinetpay_service.get_payment_by_transaction_id(transaction_id)
            
            # Retourner les informations du paiement
            return {
                "transaction_id": transaction_id,
                "statut": paiement.statut,
                "montant": paiement.montant,
                "devise": paiement.devise,
                "description": paiement.description
            }
        
        return {"message": "Aucune transaction spécifiée"}
        
    except Exception as e:
        logging.error(f"Erreur lors du traitement du retour: {e}")
        raise HTTPException(status_code=500, detail=str(e))
    
# ──────────────────────────────────────────────────────────────
# Router Évaluations
# ──────────────────────────────────────────────────────────────
evaluations = APIRouter(
    prefix="/evaluations",
    tags=["evaluations"],
)

@evaluations.post(
    "",
    response_model=EvaluationResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Créer une nouvelle évaluation",
    description="Crée une nouvelle évaluation pour une session de formation."
)
async def create_evaluation(
    evaluation_data: EvaluationCreate,
    user_id: int,
    db: AsyncSession = Depends(get_async_db)
):
    """Créer une évaluation"""
    service = EvaluationService(db)
    return await service.create(evaluation_data, user_id)

@evaluations.get(
    "/{evaluation_id}",
    response_model=EvaluationResponse,
    status_code=status.HTTP_200_OK,
    summary="Récupérer une évaluation par ID",
    description="Récupère les détails complets d'une évaluation."
)
async def get_evaluation(
    evaluation_id: int,
    db: AsyncSession = Depends(get_async_db)
):
    service = EvaluationService(db)
    return await service.get_by_id(evaluation_id)

@evaluations.get(
    "/session/{session_id}",
    response_model=List[EvaluationResponse],
    status_code=status.HTTP_200_OK,
    summary="Lister les évaluations d'une session",
    description="Récupère toutes les évaluations d'une session de formation."
)
async def get_evaluations_session(
    session_id: int,
    db: AsyncSession = Depends(get_async_db)
):
    service = EvaluationService(db)
    return await service.get_by_session(session_id)

@evaluations.put(
    "/{evaluation_id}",
    response_model=EvaluationResponse,
    status_code=status.HTTP_200_OK,
    summary="Mettre à jour une évaluation",
    description="Met à jour les informations d'une évaluation existante."
)
async def update_evaluation(
    evaluation_id: int,
    evaluation_data: EvaluationUpdate,
    user_id: int,
    db: AsyncSession = Depends(get_async_db)
):
    """Mettre à jour une évaluation"""
    service = EvaluationService(db)
    return await service.update(evaluation_id, evaluation_data)

@evaluations.delete(
    "/{evaluation_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Supprimer une évaluation",
    description="Supprime une évaluation et toutes ses questions associées."
)
async def delete_evaluation(
    evaluation_id: int,
    user_id: int,
    db: AsyncSession = Depends(get_async_db)
):
    """Supprimer une évaluation"""
    service = EvaluationService(db)
    await service.delete(evaluation_id)

# ──────────────────────────────────────────────────────────────
# Router Résultats d'évaluation
# ──────────────────────────────────────────────────────────────
resultats_evaluations = APIRouter(
    prefix="/resultats-evaluations",
    tags=["resultats-evaluations"],
)

@resultats_evaluations.post(
    "/commencer",
    response_model=ResultatEvaluationResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Commencer une évaluation",
    description="Commence une évaluation pour un candidat."
)
async def commencer_evaluation(
    evaluation_id: int,
    user_id: int,
    db: AsyncSession = Depends(get_async_db)
):
    """Commencer une évaluation"""
    service = ResultatEvaluationService(db)
    return await service.commencer_evaluation(evaluation_id, user_id)

@resultats_evaluations.post(
    "/{resultat_id}/soumettre",
    response_model=ResultatEvaluationResponse,
    status_code=status.HTTP_200_OK,
    summary="Soumettre une évaluation",
    description="Soumet les réponses d'un candidat pour une évaluation."
)
async def soumettre_evaluation(
    resultat_id: int,
    reponses: List[ReponseCandidatCreate],
    user_id: int,
    db: AsyncSession = Depends(get_async_db)
):
    """Soumettre une évaluation"""
    service = ResultatEvaluationService(db)
    return await service.soumettre_evaluation(resultat_id, reponses)

# ──────────────────────────────────────────────────────────────
# Router Certificats
# ──────────────────────────────────────────────────────────────
certificats = APIRouter(
    prefix="/certificats",
    tags=["certificats"],
)

@certificats.post(
    "/generer",
    response_model=CertificatResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Générer un certificat",
    description="Génère un certificat pour un candidat ayant terminé une session."
)
async def generer_certificat(
    candidat_id: int,
    session_id: int,
    user_id: int,
    db: AsyncSession = Depends(get_async_db)
):
    """Générer un certificat"""
    service = CertificatService(db)
    return await service.generer_certificat(candidat_id, session_id)

@certificats.get(
    "/candidat/{candidat_id}",
    response_model=List[CertificatLight],
    status_code=status.HTTP_200_OK,
    summary="Lister les certificats d'un candidat",
    description="Récupère tous les certificats obtenus par un candidat."
)
async def get_certificats_candidat(
    candidat_id: int,
    user_id: int,
    db: AsyncSession = Depends(get_async_db)
):
    """Lister les certificats d'un candidat"""
    # TODO: Implémenter le service pour récupérer les certificats
    return []

# ──────────────────────────────────────────────────────────────
# Router Questions d'évaluation
# ──────────────────────────────────────────────────────────────
questions_evaluation = APIRouter(
    prefix="/questions-evaluation",
    tags=["questions-evaluation"],
)

@questions_evaluation.post(
    "",
    response_model=QuestionEvaluationResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Créer une nouvelle question d'évaluation",
    description="Crée une nouvelle question pour une évaluation."
)
async def create_question_evaluation(
    question_data: QuestionEvaluationCreate,
    user_id: int,
    db: AsyncSession = Depends(get_async_db)
):
    """Créer une question d'évaluation"""
    service = QuestionEvaluationService(db)
    return await service.create(question_data)

@questions_evaluation.get(
    "/{question_id}",
    response_model=QuestionEvaluationResponse,
    status_code=status.HTTP_200_OK,
    summary="Récupérer une question d'évaluation par ID",
    description="Récupère les détails complets d'une question d'évaluation."
)
async def get_question_evaluation(
    question_id: int,
    db: AsyncSession = Depends(get_async_db)
):
    """Récupérer une question d'évaluation"""
    service = QuestionEvaluationService(db)
    return await service.get_by_id(question_id)

@questions_evaluation.get(
    "/evaluation/{evaluation_id}",
    response_model=List[QuestionEvaluationResponse],
    status_code=status.HTTP_200_OK,
    summary="Lister les questions d'une évaluation",
    description="Récupère toutes les questions d'une évaluation dans l'ordre."
)
async def get_questions_evaluation(
    evaluation_id: int,
    db: AsyncSession = Depends(get_async_db)
):
    """Lister les questions d'une évaluation"""
    service = QuestionEvaluationService(db)
    return await service.get_by_evaluation(evaluation_id)

@questions_evaluation.put(
    "/{question_id}",
    response_model=QuestionEvaluationResponse,
    status_code=status.HTTP_200_OK,
    summary="Mettre à jour une question d'évaluation",
    description="Met à jour les informations d'une question d'évaluation existante."
)
async def update_question_evaluation(
    question_id: int,
    question_data: QuestionEvaluationUpdate,
    user_id: int,
    db: AsyncSession = Depends(get_async_db)
):
    """Mettre à jour une question d'évaluation"""
    service = QuestionEvaluationService(db)
    return await service.update(question_id, question_data)

@questions_evaluation.delete(
    "/{question_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Supprimer une question d'évaluation",
    description="Supprime une question d'évaluation et toutes ses réponses associées."
)
async def delete_question_evaluation(
    question_id: int,
    user_id: int,
    db: AsyncSession = Depends(get_async_db)
):
    """Supprimer une question d'évaluation"""
    service = QuestionEvaluationService(db)
    await service.delete(question_id)

@questions_evaluation.post(
    "/{evaluation_id}/reordonner",
    status_code=status.HTTP_200_OK,
    summary="Réordonner les questions d'une évaluation",
    description="Change l'ordre des questions d'une évaluation."
)
async def reordonner_questions_evaluation(
    evaluation_id: int,
    question_orders: List[Dict[str, int]],
    user_id: int,
    db: AsyncSession = Depends(get_async_db)
):
    """Réordonner les questions d'une évaluation"""
    service = QuestionEvaluationService(db)
    await service.reorder_questions(evaluation_id, question_orders)
    return {"message": "Questions réordonnées avec succès"}

# ──────────────────────────────────────────────────────────────
# Router Réponses des candidats
# ──────────────────────────────────────────────────────────────
reponses_candidats = APIRouter(
    prefix="/reponses-candidats",
    tags=["reponses-candidats"],
)

@reponses_candidats.post(
    "",
    response_model=ReponseCandidatResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Créer une nouvelle réponse de candidat",
    description="Crée une nouvelle réponse pour une question d'évaluation."
)
async def create_reponse_candidat(
    reponse_data: ReponseCandidatCreate,
    user_id: int,
    db: AsyncSession = Depends(get_async_db)
):
    """Créer une réponse de candidat"""
    service = ReponseCandidatService(db)
    return await service.create(reponse_data)

@reponses_candidats.get(
    "/{reponse_id}",
    response_model=ReponseCandidatResponse,
    status_code=status.HTTP_200_OK,
    summary="Récupérer une réponse de candidat par ID",
    description="Récupère les détails complets d'une réponse de candidat."
)
async def get_reponse_candidat(
    reponse_id: int,
    db: AsyncSession = Depends(get_async_db)
):
    """Récupérer une réponse de candidat"""
    service = ReponseCandidatService(db)
    return await service.get_by_id(reponse_id)

@reponses_candidats.get(
    "/resultat/{resultat_id}",
    response_model=List[ReponseCandidatResponse],
    status_code=status.HTTP_200_OK,
    summary="Lister les réponses d'un résultat d'évaluation",
    description="Récupère toutes les réponses d'un résultat d'évaluation."
)
async def get_reponses_resultat(
    resultat_id: int,
    db: AsyncSession = Depends(get_async_db)
):
    """Lister les réponses d'un résultat d'évaluation"""
    service = ReponseCandidatService(db)
    return await service.get_by_resultat(resultat_id)

@reponses_candidats.put(
    "/{reponse_id}",
    response_model=ReponseCandidatResponse,
    status_code=status.HTTP_200_OK,
    summary="Mettre à jour une réponse de candidat",
    description="Met à jour les informations d'une réponse de candidat existante."
)
async def update_reponse_candidat(
    reponse_id: int,
    reponse_data: ReponseCandidatCreate,
    user_id: int,
    db: AsyncSession = Depends(get_async_db)
):
    """Mettre à jour une réponse de candidat"""
    service = ReponseCandidatService(db)
    return await service.update(reponse_id, reponse_data)

@reponses_candidats.delete(
    "/{reponse_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Supprimer une réponse de candidat",
    description="Supprime une réponse de candidat."
)
async def delete_reponse_candidat(
    reponse_id: int,
    user_id: int,
    db: AsyncSession = Depends(get_async_db)
):
    """Supprimer une réponse de candidat"""
    service = ReponseCandidatService(db)
    await service.delete(reponse_id)

@reponses_candidats.post(
    "/{reponse_id}/corriger",
    response_model=ReponseCandidatResponse,
    status_code=status.HTTP_200_OK,
    summary="Corriger une réponse de candidat",
    description="Corrige une réponse de candidat en attribuant des points et un commentaire."
)
async def corriger_reponse_candidat(
    reponse_id: int,
    points_obtenus: float,
    commentaire: Optional[str] = None,
    user_id: int = None,
    db: AsyncSession = Depends(get_async_db)
):
    """Corriger une réponse de candidat"""
    service = ReponseCandidatService(db)
    await service.corriger_reponse(reponse_id, points_obtenus, commentaire)
    return await service.get_by_id(reponse_id)

# ──────────────────────────────────────────────────────────────
# Routes supplémentaires pour les résultats d'évaluation
# ──────────────────────────────────────────────────────────────

@resultats_evaluations.get(
    "/{resultat_id}",
    response_model=ResultatEvaluationResponse,
    status_code=status.HTTP_200_OK,
    summary="Récupérer un résultat d'évaluation par ID",
    description="Récupère les détails complets d'un résultat d'évaluation."
)
async def get_resultat_evaluation(
    resultat_id: int,
    db: AsyncSession = Depends(get_async_db)
):
    """Récupérer un résultat d'évaluation"""
    service = ResultatEvaluationService(db)
    return await service.get_by_id(resultat_id)

@resultats_evaluations.get(
    "/evaluation/{evaluation_id}",
    response_model=List[ResultatEvaluationResponse],
    status_code=status.HTTP_200_OK,
    summary="Lister les résultats d'une évaluation",
    description="Récupère tous les résultats d'une évaluation."
)
async def get_resultats_evaluation(
    evaluation_id: int,
    db: AsyncSession = Depends(get_async_db)
):
    """Lister les résultats d'une évaluation"""
    service = ResultatEvaluationService(db)
    return await service.get_by_evaluation(evaluation_id)

@resultats_evaluations.get(
    "/candidat/{candidat_id}",
    response_model=List[ResultatEvaluationResponse],
    status_code=status.HTTP_200_OK,
    summary="Lister les résultats d'un candidat",
    description="Récupère tous les résultats d'évaluation d'un candidat."
)
async def get_resultats_candidat(
    candidat_id: int,
    db: AsyncSession = Depends(get_async_db)
):
    """Lister les résultats d'un candidat"""
    service = ResultatEvaluationService(db)
    return await service.get_by_candidat(candidat_id)

@resultats_evaluations.post(
    "/{resultat_id}/corriger",
    response_model=ResultatEvaluationResponse,
    status_code=status.HTTP_200_OK,
    summary="Corriger une évaluation",
    description="Corrige automatiquement une évaluation soumise."
)
async def corriger_evaluation(
    resultat_id: int,
    user_id: int,
    db: AsyncSession = Depends(get_async_db)
):
    """Corriger une évaluation"""
    service = ResultatEvaluationService(db)
    return await service.corriger_evaluation(resultat_id)

@resultats_evaluations.put(
    "/{resultat_id}",
    response_model=ResultatEvaluationResponse,
    status_code=status.HTTP_200_OK,
    summary="Mettre à jour un résultat d'évaluation",
    description="Met à jour les informations d'un résultat d'évaluation existant."
)
async def update_resultat_evaluation(
    resultat_id: int,
    resultat_data: dict,
    user_id: int,
    db: AsyncSession = Depends(get_async_db)
):
    """Mettre à jour un résultat d'évaluation"""
    service = ResultatEvaluationService(db)
    return await service.update(resultat_id, resultat_data)

@resultats_evaluations.delete(
    "/{resultat_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Supprimer un résultat d'évaluation",
    description="Supprime un résultat d'évaluation et toutes ses réponses associées."
)
async def delete_resultat_evaluation(
    resultat_id: int,
    user_id: int,
    db: AsyncSession = Depends(get_async_db)
):
    """Supprimer un résultat d'évaluation"""
    service = ResultatEvaluationService(db)
    await service.delete(resultat_id)