from fastapi import APIRouter, Depends, HTTPException, File, UploadFile, status, Request
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
    Utilisateur, UtilisateurLight, UtilisateurCreate, UtilisateurUpdate, loginSchema,
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
    Actualite, ActualiteLight, ActualiteCreate, ActualiteUpdate,
    ResetPasswordRequestSchema, ChangePasswordSchema
)
from src.util.helper.enum import FileTypeEnum, StatutCompteEnum
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
@router.put(
    "/users/{user_id}/status",
    response_model=UtilisateurLight,
    tags=["Utilisateurs"],
    summary="Changer le statut d'un utilisateur",
    description="Modifie le statut d'un utilisateur spécifique (actif, inactif, supprimer)."
)
async def change_user_status(user_id: int, statut: StatutCompteEnum, db: AsyncSession = Depends(get_async_db)):
    """
    Change le statut d'un utilisateur.

    - **user_id**: ID de l'utilisateur à modifier.
    - **statut**: Nouveau statut (actif, inactif, supprimer).
    - **Réponses**:
        - **200**: Statut mis à jour avec succès (ex. `{"id": 1, "nom": "Doe", "statut": "actif"}`).
        - **404**: Utilisateur non trouvé.
        - **400**: Statut invalide.
        - **500**: Erreur interne du serveur.
    """
    return await utilisateur_service.change_user_status(db, user_id, statut)

@router.post(
    "/login",
    response_model=dict,
    tags=["Utilisateurs"],
    summary="Connexion d'un utilisateur",
    description="Authentifie un utilisateur avec son email et mot de passe, retourne un token JWT."
)
async def login(form_data: loginSchema, db: AsyncSession = Depends(get_async_db)):
    """
    Authentifie un utilisateur et génère un token JWT.

    - **form_data**: Contient l'email et le mot de passe de l'utilisateur.
    - **Réponses**:
        - **200**: Token JWT généré avec succès (ex. `{"access_token": "jwt_token", "token_type": "bearer"}`).
        - **401**: Email ou mot de passe incorrect.
        - **500**: Erreur interne du serveur.
    """
    return await utilisateur_service.login(db, form_data)

@router.get(
    "/users/me",
    response_model=UtilisateurLight,
    tags=["Utilisateurs"],
    summary="Récupérer l'utilisateur connecté",
    description="Retourne les informations de l'utilisateur connecté, incluant ses permissions (directes et via rôle)."
)
async def read_users_me(token: str, db: AsyncSession = Depends(get_async_db)):
    """
    Récupère les informations de l'utilisateur connecté à partir du token JWT.

    - **token**: Token JWT fourni dans l'en-tête Authorization.
    - **Réponses**:
        - **200**: Informations de l'utilisateur connecté (ex. `{"id": 1, "nom": "Doe", "prenom": "John", ...}`).
        - **401**: Token invalide ou expiré.
        - **500**: Erreur interne du serveur.
    """
    return await utilisateur_service.get_current_user(db, token)

@router.post(
    "/users",
    response_model=UtilisateurLight,
    tags=["Utilisateurs"],
    summary="Créer un nouvel utilisateur",
    description="Crée un nouvel utilisateur avec un mot de passe généré automatiquement."
)
async def create_user(user: UtilisateurCreate, db: AsyncSession = Depends(get_async_db)):
    """
    Crée un nouvel utilisateur avec validation de l'unicité de l'email.

    - **user**: Schéma de création de l'utilisateur (nom, email, rôle, etc.).
    - **Réponses**:
        - **200**: Utilisateur créé avec succès (ex. `{"id": 1, "nom": "Doe", "email": "john.doe@example.com", ...}`).
        - **400**: Données invalides.
        - **409**: Email déjà utilisé.
        - **500**: Erreur interne du serveur.
    """
    return await utilisateur_service.create(db, user)

@router.get(
    "/users/{user_id}",
    response_model=Utilisateur,
    tags=["Utilisateurs"],
    summary="Récupérer un utilisateur par ID",
    description="Récupère les détails d'un utilisateur spécifique par son ID, incluant ses relations."
)
async def get_user(user_id: int, db: AsyncSession = Depends(get_async_db)):
    """
    Récupère un utilisateur spécifique par son ID.

    - **user_id**: ID de l'utilisateur à récupérer.
    - **Réponses**:
        - **200**: Détails de l'utilisateur (ex. `{"id": 1, "nom": "Doe", "inscriptions": [...], ...}`).
        - **404**: Utilisateur non trouvé.
        - **500**: Erreur interne du serveur.
    """
    return await utilisateur_service.get(db, user_id)

@router.get(
    "/users",
    response_model=List[UtilisateurLight],
    tags=["Utilisateurs"],
    summary="Lister tous les utilisateurs",
    description="Récupère une liste paginée de tous les utilisateurs avec leurs relations."
)
async def list_users(skip: int = 0, limit: int = 100, db: AsyncSession = Depends(get_async_db)):
    """
    Liste tous les utilisateurs avec pagination.

    - **skip**: Nombre d'utilisateurs à sauter (défaut: 0).
    - **limit**: Nombre maximum d'utilisateurs à retourner (défaut: 100).
    - **Réponses**:
        - **200**: Liste des utilisateurs (ex. `[{"id": 1, "nom": "Doe", ...}, ...]`).
        - **500**: Erreur interne du serveur.
    """
    return await utilisateur_service.get_all(db, skip, limit)

@router.put(
    "/users/{user_id}",
    response_model=Utilisateur,
    tags=["Utilisateurs"],
    summary="Mettre à jour un utilisateur",
    description="Met à jour les informations d'un utilisateur spécifique par son ID."
)
async def update_user(user_id: int, user_update: UtilisateurUpdate, db: AsyncSession = Depends(get_async_db)):
    """
    Met à jour un utilisateur spécifique.

    - **user_id**: ID de l'utilisateur à mettre à jour.
    - **user_update**: Schéma de mise à jour de l'utilisateur.
    - **Réponses**:
        - **200**: Utilisateur mis à jour avec succès.
        - **404**: Utilisateur non trouvé.
        - **400**: Données invalides.
        - **409**: Email déjà utilisé.
        - **500**: Erreur interne du serveur.
    """
    return await utilisateur_service.update(db, user_id, user_update)

@router.delete(
    "/users/{user_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    tags=["Utilisateurs"],
    summary="Supprimer un utilisateur",
    description="Supprime un utilisateur spécifique par son ID."
)
async def delete_user(user_id: int, db: AsyncSession = Depends(get_async_db)):
    """
    Supprime un utilisateur spécifique.

    - **user_id**: ID de l'utilisateur à supprimer.
    - **Réponses**:
        - **204**: Utilisateur supprimé avec succès.
        - **404**: Utilisateur non trouvé.
        - **500**: Erreur interne du serveur.
    """
    await utilisateur_service.delete(db, user_id)

@router.post(
    "/users/{user_id}/assign-permissions",
    response_model=str,
    tags=["Utilisateurs"],
    summary="Assigner des permissions à un utilisateur",
    description="Assigne directement des permissions à un utilisateur spécifique, en plus de celles héritées de son rôle."
)
async def assign_permissions_to_user(user_id: int, permission_ids: List[int], db: AsyncSession = Depends(get_async_db)):
    """
    Assigne des permissions directement à un utilisateur.

    Cette fonction permet d'assigner des permissions spécifiques à un utilisateur,
    en plus de celles qu'il hérite de son rôle. Les permissions sont ajoutées
    sans créer de doublons si elles existent déjà.

    - **user_id**: ID de l'utilisateur à qui assigner les permissions.
    - **permission_ids**: Liste des IDs des permissions à assigner.
    - **Réponses**:
        - **200**: Permissions assignées avec succès (ex. `"Permissions create_user, read_user assignées avec succès à l'utilisateur John Doe"`).
        - **400**: Aucune permission valide fournie.
        - **404**: Utilisateur non trouvé.
        - **500**: Erreur interne du serveur.
    """
    return await utilisateur_service.assign_permissions(db, user_id, permission_ids)

@router.post(
    "/users/{user_id}/revoke-permissions",
    response_model=str,
    tags=["Utilisateurs"],
    summary="Révoquer des permissions d'un utilisateur",
    description="Révoque directement des permissions d'un utilisateur spécifique, sans affecter celles héritées de son rôle."
)
async def revoke_permissions_from_user(user_id: int, permission_ids: List[int], db: AsyncSession = Depends(get_async_db)):
    """
    Révoque des permissions directement d'un utilisateur.

    Cette fonction permet de révoquer des permissions spécifiques d'un utilisateur,
    sans affecter celles qu'il hérite de son rôle. Seules les permissions
    directement assignées à l'utilisateur sont révoquées.

    - **user_id**: ID de l'utilisateur de qui révoquer les permissions.
    - **permission_ids**: Liste des IDs des permissions à révoquer.
    - **Réponses**:
        - **200**: Permissions révoquées avec succès (ex. `"Permissions create_user, read_user révoquées avec succès de l'utilisateur John Doe"`).
        - **400**: Aucune permission valide fournie.
        - **404**: Utilisateur non trouvé.
        - **500**: Erreur interne du serveur.
    """
    return await utilisateur_service.revoke_permissions(db, user_id, permission_ids)


@router.post(
    "/users/change-password",
    response_model=dict,
    tags=["Utilisateurs"],
    summary="Changer le mot de passe d'un utilisateur",
    description="Permet de changer le mot de passe d'un utilisateur via son id, son mot de passe actuel et le nouveau."
)
async def change_password(body: ChangePasswordSchema, db: AsyncSession = Depends(get_async_db)):
    """
    Change le mot de passe d'un utilisateur.

    - **utilisateur_id**: ID de l'utilisateur
    - **current_password**: Mot de passe actuel
    - **new_password**: Nouveau mot de passe
    - **Réponses**:
        - **200**: Mot de passe changé avec succès (ex. `{"message": "Mot de passe changé avec succès"}`).
        - **401**: Mot de passe actuel incorrect.
        - **500**: Erreur interne du serveur.
    """
    msg = await utilisateur_service.change_password(db, body.utilisateur_id, body.current_password, body.new_password)
    return {"message": msg}

@router.post(
    "/reset-password-request",
    response_model=dict,
    tags=["Utilisateurs"],
    summary="Demander la réinitialisation du mot de passe",
    description="Envoie un email avec un lien de réinitialisation de mot de passe si l'email existe."
)
async def reset_password_request(request: Request, body: ResetPasswordRequestSchema, db: AsyncSession = Depends(get_async_db)):
    await utilisateur_service.send_reset_link(db, body.email, request)
    return {"message": "Si l'email existe, un lien de réinitialisation a été envoyé."}

@router.get(
    "/reset-password-confirm",
    response_model=dict,
    tags=["Utilisateurs"],
    summary="Confirmer la réinitialisation du mot de passe",
    description="Valide le token, génère un nouveau mot de passe, l'envoie par email, et invalide le token."
)
async def reset_password_confirm(token: str, db: AsyncSession = Depends(get_async_db)):
    await utilisateur_service.confirm_reset_password(db, token)
    return {"message": "Votre mot de passe a été réinitialisé et envoyé par email."}

# ============================================================================
# ========================= ROUTES DES PERMISSIONS ===========================
# ============================================================================

@router.post(
    "/permissions",
    response_model=PermissionLight,
    tags=["Permissions"],
    summary="Créer une nouvelle permission",
    description="Crée une nouvelle permission dans le système."
)
async def create_permission(permission: PermissionCreate, db: AsyncSession = Depends(get_async_db)):
    """
    Crée une nouvelle permission avec validation de l'unicité du nom.

    - **permission**: Schéma de création de la permission.
    - **Réponses**:
        - **200**: Permission créée avec succès (ex. `{"id": 1, "nom": "lire_formation"}`).
        - **400**: Données invalides.
        - **409**: Permission existe déjà.
        - **500**: Erreur interne du serveur.
    """
    return await permission_service.create(db, permission)

