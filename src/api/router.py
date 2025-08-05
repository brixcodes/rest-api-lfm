from fastapi import APIRouter, Depends, HTTPException, Request, status, UploadFile, File
from fastapi.security import OAuth2PasswordRequestForm
from sqlalchemy.ext.asyncio import AsyncSession
from typing import List
from src.util.database.database import get_async_db
from src.api.service import (
    UtilisateurService, PermissionService, RoleService, FormationService,
    InscriptionFormationService, PaiementService, ModuleService, RessourceService,
    ChefDOeuvreService, ProjetCollectifService, EvaluationService, QuestionService,
    PropositionService, ResultatEvaluationService, GenotypeIndividuelService,
    AscendanceGenotypeService, SanteGenotypeService, EducationGenotypeService,
    PlanInterventionIndividualiseService, AccreditationService, ActualiteService,
    FileService
)
from src.api.schema import (
    Utilisateur, UtilisateurLight, UtilisateurCreate, UtilisateurUpdate,
    Permission, PermissionLight, PermissionCreate, PermissionUpdate,
    Role, RoleLight, RoleCreate, RoleUpdate,
    Formation, FormationLight, FormationCreate, FormationUpdate,
    InscriptionFormation, InscriptionFormationLight, InscriptionFormationCreate, InscriptionFormationUpdate,
    Paiement, PaiementLight, PaiementCreate, PaiementUpdate,
    Module, ModuleLight, ModuleCreate, ModuleUpdate,
    Ressource, RessourceLight, RessourceCreate, RessourceUpdate,
    ChefDOeuvre, ChefDOeuvreLight, ChefDOeuvreCreate, ChefDOeuvreUpdate,
    ProjetCollectif, ProjetCollectifLight, ProjetCollectifCreate, ProjetCollectifUpdate,
    Evaluation, EvaluationLight, EvaluationCreate, EvaluationUpdate,
    Question, QuestionLight, QuestionCreate, QuestionUpdate,
    Proposition, PropositionLight, PropositionCreate, PropositionUpdate,
    ResultatEvaluation, ResultatEvaluationLight, ResultatEvaluationCreate, ResultatEvaluationUpdate,
    GenotypeIndividuel, GenotypeIndividuelLight, GenotypeIndividuelCreate, GenotypeIndividuelUpdate,
    AscendanceGenotype, AscendanceGenotypeLight, AscendanceGenotypeCreate, AscendanceGenotypeUpdate,
    SanteGenotype, SanteGenotypeLight, SanteGenotypeCreate, SanteGenotypeUpdate,
    EducationGenotype, EducationGenotypeLight, EducationGenotypeCreate, EducationGenotypeUpdate,
    PlanInterventionIndividualise, PlanInterventionIndividualiseLight, PlanInterventionIndividualiseCreate, PlanInterventionIndividualiseUpdate,
    Accreditation, AccreditationLight, AccreditationCreate, AccreditationUpdate,
    Actualite, ActualiteLight, ActualiteCreate, ActualiteUpdate
)
from src.util.helper.enum import FileTypeEnum
from src.util.security.security import get_current_active_user, has_permission, require_permissions
import logging

logger = logging.getLogger(__name__)

# Initialisation des services
utilisateur_service = UtilisateurService()
permission_service = PermissionService()
role_service = RoleService()
formation_service = FormationService()
inscription_formation_service = InscriptionFormationService()
paiement_service = PaiementService()
module_service = ModuleService()
ressource_service = RessourceService()
chef_d_oeuvre_service = ChefDOeuvreService()
projet_collectif_service = ProjetCollectifService()
evaluation_service = EvaluationService()
question_service = QuestionService()
proposition_service = PropositionService()
resultat_evaluation_service = ResultatEvaluationService()
genotype_individuel_service = GenotypeIndividuelService()
ascendance_genotype_service = AscendanceGenotypeService()
sante_genotype_service = SanteGenotypeService()
education_genotype_service = EducationGenotypeService()
plan_intervention_service = PlanInterventionIndividualiseService()
accreditation_service = AccreditationService()
actualite_service = ActualiteService()
file_service = FileService()

# Initialisation du routeur principal
router = APIRouter()

# ============================================================================
# ========================= ROUTES DES UTILISATEURS ==========================
# ============================================================================

@router.post(
    "/login",
    response_model=dict,
    tags=["Utilisateurs"],
    summary="Connexion d'un utilisateur",
    description="Authentifie un utilisateur avec son email et mot de passe, retourne un token JWT. Aucun rôle ou permission spécifique requis."
)
async def login(form_data: OAuth2PasswordRequestForm = Depends(), db: AsyncSession = Depends(get_async_db)):
    """
    Authentifie un utilisateur et génère un token JWT.

    - **email**: Adresse email de l'utilisateur.
    - **password**: Mot de passe de l'utilisateur.
    - **Réponses**:
        - **200**: Token JWT généré avec succès.
        - **401**: Email ou mot de passe incorrect.
        - **500**: Erreur interne du serveur.
    """
    return await utilisateur_service.login(db, form_data.username, form_data.password)

@router.get(
    "/me",
    response_model=UtilisateurLight,
    tags=["Utilisateurs"],
    summary="Récupérer l'utilisateur connecté",
    description="Retourne les informations de l'utilisateur connecté, incluant ses permissions (directes et via rôle). Requiert un utilisateur actif."
)
async def read_users_me(current_user: UtilisateurLight = Depends(get_current_active_user)):
    """
    Récupère les informations de l'utilisateur connecté.

    - **Réponses**:
        - **200**: Informations de l'utilisateur connecté.
        - **401**: Token invalide ou expiré.
        - **403**: Utilisateur inactif.
        - **500**: Erreur interne du serveur.
    """
    return current_user

@router.post(
    "/users",
    response_model=UtilisateurLight,
    tags=["Utilisateurs"],
    summary="Créer un nouvel utilisateur",
    description="Crée un nouvel utilisateur avec un mot de passe généré automatiquement. Requiert la permission CREATE_USER."
)
async def create_user(
    user: UtilisateurCreate,
    db: AsyncSession = Depends(get_async_db),
    current_user: UtilisateurLight = Depends(require_permissions(["CREATE_USER"]))
):
    """
    Crée un nouvel utilisateur avec validation de l'unicité de l'email.

    - **user**: Schéma de création de l'utilisateur (nom, email, rôle, etc.).
    - **Réponses**:
        - **200**: Utilisateur créé avec succès.
        - **400**: Données invalides.
        - **409**: Email déjà utilisé.
        - **403**: Permission CREATE_USER manquante.
        - **500**: Erreur interne du serveur.
    """
    return await utilisateur_service.create(db, user)

@router.get(
    "/users/{user_id}",
    response_model=Utilisateur,
    tags=["Utilisateurs"],
    summary="Récupérer un utilisateur par ID",
    description="Récupère les détails d'un utilisateur spécifique par son ID. Requiert la permission VIEW_USERS."
)
async def get_user(
    user_id: int,
    db: AsyncSession = Depends(get_async_db),
    current_user: UtilisateurLight = Depends(require_permissions(["VIEW_USERS"]))
):
    """
    Récupère un utilisateur spécifique par son ID.

    - **user_id**: ID de l'utilisateur à récupérer.
    - **Réponses**:
        - **200**: Détails de l'utilisateur.
        - **404**: Utilisateur non trouvé.
        - **403**: Permission VIEW_USERS manquante.
        - **500**: Erreur interne du serveur.
    """
    return await utilisateur_service.get(db, user_id)

@router.get(
    "/users",
    response_model=List[Utilisateur],
    tags=["Utilisateurs"],
    summary="Lister tous les utilisateurs",
    description="Récupère une liste paginée de tous les utilisateurs avec leurs relations. Requiert la permission VIEW_USERS."
)
async def list_users(
    skip: int = 0,
    limit: int = 100,
    db: AsyncSession = Depends(get_async_db),
    current_user: UtilisateurLight = Depends(require_permissions(["VIEW_USERS"]))
):
    """
    Liste tous les utilisateurs avec pagination.

    - **skip**: Nombre d'utilisateurs à sauter (défaut: 0).
    - **limit**: Nombre maximum d'utilisateurs à retourner (défaut: 100).
    - **Réponses**:
        - **200**: Liste des utilisateurs.
        - **403**: Permission VIEW_USERS manquante.
        - **500**: Erreur interne du serveur.
    """
    return await utilisateur_service.get_all(db, skip, limit)

@router.put(
    "/users/{user_id}",
    response_model=UtilisateurLight,
    tags=["Utilisateurs"],
    summary="Mettre à jour un utilisateur",
    description="Met à jour les informations d'un utilisateur spécifique. Requiert la permission EDIT_USERS."
)
async def update_user(
    user_id: int,
    user_update: UtilisateurUpdate,
    db: AsyncSession = Depends(get_async_db),
    current_user: UtilisateurLight = Depends(require_permissions(["EDIT_USERS"]))
):
    """
    Met à jour un utilisateur spécifique.

    - **user_id**: ID de l'utilisateur à mettre à jour.
    - **user_update**: Schéma de mise à jour de l'utilisateur.
    - **Réponses**:
        - **200**: Utilisateur mis à jour avec succès.
        - **404**: Utilisateur non trouvé.
        - **409**: Email déjà utilisé.
        - **403**: Permission EDIT_USERS manquante.
        - **500**: Erreur interne du serveur.
    """
    return await utilisateur_service.update(db, user_id, user_update)

@router.delete(
    "/users/{user_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    tags=["Utilisateurs"],
    summary="Supprimer un utilisateur",
    description="Supprime un utilisateur spécifique par son ID. Requiert la permission DELETE_USERS."
)
async def delete_user(
    user_id: int,
    db: AsyncSession = Depends(get_async_db),
    current_user: UtilisateurLight = Depends(require_permissions(["DELETE_USERS"]))
):
    """
    Supprime un utilisateur spécifique.

    - **user_id**: ID de l'utilisateur à supprimer.
    - **Réponses**:
        - **204**: Utilisateur supprimé avec succès.
        - **404**: Utilisateur non trouvé.
        - **403**: Permission DELETE_USERS manquante.
        - **500**: Erreur interne du serveur.
    """
    await utilisateur_service.delete(db, user_id)

@router.post(
    "/users/{user_id}/change-password",
    response_model=str,
    tags=["Utilisateurs"],
    summary="Changer le mot de passe d'un utilisateur",
    description="Change le mot de passe d'un utilisateur après vérification de l'ancien mot de passe. Requiert la permission CHANGE_PASSWORD ou que l'utilisateur modifie son propre mot de passe."
)
async def change_password(
    user_id: int,
    current_password: str,
    new_password: str,
    db: AsyncSession = Depends(get_async_db),
    current_user: UtilisateurLight = Depends(get_current_active_user)
):
    """
    Change le mot de passe d'un utilisateur.

    - **user_id**: ID de l'utilisateur dont le mot de passe doit être changé.
    - **current_password**: Mot de passe actuel.
    - **new_password**: Nouveau mot de passe.
    - **Réponses**:
        - **200**: Mot de passe changé avec succès.
        - **401**: Mot de passe actuel incorrect.
        - **403**: Permission CHANGE_PASSWORD manquante (si non-soi).
        - **404**: Utilisateur non trouvé.
        - **500**: Erreur interne du serveur.
    """
    if current_user.id != user_id and not has_permission(current_user, ["CHANGE_PASSWORD"]):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Permission CHANGE_PASSWORD requise pour modifier le mot de passe d'un autre utilisateur"
        )
    return await utilisateur_service.change_password(db, user_id, current_password, new_password)

@router.post(
    "/users/reset-password",
    response_model=str,
    tags=["Utilisateurs"],
    summary="Demander une réinitialisation de mot de passe",
    description="Génère un token de réinitialisation de mot de passe pour un utilisateur donné par son email. Aucun rôle ou permission requis."
)
async def reset_password(
    email: str,
    db: AsyncSession = Depends(get_async_db)
):
    """
    Demande une réinitialisation de mot de passe.

    - **email**: Email de l'utilisateur.
    - **Réponses**:
        - **200**: Token de réinitialisation généré.
        - **404**: Utilisateur non trouvé.
        - **500**: Erreur interne du serveur.
    """
    return await utilisateur_service.reset_password(db, email)

@router.post(
    "/users/confirm-reset-password",
    status_code=status.HTTP_204_NO_CONTENT,
    tags=["Utilisateurs"],
    summary="Confirmer la réinitialisation de mot de passe",
    description="Confirme la réinitialisation du mot de passe avec un token. Aucun rôle ou permission requis."
)
async def confirm_reset_password(
    reset_token: str,
    db: AsyncSession = Depends(get_async_db)
):
    """
    Confirme la réinitialisation du mot de passe.

    - **reset_token**: Token de réinitialisation.
    - **Réponses**:
        - **204**: Mot de passe réinitialisé avec succès.
        - **400**: Token invalide ou expiré.
        - **500**: Erreur interne du serveur.
    """
    await utilisateur_service.confirm_reset_password(db, reset_token)

# ============================================================================
# ========================= ROUTES DES PERMISSIONS ===========================
# ============================================================================

@router.post(
    "/permissions",
    response_model=PermissionLight,
    tags=["Permissions"],
    summary="Créer une nouvelle permission",
    description="Crée une nouvelle permission avec validation de l'unicité du nom. Requiert la permission CREATE_PERMISSION."
)
async def create_permission(
    permission: PermissionCreate,
    db: AsyncSession = Depends(get_async_db),
    current_user: UtilisateurLight = Depends(require_permissions(["CREATE_PERMISSION"]))
):
    """
    Crée une nouvelle permission.

    - **permission**: Schéma de création de la permission.
    - **Réponses**:
        - **200**: Permission créée avec succès.
        - **409**: Nom de permission déjà utilisé.
        - **403**: Permission CREATE_PERMISSION manquante.
        - **500**: Erreur interne du serveur.
    """
    return await permission_service.create(db, permission)

@router.get(
    "/permissions/{permission_id}",
    response_model=Permission,
    tags=["Permissions"],
    summary="Récupérer une permission par ID",
    description="Récupère les détails d'une permission spécifique par son ID. Requiert la permission VIEW_PERMISSIONS."
)
async def get_permission(
    permission_id: int,
    db: AsyncSession = Depends(get_async_db),
    current_user: UtilisateurLight = Depends(require_permissions(["VIEW_PERMISSIONS"]))
):
    """
    Récupère une permission spécifique.

    - **permission_id**: ID de la permission à récupérer.
    - **Réponses**:
        - **200**: Détails de la permission.
        - **404**: Permission non trouvée.
        - **403**: Permission VIEW_PERMISSIONS manquante.
        - **500**: Erreur interne du serveur.
    """
    return await permission_service.get(db, permission_id)

@router.get(
    "/permissions",
    response_model=List[Permission],
    tags=["Permissions"],
    summary="Lister toutes les permissions",
    description="Récupère une liste paginée de toutes les permissions avec leurs relations. Requiert la permission VIEW_PERMISSIONS."
)
async def list_permissions(
    skip: int = 0,
    limit: int = 100,
    db: AsyncSession = Depends(get_async_db),
    current_user: UtilisateurLight = Depends(require_permissions(["VIEW_PERMISSIONS"]))
):
    """
    Liste toutes les permissions avec pagination.

    - **skip**: Nombre de permissions à sauter (défaut: 0).
    - **limit**: Nombre maximum de permissions à retourner (défaut: 100).
    - **Réponses**:
        - **200**: Liste des permissions.
        - **403**: Permission VIEW_PERMISSIONS manquante.
        - **500**: Erreur interne du serveur.
    """
    return await permission_service.get_all(db, skip, limit)

@router.put(
    "/permissions/{permission_id}",
    response_model=Permission,
    tags=["Permissions"],
    summary="Mettre à jour une permission",
    description="Met à jour une permission spécifique. Requiert la permission EDIT_PERMISSIONS."
)
async def update_permission(
    permission_id: int,
    permission_update: PermissionUpdate,
    db: AsyncSession = Depends(get_async_db),
    current_user: UtilisateurLight = Depends(require_permissions(["EDIT_PERMISSIONS"]))
):
    """
    Met à jour une permission spécifique.

    - **permission_id**: ID de la permission à mettre à jour.
    - **permission_update**: Schéma de mise à jour de la permission.
    - **Réponses**:
        - **200**: Permission mise à jour avec succès.
        - **404**: Permission non trouvée.
        - **409**: Nom de permission déjà utilisé.
        - **403**: Permission EDIT_PERMISSIONS manquante.
        - **500**: Erreur interne du serveur.
    """
    return await permission_service.update(db, permission_id, permission_update)

@router.delete(
    "/permissions/{permission_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    tags=["Permissions"],
    summary="Supprimer une permission",
    description="Supprime une permission spécifique par son ID. Requiert la permission DELETE_PERMISSIONS."
)
async def delete_permission(
    permission_id: int,
    db: AsyncSession = Depends(get_async_db),
    current_user: UtilisateurLight = Depends(require_permissions(["DELETE_PERMISSIONS"]))
):
    """
    Supprime une permission spécifique.

    - **permission_id**: ID de la permission à supprimer.
    - **Réponses**:
        - **204**: Permission supprimée avec succès.
        - **404**: Permission non trouvée.
        - **403**: Permission DELETE_PERMISSIONS manquante.
        - **500**: Erreur interne du serveur.
    """
    await permission_service.delete(db, permission_id)

# ============================================================================
# ========================= ROUTES DES RÔLES ================================
# ============================================================================

@router.post(
    "/roles",
    response_model=RoleLight,
    tags=["Rôles"],
    summary="Créer un nouveau rôle",
    description="Crée un nouveau rôle avec ses permissions. Requiert la permission CREATE_ROLE."
)
async def create_role(
    role: RoleCreate,
    db: AsyncSession = Depends(get_async_db),
    current_user: UtilisateurLight = Depends(require_permissions(["CREATE_ROLE"]))
):
    """
    Crée un nouveau rôle.

    - **role**: Schéma de création du rôle (nom et liste d'IDs de permissions).
    - **Réponses**:
        - **200**: Rôle créé avec succès.
        - **409**: Nom de rôle déjà utilisé.
        - **403**: Permission CREATE_ROLE manquante.
        - **500**: Erreur interne du serveur.
    """
    return await role_service.create(db, role)

@router.get(
    "/roles/{role_id}",
    response_model=Role,
    tags=["Rôles"],
    summary="Récupérer un rôle par ID",
    description="Récupère les détails d'un rôle spécifique par son ID. Requiert la permission VIEW_ROLES."
)
async def get_role(
    role_id: int,
    db: AsyncSession = Depends(get_async_db),
    current_user: UtilisateurLight = Depends(require_permissions(["VIEW_ROLES"]))
):
    """
    Récupère un rôle spécifique.

    - **role_id**: ID du rôle à récupérer.
    - **Réponses**:
        - **200**: Détails du rôle.
        - **404**: Rôle non trouvé.
        - **403**: Permission VIEW_ROLES manquante.
        - **500**: Erreur interne du serveur.
    """
    return await role_service.get(db, role_id)

@router.get(
    "/roles",
    response_model=List[Role],
    tags=["Rôles"],
    summary="Lister tous les rôles",
    description="Récupère une liste paginée de tous les rôles avec leurs permissions. Requiert la permission VIEW_ROLES."
)
async def list_roles(
    skip: int = 0,
    limit: int = 100,
    db: AsyncSession = Depends(get_async_db),
    current_user: UtilisateurLight = Depends(require_permissions(["VIEW_ROLES"]))
):
    """
    Liste tous les rôles avec pagination.

    - **skip**: Nombre de rôles à sauter (défaut: 0).
    - **limit**: Nombre maximum de rôles à retourner (défaut: 100).
    - **Réponses**:
        - **200**: Liste des rôles.
        - **403**: Permission VIEW_ROLES manquante.
        - **500**: Erreur interne du serveur.
    """
    return await role_service.get_all(db, skip, limit)

@router.put(
    "/roles/{role_id}",
    response_model=Role,
    tags=["Rôles"],
    summary="Mettre à jour un rôle",
    description="Met à jour un rôle spécifique avec ses permissions. Requiert la permission EDIT_ROLES."
)
async def update_role(
    role_id: int,
    role_update: RoleUpdate,
    db: AsyncSession = Depends(get_async_db),
    current_user: UtilisateurLight = Depends(require_permissions(["EDIT_ROLES"]))
):
    """
    Met à jour un rôle spécifique.

    - **role_id**: ID du rôle à mettre à jour.
    - **role_update**: Schéma de mise à jour du rôle.
    - **Réponses**:
        - **200**: Rôle mis à jour avec succès.
        - **404**: Rôle non trouvé.
        - **409**: Nom de rôle déjà utilisé.
        - **403**: Permission EDIT_ROLES manquante.
        - **500**: Erreur interne du serveur.
    """
    return await role_service.update(db, role_id, role_update)

@router.delete(
    "/roles/{role_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    tags=["Rôles"],
    summary="Supprimer un rôle",
    description="Supprime un rôle spécifique par son ID. Requiert la permission DELETE_ROLES."
)
async def delete_role(
    role_id: int,
    db: AsyncSession = Depends(get_async_db),
    current_user: UtilisateurLight = Depends(require_permissions(["DELETE_ROLES"]))
):
    """
    Supprime un rôle spécifique.

    - **role_id**: ID du rôle à supprimer.
    - **Réponses**:
        - **204**: Rôle supprimé avec succès.
        - **404**: Rôle non trouvé.
        - **403**: Permission DELETE_ROLES manquante.
        - **500**: Erreur interne du serveur.
    """
    await role_service.delete(db, role_id)

@router.post(
    "/roles/{role_id}/permissions",
    response_model=str,
    tags=["Rôles"],
    summary="Assigner des permissions à un rôle",
    description="Assigne une ou plusieurs permissions à un rôle. Requiert la permission ASSIGN_PERMISSIONS."
)
async def assign_role_permissions(
    role_id: int,
    permission_ids: List[int],
    db: AsyncSession = Depends(get_async_db),
    current_user: UtilisateurLight = Depends(require_permissions(["ASSIGN_PERMISSIONS"]))
):
    """
    Assigne des permissions à un rôle.

    - **role_id**: ID du rôle auquel assigner les permissions.
    - **permission_ids**: Liste des IDs des permissions à assigner.
    - **Réponses**:
        - **200**: Permissions assignées avec succès.
        - **404**: Rôle ou permissions non trouvés.
        - **403**: Permission ASSIGN_PERMISSIONS manquante.
        - **500**: Erreur interne du serveur.
    """
    return await role_service.assign_permission(db, role_id, permission_ids)

@router.delete(
    "/roles/{role_id}/permissions",
    response_model=str,
    tags=["Rôles"],
    summary="Révoquer des permissions d'un rôle",
    description="Révoque une ou plusieurs permissions d'un rôle. Requiert la permission REVOKE_PERMISSIONS."
)
async def revoke_role_permissions(
    role_id: int,
    permission_ids: List[int],
    db: AsyncSession = Depends(get_async_db),
    current_user: UtilisateurLight = Depends(require_permissions(["REVOKE_PERMISSIONS"]))
):
    """
    Révoque des permissions d'un rôle.

    - **role_id**: ID du rôle auquel révoquer les permissions.
    - **permission_ids**: Liste des IDs des permissions à révoquer.
    - **Réponses**:
        - **200**: Permissions révoquées avec succès.
        - **404**: Rôle ou permissions non trouvés.
        - **403**: Permission REVOKE_PERMISSIONS manquante.
        - **500**: Erreur interne du serveur.
    """
    return await role_service.revoke_permission(db, role_id, permission_ids)

# ============================================================================
# ========================= ROUTES DES FORMATIONS ===========================
# ============================================================================

@router.post(
    "/formations",
    response_model=FormationLight,
    tags=["Formations"],
    summary="Créer une nouvelle formation",
    description="Crée une nouvelle formation avec validation de l'unicité du titre. Requiert la permission CREATE_FORMATION."
)
async def create_formation(
    formation: FormationCreate,
    db: AsyncSession = Depends(get_async_db),
    current_user: UtilisateurLight = Depends(require_permissions(["CREATE_FORMATION"]))
):
    """
    Crée une nouvelle formation.

    - **formation**: Schéma de création de la formation.
    - **Réponses**:
        - **200**: Formation créée avec succès.
        - **409**: Titre de formation déjà utilisé.
        - **403**: Permission CREATE_FORMATION manquante.
        - **500**: Erreur interne du serveur.
    """
    return await formation_service.create(db, formation)

@router.get(
    "/formations/{formation_id}",
    response_model=Formation,
    tags=["Formations"],
    summary="Récupérer une formation par ID",
    description="Récupère les détails d'une formation spécifique par son ID. Requiert la permission VIEW_FORMATIONS."
)
async def get_formation(
    formation_id: int,
    db: AsyncSession = Depends(get_async_db),
    current_user: UtilisateurLight = Depends(require_permissions(["VIEW_FORMATIONS"]))
):
    """
    Récupère une formation spécifique.

    - **formation_id**: ID de la formation à récupérer.
    - **Réponses**:
        - **200**: Détails de la formation.
        - **404**: Formation non trouvée.
        - **403**: Permission VIEW_FORMATIONS manquante.
        - **500**: Erreur interne du serveur.
    """
    return await formation_service.get(db, formation_id)

@router.get(
    "/formations",
    response_model=List[Formation],
    tags=["Formations"],
    summary="Lister toutes les formations",
    description="Récupère une liste paginée de toutes les formations avec leurs relations. Requiert la permission VIEW_FORMATIONS."
)
async def list_formations(
    skip: int = 0,
    limit: int = 100,
    db: AsyncSession = Depends(get_async_db),
    current_user: UtilisateurLight = Depends(require_permissions(["VIEW_FORMATIONS"]))
):
    """
    Liste toutes les formations avec pagination.

    - **skip**: Nombre de formations à sauter (défaut: 0).
    - **limit**: Nombre maximum de formations à retourner (défaut: 100).
    - **Réponses**:
        - **200**: Liste des formations.
        - **403**: Permission VIEW_FORMATIONS manquante.
        - **500**: Erreur interne du serveur.
    """
    return await formation_service.get_all(db, skip, limit)

@router.put(
    "/formations/{formation_id}",
    response_model=Formation,
    tags=["Formations"],
    summary="Mettre à jour une formation",
    description="Met à jour une formation spécifique. Requiert la permission EDIT_FORMATIONS."
)
async def update_formation(
    formation_id: int,
    formation_update: FormationUpdate,
    db: AsyncSession = Depends(get_async_db),
    current_user: UtilisateurLight = Depends(require_permissions(["EDIT_FORMATIONS"]))
):
    """
    Met à jour une formation spécifique.

    - **formation_id**: ID de la formation à mettre à jour.
    - **formation_update**: Schéma de mise à jour de la formation.
    - **Réponses**:
        - **200**: Formation mise à jour avec succès.
        - **404**: Formation non trouvée.
        - **409**: Titre de formation déjà utilisé.
        - **403**: Permission EDIT_FORMATIONS manquante.
        - **500**: Erreur interne du serveur.
    """
    return await formation_service.update(db, formation_id, formation_update)

@router.delete(
    "/formations/{formation_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    tags=["Formations"],
    summary="Supprimer une formation",
    description="Supprime une formation spécifique par son ID. Requiert la permission DELETE_FORMATIONS."
)
async def delete_formation(
    formation_id: int,
    db: AsyncSession = Depends(get_async_db),
    current_user: UtilisateurLight = Depends(require_permissions(["DELETE_FORMATIONS"]))
):
    """
    Supprime une formation spécifique.

    - **formation_id**: ID de la formation à supprimer.
    - **Réponses**:
        - **204**: Formation supprimée avec succès.
        - **404**: Formation non trouvée.
        - **403**: Permission DELETE_FORMATIONS manquante.
        - **500**: Erreur interne du serveur.
    """
    await formation_service.delete(db, formation_id)

# ============================================================================
# ========================= ROUTES DES INSCRIPTIONS ==========================
# ============================================================================

@router.post(
    "/inscriptions",
    response_model=InscriptionFormationLight,
    tags=["Inscriptions"],
    summary="Créer une nouvelle inscription",
    description="Inscrit un utilisateur à une formation. Requiert la permission CREATE_INSCRIPTION."
)
async def create_inscription(
    inscription: InscriptionFormationCreate,
    db: AsyncSession = Depends(get_async_db),
    current_user: UtilisateurLight = Depends(require_permissions(["CREATE_INSCRIPTION"]))
):
    """
    Crée une nouvelle inscription à une formation.

    - **inscription**: Schéma de création de l'inscription.
    - **Réponses**:
        - **200**: Inscription créée avec succès.
        - **404**: Utilisateur ou formation non trouvé.
        - **409**: Utilisateur déjà inscrit à la formation.
        - **403**: Permission CREATE_INSCRIPTION manquante.
        - **500**: Erreur interne du serveur.
    """
    return await inscription_formation_service.create(db, inscription)

@router.get(
    "/inscriptions/{inscription_id}",
    response_model=InscriptionFormation,
    tags=["Inscriptions"],
    summary="Récupérer une inscription par ID",
    description="Récupère les détails d'une inscription spécifique par son ID. Requiert la permission VIEW_INSCRIPTIONS."
)
async def get_inscription(
    inscription_id: int,
    db: AsyncSession = Depends(get_async_db),
    current_user: UtilisateurLight = Depends(require_permissions(["VIEW_INSCRIPTIONS"]))
):
    """
    Récupère une inscription spécifique.

    - **inscription_id**: ID de l'inscription à récupérer.
    - **Réponses**:
        - **200**: Détails de l'inscription.
        - **404**: Inscription non trouvée.
        - **403**: Permission VIEW_INSCRIPTIONS manquante.
        - **500**: Erreur interne du serveur.
    """
    return await inscription_formation_service.get(db, inscription_id)

@router.get(
    "/inscriptions",
    response_model=List[InscriptionFormation],
    tags=["Inscriptions"],
    summary="Lister toutes les inscriptions",
    description="Récupère une liste paginée de toutes les inscriptions avec leurs relations. Requiert la permission VIEW_INSCRIPTIONS."
)
async def list_inscriptions(
    skip: int = 0,
    limit: int = 100,
    db: AsyncSession = Depends(get_async_db),
    current_user: UtilisateurLight = Depends(require_permissions(["VIEW_INSCRIPTIONS"]))
):
    """
    Liste toutes les inscriptions avec pagination.

    - **skip**: Nombre d'inscriptions à sauter (défaut: 0).
    - **limit**: Nombre maximum d'inscriptions à retourner (défaut: 100).
    - **Réponses**:
        - **200**: Liste des inscriptions.
        - **403**: Permission VIEW_INSCRIPTIONS manquante.
        - **500**: Erreur interne du serveur.
    """
    return await inscription_formation_service.get_all(db, skip, limit)

@router.get(
    "/inscriptions/{inscription_id}/paiements",
    response_model=List[InscriptionFormation],
    tags=["Inscriptions"],
    summary="Récupérer une inscription avec ses paiements",
    description="Récupère une inscription spécifique avec ses paiements associés. Requiert la permission VIEW_INSCRIPTIONS."
)
async def get_inscription_with_paiements(
    inscription_id: int,
    db: AsyncSession = Depends(get_async_db),
    current_user: UtilisateurLight = Depends(require_permissions(["VIEW_INSCRIPTIONS"]))
):
    """
    Récupère une inscription avec ses paiements.

    - **inscription_id**: ID de l'inscription à récupérer.
    - **Réponses**:
        - **200**: Inscription avec paiements.
        - **404**: Inscription non trouvée.
        - **403**: Permission VIEW_INSCRIPTIONS manquante.
        - **500**: Erreur interne du serveur.
    """
    return await inscription_formation_service.get_with_paiements(db, inscription_id)

@router.put(
    "/inscriptions/{inscription_id}",
    response_model=InscriptionFormation,
    tags=["Inscriptions"],
    summary="Mettre à jour une inscription",
    description="Met à jour une inscription spécifique avec validation du montant versé. Requiert la permission EDIT_INSCRIPTIONS."
)
async def update_inscription(
    inscription_id: int,
    inscription_update: InscriptionFormationUpdate,
    db: AsyncSession = Depends(get_async_db),
    current_user: UtilisateurLight = Depends(require_permissions(["EDIT_INSCRIPTIONS"]))
):
    """
    Met à jour une inscription spécifique.

    - **inscription_id**: ID de l'inscription à mettre à jour.
    - **inscription_update**: Schéma de mise à jour de l'inscription.
    - **Réponses**:
        - **200**: Inscription mise à jour avec succès.
        - **404**: Inscription, utilisateur ou formation non trouvé.
        - **400**: Montant versé dépasse les frais de la formation.
        - **403**: Permission EDIT_INSCRIPTIONS manquante.
        - **500**: Erreur interne du serveur.
    """
    return await inscription_formation_service.update(db, inscription_id, inscription_update)

@router.delete(
    "/inscriptions/{inscription_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    tags=["Inscriptions"],
    summary="Supprimer une inscription",
    description="Supprime une inscription spécifique par son ID. Requiert la permission DELETE_INSCRIPTIONS."
)
async def delete_inscription(
    inscription_id: int,
    db: AsyncSession = Depends(get_async_db),
    current_user: UtilisateurLight = Depends(require_permissions(["DELETE_INSCRIPTIONS"]))
):
    """
    Supprime une inscription spécifique.

    - **inscription_id**: ID de l'inscription à supprimer.
    - **Réponses**:
        - **204**: Inscription supprimée avec succès.
        - **404**: Inscription non trouvée.
        - **403**: Permission DELETE_INSCRIPTIONS manquante.
        - **500**: Erreur interne du serveur.
    """
    await inscription_formation_service.delete(db, inscription_id)

# ============================================================================
# ========================= ROUTES DES PAIEMENTS =============================
# ============================================================================

@router.post(
    "/paiements",
    response_model=PaiementLight,
    tags=["Paiements"],
    summary="Créer un nouveau paiement",
    description="Crée un nouveau paiement pour une inscription avec mise à jour du statut de paiement. Requiert la permission CREATE_PAIEMENT."
)
async def create_paiement(
    paiement: PaiementCreate,
    db: AsyncSession = Depends(get_async_db),
    current_user: UtilisateurLight = Depends(require_permissions(["CREATE_PAIEMENT"]))
):
    """
    Crée un nouveau paiement.

    - **paiement**: Schéma de création du paiement.
    - **Réponses**:
        - **200**: Paiement créé avec succès.
        - **400**: Montant total dépasse les frais de la formation.
        - **404**: Inscription ou formation non trouvée.
        - **403**: Permission CREATE_PAIEMENT manquante.
        - **500**: Erreur interne du serveur.
    """
    return await paiement_service.create(db, paiement)

@router.get(
    "/paiements/{paiement_id}",
    response_model=Paiement,
    tags=["Paiements"],
    summary="Récupérer un paiement par ID",
    description="Récupère les détails d'un paiement spécifique par son ID. Requiert la permission VIEW_PAIEMENTS."
)
async def get_paiement(
    paiement_id: int,
    db: AsyncSession = Depends(get_async_db),
    current_user: UtilisateurLight = Depends(require_permissions(["VIEW_PAIEMENTS"]))
):
    """
    Récupère un paiement spécifique.

    - **paiement_id**: ID du paiement à récupérer.
    - **Réponses**:
        - **200**: Détails du paiement.
        - **404**: Paiement non trouvé.
        - **403**: Permission VIEW_PAIEMENTS manquante.
        - **500**: Erreur interne du serveur.
    """
    return await paiement_service.get(db, paiement_id)

@router.get(
    "/paiements",
    response_model=List[Paiement],
    tags=["Paiements"],
    summary="Lister tous les paiements",
    description="Récupère une liste paginée de tous les paiements avec leurs relations. Requiert la permission VIEW_PAIEMENTS."
)
async def list_paiements(
    skip: int = 0,
    limit: int = 100,
    db: AsyncSession = Depends(get_async_db),
    current_user: UtilisateurLight = Depends(require_permissions(["VIEW_PAIEMENTS"]))
):
    """
    Liste tous les paiements avec pagination.

    - **skip**: Nombre de paiements à sauter (défaut: 0).
    - **limit**: Nombre maximum de paiements à retourner (défaut: 100).
    - **Réponses**:
        - **200**: Liste des paiements.
        - **403**: Permission VIEW_PAIEMENTS manquante.
        - **500**: Erreur interne du serveur.
    """
    return await paiement_service.get_all(db, skip, limit)

@router.get(
    "/inscriptions/{inscription_id}/paiements",
    response_model=List[Paiement],
    tags=["Paiements"],
    summary="Lister les paiements d'une inscription",
    description="Récupère tous les paiements associés à une inscription spécifique. Requiert la permission VIEW_PAIEMENTS."
)
async def list_paiements_by_inscription(
    inscription_id: int,
    skip: int = 0,
    limit: int = 100,
    db: AsyncSession = Depends(get_async_db),
    current_user: UtilisateurLight = Depends(require_permissions(["VIEW_PAIEMENTS"]))
):
    """
    Liste les paiements pour une inscription spécifique.

    - **inscription_id**: ID de l'inscription.
    - **skip**: Nombre de paiements à sauter (défaut: 0).
    - **limit**: Nombre maximum de paiements à retourner (défaut: 100).
    - **Réponses**:
        - **200**: Liste des paiements.
        - **404**: Inscription non trouvée.
        - **403**: Permission VIEW_PAIEMENTS manquante.
        - **500**: Erreur interne du serveur.
    """
    return await paiement_service.get_by_inscription(db, inscription_id, skip, limit)

@router.put(
    "/paiements/{paiement_id}",
    response_model=Paiement,
    tags=["Paiements"],
    summary="Mettre à jour un paiement",
    description="Met à jour un paiement spécifique avec mise à jour du statut de paiement de l'inscription. Requiert la permission EDIT_PAIEMENTS."
)
async def update_paiement(
    paiement_id: int,
    paiement_update: PaiementUpdate,
    db: AsyncSession = Depends(get_async_db),
    current_user: UtilisateurLight = Depends(require_permissions(["EDIT_PAIEMENTS"]))
):
    """
    Met à jour un paiement spécifique.

    - **paiement_id**: ID du paiement à mettre à jour.
    - **paiement_update**: Schéma de mise à jour du paiement.
    - **Réponses**:
        - **200**: Paiement mis à jour avec succès.
        - **400**: Montant total dépasse les frais de la formation.
        - **404**: Paiement ou inscription non trouvé.
        - **403**: Permission EDIT_PAIEMENTS manquante.
        - **500**: Erreur interne du serveur.
    """
    return await paiement_service.update(db, paiement_id, paiement_update)

@router.delete(
    "/paiements/{paiement_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    tags=["Paiements"],
    summary="Supprimer un paiement",
    description="Supprime un paiement spécifique et met à jour l'inscription associée. Requiert la permission DELETE_PAIEMENTS."
)
async def delete_paiement(
    paiement_id: int,
    db: AsyncSession = Depends(get_async_db),
    current_user: UtilisateurLight = Depends(require_permissions(["DELETE_PAIEMENTS"]))
):
    """
    Supprime un paiement spécifique.

    - **paiement_id**: ID du paiement à supprimer.
    - **Réponses**:
        - **204**: Paiement supprimé avec succès.
        - **404**: Paiement ou inscription non trouvé.
        - **403**: Permission DELETE_PAIEMENTS manquante.
        - **500**: Erreur interne du serveur.
    """
    await paiement_service.delete(db, paiement_id)

# ============================================================================
# ========================= ROUTES DES MODULES ===============================
# ============================================================================

@router.post(
    "/modules",
    response_model=ModuleLight,
    tags=["Modules"],
    summary="Créer un nouveau module",
    description="Crée un nouveau module pour une formation avec ordre automatique. Requiert la permission CREATE_MODULE."
)
async def create_module(
    module: ModuleCreate,
    db: AsyncSession = Depends(get_async_db),
    current_user: UtilisateurLight = Depends(require_permissions(["CREATE_MODULE"]))
):
    """
    Crée un nouveau module.

    - **module**: Schéma de création du module.
    - **Réponses**:
        - **200**: Module créé avec succès.
        - **404**: Formation non trouvée.
        - **409**: Module avec ces données existe déjà.
        - **403**: Permission CREATE_MODULE manquante.
        - **500**: Erreur interne du serveur.
    """
    return await module_service.create(db, module)

@router.get(
    "/modules/{module_id}",
    response_model=Module,
    tags=["Modules"],
    summary="Récupérer un module par ID",
    description="Récupère les détails d'un module spécifique par son ID. Requiert la permission VIEW_MODULES."
)
async def get_module(
    module_id: int,
    db: AsyncSession = Depends(get_async_db),
    current_user: UtilisateurLight = Depends(require_permissions(["VIEW_MODULES"]))
):
    """
    Récupère un module spécifique.

    - **module_id**: ID du module à récupérer.
    - **Réponses**:
        - **200**: Détails du module.
        - **404**: Module non trouvé.
        - **403**: Permission VIEW_MODULES manquante.
        - **500**: Erreur interne du serveur.
    """
    return await module_service.get(db, module_id)

@router.get(
    "/modules",
    response_model=List[Module],
    tags=["Modules"],
    summary="Lister tous les modules",
    description="Récupère une liste paginée de tous les modules avec leurs relations. Requiert la permission VIEW_MODULES."
)
async def list_modules(
    skip: int = 0,
    limit: int = 100,
    db: AsyncSession = Depends(get_async_db),
    current_user: UtilisateurLight = Depends(require_permissions(["VIEW_MODULES"]))
):
    """
    Liste tous les modules avec pagination.

    - **skip**: Nombre de modules à sauter (défaut: 0).
    - **limit**: Nombre maximum de modules à retourner (défaut: 100).
    - **Réponses**:
        - **200**: Liste des modules.
        - **403**: Permission VIEW_MODULES manquante.
        - **500**: Erreur interne du serveur.
    """
    return await module_service.get_all(db, skip, limit)

@router.put(
    "/modules/{module_id}",
    response_model=Module,
    tags=["Modules"],
    summary="Mettre à jour un module",
    description="Met à jour un module spécifique. Requiert la permission EDIT_MODULES."
)
async def update_module(
    module_id: int,
    module_update: ModuleUpdate,
    db: AsyncSession = Depends(get_async_db),
    current_user: UtilisateurLight = Depends(require_permissions(["EDIT_MODULES"]))
):
    """
    Met à jour un module spécifique.

    - **module_id**: ID du module à mettre à jour.
    - **module_update**: Schéma de mise à jour du module.
    - **Réponses**:
        - **200**: Module mis à jour avec succès.
        - **404**: Module ou formation non trouvé.
        - **403**: Permission EDIT_MODULES manquante.
        - **500**: Erreur interne du serveur.
    """
    return await module_service.update(db, module_id, module_update)

@router.delete(
    "/modules/{module_id}",
    response_model=str,
    tags=["Modules"],
    summary="Supprimer un module",
    description="Supprime un module spécifique et réordonne les modules restants. Requiert la permission DELETE_MODULES."
)
async def delete_module(
    module_id: int,
    db: AsyncSession = Depends(get_async_db),
    current_user: UtilisateurLight = Depends(require_permissions(["DELETE_MODULES"]))
):
    """
    Supprime un module spécifique et réordonne les modules.

    - **module_id**: ID du module à supprimer.
    - **Réponses**:
        - **200**: Module supprimé et ordres réassignés.
        - **404**: Module non trouvé.
        - **403**: Permission DELETE_MODULES manquante.
        - **500**: Erreur interne du serveur.
    """
    return await module_service.delete(db, module_id)

# ============================================================================
# ========================= ROUTES DES RESSOURCES ===========================
# ============================================================================

@router.post(
    "/ressources",
    response_model=RessourceLight,
    tags=["Ressources"],
    summary="Créer une nouvelle ressource",
    description="Crée une nouvelle ressource pédagogique pour un module. Requiert la permission CREATE_RESSOURCE."
)
async def create_ressource(
    ressource: RessourceCreate,
    db: AsyncSession = Depends(get_async_db),
    current_user: UtilisateurLight = Depends(require_permissions(["CREATE_RESSOURCE"]))
):
    """
    Crée une nouvelle ressource.

    - **ressource**: Schéma de création de la ressource.
    - **Réponses**:
        - **200**: Ressource créée avec succès.
        - **404**: Module non trouvé.
        - **403**: Permission CREATE_RESSOURCE manquante.
        - **500**: Erreur interne du serveur.
    """
    return await ressource_service.create(db, ressource)

@router.get(
    "/ressources/{ressource_id}",
    response_model=Ressource,
    tags=["Ressources"],
    summary="Récupérer une ressource par ID",
    description="Récupère les détails d'une ressource spécifique par son ID. Requiert la permission VIEW_RESSOURCES."
)
async def get_ressource(
    ressource_id: int,
    db: AsyncSession = Depends(get_async_db),
    current_user: UtilisateurLight = Depends(require_permissions(["VIEW_RESSOURCES"]))
):
    """
    Récupère une ressource spécifique.

    - **ressource_id**: ID de la ressource à récupérer.
    - **Réponses**:
        - **200**: Détails de la ressource.
        - **404**: Ressource non trouvée.
        - **403**: Permission VIEW_RESSOURCES manquante.
        - **500**: Erreur interne du serveur.
    """
    return await ressource_service.get(db, ressource_id)

@router.get(
    "/ressources",
    response_model=List[Ressource],
    tags=["Ressources"],
    summary="Lister toutes les ressources",
    description="Récupère une liste paginée de toutes les ressources avec leurs relations. Requiert la permission VIEW_RESSOURCES."
)
async def list_ressources(
    skip: int = 0,
    limit: int = 100,
    db: AsyncSession = Depends(get_async_db),
    current_user: UtilisateurLight = Depends(require_permissions(["VIEW_RESSOURCES"]))
):
    """
    Liste toutes les ressources avec pagination.

    - **skip**: Nombre de ressources à sauter (défaut: 0).
    - **limit**: Nombre maximum de ressources à retourner (défaut: 100).
    - **Réponses**:
        - **200**: Liste des ressources.
        - **403**: Permission VIEW_RESSOURCES manquante.
        - **500**: Erreur interne du serveur.
    """
    return await ressource_service.get_all(db, skip, limit)

@router.put(
    "/ressources/{ressource_id}",
    response_model=Ressource,
    tags=["Ressources"],
    summary="Mettre à jour une ressource",
    description="Met à jour une ressource spécifique. Requiert la permission EDIT_RESSOURCES."
)
async def update_ressource(
    ressource_id: int,
    ressource_update: RessourceUpdate,
    db: AsyncSession = Depends(get_async_db),
    current_user: UtilisateurLight = Depends(require_permissions(["EDIT_RESSOURCES"]))
):
    """
    Met à jour une ressource spécifique.

    - **ressource_id**: ID de la ressource à mettre à jour.
    - **ressource_update**: Schéma de mise à jour de la ressource.
    - **Réponses**:
        - **200**: Ressource mise à jour avec succès.
        - **404**: Ressource ou module non trouvé.
        - **403**: Permission EDIT_RESSOURCES manquante.
        - **500**: Erreur interne du serveur.
    """
    return await ressource_service.update(db, ressource_id, ressource_update)

@router.delete(
    "/ressources/{ressource_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    tags=["Ressources"],
    summary="Supprimer une ressource",
    description="Supprime une ressource spécifique par son ID. Requiert la permission DELETE_RESSOURCES."
)
async def delete_ressource(
    ressource_id: int,
    db: AsyncSession = Depends(get_async_db),
    current_user: UtilisateurLight = Depends(require_permissions(["DELETE_RESSOURCES"]))
):
    """
    Supprime une ressource spécifique.

    - **ressource_id**: ID de la ressource à supprimer.
    - **Réponses**:
        - **204**: Ressource supprimée avec succès.
        - **404**: Ressource non trouvée.
        - **403**: Permission DELETE_RESSOURCES manquante.
        - **500**: Erreur interne du serveur.
    """
    await ressource_service.delete(db, ressource_id)

# ============================================================================
# ========================= ROUTES DES CHEFS-D'ŒUVRE ========================
# ============================================================================

@router.post(
    "/chefs-d-oeuvre",
    response_model=ChefDOeuvreLight,
    tags=["Chefs-d'œuvre"],
    summary="Créer un nouveau chef-d'œuvre",
    description="Crée un nouveau chef-d'œuvre pour un utilisateur et un module. Requiert la permission CREATE_CHEF_D_OEUVRE."
)
async def create_chef_d_oeuvre(
    chef_d_oeuvre: ChefDOeuvreCreate,
    db: AsyncSession = Depends(get_async_db),
    current_user: UtilisateurLight = Depends(require_permissions(["CREATE_CHEF_D_OEUVRE"]))
):
    """
    Crée un nouveau chef-d'œuvre.

    - **chef_d_oeuvre**: Schéma de création du chef-d'œuvre.
    - **Réponses**:
        - **200**: Chef-d'œuvre créé avec succès.
        - **404**: Utilisateur ou module non trouvé.
        - **403**: Permission CREATE_CHEF_D_OEUVRE manquante.
        - **500**: Erreur interne du serveur.
    """
    return await chef_d_oeuvre_service.create(db, chef_d_oeuvre)

@router.get(
    "/chefs-d-oeuvre/{chef_d_oeuvre_id}",
    response_model=ChefDOeuvre,
    tags=["Chefs-d'œuvre"],
    summary="Récupérer un chef-d'œuvre par ID",
    description="Récupère les détails d'un chef-d'œuvre spécifique par son ID. Requiert la permission VIEW_CHEFS_D_OEUVRE."
)
async def get_chef_d_oeuvre(
    chef_d_oeuvre_id: int,
    db: AsyncSession = Depends(get_async_db),
    current_user: UtilisateurLight = Depends(require_permissions(["VIEW_CHEFS_D_OEUVRE"]))
):
    """
    Récupère un chef-d'œuvre spécifique.

    - **chef_d_oeuvre_id**: ID du chef-d'œuvre à récupérer.
    - **Réponses**:
        - **200**: Détails du chef-d'œuvre.
        - **404**: Chef-d'œuvre non trouvé.
        - **403**: Permission VIEW_CHEFS_D_OEUVRE manquante.
        - **500**: Erreur interne du serveur.
    """
    return await chef_d_oeuvre_service.get(db, chef_d_oeuvre_id)

@router.get(
    "/chefs-d-oeuvre",
    response_model=List[ChefDOeuvre],
    tags=["Chefs-d'œuvre"],
    summary="Lister tous les chefs-d'œuvre",
    description="Récupère une liste paginée de tous les chefs-d'œuvre avec leurs relations. Requiert la permission VIEW_CHEFS_D_OEUVRE."
)
async def list_chefs_d_oeuvre(
    skip: int = 0,
    limit: int = 100,
    db: AsyncSession = Depends(get_async_db),
    current_user: UtilisateurLight = Depends(require_permissions(["VIEW_CHEFS_D_OEUVRE"]))
):
    """
    Liste tous les chefs-d'œuvre avec pagination.

    - **skip**: Nombre de chefs-d'œuvre à sauter (défaut: 0).
    - **limit**: Nombre maximum de chefs-d'œuvre à retourner (défaut: 100).
    - **Réponses**:
        - **200**: Liste des chefs-d'œuvre.
        - **403**: Permission VIEW_CHEFS_D_OEUVRE manquante.
        - **500**: Erreur interne du serveur.
    """
    return await chef_d_oeuvre_service.get_all(db, skip, limit)

@router.put(
    "/chefs-d-oeuvre/{chef_d_oeuvre_id}",
    response_model=ChefDOeuvre,
    tags=["Chefs-d'œuvre"],
    summary="Mettre à jour un chef-d'œuvre",
    description="Met à jour un chef-d'œuvre spécifique. Requiert la permission EDIT_CHEFS_D_OEUVRE."
)
async def update_chef_d_oeuvre(
    chef_d_oeuvre_id: int,
    chef_d_oeuvre_update: ChefDOeuvreUpdate,
    db: AsyncSession = Depends(get_async_db),
    current_user: UtilisateurLight = Depends(require_permissions(["EDIT_CHEFS_D_OEUVRE"]))
):
    """
    Met à jour un chef-d'œuvre spécifique.

    - **chef_d_oeuvre_id**: ID du chef-d'œuvre à mettre à jour.
    - **chef_d_oeuvre_update**: Schéma de mise à jour du chef-d'œuvre.
    - **Réponses**:
        - **200**: Chef-d'œuvre mis à jour avec succès.
        - **404**: Chef-d'œuvre, utilisateur ou module non trouvé.
        - **403**: Permission EDIT_CHEFS_D_OEUVRE manquante.
        - **500**: Erreur interne du serveur.
    """
    return await chef_d_oeuvre_service.update(db, chef_d_oeuvre_id, chef_d_oeuvre_update)

@router.delete(
    "/chefs-d-oeuvre/{chef_d_oeuvre_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    tags=["Chefs-d'œuvre"],
    summary="Supprimer un chef-d'œuvre",
    description="Supprime un chef-d'œuvre spécifique par son ID. Requiert la permission DELETE_CHEFS_D_OEUVRE."
)
async def delete_chef_d_oeuvre(
    chef_d_oeuvre_id: int,
    db: AsyncSession = Depends(get_async_db),
    current_user: UtilisateurLight = Depends(require_permissions(["DELETE_CHEFS_D_OEUVRE"]))
):
    """
    Supprime un chef-d'œuvre spécifique.

    - **chef_d_oeuvre_id**: ID du chef-d'œuvre à supprimer.
    - **Réponses**:
        - **204**: Chef-d'œuvre supprimé avec succès.
        - **404**: Chef-d'œuvre non trouvé.
        - **403**: Permission DELETE_CHEFS_D_OEUVRE manquante.
        - **500**: Erreur interne du serveur.
    """
    await chef_d_oeuvre_service.delete(db, chef_d_oeuvre_id)

# ============================================================================
# ========================= ROUTES DES PROJETS COLLECTIFS ===================
# ============================================================================

@router.post(
    "/projets-collectifs",
    response_model=ProjetCollectifLight,
    tags=["Projets Collectifs"],
    summary="Créer un nouveau projet collectif",
    description="Crée un nouveau projet collectif avec ses membres. Requiert la permission CREATE_PROJET_COLLECTIF."
)
async def create_projet_collectif(
    projet_collectif: ProjetCollectifCreate,
    db: AsyncSession = Depends(get_async_db),
    current_user: UtilisateurLight = Depends(require_permissions(["CREATE_PROJET_COLLECTIF"]))
):
    """
    Crée un nouveau projet collectif.

    - **projet_collectif**: Schéma de création du projet collectif.
    - **Réponses**:
        - **200**: Projet collectif créé avec succès.
        - **404**: Formation ou membres non trouvés.
        - **403**: Permission CREATE_PROJET_COLLECTIF manquante.
        - **500**: Erreur interne du serveur.
    """
    return await projet_collectif_service.create(db, projet_collectif)

@router.get(
    "/projets-collectifs/{projet_collectif_id}",
    response_model=ProjetCollectif,
    tags=["Projets Collectifs"],
    summary="Récupérer un projet collectif par ID",
    description="Récupère les détails d'un projet collectif spécifique par son ID. Requiert la permission VIEW_PROJETS_COLLECTIFS."
)
async def get_projet_collectif(
    projet_collectif_id: int,
    db: AsyncSession = Depends(get_async_db),
    current_user: UtilisateurLight = Depends(require_permissions(["VIEW_PROJETS_COLLECTIFS"]))
):
    """
    Récupère un projet collectif spécifique.

    - **projet_collectif_id**: ID du projet collectif à récupérer.
    - **Réponses**:
        - **200**: Détails du projet collectif.
        - **404**: Projet collectif non trouvé.
        - **403**: Permission VIEW_PROJETS_COLLECTIFS manquante.
        - **500**: Erreur interne du serveur.
    """
    return await projet_collectif_service.get(db, projet_collectif_id)

@router.get(
    "/projets-collectifs",
    response_model=List[ProjetCollectif],
    tags=["Projets Collectifs"],
    summary="Lister tous les projets collectifs",
    description="Récupère une liste paginée de tous les projets collectifs avec leurs relations. Requiert la permission VIEW_PROJETS_COLLECTIFS."
)
async def list_projets_collectifs(
    skip: int = 0,
    limit: int = 100,
    db: AsyncSession = Depends(get_async_db),
    current_user: UtilisateurLight = Depends(require_permissions(["VIEW_PROJETS_COLLECTIFS"]))
):
    """
    Liste tous les projets collectifs avec pagination.

    - **skip**: Nombre de projets collectifs à sauter (défaut: 0).
    - **limit**: Nombre maximum de projets collectifs à retourner (défaut: 100).
    - **Réponses**:
        - **200**: Liste des projets collectifs.
        - **403**: Permission VIEW_PROJETS_COLLECTIFS manquante.
        - **500**: Erreur interne du serveur.
    """
    return await projet_collectif_service.get_all(db, skip, limit)

@router.put(
    "/projets-collectifs/{projet_collectif_id}",
    response_model=ProjetCollectif,
    tags=["Projets Collectifs"],
    summary="Mettre à jour un projet collectif",
    description="Met à jour un projet collectif spécifique avec ses membres. Requiert la permission EDIT_PROJETS_COLLECTIFS."
)
async def update_projet_collectif(
    projet_collectif_id: int,
    projet_collectif_update: ProjetCollectifUpdate,
    db: AsyncSession = Depends(get_async_db),
    current_user: UtilisateurLight = Depends(require_permissions(["EDIT_PROJETS_COLLECTIFS"]))
):
    """
    Met à jour un projet collectif spécifique.

    - **projet_collectif_id**: ID du projet collectif à mettre à jour.
    - **projet_collectif_update**: Schéma de mise à jour du projet collectif.
    - **Réponses**:
        - **200**: Projet collectif mis à jour avec succès.
        - **404**: Projet collectif, formation ou membres non trouvés.
        - **403**: Permission EDIT_PROJETS_COLLECTIFS manquante.
        - **500**: Erreur interne du serveur.
    """
    return await projet_collectif_service.update(db, projet_collectif_id, projet_collectif_update)

@router.delete(
    "/projets-collectifs/{projet_collectif_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    tags=["Projets Collectifs"],
    summary="Supprimer un projet collectif",
    description="Supprime un projet collectif spécifique par son ID. Requiert la permission DELETE_PROJETS_COLLECTIFS."
)
async def delete_projet_collectif(
    projet_collectif_id: int,
    db: AsyncSession = Depends(get_async_db),
    current_user: UtilisateurLight = Depends(require_permissions(["DELETE_PROJETS_COLLECTIFS"]))
):
    """
    Supprime un projet collectif spécifique.

    - **projet_collectif_id**: ID du projet collectif à supprimer.
    - **Réponses**:
        - **204**: Projet collectif supprimé avec succès.
        - **404**: Projet collectif non trouvé.
        - **403**: Permission DELETE_PROJETS_COLLECTIFS manquante.
        - **500**: Erreur interne du serveur.
    """
    await projet_collectif_service.delete(db, projet_collectif_id)

@router.post(
    "/projets-collectifs/{projet_collectif_id}/membres/{utilisateur_id}",
    response_model=ProjetCollectif,
    tags=["Projets Collectifs"],
    summary="Ajouter un membre à un projet collectif",
    description="Ajoute un utilisateur à un projet collectif. Requiert la permission ADD_MEMBRE_PROJET."
)
async def add_membre_projet(
    projet_collectif_id: int,
    utilisateur_id: int,
    db: AsyncSession = Depends(get_async_db),
    current_user: UtilisateurLight = Depends(require_permissions(["ADD_MEMBRE_PROJET"]))
):
    """
    Ajoute un membre à un projet collectif.

    - **projet_collectif_id**: ID du projet collectif.
    - **utilisateur_id**: ID de l'utilisateur à ajouter.
    - **Réponses**:
        - **200**: Membre ajouté avec succès.
        - **404**: Projet collectif ou utilisateur non trouvé.
        - **403**: Permission ADD_MEMBRE_PROJET manquante.
        - **500**: Erreur interne du serveur.
    """
    return await projet_collectif_service.add_membre(db, projet_collectif_id, utilisateur_id)