@router.get(
    "/permissions/{permission_id}",
    response_model=PermissionLight,
    tags=["Permissions"],
    summary="Récupérer une permission par ID",
    description="Récupère les détails d'une permission spécifique par son ID."
)
async def get_permission(permission_id: int, db: AsyncSession = Depends(get_async_db)):
    """
    Récupère une permission spécifique.

    - **permission_id**: ID de la permission à récupérer.
    - **Réponses**:
        - **200**: Détails de la permission (ex. `{"id": 1, "nom": "lire_formation", "roles": [...], ...}`).
        - **404**: Permission non trouvée.
        - **500**: Erreur interne du serveur.
    """
    return await permission_service.get(db, permission_id)

@router.get(
    "/permissions",
    response_model=List[PermissionLight],
    tags=["Permissions"],
    summary="Lister toutes les permissions",
    description="Récupère une liste paginée de toutes les permissions avec leurs relations."
)
async def list_permissions(skip: int = 0, limit: int = 100, db: AsyncSession = Depends(get_async_db)):
    """
    Liste toutes les permissions avec pagination.

    - **skip**: Nombre de permissions à sauter (défaut: 0).
    - **limit**: Nombre maximum de permissions à retourner (défaut: 100).
    - **Réponses**:
        - **200**: Liste des permissions (ex. `[{"id": 1, "nom": "lire_formation", ...}, ...]`).
        - **500**: Erreur interne du serveur.
    """
    return await permission_service.get_all(db, skip, limit)

@router.put(
    "/permissions/{permission_id}",
    response_model=PermissionLight,
    tags=["Permissions"],
    summary="Mettre à jour une permission",
    description="Met à jour une permission spécifique par son ID."
)
async def update_permission(permission_id: int, permission_update: PermissionUpdate, db: AsyncSession = Depends(get_async_db)):
    """
    Met à jour une permission spécifique.

    - **permission_id**: ID de la permission à mettre à jour.
    - **permission_update**: Schéma de mise à jour de la permission.
    - **Réponses**:
        - **200**: Permission mise à jour avec succès.
        - **404**: Permission non trouvée.
        - **400**: Données invalides.
        - **409**: Nom de permission déjà utilisé.
        - **500**: Erreur interne du serveur.
    """
    return await permission_service.update(db, permission_id, permission_update)

@router.delete(
    "/permissions/{permission_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    tags=["Permissions"],
    summary="Supprimer une permission",
    description="Supprime une permission spécifique par son ID."
)
async def delete_permission(permission_id: int, db: AsyncSession = Depends(get_async_db)):
    """
    Supprime une permission spécifique.

    - **permission_id**: ID de la permission à supprimer.
    - **Réponses**:
        - **204**: Permission supprimée avec succès.
        - **404**: Permission non trouvée.
        - **500**: Erreur interne du serveur.
    """
    await permission_service.delete(db, permission_id)

@router.post(
    "/permissions/init-all",
    response_model=str,
    tags=["Permissions"],
    summary="Initialiser toutes les permissions et rôles",
    description="Crée toutes les permissions, tous les rôles et affecte les permissions aux rôles."
)
async def init_permissions_and_roles(db: AsyncSession = Depends(get_async_db)):
    """
    Crée toutes les permissions, tous les rôles et affecte les permissions aux rôles.
    - **Réponses**:
        - **200**: Permissions et rôles créés et affectés avec succès.
        - **500**: Erreur interne du serveur.
    """
    return await permission_service.create_all_permissions_and_roles(db)

# ============================================================================
# ========================= ROUTES DES RÔLES ================================
# ============================================================================

@router.post(
    "/roles",
    response_model=RoleLight,
    tags=["Rôles"],
    summary="Créer un nouveau rôle",
    description="Crée un nouveau rôle dans le système."
)
async def create_role(role: RoleCreate, db: AsyncSession = Depends(get_async_db)):
    """
    Crée un nouveau rôle avec validation de l'unicité du nom.

    - **role**: Schéma de création du rôle.
    - **Réponses**:
        - **200**: Rôle créé avec succès (ex. `{"id": 1, "nom": "admin"}`).
        - **400**: Données invalides.
        - **409**: Rôle existe déjà.
        - **500**: Erreur interne du serveur.
    """
    return await role_service.create(db, role)

@router.get(
    "/roles/{role_id}",
    response_model=Role,
    tags=["Rôles"],
    summary="Récupérer un rôle par ID",
    description="Récupère les détails d'un rôle spécifique par son ID."
)
async def get_role(role_id: int, db: AsyncSession = Depends(get_async_db)):
    """
    Récupère un rôle spécifique.

    - **role_id**: ID du rôle à récupérer.
    - **Réponses**:
        - **200**: Détails du rôle (ex. `{"id": 1, "nom": "admin", "permissions": [...], ...}`).
        - **404**: Rôle non trouvé.
        - **500**: Erreur interne du serveur.
    """
    return await role_service.get(db, role_id)

@router.get(
    "/roles",
    response_model=List[RoleLight],
    tags=["Rôles"],
    summary="Lister tous les rôles",
    description="Récupère une liste paginée de tous les rôles avec leurs relations."
)
async def list_roles(skip: int = 0, limit: int = 100, db: AsyncSession = Depends(get_async_db)):
    """
    Liste tous les rôles avec pagination.

    - **skip**: Nombre de rôles à sauter (défaut: 0).
    - **limit**: Nombre maximum de rôles à retourner (défaut: 100).
    - **Réponses**:
        - **200**: Liste des rôles (ex. `[{"id": 1, "nom": "admin", ...}, ...]`).
        - **500**: Erreur interne du serveur.
    """
    return await role_service.get_all(db, skip, limit)

@router.put(
    "/roles/{role_id}",
    response_model=Role,
    tags=["Rôles"],
    summary="Mettre à jour un rôle",
    description="Met à jour un rôle spécifique par son ID."
)
async def update_role(role_id: int, role_update: RoleUpdate, db: AsyncSession = Depends(get_async_db)):
    """
    Met à jour un rôle spécifique.

    - **role_id**: ID du rôle à mettre à jour.
    - **role_update**: Schéma de mise à jour du rôle.
    - **Réponses**:
        - **200**: Rôle mis à jour avec succès.
        - **404**: Rôle non trouvé.
        - **400**: Données invalides.
        - **409**: Nom de rôle déjà utilisé.
        - **500**: Erreur interne du serveur.
    """
    return await role_service.update(db, role_id, role_update)

@router.delete(
    "/roles/{role_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    tags=["Rôles"],
    summary="Supprimer un rôle",
    description="Supprime un rôle spécifique par son ID."
)
async def delete_role(role_id: int, db: AsyncSession = Depends(get_async_db)):
    """
    Supprime un rôle spécifique.

    - **role_id**: ID du rôle à supprimer.
    - **Réponses**:
        - **204**: Rôle supprimé avec succès.
        - **404**: Rôle non trouvé.
        - **500**: Erreur interne du serveur.
    """
    await role_service.delete(db, role_id)

@router.post(
    "/roles/{role_id}/assign-permissions",
    response_model=str,
    tags=["Rôles"],
    summary="Assigner des permissions à un rôle",
    description="Assigne une liste de permissions à un rôle sans doublons."
)
async def assign_permissions_to_role(role_id: int, permission_ids: List[int], db: AsyncSession = Depends(get_async_db)):
    """
    Assigne plusieurs permissions à un rôle sans doublons.
    - **role_id**: ID du rôle
    - **permission_ids**: Liste des IDs de permissions à assigner
    - **Réponses**:
        - **200**: Permissions assignées avec succès
        - **404**: Rôle ou permission non trouvé
        - **500**: Erreur interne du serveur
    """
    return await role_service.assign_permission(db, role_id, permission_ids)

@router.post(
    "/roles/{role_id}/revoke-permissions",
    response_model=str,
    tags=["Rôles"],
    summary="Révoquer des permissions d'un rôle",
    description="Révoque une liste de permissions d'un rôle."
)
async def revoke_permissions_from_role(role_id: int, permission_ids: List[int], db: AsyncSession = Depends(get_async_db)):
    """
    Révoque plusieurs permissions d'un rôle.
    - **role_id**: ID du rôle
    - **permission_ids**: Liste des IDs de permissions à révoquer
    - **Réponses**:
        - **200**: Permissions révoquées avec succès
        - **404**: Rôle ou permission non trouvé
        - **500**: Erreur interne du serveur
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
    description="Crée une nouvelle formation dans le système."
)
async def create_formation(formation: FormationCreate, db: AsyncSession = Depends(get_async_db)):
    """
    Crée une nouvelle formation.

    - **formation**: Schéma de création de la formation.
    - **Réponses**:
        - **200**: Formation créée avec succès (ex. `{"id": 1, "titre": "Python Avancé", ...}`).
        - **400**: Données invalides.
        - **500**: Erreur interne du serveur.
    """
    return await formation_service.create(db, formation)

@router.get(
    "/formations/{formation_id}",
    response_model=Formation,
    tags=["Formations"],
    summary="Récupérer une formation par ID",
    description="Récupère les détails d'une formation spécifique par son ID."
)
async def get_formation(formation_id: int, db: AsyncSession = Depends(get_async_db)):
    """
    Récupère une formation spécifique.

    - **formation_id**: ID de la formation à récupérer.
    - **Réponses**:
        - **200**: Détails de la formation (ex. `{"id": 1, "titre": "Python Avancé", "modules": [...], ...}`).
        - **404**: Formation non trouvée.
        - **500**: Erreur interne du serveur.
    """
    return await formation_service.get(db, formation_id)

@router.get(
    "/formations/{formation_id}/modules",
    response_model=List[ModuleLight],
    tags=["Formations"],
    summary="Récupérer tous les modules d'une formation",
    description="Récupère une liste paginée de tous les modules d'une formation spécifique, triés par ordre."
)
async def get_formation_modules(formation_id: int, skip: int = 0, limit: int = 100, db: AsyncSession = Depends(get_async_db)):
    """
    Récupère tous les modules d'une formation spécifique.

    - **formation_id**: ID de la formation dont on veut récupérer les modules.
    - **skip**: Nombre de modules à sauter (défaut: 0).
    - **limit**: Nombre maximum de modules à retourner (défaut: 100).
    - **Réponses**:
        - **200**: Liste des modules de la formation (ex. `[{"id": 1, "titre": "Introduction", "ordre": 1}, ...]`).
        - **404**: Formation non trouvée.
        - **500**: Erreur interne du serveur.
    """
    return await module_service.get_modules_by_formation(db, formation_id, skip, limit)

@router.get(
    "/formations",
    response_model=List[FormationLight],
    tags=["Formations"],
    summary="Lister toutes les formations",
    description="Récupère une liste paginée de toutes les formations avec leurs relations."
)
async def list_formations(skip: int = 0, limit: int = 100, db: AsyncSession = Depends(get_async_db)):
    """
    Liste toutes les formations avec pagination.

    - **skip**: Nombre de formations à sauter (défaut: 0).
    - **limit**: Nombre maximum de formations à retourner (défaut: 100).
    - **Réponses**:
        - **200**: Liste des formations (ex. `[{"id": 1, "titre": "Python Avancé", ...}, ...]`).
        - **500**: Erreur interne du serveur.
    """
    return await formation_service.get_all(db, skip, limit)

@router.put(
    "/formations/{formation_id}",
    response_model=Formation,
    tags=["Formations"],
    summary="Mettre à jour une formation",
    description="Met à jour une formation spécifique par son ID."
)
async def update_formation(formation_id: int, formation_update: FormationUpdate, db: AsyncSession = Depends(get_async_db)):
    """
    Met à jour une formation spécifique.

    - **formation_id**: ID de la formation à mettre à jour.
    - **formation_update**: Schéma de mise à jour de la formation.
    - **Réponses**:
        - **200**: Formation mise à jour avec succès.
        - **404**: Formation non trouvée.
        - **400**: Données invalides.
        - **500**: Erreur interne du serveur.
    """
    return await formation_service.update(db, formation_id, formation_update)

@router.delete(
    "/formations/{formation_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    tags=["Formations"],
    summary="Supprimer une formation",
    description="Supprime une formation spécifique par son ID."
)
async def delete_formation(formation_id: int, db: AsyncSession = Depends(get_async_db)):
    """
    Supprime une formation spécifique.

    - **formation_id**: ID de la formation à supprimer.
    - **Réponses**:
        - **204**: Formation supprimée avec succès.
        - **404**: Formation non trouvée.
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
    description="Crée une nouvelle inscription à une formation pour un utilisateur."
)
async def create_inscription(inscription: InscriptionFormationCreate, db: AsyncSession = Depends(get_async_db)):
    """
    Crée une nouvelle inscription à une formation.

    - **inscription**: Schéma de création de l'inscription.
    - **Réponses**:
        - **200**: Inscription créée avec succès (ex. `{"id": 1, "statut": "EN_COURS", ...}`).
        - **400**: Données invalides.
        - **404**: Utilisateur ou formation non trouvé.
        - **500**: Erreur interne du serveur.
    """
    return await inscription_formation_service.create(db, inscription)