@router.delete(
    "/projets-collectifs/{projet_collectif_id}/membres/{utilisateur_id}",
    response_model=ProjetCollectif,
    tags=["Projets Collectifs"],
    summary="Supprimer un membre d'un projet collectif",
    description="Supprime un utilisateur d'un projet collectif. Requiert la permission REMOVE_MEMBRE_PROJET."
)
async def remove_membre_projet(
    projet_collectif_id: int,
    utilisateur_id: int,
    db: AsyncSession = Depends(get_async_db),
    current_user: UtilisateurLight = Depends(require_permissions(["REMOVE_MEMBRE_PROJET"]))
):
    """
    Supprime un membre d'un projet collectif.

    - **projet_collectif_id**: ID du projet collectif.
    - **utilisateur_id**: ID de l'utilisateur à supprimer.
    - **Réponses**:
        - **200**: Membre supprimé avec succès.
        - **404**: Projet collectif ou utilisateur non trouvé.
        - **403**: Permission REMOVE_MEMBRE_PROJET manquante.
        - **500**: Erreur interne du serveur.
    """
    return await projet_collectif_service.remove_membre(db, projet_collectif_id, utilisateur_id)

# ============================================================================
# ========================= ROUTES DES ÉVALUATIONS ==========================
# ============================================================================

@router.post(
    "/evaluations",
    response_model=EvaluationLight,
    tags=["Évaluations"],
    summary="Créer une nouvelle évaluation",
    description="Crée une nouvelle évaluation pour un module. Requiert la permission CREATE_EVALUATION."
)
async def create_evaluation(
    evaluation: EvaluationCreate,
    db: AsyncSession = Depends(get_async_db),
    current_user: UtilisateurLight = Depends(require_permissions(["CREATE_EVALUATION"]))
):
    """
    Crée une nouvelle évaluation.

    - **evaluation**: Schéma de création de l'évaluation.
    - **Réponses**:
        - **200**: Évaluation créée avec succès.
        - **404**: Module non trouvé.
        - **403**: Permission CREATE_EVALUATION manquante.
        - **500**: Erreur interne du serveur.
    """
    return await evaluation_service.create(db, evaluation)

@router.get(
    "/evaluations/{evaluation_id}",
    response_model=Evaluation,
    tags=["Évaluations"],
    summary="Récupérer une évaluation par ID",
    description="Récupère les détails d'une évaluation spécifique par son ID. Requiert la permission VIEW_EVALUATIONS."
)
async def get_evaluation(
    evaluation_id: int,
    db: AsyncSession = Depends(get_async_db),
    current_user: UtilisateurLight = Depends(require_permissions(["VIEW_EVALUATIONS"]))
):
    """
    Récupère une évaluation spécifique.

    - **evaluation_id**: ID de l'évaluation à récupérer.
    - **Réponses**:
        - **200**: Détails de l'évaluation.
        - **404**: Évaluation non trouvée.
        - **403**: Permission VIEW_EVALUATIONS manquante.
        - **500**: Erreur interne du serveur.
    """
    return await evaluation_service.get(db, evaluation_id)

@router.get(
    "/evaluations",
    response_model=List[Evaluation],
    tags=["Évaluations"],
    summary="Lister toutes les évaluations",
    description="Récupère une liste paginée de toutes les évaluations avec leurs relations. Requiert la permission VIEW_EVALUATIONS."
)
async def list_evaluations(
    skip: int = 0,
    limit: int = 100,
    db: AsyncSession = Depends(get_async_db),
    current_user: UtilisateurLight = Depends(require_permissions(["VIEW_EVALUATIONS"]))
):
    """
    Liste toutes les évaluations avec pagination.

    - **skip**: Nombre d'évaluations à sauter (défaut: 0).
    - **limit**: Nombre maximum d'évaluations à retourner (défaut: 100).
    - **Réponses**:
        - **200**: Liste des évaluations.
        - **403**: Permission VIEW_EVALUATIONS manquante.
        - **500**: Erreur interne du serveur.
    """
    return await evaluation_service.get_all(db, skip, limit)

@router.put(
    "/evaluations/{evaluation_id}",
    response_model=Evaluation,
    tags=["Évaluations"],
    summary="Mettre à jour une évaluation",
    description="Met à jour une évaluation spécifique. Requiert la permission EDIT_EVALUATIONS."
)
async def update_evaluation(
    evaluation_id: int,
    evaluation_update: EvaluationUpdate,
    db: AsyncSession = Depends(get_async_db),
    current_user: UtilisateurLight = Depends(require_permissions(["EDIT_EVALUATIONS"]))
):
    """
    Met à jour une évaluation spécifique.

    - **evaluation_id**: ID de l'évaluation à mettre à jour.
    - **evaluation_update**: Schéma de mise à jour de l'évaluation.
    - **Réponses**:
        - **200**: Évaluation mise à jour avec succès.
        - **404**: Évaluation ou module non trouvé.
        - **403**: Permission EDIT_EVALUATIONS manquante.
        - **500**: Erreur interne du serveur.
    """
    return await evaluation_service.update(db, evaluation_id, evaluation_update)

@router.delete(
    "/evaluations/{evaluation_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    tags=["Évaluations"],
    summary="Supprimer une évaluation",
    description="Supprime une évaluation spécifique par son ID. Requiert la permission DELETE_EVALUATIONS."
)
async def delete_evaluation(
    evaluation_id: int,
    db: AsyncSession = Depends(get_async_db),
    current_user: UtilisateurLight = Depends(require_permissions(["DELETE_EVALUATIONS"]))
):
    """
    Supprime une évaluation spécifique.

    - **evaluation_id**: ID de l'évaluation à supprimer.
    - **Réponses**:
        - **204**: Évaluation supprimée avec succès.
        - **404**: Évaluation non trouvée.
        - **403**: Permission DELETE_EVALUATIONS manquante.
        - **500**: Erreur interne du serveur.
    """
    await evaluation_service.delete(db, evaluation_id)

# ============================================================================
# ========================= ROUTES DES QUESTIONS ============================
# ============================================================================

@router.post(
    "/questions",
    response_model=QuestionLight,
    tags=["Questions"],
    summary="Créer une nouvelle question",
    description="Crée une nouvelle question pour une évaluation avec ses propositions. Requiert la permission CREATE_QUESTION."
)
async def create_question(
    question: QuestionCreate,
    db: AsyncSession = Depends(get_async_db),
    current_user: UtilisateurLight = Depends(require_permissions(["CREATE_QUESTION"]))
):
    """
    Crée une nouvelle question.

    - **question**: Schéma de création de la question.
    - **Réponses**:
        - **200**: Question créée avec succès.
        - **404**: Évaluation non trouvée.
        - **403**: Permission CREATE_QUESTION manquante.
        - **500**: Erreur interne du serveur.
    """
    return await question_service.create(db, question)

@router.get(
    "/questions/{question_id}",
    response_model=Question,
    tags=["Questions"],
    summary="Récupérer une question par ID",
    description="Récupère les détails d'une question spécifique par son ID. Requiert la permission VIEW_QUESTIONS."
)
async def get_question(
    question_id: int,
    db: AsyncSession = Depends(get_async_db),
    current_user: UtilisateurLight = Depends(require_permissions(["VIEW_QUESTIONS"]))
):
    """
    Récupère une question spécifique.

    - **question_id**: ID de la question à récupérer.
    - **Réponses**:
        - **200**: Détails de la question.
        - **404**: Question non trouvée.
        - **403**: Permission VIEW_QUESTIONS manquante.
        - **500**: Erreur interne du serveur.
    """
    return await question_service.get(db, question_id)

@router.get(
    "/questions",
    response_model=List[Question],
    tags=["Questions"],
    summary="Lister toutes les questions",
    description="Récupère une liste paginée de toutes les questions avec leurs relations. Requiert la permission VIEW_QUESTIONS."
)
async def list_questions(
    skip: int = 0,
    limit: int = 100,
    db: AsyncSession = Depends(get_async_db),
    current_user: UtilisateurLight = Depends(require_permissions(["VIEW_QUESTIONS"]))
):
    """
    Liste toutes les questions avec pagination.

    - **skip**: Nombre de questions à sauter (défaut: 0).
    - **limit**: Nombre maximum de questions à retourner (défaut: 100).
    - **Réponses**:
        - **200**: Liste des questions.
        - **403**: Permission VIEW_QUESTIONS manquante.
        - **500**: Erreur interne du serveur.
    """
    return await question_service.get_all(db, skip, limit)

@router.put(
    "/questions/{question_id}",
    response_model=Question,
    tags=["Questions"],
    summary="Mettre à jour une question",
    description="Met à jour une question spécifique avec ses propositions. Requiert la permission EDIT_QUESTIONS."
)
async def update_question(
    question_id: int,
    question_update: QuestionUpdate,
    db: AsyncSession = Depends(get_async_db),
    current_user: UtilisateurLight = Depends(require_permissions(["EDIT_QUESTIONS"]))
):
    """
    Met à jour une question spécifique.

    - **question_id**: ID de la question à mettre à jour.
    - **question_update**: Schéma de mise à jour de la question.
    - **Réponses**:
        - **200**: Question mise à jour avec succès.
        - **404**: Question ou évaluation non trouvée.
        - **403**: Permission EDIT_QUESTIONS manquante.
        - **500**: Erreur interne du serveur.
    """
    return await question_service.update(db, question_id, question_update)

@router.delete(
    "/questions/{question_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    tags=["Questions"],
    summary="Supprimer une question",
    description="Supprime une question spécifique par son ID. Requiert la permission DELETE_QUESTIONS."
)
async def delete_question(
    question_id: int,
    db: AsyncSession = Depends(get_async_db),
    current_user: UtilisateurLight = Depends(require_permissions(["DELETE_QUESTIONS"]))
):
    """
    Supprime une question spécifique.

    - **question_id**: ID de la question à supprimer.
    - **Réponses**:
        - **204**: Question supprimée avec succès.
        - **404**: Question non trouvée.
        - **403**: Permission DELETE_QUESTIONS manquante.
        - **500**: Erreur interne du serveur.
    """
    await question_service.delete(db, question_id)
    
    # ============================================================================
# ========================= ROUTES DES PROPOSITIONS ==========================
# ============================================================================

@router.post(
    "/propositions",
    response_model=PropositionLight,
    tags=["Propositions"],
    summary="Créer une nouvelle proposition",
    description="Crée une nouvelle proposition pour une question. Requiert la permission CREATE_PROPOSITION."
)
async def create_proposition(
    proposition: PropositionCreate,
    db: AsyncSession = Depends(get_async_db),
    current_user: UtilisateurLight = Depends(require_permissions(["CREATE_PROPOSITION"]))
):
    """
    Crée une nouvelle proposition.

    - **proposition**: Schéma de création de la proposition.
    - **Réponses**:
        - **200**: Proposition créée avec succès.
        - **404**: Question non trouvée.
        - **403**: Permission CREATE_PROPOSITION manquante.
        - **500**: Erreur interne du serveur.
    """
    return await proposition_service.create(db, proposition)

@router.get(
    "/propositions/{proposition_id}",
    response_model=Proposition,
    tags=["Propositions"],
    summary="Récupérer une proposition par ID",
    description="Récupère les détails d'une proposition spécifique par son ID. Requiert la permission VIEW_PROPOSITIONS."
)
async def get_proposition(
    proposition_id: int,
    db: AsyncSession = Depends(get_async_db),
    current_user: UtilisateurLight = Depends(require_permissions(["VIEW_PROPOSITIONS"]))
):
    """
    Récupère une proposition spécifique.

    - **proposition_id**: ID de la proposition à récupérer.
    - **Réponses**:
        - **200**: Détails de la proposition.
        - **404**: Proposition non trouvée.
        - **403**: Permission VIEW_PROPOSITIONS manquante.
        - **500**: Erreur interne du serveur.
    """
    return await proposition_service.get(db, proposition_id)

@router.get(
    "/propositions",
    response_model=List[Proposition],
    tags=["Propositions"],
    summary="Lister toutes les propositions",
    description="Récupère une liste paginée de toutes les propositions avec leurs relations. Requiert la permission VIEW_PROPOSITIONS."
)
async def list_propositions(
    skip: int = 0,
    limit: int = 100,
    db: AsyncSession = Depends(get_async_db),
    current_user: UtilisateurLight = Depends(require_permissions(["VIEW_PROPOSITIONS"]))
):
    """
    Liste toutes les propositions avec pagination.

    - **skip**: Nombre de propositions à sauter (défaut: 0).
    - **limit**: Nombre maximum de propositions à retourner (défaut: 100).
    - **Réponses**:
        - **200**: Liste des propositions.
        - **403**: Permission VIEW_PROPOSITIONS manquante.
        - **500**: Erreur interne du serveur.
    """
    return await proposition_service.get_all(db, skip, limit)

@router.put(
    "/propositions/{proposition_id}",
    response_model=Proposition,
    tags=["Propositions"],
    summary="Mettre à jour une proposition",
    description="Met à jour une proposition spécifique. Requiert la permission EDIT_PROPOSITIONS."
)
async def update_proposition(
    proposition_id: int,
    proposition_update: PropositionUpdate,
    db: AsyncSession = Depends(get_async_db),
    current_user: UtilisateurLight = Depends(require_permissions(["EDIT_PROPOSITIONS"]))
):
    """
    Met à jour une proposition spécifique.

    - **proposition_id**: ID de la proposition à mettre à jour.
    - **proposition_update**: Schéma de mise à jour de la proposition.
    - **Réponses**:
        - **200**: Proposition mise à jour avec succès.
        - **404**: Proposition ou question non trouvée.
        - **403**: Permission EDIT_PROPOSITIONS manquante.
        - **500**: Erreur interne du serveur.
    """
    return await proposition_service.update(db, proposition_id, proposition_update)

@router.delete(
    "/propositions/{proposition_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    tags=["Propositions"],
    summary="Supprimer une proposition",
    description="Supprime une proposition spécifique par son ID. Requiert la permission DELETE_PROPOSITIONS."
)
async def delete_proposition(
    proposition_id: int,
    db: AsyncSession = Depends(get_async_db),
    current_user: UtilisateurLight = Depends(require_permissions(["DELETE_PROPOSITIONS"]))
):
    """
    Supprime une proposition spécifique.

    - **proposition_id**: ID de la proposition à supprimer.
    - **Réponses**:
        - **204**: Proposition supprimée avec succès.
        - **404**: Proposition non trouvée.
        - **403**: Permission DELETE_PROPOSITIONS manquante.
        - **500**: Erreur interne du serveur.
    """
    await proposition_service.delete(db, proposition_id)
    
    
    # ============================================================================
# ========================= ROUTES DES RÉSULTATS D'ÉVALUATION ===============
# ============================================================================

@router.post(
    "/resultats-evaluations",
    response_model=ResultatEvaluationLight,
    tags=["Résultats Évaluations"],
    summary="Créer un nouveau résultat d'évaluation",
    description="Crée un nouveau résultat d'évaluation pour un utilisateur et une évaluation. Requiert la permission CREATE_RESULTAT_EVALUATION."
)
async def create_resultat_evaluation(
    resultat_evaluation: ResultatEvaluationCreate,
    db: AsyncSession = Depends(get_async_db),
    current_user: UtilisateurLight = Depends(require_permissions(["CREATE_RESULTAT_EVALUATION"]))
):
    """
    Crée un nouveau résultat d'évaluation.

    - **resultat_evaluation**: Schéma de création du résultat d'évaluation.
    - **Réponses**:
        - **200**: Résultat d'évaluation créé avec succès.
        - **404**: Évaluation ou utilisateur non trouvé.
        - **403**: Permission CREATE_RESULTAT_EVALUATION manquante.
        - **500**: Erreur interne du serveur.
    """
    return await resultat_evaluation_service.create(db, resultat_evaluation)

@router.get(
    "/resultats-evaluations/{resultat_evaluation_id}",
    response_model=ResultatEvaluation,
    tags=["Résultats Évaluations"],
    summary="Récupérer un résultat d'évaluation par ID",
    description="Récupère les détails d'un résultat d'évaluation spécifique par son ID. Requiert la permission VIEW_RESULTATS_EVALUATIONS."
)
async def get_resultat_evaluation(
    resultat_evaluation_id: int,
    db: AsyncSession = Depends(get_async_db),
    current_user: UtilisateurLight = Depends(require_permissions(["VIEW_RESULTATS_EVALUATIONS"]))
):
    """
    Récupère un résultat d'évaluation spécifique.

    - **resultat_evaluation_id**: ID du résultat d'évaluation à récupérer.
    - **Réponses**:
        - **200**: Détails du résultat d'évaluation.
        - **404**: Résultat d'évaluation non trouvé.
        - **403**: Permission VIEW_RESULTATS_EVALUATIONS manquante.
        - **500**: Erreur interne du serveur.
    """
    return await resultat_evaluation_service.get(db, resultat_evaluation_id)

@router.get(
    "/resultats-evaluations",
    response_model=List[ResultatEvaluation],
    tags=["Résultats Évaluations"],
    summary="Lister tous les résultats d'évaluation",
    description="Récupère une liste paginée de tous les résultats d'évaluation avec leurs relations. Requiert la permission VIEW_RESULTATS_EVALUATIONS."
)
async def list_resultats_evaluations(
    skip: int = 0,
    limit: int = 100,
    db: AsyncSession = Depends(get_async_db),
    current_user: UtilisateurLight = Depends(require_permissions(["VIEW_RESULTATS_EVALUATIONS"]))
):
    """
    Liste tous les résultats d'évaluation avec pagination.

    - **skip**: Nombre de résultats à sauter (défaut: 0).
    - **limit**: Nombre maximum de résultats à retourner (défaut: 100).
    - **Réponses**:
        - **200**: Liste des résultats d'évaluation.
        - **403**: Permission VIEW_RESULTATS_EVALUATIONS manquante.
        - **500**: Erreur interne du serveur.
    """
    return await resultat_evaluation_service.get_all(db, skip, limit)

@router.put(
    "/resultats-evaluations/{resultat_evaluation_id}",
    response_model=ResultatEvaluation,
    tags=["Résultats Évaluations"],
    summary="Mettre à jour un résultat d'évaluation",
    description="Met à jour un résultat d'évaluation spécifique. Requiert la permission EDIT_RESULTATS_EVALUATIONS."
)
async def update_resultat_evaluation(
    resultat_evaluation_id: int,
    resultat_evaluation_update: ResultatEvaluationUpdate,
    db: AsyncSession = Depends(get_async_db),
    current_user: UtilisateurLight = Depends(require_permissions(["EDIT_RESULTATS_EVALUATIONS"]))
):
    """
    Met à jour un résultat d'évaluation spécifique.

    - **resultat_evaluation_id**: ID du résultat d'évaluation à mettre à jour.
    - **resultat_evaluation_update**: Schéma de mise à jour du résultat d'évaluation.
    - **Réponses**:
        - **200**: Résultat d'évaluation mis à jour avec succès.
        - **404**: Résultat d'évaluation, évaluation ou utilisateur non trouvé.
        - **403**: Permission EDIT_RESULTATS_EVALUATIONS manquante.
        - **500**: Erreur interne du serveur.
    """
    return await resultat_evaluation_service.update(db, resultat_evaluation_id, resultat_evaluation_update)

@router.delete(
    "/resultats-evaluations/{resultat_evaluation_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    tags=["Résultats Évaluations"],
    summary="Supprimer un résultat d'évaluation",
    description="Supprime un résultat d'évaluation spécifique par son ID. Requiert la permission DELETE_RESULTATS_EVALUATIONS."
)
async def delete_resultat_evaluation(
    resultat_evaluation_id: int,
    db: AsyncSession = Depends(get_async_db),
    current_user: UtilisateurLight = Depends(require_permissions(["DELETE_RESULTATS_EVALUATIONS"]))
):
    """
    Supprime un résultat d'évaluation spécifique.

    - **resultat_evaluation_id**: ID du résultat d'évaluation à supprimer.
    - **Réponses**:
        - **204**: Résultat d'évaluation supprimé avec succès.
        - **404**: Résultat d'évaluation non trouvé.
        - **403**: Permission DELETE_RESULTATS_EVALUATIONS manquante.
        - **500**: Erreur interne du serveur.
    """
    await resultat_evaluation_service.delete(db, resultat_evaluation_id)
    
    
    # ============================================================================
# ========================= ROUTES DES GÉNOTYPES INDIVIDUELS ================
# ============================================================================

@router.post(
    "/genotypes-individuels",
    response_model=GenotypeIndividuelLight,
    tags=["Génotypes Individuels"],
    summary="Créer un nouveau génotype individuel",
    description="Crée un nouveau génotype individuel pour un utilisateur. Requiert la permission CREATE_GENOTYPE_INDIVIDUEL."
)
async def create_genotype_individuel(
    genotype_individuel: GenotypeIndividuelCreate,
    db: AsyncSession = Depends(get_async_db),
    current_user: UtilisateurLight = Depends(require_permissions(["CREATE_GENOTYPE_INDIVIDUEL"]))
):
    """
    Crée un nouveau génotype individuel.

    - **genotype_individuel**: Schéma de création du génotype individuel.
    - **Réponses**:
        - **200**: Génotype individuel créé avec succès.
        - **404**: Utilisateur non trouvé.
        - **403**: Permission CREATE_GENOTYPE_INDIVIDUEL manquante.
        - **500**: Erreur interne du serveur.
    """
    return await genotype_individuel_service.create(db, genotype_individuel)

@router.get(
    "/genotypes-individuels/{genotype_individuel_id}",
    response_model=GenotypeIndividuel,
    tags=["Génotypes Individuels"],
    summary="Récupérer un génotype individuel par ID",
    description="Récupère les détails d'un génotype individuel spécifique par son ID. Requiert la permission VIEW_GENOTYPES_INDIVIDUELS."
)
async def get_genotype_individuel(
    genotype_individuel_id: int,
    db: AsyncSession = Depends(get_async_db),
    current_user: UtilisateurLight = Depends(require_permissions(["VIEW_GENOTYPES_INDIVIDUELS"]))
):
    """
    Récupère un génotype individuel spécifique.

    - **genotype_individuel_id**: ID du génotype individuel à récupérer.
    - **Réponses**:
        - **200**: Détails du génotype individuel.
        - **404**: Génotype individuel non trouvé.
        - **403**: Permission VIEW_GENOTYPES_INDIVIDUELS manquante.
        - **500**: Erreur interne du serveur.
    """
    return await genotype_individuel_service.get(db, genotype_individuel_id)

@router.get(
    "/genotypes-individuels",
    response_model=List[GenotypeIndividuel],
    tags=["Génotypes Individuels"],
    summary="Lister tous les génotypes individuels",
    description="Récupère une liste paginée de tous les génotypes individuels avec leurs relations. Requiert la permission VIEW_GENOTYPES_INDIVIDUELS."
)
async def list_genotypes_individuels(
    skip: int = 0,
    limit: int = 100,
    db: AsyncSession = Depends(get_async_db),
    current_user: UtilisateurLight = Depends(require_permissions(["VIEW_GENOTYPES_INDIVIDUELS"]))
):
    """
    Liste tous les génotypes individuels avec pagination.

    - **skip**: Nombre de génotypes individuels à sauter (défaut: 0).
    - **limit**: Nombre maximum de génotypes individuels à retourner (défaut: 100).
    - **Réponses**:
        - **200**: Liste des génotypes individuels.
        - **403**: Permission VIEW_GENOTYPES_INDIVIDUELS manquante.
        - **500**: Erreur interne du serveur.
    """
    return await genotype_individuel_service.get_all(db, skip, limit)

@router.put(
    "/genotypes-individuels/{genotype_individuel_id}",
    response_model=GenotypeIndividuel,
    tags=["Génotypes Individuels"],
    summary="Mettre à jour un génotype individuel",
    description="Met à jour un génotype individuel spécifique. Requiert la permission EDIT_GENOTYPES_INDIVIDUELS."
)
async def update_genotype_individuel(
    genotype_individuel_id: int,
    genotype_individuel_update: GenotypeIndividuelUpdate,
    db: AsyncSession = Depends(get_async_db),
    current_user: UtilisateurLight = Depends(require_permissions(["EDIT_GENOTYPES_INDIVIDUELS"]))
):
    """
    Met à jour un génotype individuel spécifique.

    - **genotype_individuel_id**: ID du génotype individuel à mettre à jour.
    - **genotype_individuel_update**: Schéma de mise à jour du génotype individuel.
    - **Réponses**:
        - **200**: Génotype individuel mis à jour avec succès.
        - **404**: Génotype individuel ou utilisateur non trouvé.
        - **403**: Permission EDIT_GENOTYPES_INDIVIDUELS manquante.
        - **500**: Erreur interne du serveur.
    """
    return await genotype_individuel_service.update(db, genotype_individuel_id, genotype_individuel_update)

@router.delete(
    "/genotypes-individuels/{genotype_individuel_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    tags=["Génotypes Individuels"],
    summary="Supprimer un génotype individuel",
    description="Supprime un génotype individuel spécifique par son ID. Requiert la permission DELETE_GENOTYPES_INDIVIDUELS."
)
async def delete_genotype_individuel(
    genotype_individuel_id: int,
    db: AsyncSession = Depends(get_async_db),
    current_user: UtilisateurLight = Depends(require_permissions(["DELETE_GENOTYPES_INDIVIDUELS"]))
):
    """
    Supprime un génotype individuel spécifique.

    - **genotype_individuel_id**: ID du génotype individuel à supprimer.
    - **Réponses**:
        - **204**: Génotype individuel supprimé avec succès.
        - **404**: Génotype individuel non trouvé.
        - **403**: Permission DELETE_GENOTYPES_INDIVIDUELS manquante.
        - **500**: Erreur interne du serveur.
    """
    await genotype_individuel_service.delete(db, genotype_individuel_id)
    
    
    # ============================================================================
# ========================= ROUTES DES ASCENDANCES GÉNOTYPES ===============
# ============================================================================

@router.post(
    "/ascendances-genotypes",
    response_model=AscendanceGenotypeLight,
    tags=["Ascendances Génotypes"],
    summary="Créer une nouvelle ascendance génotype",
    description="Crée une nouvelle ascendance génotype pour un génotype individuel. Requiert la permission CREATE_ASCENDANCE_GENOTYPE."
)
async def create_ascendance_genotype(
    ascendance_genotype: AscendanceGenotypeCreate,
    db: AsyncSession = Depends(get_async_db),
    current_user: UtilisateurLight = Depends(require_permissions(["CREATE_ASCENDANCE_GENOTYPE"]))
):
    """
    Crée une nouvelle ascendance génotype.

    - **ascendance_genotype**: Schéma de création de l'ascendance génotype.
    - **Réponses**:
        - **200**: Ascendance génotype créée avec succès.
        - **404**: Génotype individuel non trouvé.
        - **403**: Permission CREATE_ASCENDANCE_GENOTYPE manquante.
        - **500**: Erreur interne du serveur.
    """
    return await ascendance_genotype_service.create(db, ascendance_genotype)

@router.get(
    "/ascendances-genotypes/{ascendance_genotype_id}",
    response_model=AscendanceGenotype,
    tags=["Ascendances Génotypes"],
    summary="Récupérer une ascendance génotype par ID",
    description="Récupère les détails d'une ascendance génotype spécifique par son ID. Requiert la permission VIEW_ASCENDANCES_GENOTYPES."
)
async def get_ascendance_genotype(
    ascendance_genotype_id: int,
    db: AsyncSession = Depends(get_async_db),
    current_user: UtilisateurLight = Depends(require_permissions(["VIEW_ASCENDANCES_GENOTYPES"]))
):
    """
    Récupère une ascendance génotype spécifique.

    - **ascendance_genotype_id**: ID de l'ascendance génotype à récupérer.
    - **Réponses**:
        - **200**: Détails de l'ascendance génotype.
        - **404**: Ascendance génotype non trouvée.
        - **403**: Permission VIEW_ASCENDANCES_GENOTYPES manquante.
        - **500**: Erreur interne du serveur.
    """
    return await ascendance_genotype_service.get(db, ascendance_genotype_id)

@router.get(
    "/ascendances-genotypes",
    response_model=List[AscendanceGenotype],
    tags=["Ascendances Génotypes"],
    summary="Lister toutes les ascendances génotypes",
    description="Récupère une liste paginée de toutes les ascendances génotypes avec leurs relations. Requiert la permission VIEW_ASCENDANCES_GENOTYPES."
)
async def list_ascendances_genotypes(
    skip: int = 0,
    limit: int = 100,
    db: AsyncSession = Depends(get_async_db),
    current_user: UtilisateurLight = Depends(require_permissions(["VIEW_ASCENDANCES_GENOTYPES"]))
):
    """
    Liste toutes les ascendances génotypes avec pagination.

    - **skip**: Nombre d'ascendances génotypes à sauter (défaut: 0).
    - **limit**: Nombre maximum d'ascendances génotypes à retourner (défaut: 100).
    - **Réponses**:
        - **200**: Liste des ascendances génotypes.
        - **403**: Permission VIEW_ASCENDANCES_GENOTYPES manquante.
        - **500**: Erreur interne du serveur.
    """
    return await ascendance_genotype_service.get_all(db, skip, limit)

@router.put(
    "/ascendances-genotypes/{ascendance_genotype_id}",
    response_model=AscendanceGenotype,
    tags=["Ascendances Génotypes"],
    summary="Mettre à jour une ascendance génotype",
    description="Met à jour une ascendance génotype spécifique. Requiert la permission EDIT_ASCENDANCES_GENOTYPES."
)
async def update_ascendance_genotype(
    ascendance_genotype_id: int,
    ascendance_genotype_update: AscendanceGenotypeUpdate,
    db: AsyncSession = Depends(get_async_db),
    current_user: UtilisateurLight = Depends(require_permissions(["EDIT_ASCENDANCES_GENOTYPES"]))
):
    """
    Met à jour une ascendance génotype spécifique.

    - **ascendance_genotype_id**: ID de l'ascendance génotype à mettre à jour.
    - **ascendance_genotype_update**: Schéma de mise à jour de l'ascendance génotype.
    - **Réponses**:
        - **200**: Ascendance génotype mise à jour avec succès.
        - **404**: Ascendance génotype ou génotype individuel non trouvé.
        - **403**: Permission EDIT_ASCENDANCES_GENOTYPES manquante.
        - **500**: Erreur interne du serveur.
    """
    return await ascendance_genotype_service.update(db, ascendance_genotype_id, ascendance_genotype_update)

@router.delete(
    "/ascendances-genotypes/{ascendance_genotype_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    tags=["Ascendances Génotypes"],
    summary="Supprimer une ascendance génotype",
    description="Supprime une ascendance génotype spécifique par son ID. Requiert la permission DELETE_ASCENDANCES_GENOTYPES."
)
async def delete_ascendance_genotype(
    ascendance_genotype_id: int,
    db: AsyncSession = Depends(get_async_db),
    current_user: UtilisateurLight = Depends(require_permissions(["DELETE_ASCENDANCES_GENOTYPES"]))
):
    """
    Supprime une ascendance génotype spécifique.

    - **ascendance_genotype_id**: ID de l'ascendance génotype à supprimer.
    - **Réponses**:
        - **204**: Ascendance génotype supprimée avec succès.
        - **404**: Ascendance génotype non trouvée.
        - **403**: Permission DELETE_ASCENDANCES_GENOTYPES manquante.
        - **500**: Erreur interne du serveur.
    """
    await ascendance_genotype_service.delete(db, ascendance_genotype_id)
    
    
    
    # ============================================================================
# ========================= ROUTES DES SANTÉ GÉNOTYPES ======================
# ============================================================================

@router.post(
    "/sante-genotypes",
    response_model=SanteGenotypeLight,
    tags=["Santé Génotypes"],
    summary="Créer une nouvelle santé génotype",
    description="Crée une nouvelle santé génotype pour un génotype individuel. Requiert la permission CREATE_SANTE_GENOTYPE."
)
async def create_sante_genotype(
    sante_genotype: SanteGenotypeCreate,
    db: AsyncSession = Depends(get_async_db),
    current_user: UtilisateurLight = Depends(require_permissions(["CREATE_SANTE_GENOTYPE"]))
):
    """
    Crée une nouvelle santé génotype.

    - **sante_genotype**: Schéma de création de la santé génotype.
    - **Réponses**:
        - **200**: Santé génotype créée avec succès.
        - **404**: Génotype individuel non trouvé.
        - **403**: Permission CREATE_SANTE_GENOTYPE manquante.
        - **500**: Erreur interne du serveur.
    """
    return await sante_genotype_service.create(db, sante_genotype)

@router.get(
    "/sante-genotypes/{sante_genotype_id}",
    response_model=SanteGenotype,
    tags=["Santé Génotypes"],
    summary="Récupérer une santé génotype par ID",
    description="Récupère les détails d'une santé génotype spécifique par son ID. Requiert la permission VIEW_SANTE_GENOTYPES."
)
async def get_sante_genotype(
    sante_genotype_id: int,
    db: AsyncSession = Depends(get_async_db),
    current_user: UtilisateurLight = Depends(require_permissions(["VIEW_SANTE_GENOTYPES"]))
):
    """
    Récupère une santé génotype spécifique.

    - **sante_genotype_id**: ID de la santé génotype à récupérer.
    - **Réponses**:
        - **200**: Détails de la santé génotype.
        - **404**: Santé génotype non trouvée.
        - **403**: Permission VIEW_SANTE_GENOTYPES manquante.
        - **500**: Erreur interne du serveur.
    """
    return await sante_genotype_service.get(db, sante_genotype_id)

@router.get(
    "/sante-genotypes",
    response_model=List[SanteGenotype],
    tags=["Santé Génotypes"],
    summary="Lister toutes les santés génotypes",
    description="Récupère une liste paginée de toutes les santés génotypes avec leurs relations. Requiert la permission VIEW_SANTE_GENOTYPES."
)
async def list_sante_genotypes(
    skip: int = 0,
    limit: int = 100,
    db: AsyncSession = Depends(get_async_db),
    current_user: UtilisateurLight = Depends(require_permissions(["VIEW_SANTE_GENOTYPES"]))
):
    """
    Liste toutes les santés génotypes avec pagination.

    - **skip**: Nombre de santés génotypes à sauter (défaut: 0).
    - **limit**: Nombre maximum de santés génotypes à retourner (défaut: 100).
    - **Réponses**:
        - **200**: Liste des santés génotypes.
        - **403**: Permission VIEW_SANTE_GENOTYPES manquante.
        - **500**: Erreur interne du serveur.
    """
    return await sante_genotype_service.get_all(db, skip, limit)

@router.put(
    "/sante-genotypes/{sante_genotype_id}",
    response_model=SanteGenotype,
    tags=["Santé Génotypes"],
    summary="Mettre à jour une santé génotype",
    description="Met à jour une santé génotype spécifique. Requiert la permission EDIT_SANTE_GENOTYPES."
)
async def update_sante_genotype(
    sante_genotype_id: int,
    sante_genotype_update: SanteGenotypeUpdate,
    db: AsyncSession = Depends(get_async_db),
    current_user: UtilisateurLight = Depends(require_permissions(["EDIT_SANTE_GENOTYPES"]))
):
    """
    Met à jour une santé génotype spécifique.

    - **sante_genotype_id**: ID de la santé génotype à mettre à jour.
    - **sante_genotype_update**: Schéma de mise à jour de la santé génotype.
    - **Réponses**:
        - **200**: Santé génotype mise à jour avec succès.
        - **404**: Santé génotype ou génotype individuel non trouvé.
        - **403**: Permission EDIT_SANTE_GENOTYPES manquante.
        - **500**: Erreur interne du serveur.
    """
    return await sante_genotype_service.update(db, sante_genotype_id, sante_genotype_update)

@router.delete(
    "/sante-genotypes/{sante_genotype_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    tags=["Santé Génotypes"],
    summary="Supprimer une santé génotype",
    description="Supprime une santé génotype spécifique par son ID. Requiert la permission DELETE_SANTE_GENOTYPES."
)
async def delete_sante_genotype(
    sante_genotype_id: int,
    db: AsyncSession = Depends(get_async_db),
    current_user: UtilisateurLight = Depends(require_permissions(["DELETE_SANTE_GENOTYPES"]))
):
    """
    Supprime une santé génotype spécifique.

    - **sante_genotype_id**: ID de la santé génotype à supprimer.
    - **Réponses**:
        - **204**: Santé génotype supprimée avec succès.
        - **404**: Santé génotype non trouvée.
        - **403**: Permission DELETE_SANTE_GENOTYPES manquante.
        - **500**: Erreur interne du serveur.
    """
    await sante_genotype_service.delete(db, sante_genotype_id)
    
    
    # ============================================================================
# ========================= ROUTES DES ÉDUCATION GÉNOTYPES ==================
# ============================================================================

@router.post(
    "/education-genotypes",
    response_model=EducationGenotypeLight,
    tags=["Éducation Génotypes"],
    summary="Créer une nouvelle éducation génotype",
    description="Crée une nouvelle éducation génotype pour un génotype individuel. Requiert la permission CREATE_EDUCATION_GENOTYPE."
)
async def create_education_genotype(
    education_genotype: EducationGenotypeCreate,
    db: AsyncSession = Depends(get_async_db),
    current_user: UtilisateurLight = Depends(require_permissions(["CREATE_EDUCATION_GENOTYPE"]))
):
    """
    Crée une nouvelle éducation génotype.

    - **education_genotype**: Schéma de création de l'éducation génotype.
    - **Réponses**:
        - **200**: Éducation génotype créée avec succès.
        - **404**: Génotype individuel non trouvé.
        - **403**: Permission CREATE_EDUCATION_GENOTYPE manquante.
        - **500**: Erreur interne du serveur.
    """
    return await education_genotype_service.create(db, education_genotype)

@router.get(
    "/education-genotypes/{education_genotype_id}",
    response_model=EducationGenotype,
    tags=["Éducation Génotypes"],
    summary="Récupérer une éducation génotype par ID",
    description="Récupère les détails d'une éducation génotype spécifique par son ID. Requiert la permission VIEW_EDUCATION_GENOTYPES."
)
async def get_education_genotype(
    education_genotype_id: int,
    db: AsyncSession = Depends(get_async_db),
    current_user: UtilisateurLight = Depends(require_permissions(["VIEW_EDUCATION_GENOTYPES"]))
):
    """
    Récupère une éducation génotype spécifique.

    - **education_genotype_id**: ID de l'éducation génotype à récupérer.
    - **Réponses**:
        - **200**: Détails de l'éducation génotype.
        - **404**: Éducation génotype non trouvée.
        - **403**: Permission VIEW_EDUCATION_GENOTYPES manquante.
        - **500**: Erreur interne du serveur.
    """
    return await education_genotype_service.get(db, education_genotype_id)

@router.get(
    "/education-genotypes",
    response_model=List[EducationGenotype],
    tags=["Éducation Génotypes"],
    summary="Lister toutes les éducations génotypes",
    description="Récupère une liste paginée de toutes les éducations génotypes avec leurs relations. Requiert la permission VIEW_EDUCATION_GENOTYPES."
)
async def list_education_genotypes(
    skip: int = 0,
    limit: int = 100,
    db: AsyncSession = Depends(get_async_db),
    current_user: UtilisateurLight = Depends(require_permissions(["VIEW_EDUCATION_GENOTYPES"]))
):
    """
    Liste toutes les éducations génotypes avec pagination.

    - **skip**: Nombre d'éducations génotypes à sauter (défaut: 0).
    - **limit**: Nombre maximum d'éducations génotypes à retourner (défaut: 100).
    - **Réponses**:
        - **200**: Liste des éducations génotypes.
        - **403**: Permission VIEW_EDUCATION_GENOTYPES manquante.
        - **500**: Erreur interne du serveur.
    """
    return await education_genotype_service.get_all(db, skip, limit)

@router.put(
    "/education-genotypes/{education_genotype_id}",
    response_model=EducationGenotype,
    tags=["Éducation Génotypes"],
    summary="Mettre à jour une éducation génotype",
    description="Met à jour une éducation génotype spécifique. Requiert la permission EDIT_EDUCATION_GENOTYPES."
)
async def update_education_genotype(
    education_genotype_id: int,
    education_genotype_update: EducationGenotypeUpdate,
    db: AsyncSession = Depends(get_async_db),
    current_user: UtilisateurLight = Depends(require_permissions(["EDIT_EDUCATION_GENOTYPES"]))
):
    """
    Met à jour une éducation génotype spécifique.

    - **education_genotype_id**: ID de l'éducation génotype à mettre à jour.
    - **education_genotype_update**: Schéma de mise à jour de l'éducation génotype.
    - **Réponses**:
        - **200**: Éducation génotype mise à jour avec succès.
        - **404**: Éducation génotype ou génotype individuel non trouvé.
        - **403**: Permission EDIT_EDUCATION_GENOTYPES manquante.
        - **500**: Erreur interne du serveur.
    """
    return await education_genotype_service.update(db, education_genotype_id, education_genotype_update)

@router.delete(
    "/education-genotypes/{education_genotype_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    tags=["Éducation Génotypes"],
    summary="Supprimer une éducation génotype",
    description="Supprime une éducation génotype spécifique par son ID. Requiert la permission DELETE_EDUCATION_GENOTYPES."
)
async def delete_education_genotype(
    education_genotype_id: int,
    db: AsyncSession = Depends(get_async_db),
    current_user: UtilisateurLight = Depends(require_permissions(["DELETE_EDUCATION_GENOTYPES"]))
):
    """
    Supprime une éducation génotype spécifique.

    - **education_genotype_id**: ID de l'éducation génotype à supprimer.
    - **Réponses**:
        - **204**: Éducation génotype supprimée avec succès.
        - **404**: Éducation génotype non trouvée.
        - **403**: Permission DELETE_EDUCATION_GENOTYPES manquante.
        - **500**: Erreur interne du serveur.
    """
    await education_genotype_service.delete(db, education_genotype_id)
    
    # ============================================================================
# ========================= ROUTES DES PLANS D'INTERVENTION ================
# ============================================================================

@router.post(
    "/plans-intervention",
    response_model=PlanInterventionIndividualiseLight,
    tags=["Plans d'Intervention"],
    summary="Créer un nouveau plan d'intervention individualisé",
    description="Crée un nouveau plan d'intervention individualisé pour un utilisateur. Requiert la permission CREATE_PLAN_INTERVENTION."
)
async def create_plan_intervention(
    plan_intervention: PlanInterventionIndividualiseCreate,
    db: AsyncSession = Depends(get_async_db),
    current_user: UtilisateurLight = Depends(require_permissions(["CREATE_PLAN_INTERVENTION"]))
):
    """
    Crée un nouveau plan d'intervention individualisé.

    - **plan_intervention**: Schéma de création du plan d'intervention.
    - **Réponses**:
        - **200**: Plan d'intervention créé avec succès.
        - **404**: Utilisateur non trouvé.
        - **403**: Permission CREATE_PLAN_INTERVENTION manquante.
        - **500**: Erreur interne du serveur.
    """
    return await plan_intervention_service.create(db, plan_intervention)

@router.get(
    "/plans-intervention/{plan_intervention_id}",
    response_model=PlanInterventionIndividualise,
    tags=["Plans d'Intervention"],
    summary="Récupérer un plan d'intervention par ID",
    description="Récupère les détails d'un plan d'intervention spécifique par son ID. Requiert la permission VIEW_PLANS_INTERVENTION."
)
async def get_plan_intervention(
    plan_intervention_id: int,
    db: AsyncSession = Depends(get_async_db),
    current_user: UtilisateurLight = Depends(require_permissions(["VIEW_PLANS_INTERVENTION"]))
):
    """
    Récupère un plan d'intervention spécifique.

    - **plan_intervention_id**: ID du plan d'intervention à récupérer.
    - **Réponses**:
        - **200**: Détails du plan d'intervention.
        - **404**: Plan d'intervention non trouvé.
        - **403**: Permission VIEW_PLANS_INTERVENTION manquante.
        - **500**: Erreur interne du serveur.
    """
    return await plan_intervention_service.get(db, plan_intervention_id)

@router.get(
    "/plans-intervention",
    response_model=List[PlanInterventionIndividualise],
    tags=["Plans d'Intervention"],
    summary="Lister tous les plans d'intervention",
    description="Récupère une liste paginée de tous les plans d'intervention avec leurs relations. Requiert la permission VIEW_PLANS_INTERVENTION."
)
async def list_plans_intervention(
    skip: int = 0,
    limit: int = 100,
    db: AsyncSession = Depends(get_async_db),
    current_user: UtilisateurLight = Depends(require_permissions(["VIEW_PLANS_INTERVENTION"]))
):
    """
    Liste tous les plans d'intervention avec pagination.

    - **skip**: Nombre de plans d'intervention à sauter (défaut: 0).
    - **limit**: Nombre maximum de plans d'intervention à retourner (défaut: 100).
    - **Réponses**:
        - **200**: Liste des plans d'intervention.
        - **403**: Permission VIEW_PLANS_INTERVENTION manquante.
        - **500**: Erreur interne du serveur.
    """
    return await plan_intervention_service.get_all(db, skip, limit)

@router.put(
    "/plans-intervention/{plan_intervention_id}",
    response_model=PlanInterventionIndividualise,
    tags=["Plans d'Intervention"],
    summary="Mettre à jour un plan d'intervention",
    description="Met à jour un plan d'intervention spécifique. Requiert la permission EDIT_PLANS_INTERVENTION."
)
async def update_plan_intervention(
    plan_intervention_id: int,
    plan_intervention_update: PlanInterventionIndividualiseUpdate,
    db: AsyncSession = Depends(get_async_db),
    current_user: UtilisateurLight = Depends(require_permissions(["EDIT_PLANS_INTERVENTION"]))
):
    """
    Met à jour un plan d'intervention spécifique.

    - **plan_intervention_id**: ID du plan d'intervention à mettre à jour.
    - **plan_intervention_update**: Schéma de mise à jour du plan d'intervention.
    - **Réponses**:
        - **200**: Plan d'intervention mis à jour avec succès.
        - **404**: Plan d'intervention ou utilisateur non trouvé.
        - **403**: Permission EDIT_PLANS_INTERVENTION manquante.
        - **500**: Erreur interne du serveur.
    """
    return await plan_intervention_service.update(db, plan_intervention_id, plan_intervention_update)

@router.delete(
    "/plans-intervention/{plan_intervention_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    tags=["Plans d'Intervention"],
    summary="Supprimer un plan d'intervention",
    description="Supprime un plan d'intervention spécifique par son ID. Requiert la permission DELETE_PLANS_INTERVENTION."
)
async def delete_plan_intervention(
    plan_intervention_id: int,
    db: AsyncSession = Depends(get_async_db),
    current_user: UtilisateurLight = Depends(require_permissions(["DELETE_PLANS_INTERVENTION"]))
):
    """
    Supprime un plan d'intervention spécifique.

    - **plan_intervention_id**: ID du plan d'intervention à supprimer.
    - **Réponses**:
        - **204**: Plan d'intervention supprimé avec succès.
        - **404**: Plan d'intervention non trouvé.
        - **403**: Permission DELETE_PLANS_INTERVENTION manquante.
        - **500**: Erreur interne du serveur.
    """
    await plan_intervention_service.delete(db, plan_intervention_id)
    
    # ============================================================================
# ========================= ROUTES DES ACCRÉDITATIONS ======================
# ============================================================================

@router.post(
    "/accreditations",
    response_model=AccreditationLight,
    tags=["Accréditations"],
    summary="Créer une nouvelle accréditation",
    description="Crée une nouvelle accréditation pour un utilisateur et une formation. Requiert la permission CREATE_ACCREDITATION."
)
async def create_accreditation(
    accreditation: AccreditationCreate,
    db: AsyncSession = Depends(get_async_db),
    current_user: UtilisateurLight = Depends(require_permissions(["CREATE_ACCREDITATION"]))
):
    """
    Crée une nouvelle accréditation.

    - **accreditation**: Schéma de création de l'accréditation.
    - **Réponses**:
        - **200**: Accréditation créée avec succès.
        - **404**: Utilisateur ou formation non trouvé.
        - **403**: Permission CREATE_ACCREDITATION manquante.
        - **500**: Erreur interne du serveur.
    """
    return await accreditation_service.create(db, accreditation)

@router.get(
    "/accreditations/{accreditation_id}",
    response_model=Accreditation,
    tags=["Accréditations"],
    summary="Récupérer une accréditation par ID",
    description="Récupère les détails d'une accréditation spécifique par son ID. Requiert la permission VIEW_ACCREDITATIONS."
)
async def get_accreditation(
    accreditation_id: int,
    db: AsyncSession = Depends(get_async_db),
    current_user: UtilisateurLight = Depends(require_permissions(["VIEW_ACCREDITATIONS"]))
):
    """
    Récupère une accréditation spécifique.

    - **accreditation_id**: ID de l'accréditation à récupérer.
    - **Réponses**:
        - **200**: Détails de l'accréditation.
        - **404**: Accréditation non trouvée.
        - **403**: Permission VIEW_ACCREDITATIONS manquante.
        - **500**: Erreur interne du serveur.
    """
    return await accreditation_service.get(db, accreditation_id)

@router.get(
    "/accreditations",
    response_model=List[Accreditation],
    tags=["Accréditations"],
    summary="Lister toutes les accréditations",
    description="Récupère une liste paginée de toutes les accréditations avec leurs relations. Requiert la permission VIEW_ACCREDITATIONS."
)
async def list_accreditations(
    skip: int = 0,
    limit: int = 100,
    db: AsyncSession = Depends(get_async_db),
    current_user: UtilisateurLight = Depends(require_permissions(["VIEW_ACCREDITATIONS"]))
):
    """
    Liste toutes les accréditations avec pagination.

    - **skip**: Nombre d'accréditations à sauter (défaut: 0).
    - **limit**: Nombre maximum d'accréditations à retourner (défaut: 100).
    - **Réponses**:
        - **200**: Liste des accréditations.
        - **403**: Permission VIEW_ACCREDITATIONS manquante.
        - **500**: Erreur interne du serveur.
    """
    return await accreditation_service.get_all(db, skip, limit)

@router.put(
    "/accreditations/{accreditation_id}",
    response_model=Accreditation,
    tags=["Accréditations"],
    summary="Mettre à jour une accréditation",
    description="Met à jour une accréditation spécifique. Requiert la permission EDIT_ACCREDITATIONS."
)
async def update_accreditation(
    accreditation_id: int,
    accreditation_update: AccreditationUpdate,
    db: AsyncSession = Depends(get_async_db),
    current_user: UtilisateurLight = Depends(require_permissions(["EDIT_ACCREDITATIONS"]))
):
    """
    Met à jour une accréditation spécifique.

    - **accreditation_id**: ID de l'accréditation à mettre à jour.
    - **accreditation_update**: Schéma de mise à jour de l'accréditation.
    - **Réponses**:
        - **200**: Accréditation mise à jour avec succès.
        - **404**: Accréditation, utilisateur ou formation non trouvé.
        - **403**: Permission EDIT_ACCREDITATIONS manquante.
        - **500**: Erreur interne du serveur.
    """
    return await accreditation_service.update(db, accreditation_id, accreditation_update)

@router.delete(
    "/accreditations/{accreditation_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    tags=["Accréditations"],
    summary="Supprimer une accréditation",
    description="Supprime une accréditation spécifique par son ID. Requiert la permission DELETE_ACCREDITATIONS."
)
async def delete_accreditation(
    accreditation_id: int,
    db: AsyncSession = Depends(get_async_db),
    current_user: UtilisateurLight = Depends(require_permissions(["DELETE_ACCREDITATIONS"]))
):
    """
    Supprime une accréditation spécifique.

    - **accreditation_id**: ID de l'accréditation à supprimer.
    - **Réponses**:
        - **204**: Accréditation supprimée avec succès.
        - **404**: Accréditation non trouvée.
        - **403**: Permission DELETE_ACCREDITATIONS manquante.
        - **500**: Erreur interne du serveur.
    """
    await accreditation_service.delete(db, accreditation_id)
    
    # ============================================================================
# ========================= ROUTES DES ACTUALITÉS ==========================
# ============================================================================

@router.post(
    "/actualites",
    response_model=ActualiteLight,
    tags=["Actualités"],
    summary="Créer une nouvelle actualité",
    description="Crée une nouvelle actualité. Requiert la permission CREATE_ACTUALITE."
)
async def create_actualite(
    actualite: ActualiteCreate,
    db: AsyncSession = Depends(get_async_db),
    current_user: UtilisateurLight = Depends(require_permissions(["CREATE_ACTUALITE"]))
):
    """
    Crée une nouvelle actualité.

    - **actualite**: Schéma de création de l'actualité.
    - **Réponses**:
        - **200**: Actualité créée avec succès.
        - **403**: Permission CREATE_ACTUALITE manquante.
        - **500**: Erreur interne du serveur.
    """
    return await actualite_service.create(db, actualite)

@router.get(
    "/actualites/{actualite_id}",
    response_model=Actualite,
    tags=["Actualités"],
    summary="Récupérer une actualité par ID",
    description="Récupère les détails d'une actualité spécifique par son ID. Requiert la permission VIEW_ACTUALITES."
)
async def get_actualite(
    actualite_id: int,
    db: AsyncSession = Depends(get_async_db),
    current_user: UtilisateurLight = Depends(require_permissions(["VIEW_ACTUALITES"]))
):
    """
    Récupère une actualité spécifique.

    - **actualite_id**: ID de l'actualité à récupérer.
    - **Réponses**:
        - **200**: Détails de l'actualité.
        - **404**: Actualité non trouvée.
        - **403**: Permission VIEW_ACTUALITES manquante.
        - **500**: Erreur interne du serveur.
    """
    return await actualite_service.get(db, actualite_id)

@router.get(
    "/actualites",
    response_model=List[Actualite],
    tags=["Actualités"],
    summary="Lister toutes les actualités",
    description="Récupère une liste paginée de toutes les actualités avec leurs relations. Requiert la permission VIEW_ACTUALITES."
)
async def list_actualites(
    skip: int = 0,
    limit: int = 100,
    db: AsyncSession = Depends(get_async_db),
    current_user: UtilisateurLight = Depends(require_permissions(["VIEW_ACTUALITES"]))
):
    """
    Liste toutes les actualités avec pagination.

    - **skip**: Nombre d'actualités à sauter (défaut: 0).
    - **limit**: Nombre maximum d'actualités à retourner (défaut: 100).
    - **Réponses**:
        - **200**: Liste des actualités.
        - **403**: Permission VIEW_ACTUALITES manquante.
        - **500**: Erreur interne du serveur.
    """
    return await actualite_service.get_all(db, skip, limit)

@router.put(
    "/actualites/{actualite_id}",
    response_model=Actualite,
    tags=["Actualités"],
    summary="Mettre à jour une actualité",
    description="Met à jour une actualité spécifique. Requiert la permission EDIT_ACTUALITES."
)
async def update_actualite(
    actualite_id: int,
    actualite_update: ActualiteUpdate,
    db: AsyncSession = Depends(get_async_db),
    current_user: UtilisateurLight = Depends(require_permissions(["EDIT_ACTUALITES"]))
):
    """
    Met à jour une actualité spécifique.

    - **actualite_id**: ID de l'actualité à mettre à jour.
    - **actualite_update**: Schéma de mise à jour de l'actualité.
    - **Réponses**:
        - **200**: Actualité mise à jour avec succès.
        - **404**: Actualité non trouvée.
        - **403**: Permission EDIT_ACTUALITES manquante.
        - **500**: Erreur interne du serveur.
    """
    return await actualite_service.update(db, actualite_id, actualite_update)

@router.delete(
    "/actualites/{actualite_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    tags=["Actualités"],
    summary="Supprimer une actualité",
    description="Supprime une actualité spécifique par son ID. Requiert la permission DELETE_ACTUALITES."
)
async def delete_actualite(
    actualite_id: int,
    db: AsyncSession = Depends(get_async_db),
    current_user: UtilisateurLight = Depends(require_permissions(["DELETE_ACTUALITES"]))
):
    """
    Supprime une actualité spécifique.

    - **actualite_id**: ID de l'actualité à supprimer.
    - **Réponses**:
        - **204**: Actualité supprimée avec succès.
        - **404**: Actualité non trouvée.
        - **403**: Permission DELETE_ACTUALITES manquante.
        - **500**: Erreur interne du serveur.
    """
    await actualite_service.delete(db, actualite_id)
    
    
# ============================================================================
# ========================= ROUTES DES FICHIERS =============================
# ============================================================================

@router.post(
    "/files",
    response_model=str,
    tags=["Fichiers"],
    summary="Téléverser un fichier",
    description="Téléverse un fichier pour un utilisateur (image de profil, document, etc.). Requiert la permission UPLOAD_FILE."
)
async def upload_file(
    request: Request,
    file: UploadFile = File(...),
    file_type: FileTypeEnum = FileTypeEnum,
    db: AsyncSession = Depends(get_async_db),
    # current_user: UtilisateurLight = Depends(require_permissions(["UPLOAD_FILE"]))
):
    """
    Téléverse un fichier.

    - **file**: Fichier à téléverser.
    - **file_type**: Type de fichier (par exemple, IMAGE_PROFILE, DOCUMENT, etc.).
    - **Réponses**:
        - **200**: URL ou identifiant du fichier téléversé.
        - **400**: Type de fichier non supporté ou fichier invalide.
        - **403**: Permission UPLOAD_FILE manquante.
        - **500**: Erreur interne du serveur.
    """
    return await file_service.upload_file(request, file, file_type)
    # return await file_service.upload_file(db, file, current_user.id, file_type)

@router.get(
    "/files/{file_id}",
    response_model=str,
    tags=["Fichiers"],
    summary="Récupérer un fichier par ID",
    description="Récupère l'URL ou les détails d'un fichier spécifique par son ID. Requiert la permission VIEW_FILES."
)
async def get_file(
    file_id: int,
    db: AsyncSession = Depends(get_async_db),
    # current_user: UtilisateurLight = Depends(require_permissions(["VIEW_FILES"]))
):
    """
    Récupère un fichier spécifique.

    - **file_id**: ID du fichier à récupérer.
    - **Réponses**:
        - **200**: URL ou détails du fichier.
        - **404**: Fichier non trouvé.
        - **403**: Permission VIEW_FILES manquante.
        - **500**: Erreur interne du serveur.
    """
    return await file_service.get(db, file_id)

@router.get(
    "/files",
    response_model=List[str],
    tags=["Fichiers"],
    summary="Lister tous les fichiers",
    description="Récupère une liste paginée de tous les fichiers avec leurs détails. Requiert la permission VIEW_FILES."
)
async def list_files(
    skip: int = 0,
    limit: int = 100,
    db: AsyncSession = Depends(get_async_db),
    # current_user: UtilisateurLight = Depends(require_permissions(["VIEW_FILES"]))
):
    """
    Liste tous les fichiers avec pagination.

    - **skip**: Nombre de fichiers à sauter (défaut: 0).
    - **limit**: Nombre maximum de fichiers à retourner (défaut: 100).
    - **Réponses**:
        - **200**: Liste des fichiers.
        - **403**: Permission VIEW_FILES manquante.
        - **500**: Erreur interne du serveur.
    """
    return await file_service.get_all(db, skip, limit)

@router.delete(
    "/files/{file_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    tags=["Fichiers"],
    summary="Supprimer un fichier",
    description="Supprime un fichier spécifique par son ID. Requiert la permission DELETE_FILES."
)
async def delete_file(
    file_id: int,
    db: AsyncSession = Depends(get_async_db),
    # current_user: UtilisateurLight = Depends(require_permissions(["DELETE_FILES"]))
):
    """
    Supprime un fichier spécifique.

    - **file_id**: ID du fichier à supprimer.
    - **Réponses**:
        - **204**: Fichier supprimé avec succès.
        - **404**: Fichier non trouvé.
        - **403**: Permission DELETE_FILES manquante.
        - **500**: Erreur interne du serveur.
    """
    await file_service.delete(db, file_id)
    
    
    