@router.get(
    "/inscriptions/{inscription_id}",
    response_model=InscriptionFormation,
    tags=["Inscriptions"],
    summary="Récupérer une inscription par ID",
    description="Récupère les détails d'une inscription spécifique par son ID."
)
async def get_inscription(inscription_id: int, db: AsyncSession = Depends(get_async_db)):
    """
    Récupère une inscription spécifique.

    - **inscription_id**: ID de l'inscription à récupérer.
    - **Réponses**:
        - **200**: Détails de l'inscription (ex. `{"id": 1, "utilisateur": {...}, "formation": {...}, ...}`).
        - **404**: Inscription non trouvée.
        - **500**: Erreur interne du serveur.
    """
    return await inscription_formation_service.get(db, inscription_id)

@router.get(
    "/inscriptions",
    response_model=List[InscriptionFormation],
    tags=["Inscriptions"],
    summary="Lister toutes les inscriptions",
    description="Récupère une liste paginée de toutes les inscriptions avec leurs relations."
)
async def list_inscriptions(skip: int = 0, limit: int = 100, db: AsyncSession = Depends(get_async_db)):
    """
    Liste toutes les inscriptions avec pagination.

    - **skip**: Nombre d'inscriptions à sauter (défaut: 0).
    - **limit**: Nombre maximum d'inscriptions à retourner (défaut: 100).
    - **Réponses**:
        - **200**: Liste des inscriptions (ex. `[{"id": 1, "utilisateur": {...}, ...}, ...]`).
        - **500**: Erreur interne du serveur.
    """
    return await inscription_formation_service.get_all(db, skip, limit)

@router.put(
    "/inscriptions/{inscription_id}",
    response_model=InscriptionFormation,
    tags=["Inscriptions"],
    summary="Mettre à jour une inscription",
    description="Met à jour une inscription spécifique par son ID."
)
async def update_inscription(inscription_id: int, inscription_update: InscriptionFormationUpdate, db: AsyncSession = Depends(get_async_db)):
    """
    Met à jour une inscription spécifique.

    - **inscription_id**: ID de l'inscription à mettre à jour.
    - **inscription_update**: Schéma de mise à jour de l'inscription.
    - **Réponses**:
        - **200**: Inscription mise à jour avec succès.
        - **404**: Inscription non trouvée.
        - **400**: Données invalides.
        - **500**: Erreur interne du serveur.
    """
    return await inscription_formation_service.update(db, inscription_id, inscription_update)

@router.delete(
    "/inscriptions/{inscription_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    tags=["Inscriptions"],
    summary="Supprimer une inscription",
    description="Supprime une inscription spécifique par son ID."
)
async def delete_inscription(inscription_id: int, db: AsyncSession = Depends(get_async_db)):
    """
    Supprime une inscription spécifique.

    - **inscription_id**: ID de l'inscription à supprimer.
    - **Réponses**:
        - **204**: Inscription supprimée avec succès.
        - **404**: Inscription non trouvée.
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
    description="Crée un nouveau paiement pour une inscription."
)
async def create_paiement(paiement: PaiementCreate, db: AsyncSession = Depends(get_async_db)):
    """
    Crée un nouveau paiement.

    - **paiement**: Schéma de création du paiement.
    - **Réponses**:
        - **200**: Paiement créé avec succès (ex. `{"id": 1, "montant": 100.0, ...}`).
        - **400**: Données invalides.
        - **404**: Inscription non trouvée.
        - **500**: Erreur interne du serveur.
    """
    return await paiement_service.create(db, paiement)

@router.get(
    "/paiements/{paiement_id}",
    response_model=Paiement,
    tags=["Paiements"],
    summary="Récupérer un paiement par ID",
    description="Récupère les détails d'un paiement spécifique par son ID."
)
async def get_paiement(paiement_id: int, db: AsyncSession = Depends(get_async_db)):
    """
    Récupère un paiement spécifique.

    - **paiement_id**: ID du paiement à récupérer.
    - **Réponses**:
        - **200**: Détails du paiement (ex. `{"id": 1, "inscription": {...}, "montant": 100.0, ...}`).
        - **404**: Paiement non trouvé.
        - **500**: Erreur interne du serveur.
    """
    return await paiement_service.get(db, paiement_id)

@router.get(
    "/paiements",
    response_model=List[Paiement],
    tags=["Paiements"],
    summary="Lister tous les paiements",
    description="Récupère une liste paginée de tous les paiements avec leurs relations."
)
async def list_paiements(skip: int = 0, limit: int = 100, db: AsyncSession = Depends(get_async_db)):
    """
    Liste tous les paiements avec pagination.

    - **skip**: Nombre de paiements à sauter (défaut: 0).
    - **limit**: Nombre maximum de paiements à retourner (défaut: 100).
    - **Réponses**:
        - **200**: Liste des paiements (ex. `[{"id": 1, "montant": 100.0, ...}, ...]`).
        - **500**: Erreur interne du serveur.
    """
    return await paiement_service.get_all(db, skip, limit)

@router.put(
    "/paiements/{paiement_id}",
    response_model=Paiement,
    tags=["Paiements"],
    summary="Mettre à jour un paiement",
    description="Met à jour un paiement spécifique par son ID."
)
async def update_paiement(paiement_id: int, paiement_update: PaiementUpdate, db: AsyncSession = Depends(get_async_db)):
    """
    Met à jour un paiement spécifique.

    - **paiement_id**: ID du paiement à mettre à jour.
    - **paiement_update**: Schéma de mise à jour du paiement.
    - **Réponses**:
        - **200**: Paiement mis à jour avec succès.
        - **404**: Paiement non trouvé.
        - **400**: Données invalides.
        - **500**: Erreur interne du serveur.
    """
    return await paiement_service.update(db, paiement_id, paiement_update)

@router.delete(
    "/paiements/{paiement_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    tags=["Paiements"],
    summary="Supprimer un paiement",
    description="Supprime un paiement spécifique par son ID."
)
async def delete_paiement(paiement_id: int, db: AsyncSession = Depends(get_async_db)):
    """
    Supprime un paiement spécifique.

    - **paiement_id**: ID du paiement à supprimer.
    - **Réponses**:
        - **204**: Paiement supprimé avec succès.
        - **404**: Paiement non trouvé.
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
    description="Crée un nouveau module pour une formation."
)
async def create_module(module: ModuleCreate, db: AsyncSession = Depends(get_async_db)):
    """
    Crée un nouveau module.

    - **module**: Schéma de création du module.
    - **Réponses**:
        - **200**: Module créé avec succès (ex. `{"id": 1, "titre": "Introduction", ...}`).
        - **400**: Données invalides.
        - **404**: Formation non trouvée.
        - **500**: Erreur interne du serveur.
    """
    return await module_service.create(db, module)

@router.get(
    "/modules/{module_id}",
    response_model=Module,
    tags=["Modules"],
    summary="Récupérer un module par ID",
    description="Récupère les détails d'un module spécifique par son ID."
)
async def get_module(module_id: int, db: AsyncSession = Depends(get_async_db)):
    """
    Récupère un module spécifique.

    - **module_id**: ID du module à récupérer.
    - **Réponses**:
        - **200**: Détails du module (ex. `{"id": 1, "titre": "Introduction", "ressources": [...], ...}`).
        - **404**: Module non trouvé.
        - **500**: Erreur interne du serveur.
    """
    return await module_service.get(db, module_id)

@router.get(
    "/modules",
    response_model=List[Module],
    tags=["Modules"],
    summary="Lister tous les modules",
    description="Récupère une liste paginée de tous les modules avec leurs relations."
)
async def list_modules(skip: int = 0, limit: int = 100, db: AsyncSession = Depends(get_async_db)):
    """
    Liste tous les modules avec pagination.

    - **skip**: Nombre de modules à sauter (défaut: 0).
    - **limit**: Nombre maximum de modules à retourner (défaut: 100).
    - **Réponses**:
        - **200**: Liste des modules (ex. `[{"id": 1, "titre": "Introduction", ...}, ...]`).
        - **500**: Erreur interne du serveur.
    """
    return await module_service.get_all(db, skip, limit)

@router.put(
    "/modules/{module_id}",
    response_model=Module,
    tags=["Modules"],
    summary="Mettre à jour un module",
    description="Met à jour un module spécifique par son ID."
)
async def update_module(module_id: int, module_update: ModuleUpdate, db: AsyncSession = Depends(get_async_db)):
    """
    Met à jour un module spécifique.

    - **module_id**: ID du module à mettre à jour.
    - **module_update**: Schéma de mise à jour du module.
    - **Réponses**:
        - **200**: Module mis à jour avec succès.
        - **404**: Module non trouvé.
        - **400**: Données invalides.
        - **500**: Erreur interne du serveur.
    """
    return await module_service.update(db, module_id, module_update)

@router.delete(
    "/modules/{module_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    tags=["Modules"],
    summary="Supprimer un module",
    description="Supprime un module spécifique par son ID."
)
async def delete_module(module_id: int, db: AsyncSession = Depends(get_async_db)):
    """
    Supprime un module spécifique.

    - **module_id**: ID du module à supprimer.
    - **Réponses**:
        - **204**: Module supprimé avec succès.
        - **404**: Module non trouvé.
        - **500**: Erreur interne du serveur.
    """
    await module_service.delete(db, module_id)

# ============================================================================
# ========================= ROUTES DES RESSOURCES ===========================
# ============================================================================

@router.post(
    "/ressources",
    response_model=RessourceLight,
    tags=["Ressources"],
    summary="Créer une nouvelle ressource",
    description="Crée une nouvelle ressource pédagogique pour un module."
)
async def create_ressource(ressource: RessourceCreate, db: AsyncSession = Depends(get_async_db)):
    """
    Crée une nouvelle ressource.

    - **ressource**: Schéma de création de la ressource.
    - **Réponses**:
        - **200**: Ressource créée avec succès (ex. `{"id": 1, "titre": "Cours PDF", ...}`).
        - **400**: Données invalides.
        - **404**: Module non trouvé.
        - **500**: Erreur interne du serveur.
    """
    return await ressource_service.create(db, ressource)