from fastapi import APIRouter, Depends, HTTPException, status, UploadFile, File
from fastapi.security import OAuth2PasswordRequestForm
from sqlalchemy.ext.asyncio import AsyncSession
from typing import List
from src.util.database.database import get_async_db
from src.api.service import (
    UtilisateurService, PermissionService, RoleService, FormationService,
    InscriptionFormationService, PaiementService, ModuleService, RessourceService,
    ChefDOeuvreService, ProjetCollectifService, EvaluationService, QuestionService,
    PropositionService, ResultatEvaluationService, GenotypeIndividuelService,
    AscendanceGenotypeService, SanteGenotypeService, EducationGenotypeService,
    PlanInterventionIndividualiseService, AccreditationService, ActualiteService,
    FileService
)
from src.api.schema import (
    Utilisateur, UtilisateurLight, UtilisateurCreate, UtilisateurUpdate,
    Permission, PermissionLight, PermissionCreate, PermissionUpdate,
    Role, RoleLight, RoleCreate, RoleUpdate,
    Formation, FormationLight, FormationCreate, FormationUpdate,
    InscriptionFormation, InscriptionFormationLight, InscriptionFormationCreate, InscriptionFormationUpdate,
    Paiement, PaiementLight, PaiementCreate, PaiementUpdate,
    Module, ModuleLight, ModuleCreate, ModuleUpdate,
    Ressource, RessourceLight, RessourceCreate, RessourceUpdate,
    ChefDOeuvre, ChefDOeuvreLight, ChefDOeuvreCreate, ChefDOeuvreUpdate,
    ProjetCollectif, ProjetCollectifLight, ProjetCollectifCreate, ProjetCollectifUpdate,
    Evaluation, EvaluationLight, EvaluationCreate, EvaluationUpdate,
    Question, QuestionLight, QuestionCreate, QuestionUpdate,
    Proposition, PropositionLight, PropositionCreate, PropositionUpdate,
    ResultatEvaluation, ResultatEvaluationLight, ResultatEvaluationCreate, ResultatEvaluationUpdate,
    GenotypeIndividuel, GenotypeIndividuelLight, GenotypeIndividuelCreate, GenotypeIndividuelUpdate,
    AscendanceGenotype, AscendanceGenotypeLight, AscendanceGenotypeCreate, AscendanceGenotypeUpdate,
    SanteGenotype, SanteGenotypeLight, SanteGenotypeCreate, SanteGenotypeUpdate,
    EducationGenotype, EducationGenotypeLight, EducationGenotypeCreate, EducationGenotypeUpdate,
    PlanInterventionIndividualise, PlanInterventionIndividualiseLight, PlanInterventionIndividualiseCreate, PlanInterventionIndividualiseUpdate,
    Accreditation, AccreditationLight, AccreditationCreate, AccreditationUpdate,
    Actualite, ActualiteLight, ActualiteCreate, ActualiteUpdate
)
from src.util.helper.enum import FileTypeEnum
from src.util.security.security import get_current_active_user, has_permission, require_permissions
import logging

logger = logging.getLogger(__name__)

# Initialisation des services
utilisateur_service = UtilisateurService()
permission_service = PermissionService()
role_service = RoleService()
formation_service = FormationService()
inscription_formation_service = InscriptionFormationService()
paiement_service = PaiementService()
module_service = ModuleService()
ressource_service = RessourceService()
chef_d_oeuvre_service = ChefDOeuvreService()
projet_collectif_service = ProjetCollectifService()
evaluation_service = EvaluationService()
question_service = QuestionService()
proposition_service = PropositionService()
resultat_evaluation_service = ResultatEvaluationService()
genotype_individuel_service = GenotypeIndividuelService()
ascendance_genotype_service = AscendanceGenotypeService()
sante_genotype_service = SanteGenotypeService()
education_genotype_service = EducationGenotypeService()
plan_intervention_service = PlanInterventionIndividualiseService()
accreditation_service = AccreditationService()
actualite_service = ActualiteService()
file_service = FileService()

# Initialisation du routeur principal
router = APIRouter()

# ============================================================================
# ========================= ROUTES DES UTILISATEURS ==========================
# ============================================================================

@router.post(
    "/login",
    response_model=dict,
    tags=["Utilisateurs"],
    summary="Connexion d'un utilisateur",
    description="Authentifie un utilisateur avec son email et mot de passe, retourne un token JWT. Aucun rôle ou permission spécifique requis."
)
async def login(form_data: OAuth2PasswordRequestForm = Depends(), db: AsyncSession = Depends(get_async_db)):
    """
    Authentifie un utilisateur et génère un token JWT.

    - **email**: Adresse email de l'utilisateur.
    - **password**: Mot de passe de l'utilisateur.
    - **Réponses**:
        - **200**: Token JWT généré avec succès.
        - **401**: Email ou mot de passe incorrect.
        - **500**: Erreur interne du serveur.
    """
    return await utilisateur_service.login(db, form_data.username, form_data.password)

@router.get(
    "/me",
    response_model=UtilisateurLight,
    tags=["Utilisateurs"],
    summary="Récupérer l'utilisateur connecté",
    description="Retourne les informations de l'utilisateur connecté, incluant ses permissions (directes et via rôle). Requiert un utilisateur actif."
)
async def read_users_me(current_user: UtilisateurLight = Depends(get_current_active_user)):
    """
    Récupère les informations de l'utilisateur connecté.

    - **Réponses**:
        - **200**: Informations de l'utilisateur connecté.
        - **401**: Token invalide ou expiré.
        - **403**: Utilisateur inactif.
        - **500**: Erreur interne du serveur.
    """
    return current_user

@router.post(
    "/users",
    response_model=UtilisateurLight,
    tags=["Utilisateurs"],
    summary="Créer un nouvel utilisateur",
    description="Crée un nouvel utilisateur avec un mot de passe généré automatiquement. Requiert la permission CREATE_USER."
)
async def create_user(
    user: UtilisateurCreate,
    db: AsyncSession = Depends(get_async_db),
    current_user: UtilisateurLight = Depends(require_permissions(["CREATE_USER"]))
):
    """
    Crée un nouvel utilisateur avec validation de l'unicité de l'email.

    - **user**: Schéma de création de l'utilisateur (nom, email, rôle, etc.).
    - **Réponses**:
        - **200**: Utilisateur créé avec succès.
        - **400**: Données invalides.
        - **409**: Email déjà utilisé.
        - **403**: Permission CREATE_USER manquante.
        - **500**: Erreur interne du serveur.
    """
    return await utilisateur_service.create(db, user)

@router.get(
    "/users/{user_id}",
    response_model=Utilisateur,
    tags=["Utilisateurs"],
    summary="Récupérer un utilisateur par ID",
    description="Récupère les détails d'un utilisateur spécifique par son ID. Requiert la permission VIEW_USERS."
)
async def get_user(
    user_id: int,
    db: AsyncSession = Depends(get_async_db),
    current_user: UtilisateurLight = Depends(require_permissions(["VIEW_USERS"]))
):
    """
    Récupère un utilisateur spécifique par son ID.

    - **user_id**: ID de l'utilisateur à récupérer.
    - **Réponses**:
        - **200**: Détails de l'utilisateur.
        - **404**: Utilisateur non trouvé.
        - **403**: Permission VIEW_USERS manquante.
        - **500**: Erreur interne du serveur.
    """
    return await utilisateur_service.get(db, user_id)

@router.get(
    "/users",
    response_model=List[Utilisateur],
    tags=["Utilisateurs"],
    summary="Lister tous les utilisateurs",
    description="Récupère une liste paginée de tous les utilisateurs avec leurs relations. Requiert la permission VIEW_USERS."
)
async def list_users(
    skip: int = 0,
    limit: int = 100,
    db: AsyncSession = Depends(get_async_db),
    current_user: UtilisateurLight = Depends(require_permissions(["VIEW_USERS"]))
):
    """
    Liste tous les utilisateurs avec pagination.

    - **skip**: Nombre d'utilisateurs à sauter (défaut: 0).
    - **limit**: Nombre maximum d'utilisateurs à retourner (défaut: 100).
    - **Réponses**:
        - **200**: Liste des utilisateurs.
        - **403**: Permission VIEW_USERS manquante.
        - **500**: Erreur interne du serveur.
    """
    return await utilisateur_service.get_all(db, skip, limit)

@router.put(
    "/users/{user_id}",
    response_model=UtilisateurLight,
    tags=["Utilisateurs"],
    summary="Mettre à jour un utilisateur",
    description="Met à jour les informations d'un utilisateur spécifique. Requiert la permission EDIT_USERS."
)
async def update_user(
    user_id: int,
    user_update: UtilisateurUpdate,
    db: AsyncSession = Depends(get_async_db),
    current_user: UtilisateurLight = Depends(require_permissions(["EDIT_USERS"]))
):
    """
    Met à jour un utilisateur spécifique.

    - **user_id**: ID de l'utilisateur à mettre à jour.
    - **user_update**: Schéma de mise à jour de l'utilisateur.
    - **Réponses**:
        - **200**: Utilisateur mis à jour avec succès.
        - **404**: Utilisateur non trouvé.
        - **409**: Email déjà utilisé.
        - **403**: Permission EDIT_USERS manquante.
        - **500**: Erreur interne du serveur.
    """
    return await utilisateur_service.update(db, user_id, user_update)

@router.delete(
    "/users/{user_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    tags=["Utilisateurs"],
    summary="Supprimer un utilisateur",
    description="Supprime un utilisateur spécifique par son ID. Requiert la permission DELETE_USERS."
)
async def delete_user(
    user_id: int,
    db: AsyncSession = Depends(get_async_db),
    current_user: UtilisateurLight = Depends(require_permissions(["DELETE_USERS"]))
):
    """
    Supprime un utilisateur spécifique.

    - **user_id**: ID de l'utilisateur à supprimer.
    - **Réponses**:
        - **204**: Utilisateur supprimé avec succès.
        - **404**: Utilisateur non trouvé.
        - **403**: Permission DELETE_USERS manquante.
        - **500**: Erreur interne du serveur.
    """
    await utilisateur_service.delete(db, user_id)

@router.post(
    "/users/{user_id}/change-password",
    response_model=str,
    tags=["Utilisateurs"],
    summary="Changer le mot de passe d'un utilisateur",
    description="Change le mot de passe d'un utilisateur après vérification de l'ancien mot de passe. Requiert la permission CHANGE_PASSWORD ou que l'utilisateur modifie son propre mot de passe."
)
async def change_password(
    user_id: int,
    current_password: str,
    new_password: str,
    db: AsyncSession = Depends(get_async_db),
    current_user: UtilisateurLight = Depends(get_current_active_user)
):
    """
    Change le mot de passe d'un utilisateur.

    - **user_id**: ID de l'utilisateur dont le mot de passe doit être changé.
    - **current_password**: Mot de passe actuel.
    - **new_password**: Nouveau mot de passe.
    - **Réponses**:
        - **200**: Mot de passe changé avec succès.
        - **401**: Mot de passe actuel incorrect.
        - **403**: Permission CHANGE_PASSWORD manquante (si non-soi).
        - **404**: Utilisateur non trouvé.
        - **500**: Erreur interne du serveur.
    """
    if current_user.id != user_id and not has_permission(current_user, ["CHANGE_PASSWORD"]):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Permission CHANGE_PASSWORD requise pour modifier le mot de passe d'un autre utilisateur"
        )
    return await utilisateur_service.change_password(db, user_id, current_password, new_password)

@router.post(
    "/users/reset-password",
    response_model=str,
    tags=["Utilisateurs"],
    summary="Demander une réinitialisation de mot de passe",
    description="Génère un token de réinitialisation de mot de passe pour un utilisateur donné par son email. Aucun rôle ou permission requis."
)
async def reset_password(
    email: str,
    db: AsyncSession = Depends(get_async_db)
):
    """
    Demande une réinitialisation de mot de passe.

    - **email**: Email de l'utilisateur.
    - **Réponses**:
        - **200**: Token de réinitialisation généré.
        - **404**: Utilisateur non trouvé.
        - **500**: Erreur interne du serveur.
    """
    return await utilisateur_service.reset_password(db, email)

@router.post(
    "/users/confirm-reset-password",
    status_code=status.HTTP_204_NO_CONTENT,
    tags=["Utilisateurs"],
    summary="Confirmer la réinitialisation de mot de passe",
    description="Confirme la réinitialisation du mot de passe avec un token. Aucun rôle ou permission requis."
)
async def confirm_reset_password(
    reset_token: str,
    db: AsyncSession = Depends(get_async_db)
):
    """
    Confirme la réinitialisation du mot de passe.

    - **reset_token**: Token de réinitialisation.
    - **Réponses**:
        - **204**: Mot de passe réinitialisé avec succès.
        - **400**: Token invalide ou expiré.
        - **500**: Erreur interne du serveur.
    """
    await utilisateur_service.confirm_reset_password(db, reset_token)

# ============================================================================
# ========================= ROUTES DES PERMISSIONS ===========================
# ============================================================================

@router.post(
    "/permissions",
    response_model=PermissionLight,
    tags=["Permissions"],
    summary="Créer une nouvelle permission",
    description="Crée une nouvelle permission avec validation de l'unicité du nom. Requiert la permission CREATE_PERMISSION."
)
async def create_permission(
    permission: PermissionCreate,
    db: AsyncSession = Depends(get_async_db),
    current_user: UtilisateurLight = Depends(require_permissions(["CREATE_PERMISSION"]))
):
    """
    Crée une nouvelle permission.

    - **permission**: Schéma de création de la permission.
    - **Réponses**:
        - **200**: Permission créée avec succès.
        - **409**: Nom de permission déjà utilisé.
        - **403**: Permission CREATE_PERMISSION manquante.
        - **500**: Erreur interne du serveur.
    """
    return await permission_service.create(db, permission)

@router.get(
    "/permissions/{permission_id}",
    response_model=Permission,
    tags=["Permissions"],
    summary="Récupérer une permission par ID",
    description="Récupère les détails d'une permission spécifique par son ID. Requiert la permission VIEW_PERMISSIONS."
)
async def get_permission(
    permission_id: int,
    db: AsyncSession = Depends(get_async_db),
    current_user: UtilisateurLight = Depends(require_permissions(["VIEW_PERMISSIONS"]))
):
    """
    Récupère une permission spécifique.

    - **permission_id**: ID de la permission à récupérer.
    - **Réponses**:
        - **200**: Détails de la permission.
        - **404**: Permission non trouvée.
        - **403**: Permission VIEW_PERMISSIONS manquante.
        - **500**: Erreur interne du serveur.
    """
    return await permission_service.get(db, permission_id)

@router.get(
    "/permissions",
    response_model=List[Permission],
    tags=["Permissions"],
    summary="Lister toutes les permissions",
    description="Récupère une liste paginée de toutes les permissions avec leurs relations. Requiert la permission VIEW_PERMISSIONS."
)
async def list_permissions(
    skip: int = 0,
    limit: int = 100,
    db: AsyncSession = Depends(get_async_db),
    current_user: UtilisateurLight = Depends(require_permissions(["VIEW_PERMISSIONS"]))
):
    """
    Liste toutes les permissions avec pagination.

    - **skip**: Nombre de permissions à sauter (défaut: 0).
    - **limit**: Nombre maximum de permissions à retourner (défaut: 100).
    - **Réponses**:
        - **200**: Liste des permissions.
        - **403**: Permission VIEW_PERMISSIONS manquante.
        - **500**: Erreur interne du serveur.
    """
    return await permission_service.get_all(db, skip, limit)

@router.put(
    "/permissions/{permission_id}",
    response_model=Permission,
    tags=["Permissions"],
    summary="Mettre à jour une permission",
    description="Met à jour une permission spécifique. Requiert la permission EDIT_PERMISSIONS."
)
async def update_permission(
    permission_id: int,
    permission_update: PermissionUpdate,
    db: AsyncSession = Depends(get_async_db),
    current_user: UtilisateurLight = Depends(require_permissions(["EDIT_PERMISSIONS"]))
):
    """
    Met à jour une permission spécifique.

    - **permission_id**: ID de la permission à mettre à jour.
    - **permission_update**: Schéma de mise à jour de la permission.
    - **Réponses**:
        - **200**: Permission mise à jour avec succès.
        - **404**: Permission non trouvée.
        - **409**: Nom de permission déjà utilisé.
        - **403**: Permission EDIT_PERMISSIONS manquante.
        - **500**: Erreur interne du serveur.
    """
    return await permission_service.update(db, permission_id, permission_update)

@router.delete(
    "/permissions/{permission_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    tags=["Permissions"],
    summary="Supprimer une permission",
    description="Supprime une permission spécifique par son ID. Requiert la permission DELETE_PERMISSIONS."
)
async def delete_permission(
    permission_id: int,
    db: AsyncSession = Depends(get_async_db),
    current_user: UtilisateurLight = Depends(require_permissions(["DELETE_PERMISSIONS"]))
):
    """
    Supprime une permission spécifique.

    - **permission_id**: ID de la permission à supprimer.
    - **Réponses**:
        - **204**: Permission supprimée avec succès.
        - **404**: Permission non trouvée.
        - **403**: Permission DELETE_PERMISSIONS manquante.
        - **500**: Erreur interne du serveur.
    """
    await permission_service.delete(db, permission_id)

# ============================================================================
# ========================= ROUTES DES RÔLES ================================
# ============================================================================

@router.post(
    "/roles",
    response_model=RoleLight,
    tags=["Rôles"],
    summary="Créer un nouveau rôle",
    description="Crée un nouveau rôle avec ses permissions. Requiert la permission CREATE_ROLE."
)
async def create_role(
    role: RoleCreate,
    db: AsyncSession = Depends(get_async_db),
    current_user: UtilisateurLight = Depends(require_permissions(["CREATE_ROLE"]))
):
    """
    Crée un nouveau rôle.

    - **role**: Schéma de création du rôle (nom et liste d'IDs de permissions).
    - **Réponses**:
        - **200**: Rôle créé avec succès.
        - **409**: Nom de rôle déjà utilisé.
        - **403**: Permission CREATE_ROLE manquante.
        - **500**: Erreur interne du serveur.
    """
    return await role_service.create(db, role)

@router.get(
    "/roles/{role_id}",
    response_model=Role,
    tags=["Rôles"],
    summary="Récupérer un rôle par ID",
    description="Récupère les détails d'un rôle spécifique par son ID. Requiert la permission VIEW_ROLES."
)
async def get_role(
    role_id: int,
    db: AsyncSession = Depends(get_async_db),
    current_user: UtilisateurLight = Depends(require_permissions(["VIEW_ROLES"]))
):
    """
    Récupère un rôle spécifique.

    - **role_id**: ID du rôle à récupérer.
    - **Réponses**:
        - **200**: Détails du rôle.
        - **404**: Rôle non trouvé.
        - **403**: Permission VIEW_ROLES manquante.
        - **500**: Erreur interne du serveur.
    """
    return await role_service.get(db, role_id)

@router.get(
    "/roles",
    response_model=List[Role],
    tags=["Rôles"],
    summary="Lister tous les rôles",
    description="Récupère une liste paginée de tous les rôles avec leurs permissions. Requiert la permission VIEW_ROLES."
)
async def list_roles(
    skip: int = 0,
    limit: int = 100,
    db: AsyncSession = Depends(get_async_db),
    current_user: UtilisateurLight = Depends(require_permissions(["VIEW_ROLES"]))
):
    """
    Liste tous les rôles avec pagination.

    - **skip**: Nombre de rôles à sauter (défaut: 0).
    - **limit**: Nombre maximum de rôles à retourner (défaut: 100).
    - **Réponses**:
        - **200**: Liste des rôles.
        - **403**: Permission VIEW_ROLES manquante.
        - **500**: Erreur interne du serveur.
    """
    return await role_service.get_all(db, skip, limit)

@router.put(
    "/roles/{role_id}",
    response_model=Role,
    tags=["Rôles"],
    summary="Mettre à jour un rôle",
    description="Met à jour un rôle spécifique avec ses permissions. Requiert la permission EDIT_ROLES."
)
async def update_role(
    role_id: int,
    role_update: RoleUpdate,
    db: AsyncSession = Depends(get_async_db),
    current_user: UtilisateurLight = Depends(require_permissions(["EDIT_ROLES"]))
):
    """
    Met à jour un rôle spécifique.

    - **role_id**: ID du rôle à mettre à jour.
    - **role_update**: Schéma de mise à jour du rôle.
    - **Réponses**:
        - **200**: Rôle mis à jour avec succès.
        - **404**: Rôle non trouvé.
        - **409**: Nom de rôle déjà utilisé.
        - **403**: Permission EDIT_ROLES manquante.
        - **500**: Erreur interne du serveur.
    """
    return await role_service.update(db, role_id, role_update)

@router.delete(
    "/roles/{role_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    tags=["Rôles"],
    summary="Supprimer un rôle",
    description="Supprime un rôle spécifique par son ID. Requiert la permission DELETE_ROLES."
)
async def delete_role(
    role_id: int,
    db: AsyncSession = Depends(get_async_db),
    current_user: UtilisateurLight = Depends(require_permissions(["DELETE_ROLES"]))
):
    """
    Supprime un rôle spécifique.

    - **role_id**: ID du rôle à supprimer.
    - **Réponses**:
        - **204**: Rôle supprimé avec succès.
        - **404**: Rôle non trouvé.
        - **403**: Permission DELETE_ROLES manquante.
        - **500**: Erreur interne du serveur.
    """
    await role_service.delete(db, role_id)

@router.post(
    "/roles/{role_id}/permissions",
    response_model=str,
    tags=["Rôles"],
    summary="Assigner des permissions à un rôle",
    description="Assigne une ou plusieurs permissions à un rôle. Requiert la permission ASSIGN_PERMISSIONS."
)
async def assign_role_permissions(
    role_id: int,
    permission_ids: List[int],
    db: AsyncSession = Depends(get_async_db),
    current_user: UtilisateurLight = Depends(require_permissions(["ASSIGN_PERMISSIONS"]))
):
    """
    Assigne des permissions à un rôle.

    - **role_id**: ID du rôle auquel assigner les permissions.
    - **permission_ids**: Liste des IDs des permissions à assigner.
    - **Réponses**:
        - **200**: Permissions assignées avec succès.
        - **404**: Rôle ou permissions non trouvés.
        - **403**: Permission ASSIGN_PERMISSIONS manquante.
        - **500**: Erreur interne du serveur.
    """
    return await role_service.assign_permission(db, role_id, permission_ids)

@router.delete(
    "/roles/{role_id}/permissions",
    response_model=str,
    tags=["Rôles"],
    summary="Révoquer des permissions d'un rôle",
    description="Révoque une ou plusieurs permissions d'un rôle. Requiert la permission REVOKE_PERMISSIONS."
)
async def revoke_role_permissions(
    role_id: int,
    permission_ids: List[int],
    db: AsyncSession = Depends(get_async_db),
    current_user: UtilisateurLight = Depends(require_permissions(["REVOKE_PERMISSIONS"]))
):
    """
    Révoque des permissions d'un rôle.

    - **role_id**: ID du rôle auquel révoquer les permissions.
    - **permission_ids**: Liste des IDs des permissions à révoquer.
    - **Réponses**:
        - **200**: Permissions révoquées avec succès.
        - **404**: Rôle ou permissions non trouvés.
        - **403**: Permission REVOKE_PERMISSIONS manquante.
        - **500**: Erreur interne du serveur.
    """
    return await role_service.revoke_permission(db, role_id, permission_ids)

# ============================================================================
# ========================= ROUTES DES FORMATIONS ===========================
# ============================================================================

@router.post(
    "/formations",
    response_model=FormationLight,
    tags=["Formations"],
    summary="Créer une nouvelle formation",
    description="Crée une nouvelle formation avec validation de l'unicité du titre. Requiert la permission CREATE_FORMATION."
)
async def create_formation(
    formation: FormationCreate,
    db: AsyncSession = Depends(get_async_db),
    current_user: UtilisateurLight = Depends(require_permissions(["CREATE_FORMATION"]))
):
    """
    Crée une nouvelle formation.

    - **formation**: Schéma de création de la formation.
    - **Réponses**:
        - **200**: Formation créée avec succès.
        - **409**: Titre de formation déjà utilisé.
        - **403**: Permission CREATE_FORMATION manquante.
        - **500**: Erreur interne du serveur.
    """
    return await formation_service.create(db, formation)

@router.get(
    "/formations/{formation_id}",
    response_model=Formation,
    tags=["Formations"],
    summary="Récupérer une formation par ID",
    description="Récupère les détails d'une formation spécifique par son ID. Requiert la permission VIEW_FORMATIONS."
)
async def get_formation(
    formation_id: int,
    db: AsyncSession = Depends(get_async_db),
    current_user: UtilisateurLight = Depends(require_permissions(["VIEW_FORMATIONS"]))
):
    """
    Récupère une formation spécifique.

    - **formation_id**: ID de la formation à récupérer.
    - **Réponses**:
        - **200**: Détails de la formation.
        - **404**: Formation non trouvée.
        - **403**: Permission VIEW_FORMATIONS manquante.
        - **500**: Erreur interne du serveur.
    """
    return await formation_service.get(db, formation_id)

@router.get(
    "/formations",
    response_model=List[Formation],
    tags=["Formations"],
    summary="Lister toutes les formations",
    description="Récupère une liste paginée de toutes les formations avec leurs relations. Requiert la permission VIEW_FORMATIONS."
)
async def list_formations(
    skip: int = 0,
    limit: int = 100,
    db: AsyncSession = Depends(get_async_db),
    current_user: UtilisateurLight = Depends(require_permissions(["VIEW_FORMATIONS"]))
):
    """
    Liste toutes les formations avec pagination.

    - **skip**: Nombre de formations à sauter (défaut: 0).
    - **limit**: Nombre maximum de formations à retourner (défaut: 100).
    - **Réponses**:
        - **200**: Liste des formations.
        - **403**: Permission VIEW_FORMATIONS manquante.
        - **500**: Erreur interne du serveur.
    """
    return await formation_service.get_all(db, skip, limit)

@router.put(
    "/formations/{formation_id}",
    response_model=Formation,
    tags=["Formations"],
    summary="Mettre à jour une formation",
    description="Met à jour une formation spécifique. Requiert la permission EDIT_FORMATIONS."
)
async def update_formation(
    formation_id: int,
    formation_update: FormationUpdate,
    db: AsyncSession = Depends(get_async_db),
    current_user: UtilisateurLight = Depends(require_permissions(["EDIT_FORMATIONS"]))
):
    """
    Met à jour une formation spécifique.

    - **formation_id**: ID de la formation à mettre à jour.
    - **formation_update**: Schéma de mise à jour de la formation.
    - **Réponses**:
        - **200**: Formation mise à jour avec succès.
        - **404**: Formation non trouvée.
        - **409**: Titre de formation déjà utilisé.
        - **403**: Permission EDIT_FORMATIONS manquante.
        - **500**: Erreur interne du serveur.
    """
    return await formation_service.update(db, formation_id, formation_update)

@router.delete(
    "/formations/{formation_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    tags=["Formations"],
    summary="Supprimer une formation",
    description="Supprime une formation spécifique par son ID. Requiert la permission DELETE_FORMATIONS."
)
async def delete_formation(
    formation_id: int,
    db: AsyncSession = Depends(get_async_db),
    current_user: UtilisateurLight = Depends(require_permissions(["DELETE_FORMATIONS"]))
):
    """
    Supprime une formation spécifique.

    - **formation_id**: ID de la formation à supprimer.
    - **Réponses**:
        - **204**: Formation supprimée avec succès.
        - **404**: Formation non trouvée.
        - **403**: Permission DELETE_FORMATIONS manquante.
        - **500**: Erreur interne du serveur.
    """
    await formation_service.delete(db, formation_id)

# ============================================================================
# ========================= ROUTES DES INSCRIPTIONS ==========================
# ============================================================================

@router.post(
    "/inscriptions",
    response_model=InscriptionFormationLight,
    tags=["Inscriptions"],
    summary="Créer une nouvelle inscription",
    description="Inscrit un utilisateur à une formation. Requiert la permission CREATE_INSCRIPTION."
)
async def create_inscription(
    inscription: InscriptionFormationCreate,
    db: AsyncSession = Depends(get_async_db),
    current_user: UtilisateurLight = Depends(require_permissions(["CREATE_INSCRIPTION"]))
):
    """
    Crée une nouvelle inscription à une formation.

    - **inscription**: Schéma de création de l'inscription.
    - **Réponses**:
        - **200**: Inscription créée avec succès.
        - **404**: Utilisateur ou formation non trouvé.
        - **409**: Utilisateur déjà inscrit à la formation.
        - **403**: Permission CREATE_INSCRIPTION manquante.
        - **500**: Erreur interne du serveur.
    """
    return await inscription_formation_service.create(db, inscription)

@router.get(
    "/inscriptions/{inscription_id}",
    response_model=InscriptionFormation,
    tags=["Inscriptions"],
    summary="Récupérer une inscription par ID",
    description="Récupère les détails d'une inscription spécifique par son ID. Requiert la permission VIEW_INSCRIPTIONS."
)
async def get_inscription(
    inscription_id: int,
    db: AsyncSession = Depends(get_async_db),
    current_user: UtilisateurLight = Depends(require_permissions(["VIEW_INSCRIPTIONS"]))
):
    """
    Récupère une inscription spécifique.

    - **inscription_id**: ID de l'inscription à récupérer.
    - **Réponses**:
        - **200**: Détails de l'inscription.
        - **404**: Inscription non trouvée.
        - **403**: Permission VIEW_INSCRIPTIONS manquante.
        - **500**: Erreur interne du serveur.
    """
    return await inscription_formation_service.get(db, inscription_id)

@router.get(
    "/inscriptions",
    response_model=List[InscriptionFormation],
    tags=["Inscriptions"],
    summary="Lister toutes les inscriptions",
    description="Récupère une liste paginée de toutes les inscriptions avec leurs relations. Requiert la permission VIEW_INSCRIPTIONS."
)
async def list_inscriptions(
    skip: int = 0,
    limit: int = 100,
    db: AsyncSession = Depends(get_async_db),
    current_user: UtilisateurLight = Depends(require_permissions(["VIEW_INSCRIPTIONS"]))
):
    """
    Liste toutes les inscriptions avec pagination.

    - **skip**: Nombre d'inscriptions à sauter (défaut: 0).
    - **limit**: Nombre maximum d'inscriptions à retourner (défaut: 100).
    - **Réponses**:
        - **200**: Liste des inscriptions.
        - **403**: Permission VIEW_INSCRIPTIONS manquante.
        - **500**: Erreur interne du serveur.
    """
    return await inscription_formation_service.get_all(db, skip, limit)

@router.get(
    "/inscriptions/{inscription_id}/paiements",
    response_model=List[InscriptionFormation],
    tags=["Inscriptions"],
    summary="Récupérer une inscription avec ses paiements",
    description="Récupère une inscription spécifique avec ses paiements associés. Requiert la permission VIEW_INSCRIPTIONS."
)
async def get_inscription_with_paiements(
    inscription_id: int,
    db: AsyncSession = Depends(get_async_db),
    current_user: UtilisateurLight = Depends(require_permissions(["VIEW_INSCRIPTIONS"]))
):
    """
    Récupère une inscription avec ses paiements.

    - **inscription_id**: ID de l'inscription à récupérer.
    - **Réponses**:
        - **200**: Inscription avec paiements.
        - **404**: Inscription non trouvée.
        - **403**: Permission VIEW_INSCRIPTIONS manquante.
        - **500**: Erreur interne du serveur.
    """
    return await inscription_formation_service.get_with_paiements(db, inscription_id)

@router.put(
    "/inscriptions/{inscription_id}",
    response_model=InscriptionFormation,
    tags=["Inscriptions"],
    summary="Mettre à jour une inscription",
    description="Met à jour une inscription spécifique avec validation du montant versé. Requiert la permission EDIT_INSCRIPTIONS."
)
async def update_inscription(
    inscription_id: int,
    inscription_update: InscriptionFormationUpdate,
    db: AsyncSession = Depends(get_async_db),
    current_user: UtilisateurLight = Depends(require_permissions(["EDIT_INSCRIPTIONS"]))
):
    """
    Met à jour une inscription spécifique.

    - **inscription_id**: ID de l'inscription à mettre à jour.
    - **inscription_update**: Schéma de mise à jour de l'inscription.
    - **Réponses**:
        - **200**: Inscription mise à jour avec succès.
        - **404**: Inscription, utilisateur ou formation non trouvé.
        - **400**: Montant versé dépasse les frais de la formation.
        - **403**: Permission EDIT_INSCRIPTIONS manquante.
        - **500**: Erreur interne du serveur.
    """
    return await inscription_formation_service.update(db, inscription_id, inscription_update)

@router.delete(
    "/inscriptions/{inscription_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    tags=["Inscriptions"],
    summary="Supprimer une inscription",
    description="Supprime une inscription spécifique par son ID. Requiert la permission DELETE_INSCRIPTIONS."
)
async def delete_inscription(
    inscription_id: int,
    db: AsyncSession = Depends(get_async_db),
    current_user: UtilisateurLight = Depends(require_permissions(["DELETE_INSCRIPTIONS"]))
):
    """
    Supprime une inscription spécifique.

    - **inscription_id**: ID de l'inscription à supprimer.
    - **Réponses**:
        - **204**: Inscription supprimée avec succès.
        - **404**: Inscription non trouvée.
        - **403**: Permission DELETE_INSCRIPTIONS manquante.
        - **500**: Erreur interne du serveur.
    """
    await inscription_formation_service.delete(db, inscription_id)

# ============================================================================
# ========================= ROUTES DES PAIEMENTS =============================
# ============================================================================

@router.post(
    "/paiements",
    response_model=PaiementLight,
    tags=["Paiements"],
    summary="Créer un nouveau paiement",
    description="Crée un nouveau paiement pour une inscription avec mise à jour du statut de paiement. Requiert la permission CREATE_PAIEMENT."
)
async def create_paiement(
    paiement: PaiementCreate,
    db: AsyncSession = Depends(get_async_db),
    current_user: UtilisateurLight = Depends(require_permissions(["CREATE_PAIEMENT"]))
):
    """
    Crée un nouveau paiement.

    - **paiement**: Schéma de création du paiement.
    - **Réponses**:
        - **200**: Paiement créé avec succès.
        - **400**: Montant total dépasse les frais de la formation.
        - **404**: Inscription ou formation non trouvée.
        - **403**: Permission CREATE_PAIEMENT manquante.
        - **500**: Erreur interne du serveur.
    """
    return await paiement_service.create(db, paiement)

@router.get(
    "/paiements/{paiement_id}",
    response_model=Paiement,
    tags=["Paiements"],
    summary="Récupérer un paiement par ID",
    description="Récupère les détails d'un paiement spécifique par son ID. Requiert la permission VIEW_PAIEMENTS."
)
async def get_paiement(
    paiement_id: int,
    db: AsyncSession = Depends(get_async_db),
    current_user: UtilisateurLight = Depends(require_permissions(["VIEW_PAIEMENTS"]))
):
    """
    Récupère un paiement spécifique.

    - **paiement_id**: ID du paiement à récupérer.
    - **Réponses**:
        - **200**: Détails du paiement.
        - **404**: Paiement non trouvé.
        - **403**: Permission VIEW_PAIEMENTS manquante.
        - **500**: Erreur interne du serveur.
    """
    return await paiement_service.get(db, paiement_id)

@router.get(
    "/paiements",
    response_model=List[Paiement],
    tags=["Paiements"],
    summary="Lister tous les paiements",
    description="Récupère une liste paginée de tous les paiements avec leurs relations. Requiert la permission VIEW_PAIEMENTS."
)
async def list_paiements(
    skip: int = 0,
    limit: int = 100,
    db: AsyncSession = Depends(get_async_db),
    current_user: UtilisateurLight = Depends(require_permissions(["VIEW_PAIEMENTS"]))
):
    """
    Liste tous les paiements avec pagination.

    - **skip**: Nombre de paiements à sauter (défaut: 0).
    - **limit**: Nombre maximum de paiements à retourner (défaut: 100).
    - **Réponses**:
        - **200**: Liste des paiements.
        - **403**: Permission VIEW_PAIEMENTS manquante.
        - **500**: Erreur interne du serveur.
    """
    return await paiement_service.get_all(db, skip, limit)

@router.get(
    "/inscriptions/{inscription_id}/paiements",
    response_model=List[Paiement],
    tags=["Paiements"],
    summary="Lister les paiements d'une inscription",
    description="Récupère tous les paiements associés à une inscription spécifique. Requiert la permission VIEW_PAIEMENTS."
)
async def list_paiements_by_inscription(
    inscription_id: int,
    skip: int = 0,
    limit: int = 100,
    db: AsyncSession = Depends(get_async_db),
    current_user: UtilisateurLight = Depends(require_permissions(["VIEW_PAIEMENTS"]))
):
    """
    Liste les paiements pour une inscription spécifique.

    - **inscription_id**: ID de l'inscription.
    - **skip**: Nombre de paiements à sauter (défaut: 0).
    - **limit**: Nombre maximum de paiements à retourner (défaut: 100).
    - **Réponses**:
        - **200**: Liste des paiements.
        - **404**: Inscription non trouvée.
        - **403**: Permission VIEW_PAIEMENTS manquante.
        - **500**: Erreur interne du serveur.
    """
    return await paiement_service.get_by_inscription(db, inscription_id, skip, limit)

@router.put(
    "/paiements/{paiement_id}",
    response_model=Paiement,
    tags=["Paiements"],
    summary="Mettre à jour un paiement",
    description="Met à jour un paiement spécifique avec mise à jour du statut de paiement de l'inscription. Requiert la permission EDIT_PAIEMENTS."
)
async def update_paiement(
    paiement_id: int,
    paiement_update: PaiementUpdate,
    db: AsyncSession = Depends(get_async_db),
    current_user: UtilisateurLight = Depends(require_permissions(["EDIT_PAIEMENTS"]))
):
    """
    Met à jour un paiement spécifique.

    - **paiement_id**: ID du paiement à mettre à jour.
    - **paiement_update**: Schéma de mise à jour du paiement.
    - **Réponses**:
        - **200**: Paiement mis à jour avec succès.
        - **400**: Montant total dépasse les frais de la formation.
        - **404**: Paiement ou inscription non trouvé.
        - **403**: Permission EDIT_PAIEMENTS manquante.
        - **500**: Erreur interne du serveur.
    """
    return await paiement_service.update(db, paiement_id, paiement_update)

@router.delete(
    "/paiements/{paiement_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    tags=["Paiements"],
    summary="Supprimer un paiement",
    description="Supprime un paiement spécifique et met à jour l'inscription associée. Requiert la permission DELETE_PAIEMENTS."
)
async def delete_paiement(
    paiement_id: int,
    db: AsyncSession = Depends(get_async_db),
    current_user: UtilisateurLight = Depends(require_permissions(["DELETE_PAIEMENTS"]))
):
    """
    Supprime un paiement spécifique.

    - **paiement_id**: ID du paiement à supprimer.
    - **Réponses**:
        - **204**: Paiement supprimé avec succès.
        - **404**: Paiement ou inscription non trouvé.
        - **403**: Permission DELETE_PAIEMENTS manquante.
        - **500**: Erreur interne du serveur.
    """
    await paiement_service.delete(db, paiement_id)

# ============================================================================
# ========================= ROUTES DES MODULES ===============================
# ============================================================================

@router.post(
    "/modules",
    response_model=ModuleLight,
    tags=["Modules"],
    summary="Créer un nouveau module",
    description="Crée un nouveau module pour une formation avec ordre automatique. Requiert la permission CREATE_MODULE."
)
async def create_module(
    module: ModuleCreate,
    db: AsyncSession = Depends(get_async_db),
    current_user: UtilisateurLight = Depends(require_permissions(["CREATE_MODULE"]))
):
    """
    Crée un nouveau module.

    - **module**: Schéma de création du module.
    - **Réponses**:
        - **200**: Module créé avec succès.
        - **404**: Formation non trouvée.
        - **409**: Module avec ces données existe déjà.
        - **403**: Permission CREATE_MODULE manquante.
        - **500**: Erreur interne du serveur.
    """
    return await module_service.create(db, module)

@router.get(
    "/modules/{module_id}",
    response_model=Module,
    tags=["Modules"],
    summary="Récupérer un module par ID",
    description="Récupère les détails d'un module spécifique par son ID. Requiert la permission VIEW_MODULES."
)
async def get_module(
    module_id: int,
    db: AsyncSession = Depends(get_async_db),
    current_user: UtilisateurLight = Depends(require_permissions(["VIEW_MODULES"]))
):
    """
    Récupère un module spécifique.

    - **module_id**: ID du module à récupérer.
    - **Réponses**:
        - **200**: Détails du module.
        - **404**: Module non trouvé.
        - **403**: Permission VIEW_MODULES manquante.
        - **500**: Erreur interne du serveur.
    """
    return await module_service.get(db, module_id)

@router.get(
    "/modules",
    response_model=List[Module],
    tags=["Modules"],
    summary="Lister tous les modules",
    description="Récupère une liste paginée de tous les modules avec leurs relations. Requiert la permission VIEW_MODULES."
)
async def list_modules(
    skip: int = 0,
    limit: int = 100,
    db: AsyncSession = Depends(get_async_db),
    current_user: UtilisateurLight = Depends(require_permissions(["VIEW_MODULES"]))
):
    """
    Liste tous les modules avec pagination.

    - **skip**: Nombre de modules à sauter (défaut: 0).
    - **limit**: Nombre maximum de modules à retourner (défaut: 100).
    - **Réponses**:
        - **200**: Liste des modules.
        - **403**: Permission VIEW_MODULES manquante.
        - **500**: Erreur interne du serveur.
    """
    return await module_service.get_all(db, skip, limit)

@router.put(
    "/modules/{module_id}",
    response_model=Module,
    tags=["Modules"],
    summary="Mettre à jour un module",
    description="Met à jour un module spécifique. Requiert la permission EDIT_MODULES."
)
async def update_module(
    module_id: int,
    module_update: ModuleUpdate,
    db: AsyncSession = Depends(get_async_db),
    current_user: UtilisateurLight = Depends(require_permissions(["EDIT_MODULES"]))
):
    """
    Met à jour un module spécifique.

    - **module_id**: ID du module à mettre à jour.
    - **module_update**: Schéma de mise à jour du module.
    - **Réponses**:
        - **200**: Module mis à jour avec succès.
        - **404**: Module ou formation non trouvé.
        - **403**: Permission EDIT_MODULES manquante.
        - **500**: Erreur interne du serveur.
    """
    return await module_service.update(db, module_id, module_update)

@router.delete(
    "/modules/{module_id}",
    response_model=str,
    tags=["Modules"],
    summary="Supprimer un module",
    description="Supprime un module spécifique et réordonne les modules restants. Requiert la permission DELETE_MODULES."
)
async def delete_module(
    module_id: int,
    db: AsyncSession = Depends(get_async_db),
    current_user: UtilisateurLight = Depends(require_permissions(["DELETE_MODULES"]))
):
    """
    Supprime un module spécifique et réordonne les modules.

    - **module_id**: ID du module à supprimer.
    - **Réponses**:
        - **200**: Module supprimé et ordres réassignés.
        - **404**: Module non trouvé.
        - **403**: Permission DELETE_MODULES manquante.
        - **500**: Erreur interne du serveur.
    """
    return await module_service.delete(db, module_id)

# ============================================================================
# ========================= ROUTES DES RESSOURCES ===========================
# ============================================================================

@router.post(
    "/ressources",
    response_model=RessourceLight,
    tags=["Ressources"],
    summary="Créer une nouvelle ressource",
    description="Crée une nouvelle ressource pédagogique pour un module. Requiert la permission CREATE_RESSOURCE."
)
async def create_ressource(
    ressource: RessourceCreate,
    db: AsyncSession = Depends(get_async_db),
    current_user: UtilisateurLight = Depends(require_permissions(["CREATE_RESSOURCE"]))
):
    """
    Crée une nouvelle ressource.

    - **ressource**: Schéma de création de la ressource.
    - **Réponses**:
        - **200**: Ressource créée avec succès.
        - **404**: Module non trouvé.
        - **403**: Permission CREATE_RESSOURCE manquante.
        - **500**: Erreur interne du serveur.
    """
    return await ressource_service.create(db, ressource)

@router.get(
    "/ressources/{ressource_id}",
    response_model=Ressource,
    tags=["Ressources"],
    summary="Récupérer une ressource par ID",
    description="Récupère les détails d'une ressource spécifique par son ID. Requiert la permission VIEW_RESSOURCES."
)
async def get_ressource(
    ressource_id: int,
    db: AsyncSession = Depends(get_async_db),
    current_user: UtilisateurLight = Depends(require_permissions(["VIEW_RESSOURCES"]))
):
    """
    Récupère une ressource spécifique.

    - **ressource_id**: ID de la ressource à récupérer.
    - **Réponses**:
        - **200**: Détails de la ressource.
        - **404**: Ressource non trouvée.
        - **403**: Permission VIEW_RESSOURCES manquante.
        - **500**: Erreur interne du serveur.
    """
    return await ressource_service.get(db, ressource_id)

@router.get(
    "/ressources",
    response_model=List[Ressource],
    tags=["Ressources"],
    summary="Lister toutes les ressources",
    description="Récupère une liste paginée de toutes les ressources avec leurs relations. Requiert la permission VIEW_RESSOURCES."
)
async def list_ressources(
    skip: int = 0,
    limit: int = 100,
    db: AsyncSession = Depends(get_async_db),
    current_user: UtilisateurLight = Depends(require_permissions(["VIEW_RESSOURCES"]))
):
    """
    Liste toutes les ressources avec pagination.

    - **skip**: Nombre de ressources à sauter (défaut: 0).
    - **limit**: Nombre maximum de ressources à retourner (défaut: 100).
    - **Réponses**:
        - **200**: Liste des ressources.
        - **403**: Permission VIEW_RESSOURCES manquante.
        - **500**: Erreur interne du serveur.
    """
    return await ressource_service.get_all(db, skip, limit)

@router.put(
    "/ressources/{ressource_id}",
    response_model=Ressource,
    tags=["Ressources"],
    summary="Mettre à jour une ressource",
    description="Met à jour une ressource spécifique. Requiert la permission EDIT_RESSOURCES."
)
async def update_ressource(
    ressource_id: int,
    ressource_update: RessourceUpdate,
    db: AsyncSession = Depends(get_async_db),
    current_user: UtilisateurLight = Depends(require_permissions(["EDIT_RESSOURCES"]))
):
    """
    Met à jour une ressource spécifique.

    - **ressource_id**: ID de la ressource à mettre à jour.
    - **ressource_update**: Schéma de mise à jour de la ressource.
    - **Réponses**:
        - **200**: Ressource mise à jour avec succès.
        - **404**: Ressource ou module non trouvé.
        - **403**: Permission EDIT_RESSOURCES manquante.
        - **500**: Erreur interne du serveur.
    """
    return await ressource_service.update(db, ressource_id, ressource_update)

@router.delete(
    "/ressources/{ressource_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    tags=["Ressources"],
    summary="Supprimer une ressource",
    description="Supprime une ressource spécifique par son ID. Requiert la permission DELETE_RESSOURCES."
)
async def delete_ressource(
    ressource_id: int,
    db: AsyncSession = Depends(get_async_db),
    current_user: UtilisateurLight = Depends(require_permissions(["DELETE_RESSOURCES"]))
):
    """
    Supprime une ressource spécifique.

    - **ressource_id**: ID de la ressource à supprimer.
    - **Réponses**:
        - **204**: Ressource supprimée avec succès.
        - **404**: Ressource non trouvée.
        - **403**: Permission DELETE_RESSOURCES manquante.
        - **500**: Erreur interne du serveur.
    """
    await ressource_service.delete(db, ressource_id)

# ============================================================================
# ========================= ROUTES DES CHEFS-D'ŒUVRE ========================
# ============================================================================

@router.post(
    "/chefs-d-oeuvre",
    response_model=ChefDOeuvreLight,
    tags=["Chefs-d'œuvre"],
    summary="Créer un nouveau chef-d'œuvre",
    description="Crée un nouveau chef-d'œuvre pour un utilisateur et un module. Requiert la permission CREATE_CHEF_D_OEUVRE."
)
async def create_chef_d_oeuvre(
    chef_d_oeuvre: ChefDOeuvreCreate,
    db: AsyncSession = Depends(get_async_db),
    current_user: UtilisateurLight = Depends(require_permissions(["CREATE_CHEF_D_OEUVRE"]))
):
    """
    Crée un nouveau chef-d'œuvre.

    - **chef_d_oeuvre**: Schéma de création du chef-d'œuvre.
    - **Réponses**:
        - **200**: Chef-d'œuvre créé avec succès.
        - **404**: Utilisateur ou module non trouvé.
        - **403**: Permission CREATE_CHEF_D_OEUVRE manquante.
        - **500**: Erreur interne du serveur.
    """
    return await chef_d_oeuvre_service.create(db, chef_d_oeuvre)

@router.get(
    "/chefs-d-oeuvre/{chef_d_oeuvre_id}",
    response_model=ChefDOeuvre,
    tags=["Chefs-d'œuvre"],
    summary="Récupérer un chef-d'œuvre par ID",
    description="Récupère les détails d'un chef-d'œuvre spécifique par son ID. Requiert la permission VIEW_CHEFS_D_OEUVRE."
)
async def get_chef_d_oeuvre(
    chef_d_oeuvre_id: int,
    db: AsyncSession = Depends(get_async_db),
    current_user: UtilisateurLight = Depends(require_permissions(["VIEW_CHEFS_D_OEUVRE"]))
):
    """
    Récupère un chef-d'œuvre spécifique.

    - **chef_d_oeuvre_id**: ID du chef-d'œuvre à récupérer.
    - **Réponses**:
        - **200**: Détails du chef-d'œuvre.
        - **404**: Chef-d'œuvre non trouvé.
        - **403**: Permission VIEW_CHEFS_D_OEUVRE manquante.
        - **500**: Erreur interne du serveur.
    """
    return await chef_d_oeuvre_service.get(db, chef_d_oeuvre_id)

@router.get(
    "/chefs-d-oeuvre",
    response_model=List[ChefDOeuvre],
    tags=["Chefs-d'œuvre"],
    summary="Lister tous les chefs-d'œuvre",
    description="Récupère une liste paginée de tous les chefs-d'œuvre avec leurs relations. Requiert la permission VIEW_CHEFS_D_OEUVRE."
)
async def list_chefs_d_oeuvre(
    skip: int = 0,
    limit: int = 100,
    db: AsyncSession = Depends(get_async_db),
    current_user: UtilisateurLight = Depends(require_permissions(["VIEW_CHEFS_D_OEUVRE"]))
):
    """
    Liste tous les chefs-d'œuvre avec pagination.

    - **skip**: Nombre de chefs-d'œuvre à sauter (défaut: 0).
    - **limit**: Nombre maximum de chefs-d'œuvre à retourner (défaut: 100).
    - **Réponses**:
        - **200**: Liste des chefs-d'œuvre.
        - **403**: Permission VIEW_CHEFS_D_OEUVRE manquante.
        - **500**: Erreur interne du serveur.
    """
    return await chef_d_oeuvre_service.get_all(db, skip, limit)

@router.put(
    "/chefs-d-oeuvre/{chef_d_oeuvre_id}",
    response_model=ChefDOeuvre,
    tags=["Chefs-d'œuvre"],
    summary="Mettre à jour un chef-d'œuvre",
    description="Met à jour un chef-d'œuvre spécifique. Requiert la permission EDIT_CHEFS_D_OEUVRE."
)
async def update_chef_d_oeuvre(
    chef_d_oeuvre_id: int,
    chef_d_oeuvre_update: ChefDOeuvreUpdate,
    db: AsyncSession = Depends(get_async_db),
    current_user: UtilisateurLight = Depends(require_permissions(["EDIT_CHEFS_D_OEUVRE"]))
):
    """
    Met à jour un chef-d'œuvre spécifique.

    - **chef_d_oeuvre_id**: ID du chef-d'œuvre à mettre à jour.
    - **chef_d_oeuvre_update**: Schéma de mise à jour du chef-d'œuvre.
    - **Réponses**:
        - **200**: Chef-d'œuvre mis à jour avec succès.
        - **404**: Chef-d'œuvre, utilisateur ou module non trouvé.
        - **403**: Permission EDIT_CHEFS_D_OEUVRE manquante.
        - **500**: Erreur interne du serveur.
    """
    return await chef_d_oeuvre_service.update(db, chef_d_oeuvre_id, chef_d_oeuvre_update)

@router.delete(
    "/chefs-d-oeuvre/{chef_d_oeuvre_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    tags=["Chefs-d'œuvre"],
    summary="Supprimer un chef-d'œuvre",
    description="Supprime un chef-d'œuvre spécifique par son ID. Requiert la permission DELETE_CHEFS_D_OEUVRE."
)
async def delete_chef_d_oeuvre(
    chef_d_oeuvre_id: int,
    db: AsyncSession = Depends(get_async_db),
    current_user: UtilisateurLight = Depends(require_permissions(["DELETE_CHEFS_D_OEUVRE"]))
):
    """
    Supprime un chef-d'œuvre spécifique.

    - **chef_d_oeuvre_id**: ID du chef-d'œuvre à supprimer.
    - **Réponses**:
        - **204**: Chef-d'œuvre supprimé avec succès.
        - **404**: Chef-d'œuvre non trouvé.
        - **403**: Permission DELETE_CHEFS_D_OEUVRE manquante.
        - **500**: Erreur interne du serveur.
    """
    await chef_d_oeuvre_service.delete(db, chef_d_oeuvre_id)

# ============================================================================
# ========================= ROUTES DES PROJETS COLLECTIFS ===================
# ============================================================================

@router.post(
    "/projets-collectifs",
    response_model=ProjetCollectifLight,
    tags=["Projets Collectifs"],
    summary="Créer un nouveau projet collectif",
    description="Crée un nouveau projet collectif avec ses membres. Requiert la permission CREATE_PROJET_COLLECTIF."
)
async def create_projet_collectif(
    projet_collectif: ProjetCollectifCreate,
    db: AsyncSession = Depends(get_async_db),
    current_user: UtilisateurLight = Depends(require_permissions(["CREATE_PROJET_COLLECTIF"]))
):
    """
    Crée un nouveau projet collectif.

    - **projet_collectif**: Schéma de création du projet collectif.
    - **Réponses**:
        - **200**: Projet collectif créé avec succès.
        - **404**: Formation ou membres non trouvés.
        - **403**: Permission CREATE_PROJET_COLLECTIF manquante.
        - **500**: Erreur interne du serveur.
    """
    return await projet_collectif_service.create(db, projet_collectif)

@router.get(
    "/projets-collectifs/{projet_collectif_id}",
    response_model=ProjetCollectif,
    tags=["Projets Collectifs"],
    summary="Récupérer un projet collectif par ID",
    description="Récupère les détails d'un projet collectif spécifique par son ID. Requiert la permission VIEW_PROJETS_COLLECTIFS."
)
async def get_projet_collectif(
    projet_collectif_id: int,
    db: AsyncSession = Depends(get_async_db),
    current_user: UtilisateurLight = Depends(require_permissions(["VIEW_PROJETS_COLLECTIFS"]))
):
    """
    Récupère un projet collectif spécifique.

    - **projet_collectif_id**: ID du projet collectif à récupérer.
    - **Réponses**:
        - **200**: Détails du projet collectif.
        - **404**: Projet collectif non trouvé.
        - **403**: Permission VIEW_PROJETS_COLLECTIFS manquante.
        - **500**: Erreur interne du serveur.
    """
    return await projet_collectif_service.get(db, projet_collectif_id)

@router.get(
    "/projets-collectifs",
    response_model=List[ProjetCollectif],
    tags=["Projets Collectifs"],
    summary="Lister tous les projets collectifs",
    description="Récupère une liste paginée de tous les projets collectifs avec leurs relations. Requiert la permission VIEW_PROJETS_COLLECTIFS."
)
async def list_projets_collectifs(
    skip: int = 0,
    limit: int = 100,
    db: AsyncSession = Depends(get_async_db),
    current_user: UtilisateurLight = Depends(require_permissions(["VIEW_PROJETS_COLLECTIFS"]))
):
    """
    Liste tous les projets collectifs avec pagination.

    - **skip**: Nombre de projets collectifs à sauter (défaut: 0).
    - **limit**: Nombre maximum de projets collectifs à retourner (défaut: 100).
    - **Réponses**:
        - **200**: Liste des projets collectifs.
        - **403**: Permission VIEW_PROJETS_COLLECTIFS manquante.
        - **500**: Erreur interne du serveur.
    """
    return await projet_collectif_service.get_all(db, skip, limit)

@router.put(
    "/projets-collectifs/{projet_collectif_id}",
    response_model=ProjetCollectif,
    tags=["Projets Collectifs"],
    summary="Mettre à jour un projet collectif",
    description="Met à jour un projet collectif spécifique avec ses membres. Requiert la permission EDIT_PROJETS_COLLECTIFS."
)
async def update_projet_collectif(
    projet_collectif_id: int,
    projet_collectif_update: ProjetCollectifUpdate,
    db: AsyncSession = Depends(get_async_db),
    current_user: UtilisateurLight = Depends(require_permissions(["EDIT_PROJETS_COLLECTIFS"]))
):
    """
    Met à jour un projet collectif spécifique.

    - **projet_collectif_id**: ID du projet collectif à mettre à jour.
    - **projet_collectif_update**: Schéma de mise à jour du projet collectif.
    - **Réponses**:
        - **200**: Projet collectif mis à jour avec succès.
        - **404**: Projet collectif, formation ou membres non trouvés.
        - **403**: Permission EDIT_PROJETS_COLLECTIFS manquante.
        - **500**: Erreur interne du serveur.
    """
    return await projet_collectif_service.update(db, projet_collectif_id, projet_collectif_update)

@router.delete(
    "/projets-collectifs/{projet_collectif_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    tags=["Projets Collectifs"],
    summary="Supprimer un projet collectif",
    description="Supprime un projet collectif spécifique par son ID. Requiert la permission DELETE_PROJETS_COLLECTIFS."
)
async def delete_projet_collectif(
    projet_collectif_id: int,
    db: AsyncSession = Depends(get_async_db),
    current_user: UtilisateurLight = Depends(require_permissions(["DELETE_PROJETS_COLLECTIFS"]))
):
    """
    Supprime un projet collectif spécifique.

    - **projet_collectif_id**: ID du projet collectif à supprimer.
    - **Réponses**:
        - **204**: Projet collectif supprimé avec succès.
        - **404**: Projet collectif non trouvé.
        - **403**: Permission DELETE_PROJETS_COLLECTIFS manquante.
        - **500**: Erreur interne du serveur.
    """
    await projet_collectif_service.delete(db, projet_collectif_id)

@router.post(
    "/projets-collectifs/{projet_collectif_id}/membres/{utilisateur_id}",
    response_model=ProjetCollectif,
    tags=["Projets Collectifs"],
    summary="Ajouter un membre à un projet collectif",
    description="Ajoute un utilisateur à un projet collectif. Requiert la permission ADD_MEMBRE_PROJET."
)
async def add_membre_projet(
    projet_collectif_id: int,
    utilisateur_id: int,
    db: AsyncSession = Depends(get_async_db),
    current_user: UtilisateurLight = Depends(require_permissions(["ADD_MEMBRE_PROJET"]))
):
    """
    Ajoute un membre à un projet collectif.

    - **projet_collectif_id**: ID du projet collectif.
    - **utilisateur_id**: ID de l'utilisateur à ajouter.
    - **Réponses**:
        - **200**: Membre ajouté avec succès.
        - **404**: Projet collectif ou utilisateur non trouvé.
        - **403**: Permission ADD_MEMBRE_PROJET manquante.
        - **500**: Erreur interne du serveur.
    """
    return await projet_collectif_service.add_membre(db, projet_collectif_id, utilisateur_id)