@router.get(
    "/ressources/{ressource_id}",
    response_model=Ressource,
    tags=["Ressources"],
    summary="Récupérer une ressource par ID",
    description="Récupère les détails d'une ressource spécifique par son ID."
)
async def get_ressource(ressource_id: int, db: AsyncSession = Depends(get_async_db)):
    """
    Récupère une ressource spécifique.

    - **ressource_id**: ID de la ressource à récupérer.
    - **Réponses**:
        - **200**: Détails de la ressource (ex. `{"id": 1, "titre": "Cours PDF", "type": "document", ...}`).
        - **404**: Ressource non trouvée.
        - **500**: Erreur interne du serveur.
    """
    return await ressource_service.get(db, ressource_id)

@router.get(
    "/ressources",
    response_model=List[Ressource],
    tags=["Ressources"],
    summary="Lister toutes les ressources",
    description="Récupère une liste paginée de toutes les ressources avec leurs relations."
)
async def list_ressources(skip: int = 0, limit: int = 100, db: AsyncSession = Depends(get_async_db)):
    """
    Liste toutes les ressources avec pagination.

    - **skip**: Nombre de ressources à sauter (défaut: 0).
    - **limit**: Nombre maximum de ressources à retourner (défaut: 100).
    - **Réponses**:
        - **200**: Liste des ressources (ex. `[{"id": 1, "titre": "Cours PDF", ...}, ...]`).
        - **500**: Erreur interne du serveur.
    """
    return await ressource_service.get_all(db, skip, limit)

@router.put(
    "/ressources/{ressource_id}",
    response_model=Ressource,
    tags=["Ressources"],
    summary="Mettre à jour une ressource",
    description="Met à jour une ressource spécifique par son ID."
)
async def update_ressource(ressource_id: int, ressource_update: RessourceUpdate, db: AsyncSession = Depends(get_async_db)):
    """
    Met à jour une ressource spécifique.

    - **ressource_id**: ID de la ressource à mettre à jour.
    - **ressource_update**: Schéma de mise à jour de la ressource.
    - **Réponses**:
        - **200**: Ressource mise à jour avec succès.
        - **404**: Ressource non trouvée.
        - **400**: Données invalides.
        - **500**: Erreur interne du serveur.
    """
    return await ressource_service.update(db, ressource_id, ressource_update)

@router.delete(
    "/ressources/{ressource_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    tags=["Ressources"],
    summary="Supprimer une ressource",
    description="Supprime une ressource spécifique par son ID."
)
async def delete_ressource(ressource_id: int, db: AsyncSession = Depends(get_async_db)):
    """
    Supprime une ressource spécifique.

    - **ressource_id**: ID de la ressource à supprimer.
    - **Réponses**:
        - **204**: Ressource supprimée avec succès.
        - **404**: Ressource non trouvée.
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
    description="Crée un nouveau chef-d'œuvre pour un utilisateur et un module."
)
async def create_chef_d_oeuvre(chef_d_oeuvre: ChefDOeuvreCreate, db: AsyncSession = Depends(get_async_db)):
    """
    Crée un nouveau chef-d'œuvre.

    - **chef_d_oeuvre**: Schéma de création du chef-d'œuvre.
    - **Réponses**:
        - **200**: Chef-d'œuvre créé avec succès (ex. `{"id": 1, "titre": "Projet Final", ...}`).
        - **400**: Données invalides.
        - **404**: Utilisateur ou module non trouvé.
        - **500**: Erreur interne du serveur.
    """
    return await chef_d_oeuvre_service.create(db, chef_d_oeuvre)

@router.get(
    "/chefs-d-oeuvre/{chef_d_oeuvre_id}",
    response_model=ChefDOeuvre,
    tags=["Chefs-d'œuvre"],
    summary="Récupérer un chef-d'œuvre par ID",
    description="Récupère les détails d'un chef-d'œuvre spécifique par son ID."
)
async def get_chef_d_oeuvre(chef_d_oeuvre_id: int, db: AsyncSession = Depends(get_async_db)):
    """
    Récupère un chef-d'œuvre spécifique.

    - **chef_d_oeuvre_id**: ID du chef-d'œuvre à récupérer.
    - **Réponses**:
        - **200**: Détails du chef-d'œuvre (ex. `{"id": 1, "titre": "Projet Final", "utilisateur": {...}, ...}`).
        - **404**: Chef-d'œuvre non trouvé.
        - **500**: Erreur interne du serveur.
    """
    return await chef_d_oeuvre_service.get(db, chef_d_oeuvre_id)

@router.get(
    "/chefs-d-oeuvre",
    response_model=List[ChefDOeuvre],
    tags=["Chefs-d'œuvre"],
    summary="Lister tous les chefs-d'œuvre",
    description="Récupère une liste paginée de tous les chefs-d'œuvre avec leurs relations."
)
async def list_chefs_d_oeuvre(skip: int = 0, limit: int = 100, db: AsyncSession = Depends(get_async_db)):
    """
    Liste tous les chefs-d'œuvre avec pagination.

    - **skip**: Nombre de chefs-d'œuvre à sauter (défaut: 0).
    - **limit**: Nombre maximum de chefs-d'œuvre à retourner (défaut: 100).
    - **Réponses**:
        - **200**: Liste des chefs-d'œuvre (ex. `[{"id": 1, "titre": "Projet Final", ...}, ...]`).
        - **500**: Erreur interne du serveur.
    """
    return await chef_d_oeuvre_service.get_all(db, skip, limit)

@router.put(
    "/chefs-d-oeuvre/{chef_d_oeuvre_id}",
    response_model=ChefDOeuvre,
    tags=["Chefs-d'œuvre"],
    summary="Mettre à jour un chef-d'œuvre",
    description="Met à jour un chef-d'œuvre spécifique par son ID."
)
async def update_chef_d_oeuvre(chef_d_oeuvre_id: int, chef_d_oeuvre_update: ChefDOeuvreUpdate, db: AsyncSession = Depends(get_async_db)):
    """
    Met à jour un chef-d'œuvre spécifique.

    - **chef_d_oeuvre_id**: ID du chef-d'œuvre à mettre à jour.
    - **chef_d_oeuvre_update**: Schéma de mise à jour du chef-d'œuvre.
    - **Réponses**:
        - **200**: Chef-d'œuvre mis à jour avec succès.
        - **404**: Chef-d'œuvre non trouvé.
        - **400**: Données invalides.
        - **500**: Erreur interne du serveur.
    """
    return await chef_d_oeuvre_service.update(db, chef_d_oeuvre_id, chef_d_oeuvre_update)

@router.delete(
    "/chefs-d-oeuvre/{chef_d_oeuvre_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    tags=["Chefs-d'œuvre"],
    summary="Supprimer un chef-d'œuvre",
    description="Supprime un chef-d'œuvre spécifique par son ID."
)
async def delete_chef_d_oeuvre(chef_d_oeuvre_id: int, db: AsyncSession = Depends(get_async_db)):
    """
    Supprime un chef-d'œuvre spécifique.

    - **chef_d_oeuvre_id**: ID du chef-d'œuvre à supprimer.
    - **Réponses**:
        - **204**: Chef-d'œuvre supprimé avec succès.
        - **404**: Chef-d'œuvre non trouvé.
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
    description="Crée un nouveau projet collectif avec des membres associés."
)
async def create_projet_collectif(projet: ProjetCollectifCreate, db: AsyncSession = Depends(get_async_db)):
    """
    Crée un nouveau projet collectif.

    - **projet**: Schéma de création du projet collectif.
    - **Réponses**:
        - **200**: Projet collectif créé avec succès (ex. `{"id": 1, "titre": "Projet Groupe", ...}`).
        - **400**: Données invalides.
        - **404**: Formation ou membres non trouvés.
        - **500**: Erreur interne du serveur.
    """
    return await projet_collectif_service.create(db, projet)

@router.get(
    "/projets-collectifs/{projet_id}",
    response_model=ProjetCollectif,
    tags=["Projets Collectifs"],
    summary="Récupérer un projet collectif par ID",
    description="Récupère les détails d'un projet collectif spécifique par son ID."
)
async def get_projet_collectif(projet_id: int, db: AsyncSession = Depends(get_async_db)):
    """
    Récupère un projet collectif spécifique.

    - **projet_id**: ID du projet collectif à récupérer.
    - **Réponses**:
        - **200**: Détails du projet collectif (ex. `{"id": 1, "titre": "Projet Groupe", "membres": [...], ...}`).
        - **404**: Projet collectif non trouvé.
        - **500**: Erreur interne du serveur.
    """
    return await projet_collectif_service.get(db, projet_id)

@router.get(
    "/projets-collectifs",
    response_model=List[ProjetCollectif],
    tags=["Projets Collectifs"],
    summary="Lister tous les projets collectifs",
    description="Récupère une liste paginée de tous les projets collectifs avec leurs relations."
)
async def list_projets_collectifs(skip: int = 0, limit: int = 100, db: AsyncSession = Depends(get_async_db)):
    """
    Liste tous les projets collectifs avec pagination.

    - **skip**: Nombre de projets collectifs à sauter (défaut: 0).
    - **limit**: Nombre maximum de projets collectifs à retourner (défaut: 100).
    - **Réponses**:
        - **200**: Liste des projets collectifs (ex. `[{"id": 1, "titre": "Projet Groupe", ...}, ...]`).
        - **500**: Erreur interne du serveur.
    """
    return await projet_collectif_service.get_all(db, skip, limit)

@router.put(
    "/projets-collectifs/{projet_id}",
    response_model=ProjetCollectif,
    tags=["Projets Collectifs"],
    summary="Mettre à jour un projet collectif",
    description="Met à jour un projet collectif spécifique par son ID."
)
async def update_projet_collectif(projet_id: int, projet_update: ProjetCollectifUpdate, db: AsyncSession = Depends(get_async_db)):
    """
    Met à jour un projet collectif spécifique.

    - **projet_id**: ID du projet collectif à mettre à jour.
    - **projet_update**: Schéma de mise à jour du projet collectif.
    - **Réponses**:
        - **200**: Projet collectif mis à jour avec succès.
        - **404**: Projet collectif non trouvé.
        - **400**: Données invalides.
        - **500**: Erreur interne du serveur.
    """
    return await projet_collectif_service.update(db, projet_id, projet_update)

@router.delete(
    "/projets-collectifs/{projet_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    tags=["Projets Collectifs"],
    summary="Supprimer un projet collectif",
    description="Supprime un projet collectif spécifique par son ID."
)
async def delete_projet_collectif(projet_id: int, db: AsyncSession = Depends(get_async_db)):
    """
    Supprime un projet collectif spécifique.

    - **projet_id**: ID du projet collectif à supprimer.
    - **Réponses**:
        - **204**: Projet collectif supprimé avec succès.
        - **404**: Projet collectif non trouvé.
        - **500**: Erreur interne du serveur.
    """
    await projet_collectif_service.delete(db, projet_id)

# ============================================================================
# ========================= ROUTES DES ÉVALUATIONS ==========================
# ============================================================================

@router.post(
    "/evaluations",
    response_model=EvaluationLight,
    tags=["Évaluations"],
    summary="Créer une nouvelle évaluation",
    description="Crée une nouvelle évaluation pour un module."
)
async def create_evaluation(evaluation: EvaluationCreate, db: AsyncSession = Depends(get_async_db)):
    """
    Crée une nouvelle évaluation.

    - **evaluation**: Schéma de création de l'évaluation.
    - **Réponses**:
        - **200**: Évaluation créée avec succès (ex. `{"id": 1, "titre": "Examen Final", ...}`).
        - **400**: Données invalides.
        - **404**: Module non trouvé.
        - **500**: Erreur interne du serveur.
    """
    return await evaluation_service.create(db, evaluation)