@router.delete(
    "/projets-collectifs/{projet_collectif_id}/membres/{utilisateur_id}",
    response_model=ProjetCollectif,
    tags=["Projets Collectifs"],
    summary="Supprimer un membre d'un projet collectif",
    description="Supprime un utilisateur d'un projet collectif. Requiert la permission REMOVE_MEMBRE_PROJET."
)
async def remove_membre_projet(
    projet_collectif_id: int,
    utilisateur_id: int,
    db: AsyncSession = Depends(get_async_db),
    current_user: UtilisateurLight = Depends(require_permissions(["REMOVE_MEMBRE_PROJET"]))
):
    """
    Supprime un membre d'un projet collectif.

    - **projet_collectif_id**: ID du projet collectif.
    - **utilisateur_id**: ID de l'utilisateur à supprimer.
    - **Réponses**:
        - **200**: Membre supprimé avec succès.
        - **404**: Projet collectif ou utilisateur non trouvé.
        - **403**: Permission REMOVE_MEMBRE_PROJET manquante.
        - **500**: Erreur interne du serveur.
    """
    return await projet_collectif_service.remove_membre(db, projet_collectif_id, utilisateur_id)

# ============================================================================
# ========================= ROUTES DES ÉVALUATIONS ==========================
# ============================================================================

@router.post(
    "/evaluations",
    response_model=EvaluationLight,
    tags=["Évaluations"],
    summary="Créer une nouvelle évaluation",
    description="Crée une nouvelle évaluation pour un module. Requiert la permission CREATE_EVALUATION."
)
async def create_evaluation(
    evaluation: EvaluationCreate,
    db: AsyncSession = Depends(get_async_db),
    current_user: UtilisateurLight = Depends(require_permissions(["CREATE_EVALUATION"]))
):
    """
    Crée une nouvelle évaluation.

    - **evaluation**: Schéma de création de l'évaluation.
    - **Réponses**:
        - **200**: Évaluation créée avec succès.
        - **404**: Module non trouvé.
        - **403**: Permission CREATE_EVALUATION manquante.
        - **500**: Erreur interne du serveur.
    """
    return await evaluation_service.create(db, evaluation)

@router.get(
    "/evaluations/{evaluation_id}",
    response_model=Evaluation,
    tags=["Évaluations"],
    summary="Récupérer une évaluation par ID",
    description="Récupère les détails d'une évaluation spécifique par son ID. Requiert la permission VIEW_EVALUATIONS."
)
async def get_evaluation(
    evaluation_id: int,
    db: AsyncSession = Depends(get_async_db),
    current_user: UtilisateurLight = Depends(require_permissions(["VIEW_EVALUATIONS"]))
):
    """
    Récupère une évaluation spécifique.

    - **evaluation_id**: ID de l'évaluation à récupérer.
    - **Réponses**:
        - **200**: Détails de l'évaluation.
        - **404**: Évaluation non trouvée.
        - **403**: Permission VIEW_EVALUATIONS manquante.
        - **500**: Erreur interne du serveur.
    """
    return await evaluation_service.get(db, evaluation_id)

@router.get(
    "/evaluations",
    response_model=List[Evaluation],
    tags=["Évaluations"],
    summary="Lister toutes les évaluations",
    description="Récupère une liste paginée de toutes les évaluations avec leurs relations. Requiert la permission VIEW_EVALUATIONS."
)
async def list_evaluations(
    skip: int = 0,
    limit: int = 100,
    db: AsyncSession = Depends(get_async_db),
    current_user: UtilisateurLight = Depends(require_permissions(["VIEW_EVALUATIONS"]))
):
    """
    Liste toutes les évaluations avec pagination.

    - **skip**: Nombre d'évaluations à sauter (défaut: 0).
    - **limit**: Nombre maximum d'évaluations à retourner (défaut: 100).
    - **Réponses**:
        - **200**: Liste des évaluations.
        - **403**: Permission VIEW_EVALUATIONS manquante.
        - **500**: Erreur interne du serveur.
    """
    return await evaluation_service.get_all(db, skip, limit)

@router.put(
    "/evaluations/{evaluation_id}",
    response_model=Evaluation,
    tags=["Évaluations"],
    summary="Mettre à jour une évaluation",
    description="Met à jour une évaluation spécifique. Requiert la permission EDIT_EVALUATIONS."
)
async def update_evaluation(
    evaluation_id: int,
    evaluation_update: EvaluationUpdate,
    db: AsyncSession = Depends(get_async_db),
    current_user: UtilisateurLight = Depends(require_permissions(["EDIT_EVALUATIONS"]))
):
    """
    Met à jour une évaluation spécifique.

    - **evaluation_id**: ID de l'évaluation à mettre à jour.
    - **evaluation_update**: Schéma de mise à jour de l'évaluation.
    - **Réponses**:
        - **200**: Évaluation mise à jour avec succès.
        - **404**: Évaluation ou module non trouvé.
        - **403**: Permission EDIT_EVALUATIONS manquante.
        - **500**: Erreur interne du serveur.
    """
    return await evaluation_service.update(db, evaluation_id, evaluation_update)

@router.delete(
    "/evaluations/{evaluation_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    tags=["Évaluations"],
    summary="Supprimer une évaluation",
    description="Supprime une évaluation spécifique par son ID. Requiert la permission DELETE_EVALUATIONS."
)
async def delete_evaluation(
    evaluation_id: int,
    db: AsyncSession = Depends(get_async_db),
    current_user: UtilisateurLight = Depends(require_permissions(["DELETE_EVALUATIONS"]))
):
    """
    Supprime une évaluation spécifique.

    - **evaluation_id**: ID de l'évaluation à supprimer.
    - **Réponses**:
        - **204**: Évaluation supprimée avec succès.
        - **404**: Évaluation non trouvée.
        - **403**: Permission DELETE_EVALUATIONS manquante.
        - **500**: Erreur interne du serveur.
    """
    await evaluation_service.delete(db, evaluation_id)

# ============================================================================
# ========================= ROUTES DES QUESTIONS ============================
# ============================================================================

@router.post(
    "/questions",
    response_model=QuestionLight,
    tags=["Questions"],
    summary="Créer une nouvelle question",
    description="Crée une nouvelle question pour une évaluation avec ses propositions. Requiert la permission CREATE_QUESTION."
)
async def create_question(
    question: QuestionCreate,
    db: AsyncSession = Depends(get_async_db),
    current_user: UtilisateurLight = Depends(require_permissions(["CREATE_QUESTION"]))
):
    """
    Crée une nouvelle question.

    - **question**: Schéma de création de la question.
    - **Réponses**:
        - **200**: Question créée avec succès.
        - **404**: Évaluation non trouvée.
        - **403**: Permission CREATE_QUESTION manquante.
        - **500**: Erreur interne du serveur.
    """
    return await question_service.create(db, question)

@router.get(
    "/questions/{question_id}",
    response_model=Question,
    tags=["Questions"],
    summary="Récupérer une question par ID",
    description="Récupère les détails d'une question spécifique par son ID. Requiert la permission VIEW_QUESTIONS."
)
async def get_question(
    question_id: int,
    db: AsyncSession = Depends(get_async_db),
    current_user: UtilisateurLight = Depends(require_permissions(["VIEW_QUESTIONS"]))
):
    """
    Récupère une question spécifique.

    - **question_id**: ID de la question à récupérer.
    - **Réponses**:
        - **200**: Détails de la question.
        - **404**: Question non trouvée.
        - **403**: Permission VIEW_QUESTIONS manquante.
        - **500**: Erreur interne du serveur.
    """
    return await question_service.get(db, question_id)

@router.get(
    "/questions",
    response_model=List[Question],
    tags=["Questions"],
    summary="Lister toutes les questions",
    description="Récupère une liste paginée de toutes les questions avec leurs relations. Requiert la permission VIEW_QUESTIONS."
)
async def list_questions(
    skip: int = 0,
    limit: int = 100,
    db: AsyncSession = Depends(get_async_db),
    current_user: UtilisateurLight = Depends(require_permissions(["VIEW_QUESTIONS"]))
):
    """
    Liste toutes les questions avec pagination.

    - **skip**: Nombre de questions à sauter (défaut: 0).
    - **limit**: Nombre maximum de questions à retourner (défaut: 100).
    - **Réponses**:
        - **200**: Liste des questions.
        - **403**: Permission VIEW_QUESTIONS manquante.
        - **500**: Erreur interne du serveur.
    """
    return await question_service.get_all(db, skip, limit)

@router.put(
    "/questions/{question_id}",
    response_model=Question,
    tags=["Questions"],
    summary="Mettre à jour une question",
    description="Met à jour une question spécifique avec ses propositions. Requiert la permission EDIT_QUESTIONS."
)
async def update_question(
    question_id: int,
    question_update: QuestionUpdate,
    db: AsyncSession = Depends(get_async_db),
    current_user: UtilisateurLight = Depends(require_permissions(["EDIT_QUESTIONS"]))
):
    """
    Met à jour une question spécifique.

    - **question_id**: ID de la question à mettre à jour.
    - **question_update**: Schéma de mise à jour de la question.
    - **Réponses**:
        - **200**: Question mise à jour avec succès.
        - **404**: Question ou évaluation non trouvée.
        - **403**: Permission EDIT_QUESTIONS manquante.
        - **500**: Erreur interne du serveur.
    """
    return await question_service.update(db, question_id, question_update)

@router.delete(
    "/questions/{question_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    tags=["Questions"],
    summary="Supprimer une question",
    description="Supprime une question spécifique par son ID. Requiert la permission DELETE_QUESTIONS."
)
async def delete_question(
    question_id: int,
    db: AsyncSession = Depends(get_async_db),
    current_user: UtilisateurLight = Depends(require_permissions(["DELETE_QUESTIONS"]))
):
    """
    Supprime une question spécifique.

    - **question_id**: ID de la question à supprimer.
    - **Réponses**:
        - **204**: Question supprimée avec succès.
        - **404**: Question non trouvée.
        - **403**: Permission DELETE_QUESTIONS manquante.
        - **500**: Erreur interne du serveur.
    """
    await question_service.delete(db, question_id)
    
    # ============================================================================
# ========================= ROUTES DES PROPOSITIONS ==========================
# ============================================================================

@router.post(
    "/propositions",
    response_model=PropositionLight,
    tags=["Propositions"],
    summary="Créer une nouvelle proposition",
    description="Crée une nouvelle proposition pour une question. Requiert la permission CREATE_PROPOSITION."
)
async def create_proposition(
    proposition: PropositionCreate,
    db: AsyncSession = Depends(get_async_db),
    current_user: UtilisateurLight = Depends(require_permissions(["CREATE_PROPOSITION"]))
):
    """
    Crée une nouvelle proposition.

    - **proposition**: Schéma de création de la proposition.
    - **Réponses**:
        - **200**: Proposition créée avec succès.
        - **404**: Question non trouvée.
        - **403**: Permission CREATE_PROPOSITION manquante.
        - **500**: Erreur interne du serveur.
    """
    return await proposition_service.create(db, proposition)

@router.get(
    "/propositions/{proposition_id}",
    response_model=Proposition,
    tags=["Propositions"],
    summary="Récupérer une proposition par ID",
    description="Récupère les détails d'une proposition spécifique par son ID. Requiert la permission VIEW_PROPOSITIONS."
)
async def get_proposition(
    proposition_id: int,
    db: AsyncSession = Depends(get_async_db),
    current_user: UtilisateurLight = Depends(require_permissions(["VIEW_PROPOSITIONS"]))
):
    """
    Récupère une proposition spécifique.

    - **proposition_id**: ID de la proposition à récupérer.
    - **Réponses**:
        - **200**: Détails de la proposition.
        - **404**: Proposition non trouvée.
        - **403**: Permission VIEW_PROPOSITIONS manquante.
        - **500**: Erreur interne du serveur.
    """
    return await proposition_service.get(db, proposition_id)

@router.get(
    "/propositions",
    response_model=List[Proposition],
    tags=["Propositions"],
    summary="Lister toutes les propositions",
    description="Récupère une liste paginée de toutes les propositions avec leurs relations. Requiert la permission VIEW_PROPOSITIONS."
)
async def list_propositions(
    skip: int = 0,
    limit: int = 100,
    db: AsyncSession = Depends(get_async_db),
    current_user: UtilisateurLight = Depends(require_permissions(["VIEW_PROPOSITIONS"]))
):
    """
    Liste toutes les propositions avec pagination.

    - **skip**: Nombre de propositions à sauter (défaut: 0).
    - **limit**: Nombre maximum de propositions à retourner (défaut: 100).
    - **Réponses**:
        - **200**: Liste des propositions.
        - **403**: Permission VIEW_PROPOSITIONS manquante.
        - **500**: Erreur interne du serveur.
    """
    return await proposition_service.get_all(db, skip, limit)

@router.put(
    "/propositions/{proposition_id}",
    response_model=Proposition,
    tags=["Propositions"],
    summary="Mettre à jour une proposition",
    description="Met à jour une proposition spécifique. Requiert la permission EDIT_PROPOSITIONS."
)
async def update_proposition(
    proposition_id: int,
    proposition_update: PropositionUpdate,
    db: AsyncSession = Depends(get_async_db),
    current_user: UtilisateurLight = Depends(require_permissions(["EDIT_PROPOSITIONS"]))
):
    """
    Met à jour une proposition spécifique.

    - **proposition_id**: ID de la proposition à mettre à jour.
    - **proposition_update**: Schéma de mise à jour de la proposition.
    - **Réponses**:
        - **200**: Proposition mise à jour avec succès.
        - **404**: Proposition ou question non trouvée.
        - **403**: Permission EDIT_PROPOSITIONS manquante.
        - **500**: Erreur interne du serveur.
    """
    return await proposition_service.update(db, proposition_id, proposition_update)

@router.delete(
    "/propositions/{proposition_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    tags=["Propositions"],
    summary="Supprimer une proposition",
    description="Supprime une proposition spécifique par son ID. Requiert la permission DELETE_PROPOSITIONS."
)
async def delete_proposition(
    proposition_id: int,
    db: AsyncSession = Depends(get_async_db),
    current_user: UtilisateurLight = Depends(require_permissions(["DELETE_PROPOSITIONS"]))
):
    """
    Supprime une proposition spécifique.

    - **proposition_id**: ID de la proposition à supprimer.
    - **Réponses**:
        - **204**: Proposition supprimée avec succès.
        - **404**: Proposition non trouvée.
        - **403**: Permission DELETE_PROPOSITIONS manquante.
        - **500**: Erreur interne du serveur.
    """
    await proposition_service.delete(db, proposition_id)
    
    
    # ============================================================================
# ========================= ROUTES DES RÉSULTATS D'ÉVALUATION ===============
# ============================================================================

@router.post(
    "/resultats-evaluations",
    response_model=ResultatEvaluationLight,
    tags=["Résultats Évaluations"],
    summary="Créer un nouveau résultat d'évaluation",
    description="Crée un nouveau résultat d'évaluation pour un utilisateur et une évaluation. Requiert la permission CREATE_RESULTAT_EVALUATION."
)
async def create_resultat_evaluation(
    resultat_evaluation: ResultatEvaluationCreate,
    db: AsyncSession = Depends(get_async_db),
    current_user: UtilisateurLight = Depends(require_permissions(["CREATE_RESULTAT_EVALUATION"]))
):
    """
    Crée un nouveau résultat d'évaluation.

    - **resultat_evaluation**: Schéma de création du résultat d'évaluation.
    - **Réponses**:
        - **200**: Résultat d'évaluation créé avec succès.
        - **404**: Évaluation ou utilisateur non trouvé.
        - **403**: Permission CREATE_RESULTAT_EVALUATION manquante.
        - **500**: Erreur interne du serveur.
    """
    return await resultat_evaluation_service.create(db, resultat_evaluation)

@router.get(
    "/resultats-evaluations/{resultat_evaluation_id}",
    response_model=ResultatEvaluation,
    tags=["Résultats Évaluations"],
    summary="Récupérer un résultat d'évaluation par ID",
    description="Récupère les détails d'un résultat d'évaluation spécifique par son ID. Requiert la permission VIEW_RESULTATS_EVALUATIONS."
)
async def get_resultat_evaluation(
    resultat_evaluation_id: int,
    db: AsyncSession = Depends(get_async_db),
    current_user: UtilisateurLight = Depends(require_permissions(["VIEW_RESULTATS_EVALUATIONS"]))
):
    """
    Récupère un résultat d'évaluation spécifique.

    - **resultat_evaluation_id**: ID du résultat d'évaluation à récupérer.
    - **Réponses**:
        - **200**: Détails du résultat d'évaluation.
        - **404**: Résultat d'évaluation non trouvé.
        - **403**: Permission VIEW_RESULTATS_EVALUATIONS manquante.
        - **500**: Erreur interne du serveur.
    """
    return await resultat_evaluation_service.get(db, resultat_evaluation_id)

@router.get(
    "/resultats-evaluations",
    response_model=List[ResultatEvaluation],
    tags=["Résultats Évaluations"],
    summary="Lister tous les résultats d'évaluation",
    description="Récupère une liste paginée de tous les résultats d'évaluation avec leurs relations. Requiert la permission VIEW_RESULTATS_EVALUATIONS."
)
async def list_resultats_evaluations(
    skip: int = 0,
    limit: int = 100,
    db: AsyncSession = Depends(get_async_db),
    current_user: UtilisateurLight = Depends(require_permissions(["VIEW_RESULTATS_EVALUATIONS"]))
):
    """
    Liste tous les résultats d'évaluation avec pagination.

    - **skip**: Nombre de résultats à sauter (défaut: 0).
    - **limit**: Nombre maximum de résultats à retourner (défaut: 100).
    - **Réponses**:
        - **200**: Liste des résultats d'évaluation.
        - **403**: Permission VIEW_RESULTATS_EVALUATIONS manquante.
        - **500**: Erreur interne du serveur.
    """
    return await resultat_evaluation_service.get_all(db, skip, limit)

@router.put(
    "/resultats-evaluations/{resultat_evaluation_id}",
    response_model=ResultatEvaluation,
    tags=["Résultats Évaluations"],
    summary="Mettre à jour un résultat d'évaluation",
    description="Met à jour un résultat d'évaluation spécifique. Requiert la permission EDIT_RESULTATS_EVALUATIONS."
)
async def update_resultat_evaluation(
    resultat_evaluation_id: int,
    resultat_evaluation_update: ResultatEvaluationUpdate,
    db: AsyncSession = Depends(get_async_db),
    current_user: UtilisateurLight = Depends(require_permissions(["EDIT_RESULTATS_EVALUATIONS"]))
):
    """
    Met à jour un résultat d'évaluation spécifique.

    - **resultat_evaluation_id**: ID du résultat d'évaluation à mettre à jour.
    - **resultat_evaluation_update**: Schéma de mise à jour du résultat d'évaluation.
    - **Réponses**:
        - **200**: Résultat d'évaluation mis à jour avec succès.
        - **404**: Résultat d'évaluation, évaluation ou utilisateur non trouvé.
        - **403**: Permission EDIT_RESULTATS_EVALUATIONS manquante.
        - **500**: Erreur interne du serveur.
    """
    return await resultat_evaluation_service.update(db, resultat_evaluation_id, resultat_evaluation_update)

@router.delete(
    "/resultats-evaluations/{resultat_evaluation_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    tags=["Résultats Évaluations"],
    summary="Supprimer un résultat d'évaluation",
    description="Supprime un résultat d'évaluation spécifique par son ID. Requiert la permission DELETE_RESULTATS_EVALUATIONS."
)
async def delete_resultat_evaluation(
    resultat_evaluation_id: int,
    db: AsyncSession = Depends(get_async_db),
    current_user: UtilisateurLight = Depends(require_permissions(["DELETE_RESULTATS_EVALUATIONS"]))
):
    """
    Supprime un résultat d'évaluation spécifique.

    - **resultat_evaluation_id**: ID du résultat d'évaluation à supprimer.
    - **Réponses**:
        - **204**: Résultat d'évaluation supprimé avec succès.
        - **404**: Résultat d'évaluation non trouvé.
        - **403**: Permission DELETE_RESULTATS_EVALUATIONS manquante.
        - **500**: Erreur interne du serveur.
    """
    await resultat_evaluation_service.delete(db, resultat_evaluation_id)
    
    
    # ============================================================================
# ========================= ROUTES DES GÉNOTYPES INDIVIDUELS ================
# ============================================================================

@router.post(
    "/genotypes-individuels",
    response_model=GenotypeIndividuelLight,
    tags=["Génotypes Individuels"],
    summary="Créer un nouveau génotype individuel",
    description="Crée un nouveau génotype individuel pour un utilisateur. Requiert la permission CREATE_GENOTYPE_INDIVIDUEL."
)
async def create_genotype_individuel(
    genotype_individuel: GenotypeIndividuelCreate,
    db: AsyncSession = Depends(get_async_db),
    current_user: UtilisateurLight = Depends(require_permissions(["CREATE_GENOTYPE_INDIVIDUEL"]))
):
    """
    Crée un nouveau génotype individuel.

    - **genotype_individuel**: Schéma de création du génotype individuel.
    - **Réponses**:
        - **200**: Génotype individuel créé avec succès.
        - **404**: Utilisateur non trouvé.
        - **403**: Permission CREATE_GENOTYPE_INDIVIDUEL manquante.
        - **500**: Erreur interne du serveur.
    """
    return await genotype_individuel_service.create(db, genotype_individuel)

@router.get(
    "/genotypes-individuels/{genotype_individuel_id}",
    response_model=GenotypeIndividuel,
    tags=["Génotypes Individuels"],
    summary="Récupérer un génotype individuel par ID",
    description="Récupère les détails d'un génotype individuel spécifique par son ID. Requiert la permission VIEW_GENOTYPES_INDIVIDUELS."
)
async def get_genotype_individuel(
    genotype_individuel_id: int,
    db: AsyncSession = Depends(get_async_db),
    current_user: UtilisateurLight = Depends(require_permissions(["VIEW_GENOTYPES_INDIVIDUELS"]))
):
    """
    Récupère un génotype individuel spécifique.

    - **genotype_individuel_id**: ID du génotype individuel à récupérer.
    - **Réponses**:
        - **200**: Détails du génotype individuel.
        - **404**: Génotype individuel non trouvé.
        - **403**: Permission VIEW_GENOTYPES_INDIVIDUELS manquante.
        - **500**: Erreur interne du serveur.
    """
    return await genotype_individuel_service.get(db, genotype_individuel_id)

@router.get(
    "/genotypes-individuels",
    response_model=List[GenotypeIndividuel],
    tags=["Génotypes Individuels"],
    summary="Lister tous les génotypes individuels",
    description="Récupère une liste paginée de tous les génotypes individuels avec leurs relations. Requiert la permission VIEW_GENOTYPES_INDIVIDUELS."
)
async def list_genotypes_individuels(
    skip: int = 0,
    limit: int = 100,
    db: AsyncSession = Depends(get_async_db),
    current_user: UtilisateurLight = Depends(require_permissions(["VIEW_GENOTYPES_INDIVIDUELS"]))
):
    """
    Liste tous les génotypes individuels avec pagination.

    - **skip**: Nombre de génotypes individuels à sauter (défaut: 0).
    - **limit**: Nombre maximum de génotypes individuels à retourner (défaut: 100).
    - **Réponses**:
        - **200**: Liste des génotypes individuels.
        - **403**: Permission VIEW_GENOTYPES_INDIVIDUELS manquante.
        - **500**: Erreur interne du serveur.
    """
    return await genotype_individuel_service.get_all(db, skip, limit)

@router.put(
    "/genotypes-individuels/{genotype_individuel_id}",
    response_model=GenotypeIndividuel,
    tags=["Génotypes Individuels"],
    summary="Mettre à jour un génotype individuel",
    description="Met à jour un génotype individuel spécifique. Requiert la permission EDIT_GENOTYPES_INDIVIDUELS."
)
async def update_genotype_individuel(
    genotype_individuel_id: int,
    genotype_individuel_update: GenotypeIndividuelUpdate,
    db: AsyncSession = Depends(get_async_db),
    current_user: UtilisateurLight = Depends(require_permissions(["EDIT_GENOTYPES_INDIVIDUELS"]))
):
    """
    Met à jour un génotype individuel spécifique.

    - **genotype_individuel_id**: ID du génotype individuel à mettre à jour.
    - **genotype_individuel_update**: Schéma de mise à jour du génotype individuel.
    - **Réponses**:
        - **200**: Génotype individuel mis à jour avec succès.
        - **404**: Génotype individuel ou utilisateur non trouvé.
        - **403**: Permission EDIT_GENOTYPES_INDIVIDUELS manquante.
        - **500**: Erreur interne du serveur.
    """
    return await genotype_individuel_service.update(db, genotype_individuel_id, genotype_individuel_update)

@router.delete(
    "/genotypes-individuels/{genotype_individuel_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    tags=["Génotypes Individuels"],
    summary="Supprimer un génotype individuel",
    description="Supprime un génotype individuel spécifique par son ID. Requiert la permission DELETE_GENOTYPES_INDIVIDUELS."
)
async def delete_genotype_individuel(
    genotype_individuel_id: int,
    db: AsyncSession = Depends(get_async_db),
    current_user: UtilisateurLight = Depends(require_permissions(["DELETE_GENOTYPES_INDIVIDUELS"]))
):
    """
    Supprime un génotype individuel spécifique.

    - **genotype_individuel_id**: ID du génotype individuel à supprimer.
    - **Réponses**:
        - **204**: Génotype individuel supprimé avec succès.
        - **404**: Génotype individuel non trouvé.
        - **403**: Permission DELETE_GENOTYPES_INDIVIDUELS manquante.
        - **500**: Erreur interne du serveur.
    """
    await genotype_individuel_service.delete(db, genotype_individuel_id)
    
    
    # ============================================================================
# ========================= ROUTES DES ASCENDANCES GÉNOTYPES ===============
# ============================================================================

@router.post(
    "/ascendances-genotypes",
    response_model=AscendanceGenotypeLight,
    tags=["Ascendances Génotypes"],
    summary="Créer une nouvelle ascendance génotype",
    description="Crée une nouvelle ascendance génotype pour un génotype individuel. Requiert la permission CREATE_ASCENDANCE_GENOTYPE."
)
async def create_ascendance_genotype(
    ascendance_genotype: AscendanceGenotypeCreate,
    db: AsyncSession = Depends(get_async_db),
    current_user: UtilisateurLight = Depends(require_permissions(["CREATE_ASCENDANCE_GENOTYPE"]))
):
    """
    Crée une nouvelle ascendance génotype.

    - **ascendance_genotype**: Schéma de création de l'ascendance génotype.
    - **Réponses**:
        - **200**: Ascendance génotype créée avec succès.
        - **404**: Génotype individuel non trouvé.
        - **403**: Permission CREATE_ASCENDANCE_GENOTYPE manquante.
        - **500**: Erreur interne du serveur.
    """
    return await ascendance_genotype_service.create(db, ascendance_genotype)

@router.get(
    "/ascendances-genotypes/{ascendance_genotype_id}",
    response_model=AscendanceGenotype,
    tags=["Ascendances Génotypes"],
    summary="Récupérer une ascendance génotype par ID",
    description="Récupère les détails d'une ascendance génotype spécifique par son ID. Requiert la permission VIEW_ASCENDANCES_GENOTYPES."
)
async def get_ascendance_genotype(
    ascendance_genotype_id: int,
    db: AsyncSession = Depends(get_async_db),
    current_user: UtilisateurLight = Depends(require_permissions(["VIEW_ASCENDANCES_GENOTYPES"]))
):
    """
    Récupère une ascendance génotype spécifique.

    - **ascendance_genotype_id**: ID de l'ascendance génotype à récupérer.
    - **Réponses**:
        - **200**: Détails de l'ascendance génotype.
        - **404**: Ascendance génotype non trouvée.
        - **403**: Permission VIEW_ASCENDANCES_GENOTYPES manquante.
        - **500**: Erreur interne du serveur.
    """
    return await ascendance_genotype_service.get(db, ascendance_genotype_id)

@router.get(
    "/ascendances-genotypes",
    response_model=List[AscendanceGenotype],
    tags=["Ascendances Génotypes"],
    summary="Lister toutes les ascendances génotypes",
    description="Récupère une liste paginée de toutes les ascendances génotypes avec leurs relations. Requiert la permission VIEW_ASCENDANCES_GENOTYPES."
)
async def list_ascendances_genotypes(
    skip: int = 0,
    limit: int = 100,
    db: AsyncSession = Depends(get_async_db),
    current_user: UtilisateurLight = Depends(require_permissions(["VIEW_ASCENDANCES_GENOTYPES"]))
):
    """
    Liste toutes les ascendances génotypes avec pagination.

    - **skip**: Nombre d'ascendances génotypes à sauter (défaut: 0).
    - **limit**: Nombre maximum d'ascendances génotypes à retourner (défaut: 100).
    - **Réponses**:
        - **200**: Liste des ascendances génotypes.
        - **403**: Permission VIEW_ASCENDANCES_GENOTYPES manquante.
        - **500**: Erreur interne du serveur.
    """
    return await ascendance_genotype_service.get_all(db, skip, limit)

@router.put(
    "/ascendances-genotypes/{ascendance_genotype_id}",
    response_model=AscendanceGenotype,
    tags=["Ascendances Génotypes"],
    summary="Mettre à jour une ascendance génotype",
    description="Met à jour une ascendance génotype spécifique. Requiert la permission EDIT_ASCENDANCES_GENOTYPES."
)
async def update_ascendance_genotype(
    ascendance_genotype_id: int,
    ascendance_genotype_update: AscendanceGenotypeUpdate,
    db: AsyncSession = Depends(get_async_db),
    current_user: UtilisateurLight = Depends(require_permissions(["EDIT_ASCENDANCES_GENOTYPES"]))
):
    """
    Met à jour une ascendance génotype spécifique.

    - **ascendance_genotype_id**: ID de l'ascendance génotype à mettre à jour.
    - **ascendance_genotype_update**: Schéma de mise à jour de l'ascendance génotype.
    - **Réponses**:
        - **200**: Ascendance génotype mise à jour avec succès.
        - **404**: Ascendance génotype ou génotype individuel non trouvé.
        - **403**: Permission EDIT_ASCENDANCES_GENOTYPES manquante.
        - **500**: Erreur interne du serveur.
    """
    return await ascendance_genotype_service.update(db, ascendance_genotype_id, ascendance_genotype_update)