@router.get(
    "/evaluations/{evaluation_id}",
    response_model=Evaluation,
    tags=["Évaluations"],
    summary="Récupérer une évaluation par ID",
    description="Récupère les détails d'une évaluation spécifique par son ID."
)
async def get_evaluation(evaluation_id: int, db: AsyncSession = Depends(get_async_db)):
    """
    Récupère une évaluation spécifique.

    - **evaluation_id**: ID de l'évaluation à récupérer.
    - **Réponses**:
        - **200**: Détails de l'évaluation (ex. `{"id": 1, "titre": "Examen Final", "questions": [...], ...}`).
        - **404**: Évaluation non trouvée.
        - **500**: Erreur interne du serveur.
    """
    return await evaluation_service.get(db, evaluation_id)

@router.get(
    "/evaluations",
    response_model=List[Evaluation],
    tags=["Évaluations"],
    summary="Lister toutes les évaluations",
    description="Récupère une liste paginée de toutes les évaluations avec leurs relations."
)
async def list_evaluations(skip: int = 0, limit: int = 100, db: AsyncSession = Depends(get_async_db)):
    """
    Liste toutes les évaluations avec pagination.

    - **skip**: Nombre d'évaluations à sauter (défaut: 0).
    - **limit**: Nombre maximum d'évaluations à retourner (défaut: 100).
    - **Réponses**:
        - **200**: Liste des évaluations (ex. `[{"id": 1, "titre": "Examen Final", ...}, ...]`).
        - **500**: Erreur interne du serveur.
    """
    return await evaluation_service.get_all(db, skip, limit)

@router.put(
    "/evaluations/{evaluation_id}",
    response_model=Evaluation,
    tags=["Évaluations"],
    summary="Mettre à jour une évaluation",
    description="Met à jour une évaluation spécifique par son ID."
)
async def update_evaluation(evaluation_id: int, evaluation_update: EvaluationUpdate, db: AsyncSession = Depends(get_async_db)):
    """
    Met à jour une évaluation spécifique.

    - **evaluation_id**: ID de l'évaluation à mettre à jour.
    - **evaluation_update**: Schéma de mise à jour de l'évaluation.
    - **Réponses**:
        - **200**: Évaluation mise à jour avec succès.
        - **404**: Évaluation non trouvée.
        - **400**: Données invalides.
        - **500**: Erreur interne du serveur.
    """
    return await evaluation_service.update(db, evaluation_id, evaluation_update)

@router.delete(
    "/evaluations/{evaluation_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    tags=["Évaluations"],
    summary="Supprimer une évaluation",
    description="Supprime une évaluation spécifique par son ID."
)
async def delete_evaluation(evaluation_id: int, db: AsyncSession = Depends(get_async_db)):
    """
    Supprime une évaluation spécifique.

    - **evaluation_id**: ID de l'évaluation à supprimer.
    - **Réponses**:
        - **204**: Évaluation supprimée avec succès.
        - **404**: Évaluation non trouvée.
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
    description="Crée une nouvelle question pour une évaluation."
)
async def create_question(question: QuestionCreate, db: AsyncSession = Depends(get_async_db)):
    """
    Crée une nouvelle question.

    - **question**: Schéma de création de la question.
    - **Réponses**:
        - **200**: Question créée avec succès (ex. `{"id": 1, "contenu": "Quelle est la capitale?", ...}`).
        - **400**: Données invalides.
        - **404**: Évaluation non trouvée.
        - **500**: Erreur interne du serveur.
    """
    return await question_service.create(db, question)

@router.get(
    "/questions/{question_id}",
    response_model=Question,
    tags=["Questions"],
    summary="Récupérer une question par ID",
    description="Récupère les détails d'une question spécifique par son ID."
)
async def get_question(question_id: int, db: AsyncSession = Depends(get_async_db)):
    """
    Récupère une question spécifique.

    - **question_id**: ID de la question à récupérer.
    - **Réponses**:
        - **200**: Détails de la question (ex. `{"id": 1, "contenu": "Quelle est la capitale?", "propositions": [...], ...}`).
        - **404**: Question non trouvée.
        - **500**: Erreur interne du serveur.
    """
    return await question_service.get(db, question_id)

@router.get(
    "/questions",
    response_model=List[Question],
    tags=["Questions"],
    summary="Lister toutes les questions",
    description="Récupère une liste paginée de toutes les questions avec leurs relations."
)
async def list_questions(skip: int = 0, limit: int = 100, db: AsyncSession = Depends(get_async_db)):
    """
    Liste toutes les questions avec pagination.

    - **skip**: Nombre de questions à sauter (défaut: 0).
    - **limit**: Nombre maximum de questions à retourner (défaut: 100).
    - **Réponses**:
        - **200**: Liste des questions (ex. `[{"id": 1, "contenu": "Quelle est la capitale?", ...}, ...]`).
        - **500**: Erreur interne du serveur.
    """
    return await question_service.get_all(db, skip, limit)

@router.put(
    "/questions/{question_id}",
    response_model=Question,
    tags=["Questions"],
    summary="Mettre à jour une question",
    description="Met à jour une question spécifique par son ID."
)
async def update_question(question_id: int, question_update: QuestionUpdate, db: AsyncSession = Depends(get_async_db)):
    """
    Met à jour une question spécifique.

    - **question_id**: ID de la question à mettre à jour.
    - **question_update**: Schéma de mise à jour de la question.
    - **Réponses**:
        - **200**: Question mise à jour avec succès.
        - **404**: Question non trouvée.
        - **400**: Données invalides.
        - **500**: Erreur interne du serveur.
    """
    return await question_service.update(db, question_id, question_update)

@router.delete(
    "/questions/{question_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    tags=["Questions"],
    summary="Supprimer une question",
    description="Supprime une question spécifique par son ID."
)
async def delete_question(question_id: int, db: AsyncSession = Depends(get_async_db)):
    """
    Supprime une question spécifique.

    - **question_id**: ID de la question à supprimer.
    - **Réponses**:
        - **204**: Question supprimée avec succès.
        - **404**: Question non trouvée.
        - **500**: Erreur interne du serveur.
    """
    await question_service.delete(db, question_id)

# ============================================================================
# ========================= ROUTES DES PROPOSITIONS =========================
# ============================================================================

@router.post(
    "/propositions",
    response_model=PropositionLight,
    tags=["Propositions"],
    summary="Créer une nouvelle proposition",
    description="Crée une nouvelle proposition pour une question."
)
async def create_proposition(proposition: PropositionCreate, db: AsyncSession = Depends(get_async_db)):
    """
    Crée une nouvelle proposition.

    - **proposition**: Schéma de création de la proposition.
    - **Réponses**:
        - **200**: Proposition créée avec succès (ex. `{"id": 1, "texte": "Paris", ...}`).
        - **400**: Données invalides.
        - **404**: Question non trouvée.
        - **500**: Erreur interne du serveur.
    """
    return await proposition_service.create(db, proposition)

@router.get(
    "/propositions/{proposition_id}",
    response_model=Proposition,
    tags=["Propositions"],
    summary="Récupérer une proposition par ID",
    description="Récupère les détails d'une proposition spécifique par son ID."
)
async def get_proposition(proposition_id: int, db: AsyncSession = Depends(get_async_db)):
    """
    Récupère une proposition spécifique.

    - **proposition_id**: ID de la proposition à récupérer.
    - **Réponses**:
        - **200**: Détails de la proposition (ex. `{"id": 1, "texte": "Paris", "est_correcte": true, ...}`).
        - **404**: Proposition non trouvée.
        - **500**: Erreur interne du serveur.
    """
    return await proposition_service.get(db, proposition_id)

@router.get(
    "/propositions",
    response_model=List[Proposition],
    tags=["Propositions"],
    summary="Lister toutes les propositions",
    description="Récupère une liste paginée de toutes les propositions avec leurs relations."
)
async def list_propositions(skip: int = 0, limit: int = 100, db: AsyncSession = Depends(get_async_db)):
    """
    Liste toutes les propositions avec pagination.

    - **skip**: Nombre de propositions à sauter (défaut: 0).
    - **limit**: Nombre maximum de propositions à retourner (défaut: 100).
    - **Réponses**:
        - **200**: Liste des propositions (ex. `[{"id": 1, "texte": "Paris", ...}, ...]`).
        - **500**: Erreur interne du serveur.
    """
    return await proposition_service.get_all(db, skip, limit)

@router.put(
    "/propositions/{proposition_id}",
    response_model=Proposition,
    tags=["Propositions"],
    summary="Mettre à jour une proposition",
    description="Met à jour une proposition spécifique par son ID."
)
async def update_proposition(proposition_id: int, proposition_update: PropositionUpdate, db: AsyncSession = Depends(get_async_db)):
    """
    Met à jour une proposition spécifique.

    - **proposition_id**: ID de la proposition à mettre à jour.
    - **proposition_update**: Schéma de mise à jour de la proposition.
    - **Réponses**:
        - **200**: Proposition mise à jour avec succès.
        - **404**: Proposition non trouvée.
        - **400**: Données invalides.
        - **500**: Erreur interne du serveur.
    """
    return await proposition_service.update(db, proposition_id, proposition_update)

@router.delete(
    "/propositions/{proposition_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    tags=["Propositions"],
    summary="Supprimer une proposition",
    description="Supprime une proposition spécifique par son ID."
)
async def delete_proposition(proposition_id: int, db: AsyncSession = Depends(get_async_db)):
    """
    Supprime une proposition spécifique.

    - **proposition_id**: ID de la proposition à supprimer.
    - **Réponses**:
        - **204**: Proposition supprimée avec succès.
        - **404**: Proposition non trouvée.
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
    description="Crée un nouveau résultat d'évaluation pour un utilisateur et une évaluation."
)
async def create_resultat_evaluation(resultat: ResultatEvaluationCreate, db: AsyncSession = Depends(get_async_db)):
    """
    Crée un nouveau résultat d'évaluation.

    - **resultat**: Schéma de création du résultat d'évaluation.
    - **Réponses**:
        - **200**: Résultat créé avec succès (ex. `{"id": 1, "note": 85.0, ...}`).
        - **400**: Données invalides.
        - **404**: Utilisateur ou évaluation non trouvé.
        - **500**: Erreur interne du serveur.
    """
    return await resultat_evaluation_service.create(db, resultat)

@router.get(
    "/resultats-evaluations/{resultat_id}",
    response_model=ResultatEvaluation,
    tags=["Résultats Évaluations"],
    summary="Récupérer un résultat d'évaluation par ID",
    description="Récupère les détails d'un résultat d'évaluation spécifique par son ID."
)
async def get_resultat_evaluation(resultat_id: int, db: AsyncSession = Depends(get_async_db)):
    """
    Récupère un résultat d'évaluation spécifique.

    - **resultat_id**: ID du résultat d'évaluation à récupérer.
    - **Réponses**:
        - **200**: Détails du résultat (ex. `{"id": 1, "note": 85.0, "utilisateur": {...}, ...}`).
        - **404**: Résultat non trouvé.
        - **500**: Erreur interne du serveur.
    """
    return await resultat_evaluation_service.get(db, resultat_id)

@router.get(
    "/resultats-evaluations",
    response_model=List[ResultatEvaluation],
    tags=["Résultats Évaluations"],
    summary="Lister tous les résultats d'évaluation",
    description="Récupère une liste paginée de tous les résultats d'évaluation avec leurs relations."
)
async def list_resultats_evaluations(skip: int = 0, limit: int = 100, db: AsyncSession = Depends(get_async_db)):
    """
    Liste tous les résultats d'évaluation avec pagination.

    - **skip**: Nombre de résultats à sauter (défaut: 0).
    - **limit**: Nombre maximum de résultats à retourner (défaut: 100).
    - **Réponses**:
        - **200**: Liste des résultats (ex. `[{"id": 1, "note": 85.0, ...}, ...]`).
        - **500**: Erreur interne du serveur.
    """
    return await resultat_evaluation_service.get_all(db, skip, limit)

@router.put(
    "/resultats-evaluations/{resultat_id}",
    response_model=ResultatEvaluation,
    tags=["Résultats Évaluations"],
    summary="Mettre à jour un résultat d'évaluation",
    description="Met à jour un résultat d'évaluation spécifique par son ID."
)
async def update_resultat_evaluation(resultat_id: int, resultat_update: ResultatEvaluationUpdate, db: AsyncSession = Depends(get_async_db)):
    """
    Met à jour un résultat d'évaluation spécifique.

    - **resultat_id**: ID du résultat d'évaluation à mettre à jour.
    - **resultat_update**: Schéma de mise à jour du résultat.
    - **Réponses**:
        - **200**: Résultat mis à jour avec succès.
        - **404**: Résultat non trouvé.
        - **400**: Données invalides.
        - **500**: Erreur interne du serveur.
    """
    return await resultat_evaluation_service.update(db, resultat_id, resultat_update)

@router.delete(
    "/resultats-evaluations/{resultat_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    tags=["Résultats Évaluations"],
    summary="Supprimer un résultat d'évaluation",
    description="Supprime un résultat d'évaluation spécifique par son ID."
)
async def delete_resultat_evaluation(resultat_id: int, db: AsyncSession = Depends(get_async_db)):
    """
    Supprime un résultat d'évaluation spécifique.

    - **resultat_id**: ID du résultat d'évaluation à supprimer.
    - **Réponses**:
        - **204**: Résultat supprimé avec succès.
        - **404**: Résultat non trouvé.
        - **500**: Erreur interne du serveur.
    """
    await resultat_evaluation_service.delete(db, resultat_id)

# ============================================================================
# ========================= ROUTES DES GÉNOTYPES ============================
# ============================================================================

@router.post(
    "/genotypes",
    response_model=GenotypeIndividuelLight,
    tags=["Génotypes"],
    summary="Créer un nouveau génotype individuel",
    description="Crée un nouveau génotype individuel pour un utilisateur."
)
async def create_genotype(genotype: GenotypeIndividuelCreate, db: AsyncSession = Depends(get_async_db)):
    """
    Crée un nouveau génotype individuel.

    - **genotype**: Schéma de création du génotype.
    - **Réponses**:
        - **200**: Génotype créé avec succès (ex. `{"id": 1, "type": "detenu", "nom": "Doe", ...}`).
        - **400**: Données invalides.
        - **404**: Utilisateur non trouvé.
        - **500**: Erreur interne du serveur.
    """
    return await genotype_individuel_service.create(db, genotype)

@router.get(
    "/genotypes/{genotype_id}",
    response_model=GenotypeIndividuel,
    tags=["Génotypes"],
    summary="Récupérer un génotype individuel par ID",
    description="Récupère les détails d'un génotype individuel spécifique par son ID."
)
async def get_genotype(genotype_id: int, db: AsyncSession = Depends(get_async_db)):
    """
    Récupère un génotype individuel spécifique.

    - **genotype_id**: ID du génotype à récupérer.
    - **Réponses**:
        - **200**: Détails du génotype (ex. `{"id": 1, "type": "detenu", "nom": "Doe", ...}`).
        - **404**: Génotype non trouvé.
        - **500**: Erreur interne du serveur.
    """
    return await genotype_individuel_service.get(db, genotype_id)

@router.get(
    "/genotypes",
    response_model=List[GenotypeIndividuel],
    tags=["Génotypes"],
    summary="Lister tous les génotypes individuels",
    description="Récupère une liste paginée de tous les génotypes individuels avec leurs relations."
)
async def list_genotypes(skip: int = 0, limit: int = 100, db: AsyncSession = Depends(get_async_db)):
    """
    Liste tous les génotypes individuels avec pagination.

    - **skip**: Nombre de génotypes à sauter (défaut: 0).
    - **limit**: Nombre maximum de génotypes à retourner (défaut: 100).
    - **Réponses**:
        - **200**: Liste des génotypes (ex. `[{"id": 1, "type": "detenu", ...}, ...]`).
        - **500**: Erreur interne du serveur.
    """
    return await genotype_individuel_service.get_all(db, skip, limit)

@router.put(
    "/genotypes/{genotype_id}",
    response_model=GenotypeIndividuel,
    tags=["Génotypes"],
    summary="Mettre à jour un génotype individuel",
    description="Met à jour un génotype individuel spécifique par son ID."
)
async def update_genotype(genotype_id: int, genotype_update: GenotypeIndividuelUpdate, db: AsyncSession = Depends(get_async_db)):
    """
    Met à jour un génotype individuel spécifique.

    - **genotype_id**: ID du génotype à mettre à jour.
    - **genotype_update**: Schéma de mise à jour du génotype.
    - **Réponses**:
        - **200**: Génotype mis à jour avec succès.
        - **404**: Génotype non trouvé.
        - **400**: Données invalides.
        - **500**: Erreur interne du serveur.
    """
    return await genotype_individuel_service.update(db, genotype_id, genotype_update)

@router.delete(
    "/genotypes/{genotype_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    tags=["Génotypes"],
    summary="Supprimer un génotype individuel",
    description="Supprime un génotype individuel spécifique par son ID."
)
async def delete_genotype(genotype_id: int, db: AsyncSession = Depends(get_async_db)):
    """
    Supprime un génotype individuel spécifique.

    - **genotype_id**: ID du génotype à supprimer.
    - **Réponses**:
        - **204**: Génotype supprimé avec succès.
        - **404**: Génotype non trouvé.
        - **500**: Erreur interne du serveur.
    """
    await genotype_individuel_service.delete(db, genotype_id)

# ============================================================================
# ========================= ROUTES DES ASCENDANCES GÉNOTYPE =================
# ============================================================================

@router.post(
    "/ascendances-genotypes",
    response_model=AscendanceGenotypeLight,
    tags=["Ascendances Génotype"],
    summary="Créer une nouvelle ascendance de génotype",
    description="Crée une nouvelle ascendance pour un génotype individuel."
)
async def create_ascendance_genotype(ascendance: AscendanceGenotypeCreate, db: AsyncSession = Depends(get_async_db)):
    """
    Crée une nouvelle ascendance de génotype.

    - **ascendance**: Schéma de création de l'ascendance.
    - **Réponses**:
        - **200**: Ascendance créée avec succès (ex. `{"id": 1, "nom_pere": "Doe", ...}`).
        - **400**: Données invalides.
        - **404**: Génotype non trouvé.
        - **500**: Erreur interne du serveur.
    """
    return await ascendance_genotype_service.create(db, ascendance)

@router.get(
    "/ascendances-genotypes/{ascendance_id}",
    response_model=AscendanceGenotype,
    tags=["Ascendances Génotype"],
    summary="Récupérer une ascendance de génotype par ID",
    description="Récupère les détails d'une ascendance de génotype spécifique par son ID."
)
async def get_ascendance_genotype(ascendance_id: int, db: AsyncSession = Depends(get_async_db)):
    """
    Récupère une ascendance de génotype spécifique.

    - **ascendance_id**: ID de l'ascendance à récupérer.
    - **Réponses**:
        - **200**: Détails de l'ascendance (ex. `{"id": 1, "nom_pere": "Doe", "genotype": {...}, ...}`).
        - **404**: Ascendance non trouvée.
        - **500**: Erreur interne du serveur.
    """
    return await ascendance_genotype_service.get(db, ascendance_id)

@router.get(
    "/ascendances-genotypes",
    response_model=List[AscendanceGenotype],
    tags=["Ascendances Génotype"],
    summary="Lister toutes les ascendances de génotype",
    description="Récupère une liste paginée de toutes les ascendances de génotype avec leurs relations."
)
async def list_ascendances_genotypes(skip: int = 0, limit: int = 100, db: AsyncSession = Depends(get_async_db)):
    """
    Liste toutes les ascendances de génotype avec pagination.

    - **skip**: Nombre d'ascendances à sauter (défaut: 0).
    - **limit**: Nombre maximum d'ascendances à retourner (défaut: 100).
    - **Réponses**:
        - **200**: Liste des ascendances (ex. `[{"id": 1, "nom_pere": "Doe", ...}, ...]`).
        - **500**: Erreur interne du serveur.
    """
    return await ascendance_genotype_service.get_all(db, skip, limit)

@router.put(
    "/ascendances-genotypes/{ascendance_id}",
    response_model=AscendanceGenotype,
    tags=["Ascendances Génotype"],
    summary="Mettre à jour une ascendance de génotype",
    description="Met à jour une ascendance de génotype spécifique par son ID."
)
async def update_ascendance_genotype(ascendance_id: int, ascendance_update: AscendanceGenotypeUpdate, db: AsyncSession = Depends(get_async_db)):
    """
    Met à jour une ascendance de génotype spécifique.

    - **ascendance_id**: ID de l'ascendance à mettre à jour.
    - **ascendance_update**: Schéma de mise à jour de l'ascendance.
    - **Réponses**:
        - **200**: Ascendance mise à jour avec succès.
        - **404**: Ascendance non trouvée.
        - **400**: Données invalides.
        - **500**: Erreur interne du serveur.
    """
    return await ascendance_genotype_service.update(db, ascendance_id, ascendance_update)

@router.delete(
    "/ascendances-genotypes/{ascendance_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    tags=["Ascendances Génotype"],
    summary="Supprimer une ascendance de génotype",
    description="Supprime une ascendance de génotype spécifique par son ID."
)
async def delete_ascendance_genotype(ascendance_id: int, db: AsyncSession = Depends(get_async_db)):
    """
    Supprime une ascendance de génotype spécifique.

    - **ascendance_id**: ID de l'ascendance à supprimer.
    - **Réponses**:
        - **204**: Ascendance supprimée avec succès.
        - **404**: Ascendance non trouvée.
        - **500**: Erreur interne du serveur.
    """
    await ascendance_genotype_service.delete(db, ascendance_id)

# ============================================================================
# ========================= ROUTES DES SANTÉS GÉNOTYPE =======================
# ============================================================================

@router.post(
    "/santes-genotypes",
    response_model=SanteGenotypeLight,
    tags=["Santés Génotype"],
    summary="Créer une nouvelle santé de génotype",
    description="Crée une nouvelle santé pour un génotype individuel."
)
async def create_sante_genotype(sante: SanteGenotypeCreate, db: AsyncSession = Depends(get_async_db)):
    """
    Crée une nouvelle santé de génotype.

    - **sante**: Schéma de création de la santé.
    - **Réponses**:
        - **200**: Santé créée avec succès (ex. `{"id": 1, "condition_medicale": "Diabète", ...}`).
        - **400**: Données invalides.
        - **404**: Génotype non trouvé.
        - **500**: Erreur interne du serveur.
    """
    return await sante_genotype_service.create(db, sante)

@router.get(
    "/santes-genotypes/{sante_id}",
    response_model=SanteGenotype,
    tags=["Santés Génotype"],
    summary="Récupérer une santé de génotype par ID",
    description="Récupère les détails d'une santé de génotype spécifique par son ID."
)
async def get_sante_genotype(sante_id: int, db: AsyncSession = Depends(get_async_db)):
    """
    Récupère une santé de génotype spécifique.

    - **sante_id**: ID de la santé à récupérer.
    - **Réponses**:
        - **200**: Détails de la santé (ex. `{"id": 1, "condition_medicale": "Diabète", "genotype": {...}, ...}`).
        - **404**: Santé non trouvée.
        - **500**: Erreur interne du serveur.
    """
    return await sante_genotype_service.get(db, sante_id)