@router.delete(
    "/ascendances-genotypes/{ascendance_genotype_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    tags=["Ascendances Génotypes"],
    summary="Supprimer une ascendance génotype",
    description="Supprime une ascendance génotype spécifique par son ID. Requiert la permission DELETE_ASCENDANCES_GENOTYPES."
)
async def delete_ascendance_genotype(
    ascendance_genotype_id: int,
    db: AsyncSession = Depends(get_async_db),
    current_user: UtilisateurLight = Depends(require_permissions(["DELETE_ASCENDANCES_GENOTYPES"]))
):
    """
    Supprime une ascendance génotype spécifique.

    - **ascendance_genotype_id**: ID de l'ascendance génotype à supprimer.
    - **Réponses**:
        - **204**: Ascendance génotype supprimée avec succès.
        - **404**: Ascendance génotype non trouvée.
        - **403**: Permission DELETE_ASCENDANCES_GENOTYPES manquante.
        - **500**: Erreur interne du serveur.
    """
    await ascendance_genotype_service.delete(db, ascendance_genotype_id)
    
    
    
    # ============================================================================
# ========================= ROUTES DES SANTÉ GÉNOTYPES ======================
# ============================================================================

@router.post(
    "/sante-genotypes",
    response_model=SanteGenotypeLight,
    tags=["Santé Génotypes"],
    summary="Créer une nouvelle santé génotype",
    description="Crée une nouvelle santé génotype pour un génotype individuel. Requiert la permission CREATE_SANTE_GENOTYPE."
)
async def create_sante_genotype(
    sante_genotype: SanteGenotypeCreate,
    db: AsyncSession = Depends(get_async_db),
    current_user: UtilisateurLight = Depends(require_permissions(["CREATE_SANTE_GENOTYPE"]))
):
    """
    Crée une nouvelle santé génotype.

    - **sante_genotype**: Schéma de création de la santé génotype.
    - **Réponses**:
        - **200**: Santé génotype créée avec succès.
        - **404**: Génotype individuel non trouvé.
        - **403**: Permission CREATE_SANTE_GENOTYPE manquante.
        - **500**: Erreur interne du serveur.
    """
    return await sante_genotype_service.create(db, sante_genotype)

@router.get(
    "/sante-genotypes/{sante_genotype_id}",
    response_model=SanteGenotype,
    tags=["Santé Génotypes"],
    summary="Récupérer une santé génotype par ID",
    description="Récupère les détails d'une santé génotype spécifique par son ID. Requiert la permission VIEW_SANTE_GENOTYPES."
)
async def get_sante_genotype(
    sante_genotype_id: int,
    db: AsyncSession = Depends(get_async_db),
    current_user: UtilisateurLight = Depends(require_permissions(["VIEW_SANTE_GENOTYPES"]))
):
    """
    Récupère une santé génotype spécifique.

    - **sante_genotype_id**: ID de la santé génotype à récupérer.
    - **Réponses**:
        - **200**: Détails de la santé génotype.
        - **404**: Santé génotype non trouvée.
        - **403**: Permission VIEW_SANTE_GENOTYPES manquante.
        - **500**: Erreur interne du serveur.
    """
    return await sante_genotype_service.get(db, sante_genotype_id)

@router.get(
    "/sante-genotypes",
    response_model=List[SanteGenotype],
    tags=["Santé Génotypes"],
    summary="Lister toutes les santés génotypes",
    description="Récupère une liste paginée de toutes les santés génotypes avec leurs relations. Requiert la permission VIEW_SANTE_GENOTYPES."
)
async def list_sante_genotypes(
    skip: int = 0,
    limit: int = 100,
    db: AsyncSession = Depends(get_async_db),
    current_user: UtilisateurLight = Depends(require_permissions(["VIEW_SANTE_GENOTYPES"]))
):
    """
    Liste toutes les santés génotypes avec pagination.

    - **skip**: Nombre de santés génotypes à sauter (défaut: 0).
    - **limit**: Nombre maximum de santés génotypes à retourner (défaut: 100).
    - **Réponses**:
        - **200**: Liste des santés génotypes.
        - **403**: Permission VIEW_SANTE_GENOTYPES manquante.
        - **500**: Erreur interne du serveur.
    """
    return await sante_genotype_service.get_all(db, skip, limit)

@router.put(
    "/sante-genotypes/{sante_genotype_id}",
    response_model=SanteGenotype,
    tags=["Santé Génotypes"],
    summary="Mettre à jour une santé génotype",
    description="Met à jour une santé génotype spécifique. Requiert la permission EDIT_SANTE_GENOTYPES."
)
async def update_sante_genotype(
    sante_genotype_id: int,
    sante_genotype_update: SanteGenotypeUpdate,
    db: AsyncSession = Depends(get_async_db),
    current_user: UtilisateurLight = Depends(require_permissions(["EDIT_SANTE_GENOTYPES"]))
):
    """
    Met à jour une santé génotype spécifique.

    - **sante_genotype_id**: ID de la santé génotype à mettre à jour.
    - **sante_genotype_update**: Schéma de mise à jour de la santé génotype.
    - **Réponses**:
        - **200**: Santé génotype mise à jour avec succès.
        - **404**: Santé génotype ou génotype individuel non trouvé.
        - **403**: Permission EDIT_SANTE_GENOTYPES manquante.
        - **500**: Erreur interne du serveur.
    """
    return await sante_genotype_service.update(db, sante_genotype_id, sante_genotype_update)

@router.delete(
    "/sante-genotypes/{sante_genotype_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    tags=["Santé Génotypes"],
    summary="Supprimer une santé génotype",
    description="Supprime une santé génotype spécifique par son ID. Requiert la permission DELETE_SANTE_GENOTYPES."
)
async def delete_sante_genotype(
    sante_genotype_id: int,
    db: AsyncSession = Depends(get_async_db),
    current_user: UtilisateurLight = Depends(require_permissions(["DELETE_SANTE_GENOTYPES"]))
):
    """
    Supprime une santé génotype spécifique.

    - **sante_genotype_id**: ID de la santé génotype à supprimer.
    - **Réponses**:
        - **204**: Santé génotype supprimée avec succès.
        - **404**: Santé génotype non trouvée.
        - **403**: Permission DELETE_SANTE_GENOTYPES manquante.
        - **500**: Erreur interne du serveur.
    """
    await sante_genotype_service.delete(db, sante_genotype_id)
    
    
    # ============================================================================
# ========================= ROUTES DES ÉDUCATION GÉNOTYPES ==================
# ============================================================================

@router.post(
    "/education-genotypes",
    response_model=EducationGenotypeLight,
    tags=["Éducation Génotypes"],
    summary="Créer une nouvelle éducation génotype",
    description="Crée une nouvelle éducation génotype pour un génotype individuel. Requiert la permission CREATE_EDUCATION_GENOTYPE."
)
async def create_education_genotype(
    education_genotype: EducationGenotypeCreate,
    db: AsyncSession = Depends(get_async_db),
    current_user: UtilisateurLight = Depends(require_permissions(["CREATE_EDUCATION_GENOTYPE"]))
):
    """
    Crée une nouvelle éducation génotype.

    - **education_genotype**: Schéma de création de l'éducation génotype.
    - **Réponses**:
        - **200**: Éducation génotype créée avec succès.
        - **404**: Génotype individuel non trouvé.
        - **403**: Permission CREATE_EDUCATION_GENOTYPE manquante.
        - **500**: Erreur interne du serveur.
    """
    return await education_genotype_service.create(db, education_genotype)

@router.get(
    "/education-genotypes/{education_genotype_id}",
    response_model=EducationGenotype,
    tags=["Éducation Génotypes"],
    summary="Récupérer une éducation génotype par ID",
    description="Récupère les détails d'une éducation génotype spécifique par son ID. Requiert la permission VIEW_EDUCATION_GENOTYPES."
)
async def get_education_genotype(
    education_genotype_id: int,
    db: AsyncSession = Depends(get_async_db),
    current_user: UtilisateurLight = Depends(require_permissions(["VIEW_EDUCATION_GENOTYPES"]))
):
    """
    Récupère une éducation génotype spécifique.

    - **education_genotype_id**: ID de l'éducation génotype à récupérer.
    - **Réponses**:
        - **200**: Détails de l'éducation génotype.
        - **404**: Éducation génotype non trouvée.
        - **403**: Permission VIEW_EDUCATION_GENOTYPES manquante.
        - **500**: Erreur interne du serveur.
    """
    return await education_genotype_service.get(db, education_genotype_id)

@router.get(
    "/education-genotypes",
    response_model=List[EducationGenotype],
    tags=["Éducation Génotypes"],
    summary="Lister toutes les éducations génotypes",
    description="Récupère une liste paginée de toutes les éducations génotypes avec leurs relations. Requiert la permission VIEW_EDUCATION_GENOTYPES."
)
async def list_education_genotypes(
    skip: int = 0,
    limit: int = 100,
    db: AsyncSession = Depends(get_async_db),
    current_user: UtilisateurLight = Depends(require_permissions(["VIEW_EDUCATION_GENOTYPES"]))
):
    """
    Liste toutes les éducations génotypes avec pagination.

    - **skip**: Nombre d'éducations génotypes à sauter (défaut: 0).
    - **limit**: Nombre maximum d'éducations génotypes à retourner (défaut: 100).
    - **Réponses**:
        - **200**: Liste des éducations génotypes.
        - **403**: Permission VIEW_EDUCATION_GENOTYPES manquante.
        - **500**: Erreur interne du serveur.
    """
    return await education_genotype_service.get_all(db, skip, limit)

@router.put(
    "/education-genotypes/{education_genotype_id}",
    response_model=EducationGenotype,
    tags=["Éducation Génotypes"],
    summary="Mettre à jour une éducation génotype",
    description="Met à jour une éducation génotype spécifique. Requiert la permission EDIT_EDUCATION_GENOTYPES."
)
async def update_education_genotype(
    education_genotype_id: int,
    education_genotype_update: EducationGenotypeUpdate,
    db: AsyncSession = Depends(get_async_db),
    current_user: UtilisateurLight = Depends(require_permissions(["EDIT_EDUCATION_GENOTYPES"]))
):
    """
    Met à jour une éducation génotype spécifique.

    - **education_genotype_id**: ID de l'éducation génotype à mettre à jour.
    - **education_genotype_update**: Schéma de mise à jour de l'éducation génotype.
    - **Réponses**:
        - **200**: Éducation génotype mise à jour avec succès.
        - **404**: Éducation génotype ou génotype individuel non trouvé.
        - **403**: Permission EDIT_EDUCATION_GENOTYPES manquante.
        - **500**: Erreur interne du serveur.
    """
    return await education_genotype_service.update(db, education_genotype_id, education_genotype_update)

@router.delete(
    "/education-genotypes/{education_genotype_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    tags=["Éducation Génotypes"],
    summary="Supprimer une éducation génotype",
    description="Supprime une éducation génotype spécifique par son ID. Requiert la permission DELETE_EDUCATION_GENOTYPES."
)
async def delete_education_genotype(
    education_genotype_id: int,
    db: AsyncSession = Depends(get_async_db),
    current_user: UtilisateurLight = Depends(require_permissions(["DELETE_EDUCATION_GENOTYPES"]))
):
    """
    Supprime une éducation génotype spécifique.

    - **education_genotype_id**: ID de l'éducation génotype à supprimer.
    - **Réponses**:
        - **204**: Éducation génotype supprimée avec succès.
        - **404**: Éducation génotype non trouvée.
        - **403**: Permission DELETE_EDUCATION_GENOTYPES manquante.
        - **500**: Erreur interne du serveur.
    """
    await education_genotype_service.delete(db, education_genotype_id)
    
    # ============================================================================
# ========================= ROUTES DES PLANS D'INTERVENTION ================
# ============================================================================

@router.post(
    "/plans-intervention",
    response_model=PlanInterventionIndividualiseLight,
    tags=["Plans d'Intervention"],
    summary="Créer un nouveau plan d'intervention individualisé",
    description="Crée un nouveau plan d'intervention individualisé pour un utilisateur. Requiert la permission CREATE_PLAN_INTERVENTION."
)
async def create_plan_intervention(
    plan_intervention: PlanInterventionIndividualiseCreate,
    db: AsyncSession = Depends(get_async_db),
    current_user: UtilisateurLight = Depends(require_permissions(["CREATE_PLAN_INTERVENTION"]))
):
    """
    Crée un nouveau plan d'intervention individualisé.

    - **plan_intervention**: Schéma de création du plan d'intervention.
    - **Réponses**:
        - **200**: Plan d'intervention créé avec succès.
        - **404**: Utilisateur non trouvé.
        - **403**: Permission CREATE_PLAN_INTERVENTION manquante.
        - **500**: Erreur interne du serveur.
    """
    return await plan_intervention_service.create(db, plan_intervention)

@router.get(
    "/plans-intervention/{plan_intervention_id}",
    response_model=PlanInterventionIndividualise,
    tags=["Plans d'Intervention"],
    summary="Récupérer un plan d'intervention par ID",
    description="Récupère les détails d'un plan d'intervention spécifique par son ID. Requiert la permission VIEW_PLANS_INTERVENTION."
)
async def get_plan_intervention(
    plan_intervention_id: int,
    db: AsyncSession = Depends(get_async_db),
    current_user: UtilisateurLight = Depends(require_permissions(["VIEW_PLANS_INTERVENTION"]))
):
    """
    Récupère un plan d'intervention spécifique.

    - **plan_intervention_id**: ID du plan d'intervention à récupérer.
    - **Réponses**:
        - **200**: Détails du plan d'intervention.
        - **404**: Plan d'intervention non trouvé.
        - **403**: Permission VIEW_PLANS_INTERVENTION manquante.
        - **500**: Erreur interne du serveur.
    """
    return await plan_intervention_service.get(db, plan_intervention_id)

@router.get(
    "/plans-intervention",
    response_model=List[PlanInterventionIndividualise],
    tags=["Plans d'Intervention"],
    summary="Lister tous les plans d'intervention",
    description="Récupère une liste paginée de tous les plans d'intervention avec leurs relations. Requiert la permission VIEW_PLANS_INTERVENTION."
)
async def list_plans_intervention(
    skip: int = 0,
    limit: int = 100,
    db: AsyncSession = Depends(get_async_db),
    current_user: UtilisateurLight = Depends(require_permissions(["VIEW_PLANS_INTERVENTION"]))
):
    """
    Liste tous les plans d'intervention avec pagination.

    - **skip**: Nombre de plans d'intervention à sauter (défaut: 0).
    - **limit**: Nombre maximum de plans d'intervention à retourner (défaut: 100).
    - **Réponses**:
        - **200**: Liste des plans d'intervention.
        - **403**: Permission VIEW_PLANS_INTERVENTION manquante.
        - **500**: Erreur interne du serveur.
    """
    return await plan_intervention_service.get_all(db, skip, limit)

@router.put(
    "/plans-intervention/{plan_intervention_id}",
    response_model=PlanInterventionIndividualise,
    tags=["Plans d'Intervention"],
    summary="Mettre à jour un plan d'intervention",
    description="Met à jour un plan d'intervention spécifique. Requiert la permission EDIT_PLANS_INTERVENTION."
)
async def update_plan_intervention(
    plan_intervention_id: int,
    plan_intervention_update: PlanInterventionIndividualiseUpdate,
    db: AsyncSession = Depends(get_async_db),
    current_user: UtilisateurLight = Depends(require_permissions(["EDIT_PLANS_INTERVENTION"]))
):
    """
    Met à jour un plan d'intervention spécifique.

    - **plan_intervention_id**: ID du plan d'intervention à mettre à jour.
    - **plan_intervention_update**: Schéma de mise à jour du plan d'intervention.
    - **Réponses**:
        - **200**: Plan d'intervention mis à jour avec succès.
        - **404**: Plan d'intervention ou utilisateur non trouvé.
        - **403**: Permission EDIT_PLANS_INTERVENTION manquante.
        - **500**: Erreur interne du serveur.
    """
    return await plan_intervention_service.update(db, plan_intervention_id, plan_intervention_update)

@router.delete(
    "/plans-intervention/{plan_intervention_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    tags=["Plans d'Intervention"],
    summary="Supprimer un plan d'intervention",
    description="Supprime un plan d'intervention spécifique par son ID. Requiert la permission DELETE_PLANS_INTERVENTION."
)
async def delete_plan_intervention(
    plan_intervention_id: int,
    db: AsyncSession = Depends(get_async_db),
    current_user: UtilisateurLight = Depends(require_permissions(["DELETE_PLANS_INTERVENTION"]))
):
    """
    Supprime un plan d'intervention spécifique.

    - **plan_intervention_id**: ID du plan d'intervention à supprimer.
    - **Réponses**:
        - **204**: Plan d'intervention supprimé avec succès.
        - **404**: Plan d'intervention non trouvé.
        - **403**: Permission DELETE_PLANS_INTERVENTION manquante.
        - **500**: Erreur interne du serveur.
    """
    await plan_intervention_service.delete(db, plan_intervention_id)
    
    # ============================================================================
# ========================= ROUTES DES ACCRÉDITATIONS ======================
# ============================================================================

@router.post(
    "/accreditations",
    response_model=AccreditationLight,
    tags=["Accréditations"],
    summary="Créer une nouvelle accréditation",
    description="Crée une nouvelle accréditation pour un utilisateur et une formation. Requiert la permission CREATE_ACCREDITATION."
)
async def create_accreditation(
    accreditation: AccreditationCreate,
    db: AsyncSession = Depends(get_async_db),
    current_user: UtilisateurLight = Depends(require_permissions(["CREATE_ACCREDITATION"]))
):
    """
    Crée une nouvelle accréditation.

    - **accreditation**: Schéma de création de l'accréditation.
    - **Réponses**:
        - **200**: Accréditation créée avec succès.
        - **404**: Utilisateur ou formation non trouvé.
        - **403**: Permission CREATE_ACCREDITATION manquante.
        - **500**: Erreur interne du serveur.
    """
    return await accreditation_service.create(db, accreditation)

@router.get(
    "/accreditations/{accreditation_id}",
    response_model=Accreditation,
    tags=["Accréditations"],
    summary="Récupérer une accréditation par ID",
    description="Récupère les détails d'une accréditation spécifique par son ID. Requiert la permission VIEW_ACCREDITATIONS."
)
async def get_accreditation(
    accreditation_id: int,
    db: AsyncSession = Depends(get_async_db),
    current_user: UtilisateurLight = Depends(require_permissions(["VIEW_ACCREDITATIONS"]))
):
    """
    Récupère une accréditation spécifique.

    - **accreditation_id**: ID de l'accréditation à récupérer.
    - **Réponses**:
        - **200**: Détails de l'accréditation.
        - **404**: Accréditation non trouvée.
        - **403**: Permission VIEW_ACCREDITATIONS manquante.
        - **500**: Erreur interne du serveur.
    """
    return await accreditation_service.get(db, accreditation_id)

@router.get(
    "/accreditations",
    response_model=List[Accreditation],
    tags=["Accréditations"],
    summary="Lister toutes les accréditations",
    description="Récupère une liste paginée de toutes les accréditations avec leurs relations. Requiert la permission VIEW_ACCREDITATIONS."
)
async def list_accreditations(
    skip: int = 0,
    limit: int = 100,
    db: AsyncSession = Depends(get_async_db),
    current_user: UtilisateurLight = Depends(require_permissions(["VIEW_ACCREDITATIONS"]))
):
    """
    Liste toutes les accréditations avec pagination.

    - **skip**: Nombre d'accréditations à sauter (défaut: 0).
    - **limit**: Nombre maximum d'accréditations à retourner (défaut: 100).
    - **Réponses**:
        - **200**: Liste des accréditations.
        - **403**: Permission VIEW_ACCREDITATIONS manquante.
        - **500**: Erreur interne du serveur.
    """
    return await accreditation_service.get_all(db, skip, limit)

@router.put(
    "/accreditations/{accreditation_id}",
    response_model=Accreditation,
    tags=["Accréditations"],
    summary="Mettre à jour une accréditation",
    description="Met à jour une accréditation spécifique. Requiert la permission EDIT_ACCREDITATIONS."
)
async def update_accreditation(
    accreditation_id: int,
    accreditation_update: AccreditationUpdate,
    db: AsyncSession = Depends(get_async_db),
    current_user: UtilisateurLight = Depends(require_permissions(["EDIT_ACCREDITATIONS"]))
):
    """
    Met à jour une accréditation spécifique.

    - **accreditation_id**: ID de l'accréditation à mettre à jour.
    - **accreditation_update**: Schéma de mise à jour de l'accréditation.
    - **Réponses**:
        - **200**: Accréditation mise à jour avec succès.
        - **404**: Accréditation, utilisateur ou formation non trouvé.
        - **403**: Permission EDIT_ACCREDITATIONS manquante.
        - **500**: Erreur interne du serveur.
    """
    return await accreditation_service.update(db, accreditation_id, accreditation_update)

@router.delete(
    "/accreditations/{accreditation_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    tags=["Accréditations"],
    summary="Supprimer une accréditation",
    description="Supprime une accréditation spécifique par son ID. Requiert la permission DELETE_ACCREDITATIONS."
)
async def delete_accreditation(
    accreditation_id: int,
    db: AsyncSession = Depends(get_async_db),
    current_user: UtilisateurLight = Depends(require_permissions(["DELETE_ACCREDITATIONS"]))
):
    """
    Supprime une accréditation spécifique.

    - **accreditation_id**: ID de l'accréditation à supprimer.
    - **Réponses**:
        - **204**: Accréditation supprimée avec succès.
        - **404**: Accréditation non trouvée.
        - **403**: Permission DELETE_ACCREDITATIONS manquante.
        - **500**: Erreur interne du serveur.
    """
    await accreditation_service.delete(db, accreditation_id)
    
    # ============================================================================
# ========================= ROUTES DES ACTUALITÉS ==========================
# ============================================================================

@router.post(
    "/actualites",
    response_model=ActualiteLight,
    tags=["Actualités"],
    summary="Créer une nouvelle actualité",
    description="Crée une nouvelle actualité. Requiert la permission CREATE_ACTUALITE."
)
async def create_actualite(
    actualite: ActualiteCreate,
    db: AsyncSession = Depends(get_async_db),
    current_user: UtilisateurLight = Depends(require_permissions(["CREATE_ACTUALITE"]))
):
    """
    Crée une nouvelle actualité.

    - **actualite**: Schéma de création de l'actualité.
    - **Réponses**:
        - **200**: Actualité créée avec succès.
        - **403**: Permission CREATE_ACTUALITE manquante.
        - **500**: Erreur interne du serveur.
    """
    return await actualite_service.create(db, actualite)

@router.get(
    "/actualites/{actualite_id}",
    response_model=Actualite,
    tags=["Actualités"],
    summary="Récupérer une actualité par ID",
    description="Récupère les détails d'une actualité spécifique par son ID. Requiert la permission VIEW_ACTUALITES."
)
async def get_actualite(
    actualite_id: int,
    db: AsyncSession = Depends(get_async_db),
    current_user: UtilisateurLight = Depends(require_permissions(["VIEW_ACTUALITES"]))
):
    """
    Récupère une actualité spécifique.

    - **actualite_id**: ID de l'actualité à récupérer.
    - **Réponses**:
        - **200**: Détails de l'actualité.
        - **404**: Actualité non trouvée.
        - **403**: Permission VIEW_ACTUALITES manquante.
        - **500**: Erreur interne du serveur.
    """
    return await actualite_service.get(db, actualite_id)

@router.get(
    "/actualites",
    response_model=List[Actualite],
    tags=["Actualités"],
    summary="Lister toutes les actualités",
    description="Récupère une liste paginée de toutes les actualités avec leurs relations. Requiert la permission VIEW_ACTUALITES."
)
async def list_actualites(
    skip: int = 0,
    limit: int = 100,
    db: AsyncSession = Depends(get_async_db),
    current_user: UtilisateurLight = Depends(require_permissions(["VIEW_ACTUALITES"]))
):
    """
    Liste toutes les actualités avec pagination.

    - **skip**: Nombre d'actualités à sauter (défaut: 0).
    - **limit**: Nombre maximum d'actualités à retourner (défaut: 100).
    - **Réponses**:
        - **200**: Liste des actualités.
        - **403**: Permission VIEW_ACTUALITES manquante.
        - **500**: Erreur interne du serveur.
    """
    return await actualite_service.get_all(db, skip, limit)

@router.put(
    "/actualites/{actualite_id}",
    response_model=Actualite,
    tags=["Actualités"],
    summary="Mettre à jour une actualité",
    description="Met à jour une actualité spécifique. Requiert la permission EDIT_ACTUALITES."
)
async def update_actualite(
    actualite_id: int,
    actualite_update: ActualiteUpdate,
    db: AsyncSession = Depends(get_async_db),
    current_user: UtilisateurLight = Depends(require_permissions(["EDIT_ACTUALITES"]))
):
    """
    Met à jour une actualité spécifique.

    - **actualite_id**: ID de l'actualité à mettre à jour.
    - **actualite_update**: Schéma de mise à jour de l'actualité.
    - **Réponses**:
        - **200**: Actualité mise à jour avec succès.
        - **404**: Actualité non trouvée.
        - **403**: Permission EDIT_ACTUALITES manquante.
        - **500**: Erreur interne du serveur.
    """
    return await actualite_service.update(db, actualite_id, actualite_update)

@router.delete(
    "/actualites/{actualite_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    tags=["Actualités"],
    summary="Supprimer une actualité",
    description="Supprime une actualité spécifique par son ID. Requiert la permission DELETE_ACTUALITES."
)
async def delete_actualite(
    actualite_id: int,
    db: AsyncSession = Depends(get_async_db),
    current_user: UtilisateurLight = Depends(require_permissions(["DELETE_ACTUALITES"]))
):
    """
    Supprime une actualité spécifique.

    - **actualite_id**: ID de l'actualité à supprimer.
    - **Réponses**:
        - **204**: Actualité supprimée avec succès.
        - **404**: Actualité non trouvée.
        - **403**: Permission DELETE_ACTUALITES manquante.
        - **500**: Erreur interne du serveur.
    """
    await actualite_service.delete(db, actualite_id)
    
    
    # ============================================================================
# ========================= ROUTES DES FICHIERS =============================
# ============================================================================

@router.post(
    "/files",
    response_model=str,
    tags=["Fichiers"],
    summary="Téléverser un fichier",
    description="Téléverse un fichier pour un utilisateur (image de profil, document, etc.). Requiert la permission UPLOAD_FILE."
)
async def upload_file(
    file: UploadFile = File(...),
    file_type: FileTypeEnum = FileTypeEnum.OTHER,
    db: AsyncSession = Depends(get_async_db),
    current_user: UtilisateurLight = Depends(require_permissions(["UPLOAD_FILE"]))
):
    """
    Téléverse un fichier.

    - **file**: Fichier à téléverser.
    - **file_type**: Type de fichier (par exemple, IMAGE_PROFILE, DOCUMENT, etc.).
    - **Réponses**:
        - **200**: URL ou identifiant du fichier téléversé.
        - **400**: Type de fichier non supporté ou fichier invalide.
        - **403**: Permission UPLOAD_FILE manquante.
        - **500**: Erreur interne du serveur.
    """
    return await file_service.upload(db, file, current_user.id, file_type)

@router.get(
    "/files/{file_id}",
    response_model=str,
    tags=["Fichiers"],
    summary="Récupérer un fichier par ID",
    description="Récupère l'URL ou les détails d'un fichier spécifique par son ID. Requiert la permission VIEW_FILES."
)
async def get_file(
    file_id: int,
    db: AsyncSession = Depends(get_async_db),
    current_user: UtilisateurLight = Depends(require_permissions(["VIEW_FILES"]))
):
    """
    Récupère un fichier spécifique.

    - **file_id**: ID du fichier à récupérer.
    - **Réponses**:
        - **200**: URL ou détails du fichier.
        - **404**: Fichier non trouvé.
        - **403**: Permission VIEW_FILES manquante.
        - **500**: Erreur interne du serveur.
    """
    return await file_service.get(db, file_id)

@router.get(
    "/files",
    response_model=List[str],
    tags=["Fichiers"],
    summary="Lister tous les fichiers",
    description="Récupère une liste paginée de tous les fichiers avec leurs détails. Requiert la permission VIEW_FILES."
)
async def list_files(
    skip: int = 0,
    limit: int = 100,
    db: AsyncSession = Depends(get_async_db),
    current_user: UtilisateurLight = Depends(require_permissions(["VIEW_FILES"]))
):
    """
    Liste tous les fichiers avec pagination.

    - **skip**: Nombre de fichiers à sauter (défaut: 0).
    - **limit**: Nombre maximum de fichiers à retourner (défaut: 100).
    - **Réponses**:
        - **200**: Liste des fichiers.
        - **403**: Permission VIEW_FILES manquante.
        - **500**: Erreur interne du serveur.
    """
    return await file_service.get_all(db, skip, limit)

@router.delete(
    "/files/{file_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    tags=["Fichiers"],
    summary="Supprimer un fichier",
    description="Supprime un fichier spécifique par son ID. Requiert la permission DELETE_FILES."
)
async def delete_file(
    file_id: int,
    db: AsyncSession = Depends(get_async_db),
    current_user: UtilisateurLight = Depends(require_permissions(["DELETE_FILES"]))
):
    """
    Supprime un fichier spécifique.

    - **file_id**: ID du fichier à supprimer.
    - **Réponses**:
        - **204**: Fichier supprimé avec succès.
        - **404**: Fichier non trouvé.
        - **403**: Permission DELETE_FILES manquante.
        - **500**: Erreur interne du serveur.
    """
    await file_service.delete(db, file_id)
    
    
    