@router.get(
    "/santes-genotypes",
    response_model=List[SanteGenotype],
    tags=["Santés Génotype"],
    summary="Lister toutes les santés de génotype",
    description="Récupère une liste paginée de toutes les santés de génotype avec leurs relations."
)
async def list_santes_genotypes(skip: int = 0, limit: int = 100, db: AsyncSession = Depends(get_async_db)):
    """
    Liste toutes les santés de génotype avec pagination.

    - **skip**: Nombre de santés à sauter (défaut: 0).
    - **limit**: Nombre maximum de santés à retourner (défaut: 100).
    - **Réponses**:
        - **200**: Liste des santés (ex. `[{"id": 1, "condition_medicale": "Diabète", ...}, ...]`).
        - **500**: Erreur interne du serveur.
    """
    return await sante_genotype_service.get_all(db, skip, limit)

@router.put(
    "/santes-genotypes/{sante_id}",
    response_model=SanteGenotype,
    tags=["Santés Génotype"],
    summary="Mettre à jour une santé de génotype",
    description="Met à jour une santé de génotype spécifique par son ID."
)
async def update_sante_genotype(sante_id: int, sante_update: SanteGenotypeUpdate, db: AsyncSession = Depends(get_async_db)):
    """
    Met à jour une santé de génotype spécifique.

    - **sante_id**: ID de la santé à mettre à jour.
    - **sante_update**: Schéma de mise à jour de la santé.
    - **Réponses**:
        - **200**: Santé mise à jour avec succès.
        - **404**: Santé non trouvée.
        - **400**: Données invalides.
        - **500**: Erreur interne du serveur.
    """
    return await sante_genotype_service.update(db, sante_id, sante_update)

@router.delete(
    "/santes-genotypes/{sante_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    tags=["Santés Génotype"],
    summary="Supprimer une santé de génotype",
    description="Supprime une santé de génotype spécifique par son ID."
)
async def delete_sante_genotype(sante_id: int, db: AsyncSession = Depends(get_async_db)):
    """
    Supprime une santé de génotype spécifique.

    - **sante_id**: ID de la santé à supprimer.
    - **Réponses**:
        - **204**: Santé supprimée avec succès.
        - **404**: Santé non trouvée.
        - **500**: Erreur interne du serveur.
    """
    await sante_genotype_service.delete(db, sante_id)

# ============================================================================
# ========================= ROUTES DES ÉDUCATIONS GÉNOTYPE ==================
# ============================================================================

@router.post(
    "/educations-genotypes",
    response_model=EducationGenotypeLight,
    tags=["Éducations Génotype"],
    summary="Créer une nouvelle éducation de génotype",
    description="Crée une nouvelle éducation pour un génotype individuel."
)
async def create_education_genotype(education: EducationGenotypeCreate, db: AsyncSession = Depends(get_async_db)):
    """
    Crée une nouvelle éducation de génotype.

    - **education**: Schéma de création de l'éducation.
    - **Réponses**:
        - **200**: Éducation créée avec succès (ex. `{"id": 1, "niveau_education": "Licence", ...}`).
        - **400**: Données invalides.
        - **404**: Génotype non trouvé.
        - **500**: Erreur interne du serveur.
    """
    return await education_genotype_service.create(db, education)

@router.get(
    "/educations-genotypes/{education_id}",
    response_model=EducationGenotype,
    tags=["Éducations Génotype"],
    summary="Récupérer une éducation de génotype par ID",
    description="Récupère les détails d'une éducation de génotype spécifique par son ID."
)
async def get_education_genotype(education_id: int, db: AsyncSession = Depends(get_async_db)):
    """
    Récupère une éducation de génotype spécifique.

    - **education_id**: ID de l'éducation à récupérer.
    - **Réponses**:
        - **200**: Détails de l'éducation (ex. `{"id": 1, "niveau_education": "Licence", "genotype": {...}, ...}`).
        - **404**: Éducation non trouvée.
        - **500**: Erreur interne du serveur.
    """
    return await education_genotype_service.get(db, education_id)

@router.get(
    "/educations-genotypes",
    response_model=List[EducationGenotype],
    tags=["Éducations Génotype"],
    summary="Lister toutes les éducations de génotype",
    description="Récupère une liste paginée de toutes les éducations de génotype avec leurs relations."
)
async def list_educations_genotypes(skip: int = 0, limit: int = 100, db: AsyncSession = Depends(get_async_db)):
    """
    Liste toutes les éducations de génotype avec pagination.

    - **skip**: Nombre d'éducations à sauter (défaut: 0).
    - **limit**: Nombre maximum d'éducations à retourner (défaut: 100).
    - **Réponses**:
        - **200**: Liste des éducations (ex. `[{"id": 1, "niveau_education": "Licence", ...}, ...]`).
        - **500**: Erreur interne du serveur.
    """
    return await education_genotype_service.get_all(db, skip, limit)

@router.put(
    "/educations-genotypes/{education_id}",
    response_model=EducationGenotype,
    tags=["Éducations Génotype"],
    summary="Mettre à jour une éducation de génotype",
    description="Met à jour une éducation de génotype spécifique par son ID."
)
async def update_education_genotype(education_id: int, education_update: EducationGenotypeUpdate, db: AsyncSession = Depends(get_async_db)):
    """
    Met à jour une éducation de génotype spécifique.

    - **education_id**: ID de l'éducation à mettre à jour.
    - **education_update**: Schéma de mise à jour de l'éducation.
    - **Réponses**:
        - **200**: Éducation mise à jour avec succès.
        - **404**: Éducation non trouvée.
        - **400**: Données invalides.
        - **500**: Erreur interne du serveur.
    """
    return await education_genotype_service.update(db, education_id, education_update)

@router.delete(
    "/educations-genotypes/{education_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    tags=["Éducations Génotype"],
    summary="Supprimer une éducation de génotype",
    description="Supprime une éducation de génotype spécifique par son ID."
)
async def delete_education_genotype(education_id: int, db: AsyncSession = Depends(get_async_db)):
    """
    Supprime une éducation de génotype spécifique.

    - **education_id**: ID de l'éducation à supprimer.
    - **Réponses**:
        - **204**: Éducation supprimée avec succès.
        - **404**: Éducation non trouvée.
        - **500**: Erreur interne du serveur.
    """
    await education_genotype_service.delete(db, education_id)

# ============================================================================
# ========================= ROUTES DES PLANS D'INTERVENTION =================
# ============================================================================

@router.post(
    "/plans-intervention",
    response_model=PlanInterventionIndividualiseLight,
    tags=["Plans d'Intervention"],
    summary="Créer un nouveau plan d'intervention",
    description="Crée un nouveau plan d'intervention individualisé pour un utilisateur."
)
async def create_plan_intervention(plan: PlanInterventionIndividualiseCreate, db: AsyncSession = Depends(get_async_db)):
    """
    Crée un nouveau plan d'intervention.

    - **plan**: Schéma de création du plan d'intervention.
    - **Réponses**:
        - **200**: Plan créé avec succès (ex. `{"id": 1, "objectifs": "Améliorer compétences", ...}`).
        - **400**: Données invalides.
        - **404**: Utilisateur non trouvé.
        - **500**: Erreur interne du serveur.
    """
    return await plan_intervention_service.create(db, plan)

@router.get(
    "/plans-intervention/{plan_id}",
    response_model=PlanInterventionIndividualise,
    tags=["Plans d'Intervention"],
    summary="Récupérer un plan d'intervention par ID",
    description="Récupère les détails d'un plan d'intervention spécifique par son ID."
)
async def get_plan_intervention(plan_id: int, db: AsyncSession = Depends(get_async_db)):
    """
    Récupère un plan d'intervention spécifique.

    - **plan_id**: ID du plan à récupérer.
    - **Réponses**:
        - **200**: Détails du plan (ex. `{"id": 1, "objectifs": "Améliorer compétences", "utilisateur": {...}, ...}`).
        - **404**: Plan non trouvé.
        - **500**: Erreur interne du serveur.
    """
    return await plan_intervention_service.get(db, plan_id)

@router.get(
    "/plans-intervention",
    response_model=List[PlanInterventionIndividualise],
    tags=["Plans d'Intervention"],
    summary="Lister tous les plans d'intervention",
    description="Récupère une liste paginée de tous les plans d'intervention avec leurs relations."
)
async def list_plans_intervention(skip: int = 0, limit: int = 100, db: AsyncSession = Depends(get_async_db)):
    """
    Liste tous les plans d'intervention avec pagination.

    - **skip**: Nombre de plans à sauter (défaut: 0).
    - **limit**: Nombre maximum de plans à retourner (défaut: 100).
    - **Réponses**:
        - **200**: Liste des plans (ex. `[{"id": 1, "objectifs": "Améliorer compétences", ...}, ...]`).
        - **500**: Erreur interne du serveur.
    """
    return await plan_intervention_service.get_all(db, skip, limit)

@router.put(
    "/plans-intervention/{plan_id}",
    response_model=PlanInterventionIndividualise,
    tags=["Plans d'Intervention"],
    summary="Mettre à jour un plan d'intervention",
    description="Met à jour un plan d'intervention spécifique par son ID."
)
async def update_plan_intervention(plan_id: int, plan_update: PlanInterventionIndividualiseUpdate, db: AsyncSession = Depends(get_async_db)):
    """
    Met à jour un plan d'intervention spécifique.

    - **plan_id**: ID du plan à mettre à jour.
    - **plan_update**: Schéma de mise à jour du plan.
    - **Réponses**:
        - **200**: Plan mis à jour avec succès.
        - **404**: Plan non trouvé.
        - **400**: Données invalides.
        - **500**: Erreur interne du serveur.
    """
    return await plan_intervention_service.update(db, plan_id, plan_update)

@router.delete(
    "/plans-intervention/{plan_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    tags=["Plans d'Intervention"],
    summary="Supprimer un plan d'intervention",
    description="Supprime un plan d'intervention spécifique par son ID."
)
async def delete_plan_intervention(plan_id: int, db: AsyncSession = Depends(get_async_db)):
    """
    Supprime un plan d'intervention spécifique.

    - **plan_id**: ID du plan à supprimer.
    - **Réponses**:
        - **204**: Plan supprimé avec succès.
        - **404**: Plan non trouvé.
        - **500**: Erreur interne du serveur.
    """
    await plan_intervention_service.delete(db, plan_id)

# ============================================================================
# ========================= ROUTES DES ACCRÉDITATIONS =======================
# ============================================================================

@router.post(
    "/accreditations",
    response_model=AccreditationLight,
    tags=["Accréditations"],
    summary="Créer une nouvelle accréditation",
    description="Crée une nouvelle accréditation pour un utilisateur."
)
async def create_accreditation(accreditation: AccreditationCreate, db: AsyncSession = Depends(get_async_db)):
    """
    Crée une nouvelle accréditation.

    - **accreditation**: Schéma de création de l'accréditation.
    - **Réponses**:
        - **200**: Accréditation créée avec succès (ex. `{"id": 1, "titre": "Certification Python", ...}`).
        - **400**: Données invalides.
        - **404**: Utilisateur ou formation non trouvé.
        - **500**: Erreur interne du serveur.
    """
    return await accreditation_service.create(db, accreditation)

@router.get(
    "/accreditations/{accreditation_id}",
    response_model=Accreditation,
    tags=["Accréditations"],
    summary="Récupérer une accréditation par ID",
    description="Récupère les détails d'une accréditation spécifique par son ID."
)
async def get_accreditation(accreditation_id: int, db: AsyncSession = Depends(get_async_db)):
    """
    Récupère une accréditation spécifique.

    - **accreditation_id**: ID de l'accréditation à récupérer.
    - **Réponses**:
        - **200**: Détails de l'accréditation (ex. `{"id": 1, "titre": "Certification Python", "utilisateur": {...}, ...}`).
        - **404**: Accréditation non trouvée.
        - **500**: Erreur interne du serveur.
    """
    return await accreditation_service.get(db, accreditation_id)

@router.get(
    "/accreditations",
    response_model=List[Accreditation],
    tags=["Accréditations"],
    summary="Lister toutes les accréditations",
    description="Récupère une liste paginée de toutes les accréditations avec leurs relations."
)
async def list_accreditations(skip: int = 0, limit: int = 100, db: AsyncSession = Depends(get_async_db)):
    """
    Liste toutes les accréditations avec pagination.

    - **skip**: Nombre d'accréditations à sauter (défaut: 0).
    - **limit**: Nombre maximum d'accréditations à retourner (défaut: 100).
    - **Réponses**:
        - **200**: Liste des accréditations (ex. `[{"id": 1, "titre": "Certification Python", ...}, ...]`).
        - **500**: Erreur interne du serveur.
    """
    return await accreditation_service.get_all(db, skip, limit)

@router.put(
    "/accreditations/{accreditation_id}",
    response_model=Accreditation,
    tags=["Accréditations"],
    summary="Mettre à jour une accréditation",
    description="Met à jour une accréditation spécifique par son ID."
)
async def update_accreditation(accreditation_id: int, accreditation_update: AccreditationUpdate, db: AsyncSession = Depends(get_async_db)):
    """
    Met à jour une accréditation spécifique.

    - **accreditation_id**: ID de l'accréditation à mettre à jour.
    - **accreditation_update**: Schéma de mise à jour de l'accréditation.
    - **Réponses**:
        - **200**: Accréditation mise à jour avec succès.
        - **404**: Accréditation non trouvée.
        - **400**: Données invalides.
        - **500**: Erreur interne du serveur.
    """
    return await accreditation_service.update(db, accreditation_id, accreditation_update)

@router.delete(
    "/accreditations/{accreditation_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    tags=["Accréditations"],
    summary="Supprimer une accréditation",
    description="Supprime une accréditation spécifique par son ID."
)
async def delete_accreditation(accreditation_id: int, db: AsyncSession = Depends(get_async_db)):
    """
    Supprime une accréditation spécifique.

    - **accreditation_id**: ID de l'accréditation à supprimer.
    - **Réponses**:
        - **204**: Accréditation supprimée avec succès.
        - **404**: Accréditation non trouvée.
        - **500**: Erreur interne du serveur.
    """
    await accreditation_service.delete(db, accreditation_id)

# ============================================================================
# ========================= ROUTES DES ACTUALITÉS ===========================
# ============================================================================

@router.post(
    "/actualites",
    response_model=ActualiteLight,
    tags=["Actualités"],
    summary="Créer une nouvelle actualité",
    description="Crée une nouvelle actualité dans le système."
)
async def create_actualite(actualite: ActualiteCreate, db: AsyncSession = Depends(get_async_db)):
    """
    Crée une nouvelle actualité.

    - **actualite**: Schéma de création de l'actualité.
    - **Réponses**:
        - **200**: Actualité créée avec succès (ex. `{"id": 1, "titre": "Nouvelle Formation", ...}`).
        - **400**: Données invalides.
        - **500**: Erreur interne du serveur.
    """
    return await actualite_service.create(db, actualite)

@router.get(
    "/actualites/{actualite_id}",
    response_model=Actualite,
    tags=["Actualités"],
    summary="Récupérer une actualité par ID",
    description="Récupère les détails d'une actualité spécifique par son ID."
)
async def get_actualite(actualite_id: int, db: AsyncSession = Depends(get_async_db)):
    """
    Récupère une actualité spécifique.

    - **actualite_id**: ID de l'actualité à récupérer.
    - **Réponses**:
        - **200**: Détails de l'actualité (ex. `{"id": 1, "titre": "Nouvelle Formation", "contenu": "...", ...}`).
        - **404**: Actualité non trouvée.
        - **500**: Erreur interne du serveur.
    """
    return await actualite_service.get(db, actualite_id)

@router.get(
    "/actualites",
    response_model=List[Actualite],
    tags=["Actualités"],
    summary="Lister toutes les actualités",
    description="Récupère une liste paginée de toutes les actualités avec leurs relations."
)
async def list_actualites(skip: int = 0, limit: int = 100, db: AsyncSession = Depends(get_async_db)):
    """
    Liste toutes les actualités avec pagination.

    - **skip**: Nombre d'actualités à sauter (défaut: 0).
    - **limit**: Nombre maximum d'actualités à retourner (défaut: 100).
    - **Réponses**:
        - **200**: Liste des actualités (ex. `[{"id": 1, "titre": "Nouvelle Formation", ...}, ...]`).
        - **500**: Erreur interne du serveur.
    """
    return await actualite_service.get_all(db, skip, limit)

@router.put(
    "/actualites/{actualite_id}",
    response_model=Actualite,
    tags=["Actualités"],
    summary="Mettre à jour une actualité",
    description="Met à jour une actualité spécifique par son ID."
)
async def update_actualite(actualite_id: int, actualite_update: ActualiteUpdate, db: AsyncSession = Depends(get_async_db)):
    """
    Met à jour une actualité spécifique.

    - **actualite_id**: ID de l'actualité à mettre à jour.
    - **actualite_update**: Schéma de mise à jour de l'actualité.
    - **Réponses**:
        - **200**: Actualité mise à jour avec succès.
        - **404**: Actualité non trouvée.
        - **400**: Données invalides.
        - **500**: Erreur interne du serveur.
    """
    return await actualite_service.update(db, actualite_id, actualite_update)

@router.delete(
    "/actualites/{actualite_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    tags=["Actualités"],
    summary="Supprimer une actualité",
    description="Supprime une actualité spécifique par son ID."
)
async def delete_actualite(actualite_id: int, db: AsyncSession = Depends(get_async_db)):
    """
    Supprime une actualité spécifique.

    - **actualite_id**: ID de l'actualité à supprimer.
    - **Réponses**:
        - **204**: Actualité supprimée avec succès.
        - **404**: Actualité non trouvée.
        - **500**: Erreur interne du serveur.
    """
    await actualite_service.delete(db, actualite_id)

# ============================================================================
# ========================= ROUTES DES FICHIERS =============================
# ============================================================================

@router.post(
    "/files/upload",
    response_model=dict,
    tags=["Fichiers"],
    summary="Téléverser un fichier",
    description="Téléverse un fichier (image, document, audio, vidéo) avec validation du type et de la taille."
)
async def upload_file(request: Request, file: UploadFile = File(...), file_type: FileTypeEnum = FileTypeEnum.DOCUMENT, db: AsyncSession = Depends(get_async_db)):
    """
    Téléverse un fichier dans le système.

    - **file**: Fichier à téléverser.
    - **file_type**: Type de fichier (document, image, audio, vidéo).
    - **Réponses**:
        - **200**: Fichier téléversé avec succès (ex. `{"filename": "document.pdf", "path": "/var/www/app/static/..."}`).
        - **400**: Type de fichier ou taille non valide.
        - **500**: Erreur interne du serveur.
    """
    return await file_service.upload_file(request, file, file_type)

@router.post(
    "/files/upload-multiple",
    response_model=List[dict],
    tags=["Fichiers"],
    summary="Téléverser plusieurs fichiers",
    description="Téléverse plusieurs fichiers (images, documents, audio, vidéos) avec validation du type et de la taille."
)
async def upload_multiple_files(request: Request, files: List[UploadFile] = File(...), file_type: FileTypeEnum = FileTypeEnum.DOCUMENT, db: AsyncSession = Depends(get_async_db)):
    """
    Téléverse plusieurs fichiers dans le système.

    - **files**: Liste de fichiers à téléverser.
    - **file_type**: Type de fichiers (document, image, audio, vidéo).
    - **Réponses**:
        - **200**: Fichiers téléversés avec succès (ex. `[{"filename": "doc1.pdf", "path": "/var/www/app/static/..."}, ...]`).
        - **400**: Type de fichier ou taille non valide.
        - **500**: Erreur interne du serveur.
    """
    return await file_service.upload_files(request, files, file_type)

@router.delete(
    "/files/delete",
    response_model=str,
    tags=["Fichiers"],
    summary="Supprimer un fichier",
    description="Supprime un fichier spécifique par son URL et type."
)
async def delete_file(file_url: str, file_type: FileTypeEnum, db: AsyncSession = Depends(get_async_db)):
    """
    Supprime un fichier spécifique.

    - **file_url**: URL complète du fichier à supprimer.
    - **file_type**: Type de fichier (document, image, audio, vidéo).
    - **Réponses**:
        - **200**: Fichier supprimé avec succès (ex. `"Fichier http://localhost:8000/static/documents/file.pdf supprimé avec succès."`).
        - **400**: Type de fichier non supporté ou URL invalide.
        - **404**: Fichier non trouvé.
        - **500**: Erreur interne du serveur.
    """
    return await file_service.delete_file_by_url(file_url, file_type)

@router.delete(
    "/files/delete-by-filename",
    response_model=str,
    tags=["Fichiers"],
    summary="Supprimer un fichier par nom",
    description="Supprime un fichier spécifique par son nom de fichier et type."
)
async def delete_file_by_filename(filename: str, file_type: FileTypeEnum, request: Request, db: AsyncSession = Depends(get_async_db)):
    """
    Supprime un fichier spécifique par son nom.

    - **filename**: Nom du fichier à supprimer (ex. "document.pdf").
    - **file_type**: Type de fichier (document, image, audio, vidéo).
    - **Réponses**:
        - **200**: Fichier supprimé avec succès (ex. `"Fichier document.pdf supprimé avec succès."`).
        - **400**: Type de fichier non supporté.
        - **404**: Fichier non trouvé.
        - **500**: Erreur interne du serveur.
    """
    # Construire l'URL complète à partir du nom de fichier
    config = file_service.FILE_CONFIG[file_type]
    base_url = f"{request.base_url}{config['url_prefix'].lstrip('/')}"
    file_url = f"{base_url}/{filename}"
    return await file_service.delete_file_by_url(file_url, file_type)

@router.delete(
    "/files/delete-multiple",
    response_model=List[str],
    tags=["Fichiers"],
    summary="Supprimer plusieurs fichiers",
    description="Supprime plusieurs fichiers spécifiques par leurs URLs et type."
)
async def delete_multiple_files(file_urls: List[str], file_type: FileTypeEnum, db: AsyncSession = Depends(get_async_db)):
    """
    Supprime plusieurs fichiers spécifiques.

    - **file_urls**: Liste des URLs complètes des fichiers à supprimer.
    - **file_type**: Type de fichiers (document, image, audio, vidéo).
    - **Réponses**:
        - **200**: Résultats de suppression (ex. `["Fichier doc1.pdf supprimé avec succès.", "Fichier doc2.pdf supprimé avec succès."]`).
        - **400**: Type de fichier non supporté ou URLs invalides.
        - **500**: Erreur interne du serveur.
    """
    return await file_service.delete_multiple_files(file_urls, file_type)

@router.get(
    "/files/list",
    response_model=List[dict],
    tags=["Fichiers"],
    summary="Lister les fichiers",
    description="Liste tous les fichiers d'un type donné avec leurs informations."
)
async def list_files(request: Request, file_type: FileTypeEnum = FileTypeEnum.DOCUMENT, db: AsyncSession = Depends(get_async_db)):
    """
    Liste tous les fichiers d'un type donné.

    - **file_type**: Type de fichiers à lister (document, image, audio, vidéo).
    - **Réponses**:
        - **200**: Liste des fichiers (ex. `[{"filename": "doc.pdf", "url": "http://localhost:8000/static/documents/doc.pdf", "size": 1024, "created_at": "2024-01-01T12:00:00", "modified_at": "2024-01-01T12:00:00"}]`).
        - **400**: Type de fichier non supporté.
        - **500**: Erreur interne du serveur.
    """
    return await file_service.list_files(file_type, request)