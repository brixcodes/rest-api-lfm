from datetime import datetime, timedelta
import os
import traceback
import aiofiles
from pathlib import Path
import secrets
import string
from typing import TypeVar, Generic, List, Type, Any, Optional
from uuid import uuid4
import uuid
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from sqlalchemy.orm import selectinload
from sqlalchemy.exc import IntegrityError, SQLAlchemyError
from fastapi import HTTPException, Request, UploadFile, status
from passlib.context import CryptContext
import logging
from jose import jwt
from src.util.database.setting import settings
from src.util.helper.enum import (
    FileTypeEnum, StatutCompteEnum, StatutFormationEnum, StatutInscriptionEnum,
    StatutProjetIndividuelEnum, StatutProjetCollectifEnum, StatutEnum,
    PermissionEnum, RoleEnum, EvaluationTypeEnum, GenotypeTypeEnum,
    SexeEnum, StatutPaiementEnum, MethodePaiementEnum
)
from src.api.schema import (
    Permission, PermissionLight, PermissionCreate, PermissionUpdate,
    Role, RoleLight, RoleCreate, RoleUpdate,
    Utilisateur, UtilisateurLight, UtilisateurCreate, UtilisateurUpdate,
    InscriptionFormation, InscriptionFormationLight, InscriptionFormationCreate, InscriptionFormationUpdate,
    Formation, FormationLight, FormationCreate, FormationUpdate,
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
    Paiement, PaiementLight, PaiementCreate, PaiementUpdate, loginSchema
)
from src.api.model import (
    Permission as PermissionModel, Role as RoleModel, Utilisateur as UtilisateurModel,
    InscriptionFormation as InscriptionFormationModel, Formation as FormationModel,
    Module as ModuleModel, Ressource as RessourceModel, ChefDOeuvre as ChefDOeuvreModel,
    ProjetCollectif as ProjetCollectifModel, Evaluation as EvaluationModel,
    Question as QuestionModel, Proposition as PropositionModel,
    ResultatEvaluation as ResultatEvaluationModel, GenotypeIndividuel as GenotypeIndividuelModel,
    AscendanceGenotype as AscendanceGenotypeModel, SanteGenotype as SanteGenotypeModel,
    EducationGenotype as EducationGenotypeModel, PlanInterventionIndividualise as PlanInterventionIndividualiseModel,
    Accreditation as AccreditationModel, Actualite as ActualiteModel,
    Paiement as PaiementModel,
    association_roles_permissions, association_utilisateurs_permissions,
    association_projets_collectifs_membres
)

logger = logging.getLogger(__name__)
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

# Type générique pour les modèles et schémas
ModelType = TypeVar("ModelType")
SchemaType = TypeVar("SchemaType")
CreateSchemaType = TypeVar("CreateSchemaType")
UpdateSchemaType = TypeVar("UpdateSchemaType")

# ============================================================================
# ========================= SERVICE DE BASE ==================================
# ============================================================================

class BaseService(Generic[ModelType, SchemaType, CreateSchemaType, UpdateSchemaType]):
    """Classe de base pour tous les services, fournissant des méthodes CRUD génériques."""
    def __init__(self, model: Type[ModelType], schema: Type[SchemaType], light_schema: Type[SchemaType]):
        self.model = model
        self.schema = schema
        self.light_schema = light_schema
        self.entity_name = model.__name__

    async def get_or_404(self, db: AsyncSession, id: int, model: Type = None, entity_name: str = None) -> ModelType:
        """Récupère une entité par ID ou lève une erreur 404."""
        model = model or self.model
        entity_name = entity_name or self.entity_name
        query = select(model).filter(model.id == id)
        result = await db.execute(query)
        entity = result.scalars().first()
        if not entity:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"{entity_name} avec l'ID {id} non trouvé"
            )
        return entity

    async def check_unique(self, db: AsyncSession, field: str, value: Any, field_name: str) -> None:
        """Vérifie l'unicité d'un champ dans la base de données."""
        query = select(self.model).filter(getattr(self.model, field) == value)
        result = await db.execute(query)
        if result.scalars().first():
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail=f"{self.entity_name} avec {field_name} '{value}' existe déjà"
            )

    async def create(self, db: AsyncSession, obj_in: CreateSchemaType) -> SchemaType:
        """Crée une nouvelle entité."""
        async with db.begin():
            try:
                db_obj = self.model(**obj_in.dict(exclude_unset=True))
                db.add(db_obj)
                await db.flush()
                await db.refresh(db_obj)
                return self.light_schema.from_orm(db_obj)
            except IntegrityError as e:
                logger.error(f"Erreur d'intégrité lors de la création de {self.entity_name}: {str(e)}")
                raise HTTPException(
                    status_code=status.HTTP_409_CONFLICT,
                    detail=f"{self.entity_name} existe déjà"
                )
            except SQLAlchemyError as e:
                logger.error(f"Erreur de base de données lors de la création de {self.entity_name}: {str(e)}", exc_info=True)
                raise HTTPException(
                    status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                    detail=f"Erreur de base de données lors de la création de {self.entity_name}"
                )

    async def get(self, db: AsyncSession, id: int) -> SchemaType:
        """Récupère une entité par ID."""
        try:
            db_obj = await self.get_or_404(db, id)
            return self.schema.from_orm(db_obj)
        except SQLAlchemyError as e:
            logger.error(f"Erreur de base de données lors de la récupération de {self.entity_name}: {str(e)}")
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"Erreur de base de données lors de la récupération de {self.entity_name}"
            )

    async def get_all(self, db: AsyncSession, skip: int = 0, limit: int = 100, relationships: List = []) -> List[SchemaType]:
        """Récupère toutes les entités avec pagination et relations optionnelles."""
        try:
            query = select(self.model).offset(skip).limit(limit)
            for rel in relationships:
                query = query.options(selectinload(rel))
            result = await db.execute(query)
            return [self.schema.from_orm(obj) for obj in result.scalars().all()]
        except SQLAlchemyError as e:
            logger.error(f"Erreur de base de données lors de la récupération des {self.entity_name}s: {str(e)}")
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"Erreur de base de données lors de la récupération des {self.entity_name}s"
            )

    async def update(self, db: AsyncSession, id: int, obj_in: UpdateSchemaType) -> SchemaType:
        """Met à jour une entité."""
        async with db.begin():
            try:
                db_obj = await self.get_or_404(db, id)
                update_data = obj_in.dict(exclude_unset=True)
                for key, value in update_data.items():
                    setattr(db_obj, key, value)
                await db.flush()
                await db.refresh(db_obj)
                return self.schema.from_orm(db_obj)
            except SQLAlchemyError as e:
                logger.error(f"Erreur de base de données lors de la mise à jour de {self.entity_name}: {str(e)}")
                raise HTTPException(
                    status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                    detail=f"Erreur de base de données lors de la mise à jour de {self.entity_name}"
                )

    async def delete(self, db: AsyncSession, id: int) -> None:
        """Supprime une entité."""
        async with db.begin():
            try:
                db_obj = await self.get_or_404(db, id)
                await db.delete(db_obj)
                await db.flush()
            except SQLAlchemyError as e:
                logger.error(f"Erreur de base de données lors de la suppression de {self.entity_name}: {str(e)}")
                raise HTTPException(
                    status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                    detail=f"Erreur de base de données lors de la suppression de {self.entity_name}"
                )

    async def assign_relationship(self, db: AsyncSession, id: int, related_id: int, related_model: Type, related_field: str, related_name: str) -> SchemaType:
        """Assigne une relation à une entité."""
        async with db.begin():
            try:
                db_obj = await self.get_or_404(db, id)
                related_obj = await self.get_or_404(db, related_id, related_model, related_name)
                related_list = getattr(db_obj, related_field)
                if related_obj not in related_list:
                    related_list.append(related_obj)
                    await db.flush()
                return self.schema.from_orm(db_obj)
            except SQLAlchemyError as e:
                logger.error(f"Erreur lors de l'assignation de {related_name} à {self.entity_name}: {str(e)}")
                raise HTTPException(
                    status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                    detail=f"Erreur lors de l'assignation de {related_name} à {self.entity_name}"
                )

    async def revoke_relationship(self, db: AsyncSession, id: int, related_id: int, related_model: Type, related_field: str, related_name: str) -> SchemaType:
        """Révoque une relation d'une entité."""
        async with db.begin():
            try:
                db_obj = await self.get_or_404(db, id)
                related_obj = await self.get_or_404(db, related_id, related_model, related_name)
                related_list = getattr(db_obj, related_field)
                if related_obj in related_list:
                    related_list.remove(related_obj)
                    await db.flush()
                return self.schema.from_orm(db_obj)
            except SQLAlchemyError as e:
                logger.error(f"Erreur lors de la révocation de {related_name} de {self.entity_name}: {str(e)}")
                raise HTTPException(
                    status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                    detail=f"Erreur lors de la révocation de {related_name} de {self.entity_name}"
                )

# ==================================================================================
# ========================= SERVICE DE GESTION DES FICHIERS ========================
# ==================================================================================

class FileService:
    """Service pour la gestion de l'upload de fichiers."""

    # Configuration des types de fichiers
    # storage_path = chemin disque absolu, url_prefix = chemin URL relatif
    FILE_CONFIG = {
        FileTypeEnum.DOCUMENT: {
            "extensions": {".pdf", ".doc", ".docx", ".txt"},
            "max_size_mb": 50,
            "storage_path": "/var/www/app/static/documents",
            "url_prefix": "/static/documents",
        },
        FileTypeEnum.IMAGE: {
            "extensions": {".jpg", ".jpeg", ".png"},
            "max_size_mb": 20,
            "storage_path": "/var/www/app/static/images",
            "url_prefix": "/static/images",
        },
        FileTypeEnum.AUDIO: {
            "extensions": {".mp3", ".wav", ".ogg"},
            "max_size_mb": 150,
            "storage_path": "/var/www/app/static/audios",
            "url_prefix": "/static/audios",
        },
        FileTypeEnum.VIDEO: {
            "extensions": {".mp4", ".avi", ".mkv"},
            "max_size_mb": 300,
            "storage_path": "/var/www/app/static/videos",
            "url_prefix": "/static/videos",
        }
    }

    def __init__(self):
        """Initialise le service et crée les répertoires si nécessaire."""
        self._ensure_directories()

    def _ensure_directories(self) -> None:
        """Crée les répertoires de stockage avec les permissions 755 si nécessaire."""
        for file_type, config in self.FILE_CONFIG.items():
            storage_path = Path(config["storage_path"])
            try:
                storage_path.mkdir(parents=True, exist_ok=True)
                if os.name != "nt":
                    os.chmod(storage_path, 0o755)
                logger.info(f"Répertoire {storage_path} créé ou vérifié avec permissions 755 pour {file_type.value}.")
            except Exception as e:
                logger.error(f"Erreur création répertoire {storage_path} pour {file_type.value}: {e}")
                raise HTTPException(
                    status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                    detail=f"Erreur création répertoire {storage_path} pour {file_type.value}"
                )

    def _validate_file(self, file: UploadFile, file_type: FileTypeEnum) -> None:
        """Valide le type et la taille d'un fichier."""
        if file_type not in self.FILE_CONFIG:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Type de fichier '{file_type.value}' non supporté."
            )
        config = self.FILE_CONFIG[file_type]
        file_ext = Path(file.filename).suffix.lower()
        if file_ext not in config["extensions"]:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Extension '{file_ext}' non autorisée pour '{file_type.value}'. Autorisées: {', '.join(config['extensions'])}"
            )
        # Vérification taille
        file.file.seek(0, os.SEEK_END)
        size = file.file.tell()
        file.file.seek(0)
        max_size = config["max_size_mb"] * 1024 * 1024
        if size > max_size:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Le fichier dépasse la taille maximale de {config['max_size_mb']} Mo pour '{file_type.value}'."
            )

    def _generate_unique_filename(self, original_filename: str) -> str:
        """Génère un nom de fichier unique avec UUID."""
        ext = Path(original_filename).suffix.lower()
        return f"{uuid.uuid4().hex}{ext}"

    async def upload_file(self, request: Request, file: UploadFile, file_type: FileTypeEnum) -> str:
        """Upload un fichier unique et retourne son URL publique avec base URL dynamique."""
        logger.info(f"Début upload fichier: {file.filename} (type: {file_type.value})")
        self._validate_file(file, file_type)
        config = self.FILE_CONFIG[file_type]
        storage_path = Path(config["storage_path"])
        unique_filename = self._generate_unique_filename(file.filename)
        file_path = storage_path / unique_filename

        try:
            storage_path.mkdir(parents=True, exist_ok=True)
            async with aiofiles.open(file_path, "wb") as out_file:
                content = await file.read()
                await out_file.write(content)

            if os.name != "nt":
                os.chmod(file_path, 0o755)

            base_url = str(request.base_url).rstrip("/")
            url = f"{base_url}{config['url_prefix'].rstrip('/')}/{unique_filename}"
            logger.info(f"Upload réussi, URL: {url}")
            return url
        except Exception as e:
            logger.error(f"Erreur upload fichier {file.filename}: {e}\n{traceback.format_exc()}")
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"Erreur lors de l'upload du fichier '{file.filename}' pour '{file_type.value}'."
            )
        finally:
            await file.close()

    async def upload_files(self, request: Request, files: List[UploadFile], file_type: FileTypeEnum) -> List[str]:
        """Upload plusieurs fichiers et retourne une liste d'URLs publiques."""
        if not files:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Aucun fichier fourni pour l'upload."
            )
        urls = []
        for file in files:
            url = await self.upload_file(request, file, file_type)
            urls.append(url)
        return urls

    async def delete_file(self, file_url: str, file_type: FileTypeEnum) -> str:
        """Supprime un fichier à partir de son URL et retourne un message."""
        if file_type not in self.FILE_CONFIG:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Type de fichier '{file_type.value}' non supporté."
            )
        config = self.FILE_CONFIG[file_type]
        filename = file_url.split("/")[-1]
        file_path = Path(config["storage_path"]) / filename
        try:
            if file_path.exists():
                file_path.unlink()
                logger.info(f"Fichier {file_path} supprimé avec succès.")
                return f"Fichier {file_url} supprimé avec succès."
            else:
                logger.warning(f"Fichier {file_path} non trouvé pour suppression.")
                return f"Fichier {file_url} non trouvé."
        except Exception as e:
            logger.error(f"Erreur suppression fichier {file_url}: {e}")
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"Erreur lors de la suppression du fichier '{file_url}'."
            )
              
# ============================================================================
# ========================= SERVICE DES PERMISSIONS ==========================
# ============================================================================

class PermissionService(BaseService[PermissionModel, Permission, PermissionCreate, PermissionUpdate]):
    """Service pour la gestion des permissions."""
    def __init__(self):
        super().__init__(PermissionModel, Permission, PermissionLight)

    async def create(self, db: AsyncSession, obj_in: PermissionCreate) -> PermissionLight:
        """Crée une nouvelle permission avec validation de l'unicité du nom."""
        await self.check_unique(db, "nom", obj_in.nom, "nom")
        return await super().create(db, obj_in)

    async def get_all(self, db: AsyncSession, skip: int = 0, limit: int = 100) -> List[Permission]:
        """Récupère toutes les permissions avec leurs relations."""
        return await super().get_all(db, skip, limit, [PermissionModel.roles, PermissionModel.utilisateurs])

    async def update(self, db: AsyncSession, id: int, obj_in: PermissionUpdate) -> Permission:
        """Met à jour une permission avec validation de l'unicité du nom."""
        if obj_in.nom:
            db_obj = await self.get_or_404(db, id)
            if obj_in.nom != db_obj.nom:
                await self.check_unique(db, "nom", obj_in.nom, "nom")
        return await super().update(db, id, obj_in)  

# ============================================================================
# ========================= SERVICE DES RÔLES ================================
# ============================================================================

class RoleService(BaseService[RoleModel, Role, RoleCreate, RoleUpdate]):
    """Service pour la gestion des rôles."""
    def __init__(self):
        super().__init__(RoleModel, Role, RoleLight)

    async def create(self, db: AsyncSession, obj_in: RoleCreate) -> RoleLight:
        """Crée un nouveau rôle avec ses permissions."""
        await self.check_unique(db, "nom", obj_in.nom, "nom")
        async with db.begin():
            try:
                db_obj = RoleModel(nom=obj_in.nom)
                db.add(db_obj)
                await db.flush()
                if obj_in.permission_ids:
                    permissions = await db.execute(
                        select(PermissionModel).filter(PermissionModel.id.in_(obj_in.permission_ids))
                    )
                    db_obj.permissions = permissions.scalars().all()
                await db.flush()
                await db.refresh(db_obj)
                return RoleLight.from_orm(db_obj)
            except SQLAlchemyError as e:
                logger.error(f"Erreur lors de la création du rôle: {str(e)}")
                raise HTTPException(
                    status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                    detail="Erreur lors de la création du rôle"
                )

    async def get_all(self, db: AsyncSession, skip: int = 0, limit: int = 100) -> List[RoleLight]:
        """Récupère tous les rôles avec leurs permissions."""
        return await super().get_all(db, skip, limit, [RoleModel.permissions, RoleModel.utilisateurs])

    async def update(self, db: AsyncSession, id: int, obj_in: RoleUpdate) -> Role:
        """Met à jour un rôle avec ses permissions."""
        async with db.begin():
            try:
                db_obj = await self.get_or_404(db, id)
                if obj_in.nom and obj_in.nom != db_obj.nom:
                    await self.check_unique(db, "nom", obj_in.nom, "nom")
                update_data = obj_in.dict(exclude_unset=True)
                if "permission_ids" in update_data:
                    permissions = await db.execute(
                        select(PermissionModel).filter(PermissionModel.id.in_(obj_in.permission_ids))
                    )
                    db_obj.permissions = permissions.scalars().all()
                    del update_data["permission_ids"]
                for key, value in update_data.items():
                    setattr(db_obj, key, value)
                await db.flush()
                await db.refresh(db_obj)
                return Role.from_orm(db_obj)
            except SQLAlchemyError as e:
                logger.error(f"Erreur lors de la mise à jour du rôle: {str(e)}")
                raise HTTPException(
                    status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                    detail="Erreur lors de la mise à jour du rôle"
                )

    async def assign_permission(self, db: AsyncSession, role_id: int, permission_ids: List[int]) -> str:
        """Assigne plusieurs permissions à un rôle sans doublons."""
        async with db.begin():
            try:
                db_role = await self.get_or_404(db, role_id)
                existing_permission_ids = {p.id for p in db_role.permissions}
                permissions_to_add = set(permission_ids) - existing_permission_ids
                
                if not permissions_to_add:
                    return f"Aucune nouvelle permission à assigner au rôle {db_role.nom}"
                
                permissions = await db.execute(
                    select(PermissionModel).filter(PermissionModel.id.in_(permissions_to_add))
                )
                permissions = permissions.scalars().all()
                
                if len(permissions) != len(permissions_to_add):
                    missing_ids = permissions_to_add - {p.id for p in permissions}
                    raise HTTPException(
                        status_code=status.HTTP_404_NOT_FOUND,
                        detail=f"Permissions avec IDs {missing_ids} non trouvées"
                    )
                
                db_role.permissions.extend(permissions)
                await db.flush()
                await db.refresh(db_role)
                return f"{len(permissions_to_add)} permission(s) assignée(s) au rôle {db_role.nom} avec succès"
            except SQLAlchemyError as e:
                logger.error(f"Erreur lors de l'assignation des permissions au rôle {role_id}: {str(e)}")
                raise HTTPException(
                    status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                    detail="Erreur lors de l'assignation des permissions au rôle"
                )

    async def revoke_permission(self, db: AsyncSession, role_id: int, permission_ids: List[int]) -> str:
        """Révoque plusieurs permissions d'un rôle."""
        async with db.begin():
            try:
                db_role = await self.get_or_404(db, role_id)
                existing_permission_ids = {p.id for p in db_role.permissions}
                permissions_to_remove = set(permission_ids) & existing_permission_ids
                
                if not permissions_to_remove:
                    return f"Aucune permission à révoquer pour le rôle {db_role.nom}"
                
                permissions = await db.execute(
                    select(PermissionModel).filter(PermissionModel.id.in_(permissions_to_remove))
                )
                permissions = permissions.scalars().all()
                
                for permission in permissions:
                    db_role.permissions.remove(permission)
                
                await db.flush()
                await db.refresh(db_role)
                return f"{len(permissions_to_remove)} permission(s) révoquée(s) du rôle {db_role.nom} avec succès"
            except SQLAlchemyError as e:
                logger.error(f"Erreur lors de la révocation des permissions du rôle {role_id}: {str(e)}")
                raise HTTPException(
                    status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                    detail="Erreur lors de la révocation des permissions du rôle"
                )
  
# ============================================================================
# ========================= SERVICE DES UTILISATEURS =========================
# ============================================================================

class UtilisateurService(BaseService[UtilisateurModel, Utilisateur, UtilisateurCreate, UtilisateurUpdate]):
    """Service pour la gestion des utilisateurs."""
    def __init__(self):
        super().__init__(UtilisateurModel, Utilisateur, UtilisateurLight)

    def _generate_password(self) -> str:
        """Génère un mot de passe aléatoire sécurisé."""
        alphabet = string.ascii_letters + string.digits + string.punctuation
        return ''.join(secrets.choice(alphabet) for _ in range(12))

    async def create(self, db: AsyncSession, obj_in: UtilisateurCreate) -> UtilisateurLight:
        """Crée un nouvel utilisateur avec mot de passe haché."""
        await self.check_unique(db, "email", obj_in.email, "email")
        async with db.begin():
            try:
                utilisateur_data = obj_in.dict(exclude_unset=True)
                password = self._generate_password()
                utilisateur_data["password"] = pwd_context.hash(password)
                db_obj = UtilisateurModel(**utilisateur_data)
                if obj_in.permission_ids:
                    permissions = await db.execute(
                        select(PermissionModel).filter(PermissionModel.id.in_(obj_in.permission_ids))
                    )
                    db_obj.permissions = permissions.scalars().all()
                if obj_in.role_id:
                    await self.get_or_404(db, obj_in.role_id, RoleModel, "Rôle")
                db.add(db_obj)
                await db.flush()
                await db.refresh(db_obj)
                return UtilisateurLight.from_orm(db_obj)
            except SQLAlchemyError as e:
                logger.error(f"Erreur lors de la création de l'utilisateur: {str(e)}")
                raise HTTPException(
                    status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                    detail="Erreur lors de la création de l'utilisateur"
                )

    async def get_all(self, db: AsyncSession, skip: int = 0, limit: int = 100) -> List[UtilisateurLight]:
        """Récupère tous les utilisateurs avec leurs relations."""
        return await super().get_all(db, skip, limit, [
            UtilisateurModel.role, UtilisateurModel.permissions, UtilisateurModel.inscriptions,
            UtilisateurModel.genotypes, UtilisateurModel.plans_intervention, UtilisateurModel.actualites,
            UtilisateurModel.accreditations, UtilisateurModel.chefs_d_oeuvre, UtilisateurModel.projets_collectifs,
            UtilisateurModel.resultats_evaluations
        ])

    async def update(self, db: AsyncSession, id: int, obj_in: UtilisateurUpdate) -> UtilisateurLight:
        """Met à jour un utilisateur avec validation."""
        async with db.begin():
            try:
                db_obj = await self.get_or_404(db, id)
                if obj_in.email and obj_in.email != db_obj.email:
                    await self.check_unique(db, "email", obj_in.email, "email")
                update_data = obj_in.dict(exclude_unset=True)
                if "password" in update_data:
                    db_obj.password = pwd_context.hash(obj_in.password)
                    del update_data["password"]
                if "permission_ids" in update_data:
                    permissions = await db.execute(
                        select(PermissionModel).filter(PermissionModel.id.in_(obj_in.permission_ids))
                    )
                    db_obj.permissions = permissions.scalars().all()
                    del update_data["permission_ids"]
                if "role_id" in update_data and obj_in.role_id is not None:
                    await self.get_or_404(db, obj_in.role_id, RoleModel, "Rôle")
                for key, value in update_data.items():
                    setattr(db_obj, key, value)
                await db.flush()
                await db.refresh(db_obj)
                return Utilisateur.from_orm(db_obj)
            except SQLAlchemyError as e:
                logger.error(f"Erreur lors de la mise à jour de l'utilisateur: {str(e)}")
                raise HTTPException(
                    status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                    detail="Erreur lors de la mise à jour de l'utilisateur"
                )

    async def change_password(self, db: AsyncSession, utilisateur_id: int, current_password: str, new_password: str) -> str:
        """Change le mot de passe d'un utilisateur après vérification."""
        async with db.begin():
            try:
                db_obj = await self.get_or_404(db, utilisateur_id)
                if not pwd_context.verify(current_password, db_obj.password):
                    raise HTTPException(
                        status_code=status.HTTP_401_UNAUTHORIZED,
                        detail="Mot de passe actuel incorrect"
                    )
                db_obj.password = pwd_context.hash(new_password)
                await db.flush()
                return f"Le mot de passe de l'utilisateur {db_obj.nom} {db_obj.prenom} a été changé avec succès"
            except SQLAlchemyError as e:
                logger.error(f"Erreur lors du changement de mot de passe: {str(e)}")
                raise HTTPException(
                    status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                    detail="Erreur lors du changement de mot de passe"
                )

    async def reset_password(self, db: AsyncSession, email: str) -> str:
        """Génère un token de réinitialisation de mot de passe."""
        async with db.begin():
            try:
                query = select(UtilisateurModel).filter(UtilisateurModel.email == email)
                result = await db.execute(query)
                db_obj = result.scalars().first()
                if not db_obj:
                    raise HTTPException(
                        status_code=status.HTTP_404_NOT_FOUND,
                        detail="Utilisateur avec cet email non trouvé"
                    )
                reset_token = str(uuid4())
                db_obj.reset_token = reset_token
                db_obj.reset_token_expiry = datetime.utcnow() + timedelta(hours=1)
                await db.flush()
                return reset_token
            except SQLAlchemyError as e:
                logger.error(f"Erreur lors de la réinitialisation du mot de passe: {str(e)}")
                raise HTTPException(
                    status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                    detail="Erreur lors de la réinitialisation du mot de passe"
                )

    async def confirm_reset_password(self, db: AsyncSession, reset_token: str) -> None:
        """Confirme la réinitialisation du mot de passe avec un token."""
        async with db.begin():
            try:
                query = select(UtilisateurModel).filter(UtilisateurModel.reset_token == reset_token)
                result = await db.execute(query)
                db_obj = result.scalars().first()
                if not db_obj or db_obj.reset_token_expiry < datetime.utcnow():
                    raise HTTPException(
                        status_code=status.HTTP_400_BAD_REQUEST,
                        detail="Token de réinitialisation invalide ou expiré"
                    )
                new_password = self._generate_password()
                db_obj.password = pwd_context.hash(new_password)
                db_obj.reset_token = None
                db_obj.reset_token_expiry = None
                await db.flush()
            except SQLAlchemyError as e:
                logger.error(f"Erreur lors de la confirmation de réinitialisation: {str(e)}")
                raise HTTPException(
                    status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                    detail="Erreur lors de la confirmation de réinitialisation"
                )

    async def login(self, db: AsyncSession, account: loginSchema) -> dict:
            """Authentifie un utilisateur et retourne un token JWT."""
            try:
                query = select(UtilisateurModel).filter(UtilisateurModel.email == account.email)
                result = await db.execute(query)
                db_obj = result.scalars().first()
                if not db_obj:
                    logger.warning(f"Tentative de connexion avec email non trouvé: {account.email}")
                    raise HTTPException(
                        status_code=status.HTTP_401_UNAUTHORIZED,
                        detail="Email ou mot de passe incorrect"
                    )
                if not pwd_context.verify(account.password, db_obj.password):
                    logger.warning(f"Mot de passe incorrect pour l'utilisateur: {account.email}")
                    raise HTTPException(
                        status_code=status.HTTP_401_UNAUTHORIZED,
                        detail="Email ou mot de passe incorrect"
                    )
                # Générer le token JWT
                payload = {
                    "sub": str(db_obj.id),
                    "email": db_obj.email,
                    "exp": datetime.utcnow() + timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)
                }
                token = jwt.encode(payload, settings.SECRET_KEY, algorithm=settings.ALGORITHM)
                logger.info(f"Connexion réussie pour l'utilisateur: {account.email}")
                return {
                    "access_token": token,
                    "token_type": "bearer"
                }
            except SQLAlchemyError as e:
                logger.error(f"Erreur de base de données lors de la connexion: {str(e)}")
                raise HTTPException(
                    status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                    detail="Erreur lors de la connexion"
                )
                
# ============================================================================
# ========================= SERVICE DES FORMATIONS ===========================
# ============================================================================

class FormationService(BaseService[FormationModel, Formation, FormationCreate, FormationUpdate]):
    """Service pour la gestion des formations."""
    def __init__(self):
        super().__init__(FormationModel, Formation, FormationLight)

    async def create(self, db: AsyncSession, obj_in: FormationCreate) -> FormationLight:
        """Crée une nouvelle formation avec validation de l'unicité du titre."""
        await self.check_unique(db, "titre", obj_in.titre, "titre")
        return await super().create(db, obj_in)

    async def get_all(self, db: AsyncSession, skip: int = 0, limit: int = 100) -> List[Formation]:
        """Récupère toutes les formations avec leurs relations."""
        return await super().get_all(db, skip, limit, [
            FormationModel.modules, FormationModel.inscriptions, FormationModel.projets_collectifs,
            FormationModel.accreditations
        ])


# ============================================================================
# ========================= SERVICE DES INSCRIPTIONS =========================
# ============================================================================

class InscriptionFormationService(BaseService[InscriptionFormationModel, InscriptionFormation, InscriptionFormationCreate, InscriptionFormationUpdate]):
    """Service pour la gestion des inscriptions aux formations."""
    def __init__(self):
        super().__init__(InscriptionFormationModel, InscriptionFormation, InscriptionFormationLight)

    async def create(self, db: AsyncSession, obj_in: InscriptionFormationCreate) -> InscriptionFormationLight:
        """Crée une nouvelle inscription avec validation."""
        async with db.begin():
            try:
                await self.get_or_404(db, obj_in.utilisateur_id, UtilisateurModel, "Utilisateur")
                await self.get_or_404(db, obj_in.formation_id, FormationModel, "Formation")
                query = select(InscriptionFormationModel).filter(
                    InscriptionFormationModel.utilisateur_id == obj_in.utilisateur_id,
                    InscriptionFormationModel.formation_id == obj_in.formation_id
                )
                result = await db.execute(query)
                if result.scalars().first():
                    raise HTTPException(
                        status_code=status.HTTP_409_CONFLICT,
                        detail="L'utilisateur est déjà inscrit à cette formation"
                    )
                return await super().create(db, obj_in)
            except SQLAlchemyError as e:
                logger.error(f"Erreur lors de la création de l'inscription: {str(e)}")
                raise HTTPException(
                    status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                    detail="Erreur lors de la création de l'inscription"
                )

    async def get_all(self, db: AsyncSession, skip: int = 0, limit: int = 100) -> List[InscriptionFormation]:
        """Récupère toutes les inscriptions avec leurs relations."""
        return await super().get_all(db, skip, limit, [
            InscriptionFormationModel.utilisateur, InscriptionFormationModel.formation,
            InscriptionFormationModel.paiements
        ])

    async def update(self, db: AsyncSession, id: int, obj_in: InscriptionFormationUpdate) -> InscriptionFormation:
        """Met à jour une inscription avec validation."""
        async with db.begin():
            try:
                db_obj = await self.get_or_404(db, id)
                formation = await self.get_or_404(db, db_obj.formation_id, FormationModel, "Formation")
                update_data = obj_in.dict(exclude_unset=True)
                
                if "montant_verse" in update_data:
                    if update_data["montant_verse"] > formation.frais:
                        raise HTTPException(
                            status_code=status.HTTP_400_BAD_REQUEST,
                            detail=f"Le montant versé ({update_data['montant_verse']}) dépasse les frais de la formation ({formation.frais})"
                        )
                    update_data["statut_paiement"] = (
                        StatutPaiementEnum.TOTAL if update_data["montant_verse"] == formation.frais
                        else StatutPaiementEnum.PARTIEL if update_data["montant_verse"] > 0
                        else StatutPaiementEnum.AUCUN_VERSEMENT
                    )
                
                if update_data.get("utilisateur_id"):
                    await self.get_or_404(db, update_data["utilisateur_id"], UtilisateurModel, "Utilisateur")
                if update_data.get("formation_id"):
                    await self.get_or_404(db, update_data["formation_id"], FormationModel, "Formation")
                
                for key, value in update_data.items():
                    setattr(db_obj, key, value)
                await db.flush()
                await db.refresh(db_obj)
                return InscriptionFormation.from_orm(db_obj)
            except SQLAlchemyError as e:
                logger.error(f"Erreur lors de la mise à jour de l'inscription: {str(e)}")
                raise HTTPException(
                    status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                    detail="Erreur lors de la mise à jour de l'inscription"
                )

    async def get_with_paiements(self, db: AsyncSession, id: int) -> InscriptionFormation:
        """Récupère une inscription avec ses paiements."""
        try:
            query = select(InscriptionFormationModel).filter(InscriptionFormationModel.id == id).options(
                selectinload(InscriptionFormationModel.paiements),
                selectinload(InscriptionFormationModel.utilisateur),
                selectinload(InscriptionFormationModel.formation)
            )
            result = await db.execute(query)
            db_obj = result.scalars().first()
            if not db_obj:
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail=f"InscriptionFormation avec l'ID {id} non trouvée"
                )
            return InscriptionFormation.from_orm(db_obj)
        except SQLAlchemyError as e:
            logger.error(f"Erreur lors de la récupération de l'inscription avec paiements: {str(e)}")
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Erreur lors de la récupération de l'inscription avec paiements"
            )
      
# ============================================================================
# ========================= SERVICE DES PAIEMENTS ============================
# ============================================================================

class PaiementService(BaseService[PaiementModel, Paiement, PaiementCreate, PaiementUpdate]):
    """Service pour la gestion des paiements."""
    def __init__(self):
        super().__init__(PaiementModel, Paiement, PaiementLight)

    async def create(self, db: AsyncSession, obj_in: PaiementCreate) -> PaiementLight:
        """Crée un nouveau paiement et met à jour l'inscription associée."""
        async with db.begin():
            try:
                inscription = await self.get_or_404(db, obj_in.inscription_id, InscriptionFormationModel, "InscriptionFormation")
                formation = await self.get_or_404(db, inscription.formation_id, FormationModel, "Formation")
                
                total_verse = inscription.montant_verse + obj_in.montant
                if total_verse >= formation.frais:
                    raise HTTPException(
                        status_code=status.HTTP_400_BAD_REQUEST,
                        detail=f"Le montant total ({total_verse}) dépasse les frais de la formation ({formation.frais})"
                    )
                
                db_obj = PaiementModel(**obj_in.dict(exclude_unset=True))
                db.add(db_obj)
                
                inscription.montant_verse = total_verse
                inscription.statut_paiement = (
                    StatutPaiementEnum.TOTAL if total_verse == formation.frais
                    else StatutPaiementEnum.PARTIEL if total_verse > 0
                    else StatutPaiementEnum.AUCUN_VERSEMENT
                )
                db.add(inscription)
                
                await db.flush()
                await db.refresh(db_obj)
                return PaiementLight.from_orm(db_obj)
            except SQLAlchemyError as e:
                logger.error(f"Erreur lors de la création du paiement: {str(e)}")
                raise HTTPException(
                    status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                    detail="Erreur lors de la création du paiement"
                )

    async def update(self, db: AsyncSession, id: int, obj_in: PaiementUpdate) -> Paiement:
        """Met à jour un paiement et l'inscription associée."""
        async with db.begin():
            try:
                db_obj = await self.get_or_404(db, id)
                inscription = await self.get_or_404(db, db_obj.inscription_id, InscriptionFormationModel, "InscriptionFormation")
                formation = await self.get_or_404(db, inscription.formation_id, FormationModel, "Formation")
                
                update_data = obj_in.dict(exclude_unset=True)
                old_montant = db_obj.montant
                
                if "montant" in update_data:
                    total_verse = inscription.montant_verse - old_montant + update_data["montant"]
                    if total_verse > formation.frais:
                        raise HTTPException(
                            status_code=status.HTTP_400_BAD_REQUEST,
                            detail=f"Le montant total ({total_verse}) dépasse les frais de la formation ({formation.frais})"
                        )
                    inscription.montant_verse = total_verse
                    inscription.statut_paiement = (
                        StatutPaiementEnum.TOTAL if total_verse == formation.frais
                        else StatutPaiementEnum.PARTIEL if total_verse > 0
                        else StatutPaiementEnum.AUCUN_VERSEMENT
                    )
                    db.add(inscription)
                
                for key, value in update_data.items():
                    setattr(db_obj, key, value)
                await db.flush()
                await db.refresh(db_obj)
                return Paiement.from_orm(db_obj)
            except SQLAlchemyError as e:
                logger.error(f"Erreur lors de la mise à jour du paiement: {str(e)}")
                raise HTTPException(
                    status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                    detail="Erreur lors de la mise à jour du paiement"
                )

    async def delete(self, db: AsyncSession, id: int) -> None:
        """Supprime un paiement et met à jour l'inscription associée."""
        async with db.begin():
            try:
                db_obj = await self.get_or_404(db, id)
                inscription = await self.get_or_404(db, db_obj.inscription_id, InscriptionFormationModel, "InscriptionFormation")
                formation = await self.get_or_404(db, inscription.formation_id, FormationModel, "Formation")
                
                inscription.montant_verse -= db_obj.montant
                inscription.statut_paiement = (
                    StatutPaiementEnum.TERMINE if inscription.montant_verse >= formation.frais
                    else StatutPaiementEnum.VERSEMENT_PARTIEL if inscription.montant_verse > 0
                    else StatutPaiementEnum.AUCUN_VERSEMENT
                )
                db.add(inscription)
                
                await db.delete(db_obj)
                await db.flush()
            except SQLAlchemyError as e:
                logger.error(f"Erreur lors de la suppression du paiement: {str(e)}")
                raise HTTPException(
                    status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                    detail="Erreur lors de la suppression du paiement"
                )

    async def get_by_inscription(self, db: AsyncSession, inscription_id: int, skip: int = 0, limit: int = 100) -> List[Paiement]:
        """Récupère tous les paiements pour une inscription donnée."""
        try:
            query = select(PaiementModel).filter(PaiementModel.inscription_id == inscription_id).offset(skip).limit(limit).options(
                selectinload(PaiementModel.inscription)
            )
            result = await db.execute(query)
            return [Paiement.from_orm(obj) for obj in result.scalars().all()]
        except SQLAlchemyError as e:
            logger.error(f"Erreur lors de la récupération des paiements: {str(e)}")
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Erreur lors de la récupération des paiements"
            )

# ============================================================================
# ========================= SERVICE DES MODULES ==============================
# ============================================================================

class ModuleService(BaseService[ModuleModel, Module, ModuleCreate, ModuleUpdate]):
    """Service pour la gestion des modules."""
    def __init__(self):
        super().__init__(ModuleModel, Module, ModuleLight)

    async def create(self, db: AsyncSession, obj_in: ModuleCreate) -> ModuleLight:
        """Crée un nouveau module avec validation et définition automatique de l'ordre."""
        async with db.begin():
            try:
                # Vérifier l'existence de la formation
                await self.get_or_404(db, obj_in.formation_id, FormationModel, "Formation")

                # Récupérer le maximum de l'ordre pour les modules de cette formation
                query = select(ModuleModel.ordre).filter(ModuleModel.formation_id == obj_in.formation_id)
                result = await db.execute(query)
                existing_orders = result.scalars().all()
                ordre = max(existing_orders, default=0) + 1

                # Ajouter l'ordre au dictionnaire des données
                module_data = obj_in.dict(exclude_unset=True)
                module_data["ordre"] = ordre

                # Créer le module
                db_obj = ModuleModel(**module_data)
                db.add(db_obj)
                await db.flush()
                await db.refresh(db_obj)
                return ModuleLight.from_orm(db_obj)
            except IntegrityError as e:
                logger.error(f"Erreur d'intégrité lors de la création du module: {str(e)}")
                raise HTTPException(
                    status_code=status.HTTP_409_CONFLICT,
                    detail="Un module avec ces données existe déjà"
                )
            except SQLAlchemyError as e:
                logger.error(f"Erreur lors de la création du module: {str(e)}")
                raise HTTPException(
                    status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                    detail="Erreur lors de la création du module"
                )

    async def get_all(self, db: AsyncSession, skip: int = 0, limit: int = 100) -> List[Module]:
        """Récupère tous les modules avec leurs relations."""
        return await super().get_all(db, skip, limit, [
            ModuleModel.formation, ModuleModel.ressources, ModuleModel.evaluations, ModuleModel.chefs_d_oeuvre
        ])

    async def update(self, db: AsyncSession, id: int, obj_in: ModuleUpdate) -> Module:
        """Met à jour un module avec validation."""
        if obj_in.formation_id is not None:
            await self.get_or_404(db, obj_in.formation_id, FormationModel, "Formation")
        return await super().update(db, id, obj_in)
    
    async def delete(self, db: AsyncSession, id: int) -> str:
        """Supprime un module et réordonne automatiquement les modules restants par created_at."""
        async with db.begin():
            try:
                # Récupérer le module à supprimer pour obtenir sa formation_id
                db_obj = await self.get_or_404(db, id)
                formation_id = db_obj.formation_id

                # Supprimer le module
                await db.delete(db_obj)
                await db.flush()

                # Récupérer tous les modules restants pour la formation, triés par created_at
                query = select(ModuleModel).filter(ModuleModel.formation_id == formation_id).order_by(ModuleModel.created_at.asc())
                result = await db.execute(query)
                remaining_modules = result.scalars().all()

                # Réassigner les ordres en commençant par 1
                for index, module in enumerate(remaining_modules, start=1):
                    module.ordre = index
                    db.add(module)

                await db.flush()
                return f"Module {id} supprimé avec succès et ordres réassignés pour cette formation"
            except SQLAlchemyError as e:
                logger.error(f"Erreur lors de la suppression du module {id} ou du réordonnancement: {str(e)}")
                raise HTTPException(
                    status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                    detail="Erreur lors de la suppression du module ou du réordonnancement"
                )

# ============================================================================
# ========================= SERVICE DES RESSOURCES ===========================
# ============================================================================

class RessourceService(BaseService[RessourceModel, Ressource, RessourceCreate, RessourceUpdate]):
    """Service pour la gestion des ressources pédagogiques."""
    def __init__(self):
        super().__init__(RessourceModel, Ressource, RessourceLight)

    async def create(self, db: AsyncSession, obj_in: RessourceCreate) -> RessourceLight:
        """Crée une nouvelle ressource avec validation."""
        await self.get_or_404(db, obj_in.module_id, ModuleModel, "Module")
        return await super().create(db, obj_in)

    async def get_all(self, db: AsyncSession, skip: int = 0, limit: int = 100) -> List[Ressource]:
        """Récupère toutes les ressources avec leurs relations."""
        return await super().get_all(db, skip, limit, [RessourceModel.module])

    async def update(self, db: AsyncSession, id: int, obj_in: RessourceUpdate) -> Ressource:
        """Met à jour une ressource avec validation."""
        if obj_in.module_id is not None:
            await self.get_or_404(db, obj_in.module_id, ModuleModel, "Module")
        return await super().update(db, id, obj_in)

# ============================================================================
# ========================= SERVICE DES CHEFS-D'ŒUVRE ========================
# ============================================================================

class ChefDOeuvreService(BaseService[ChefDOeuvreModel, ChefDOeuvre, ChefDOeuvreCreate, ChefDOeuvreUpdate]):
    """Service pour la gestion des chefs-d'œuvre."""
    def __init__(self):
        super().__init__(ChefDOeuvreModel, ChefDOeuvre, ChefDOeuvreLight)

    async def create(self, db: AsyncSession, obj_in: ChefDOeuvreCreate) -> ChefDOeuvreLight:
        """Crée un nouveau chef-d'œuvre avec validation."""
        await self.get_or_404(db, obj_in.utilisateur_id, UtilisateurModel, "Utilisateur")
        await self.get_or_404(db, obj_in.module_id, ModuleModel, "Module")
        return await super().create(db, obj_in)

    async def get_all(self, db: AsyncSession, skip: int = 0, limit: int = 100) -> List[ChefDOeuvre]:
        """Récupère tous les chefs-d'œuvre avec leurs relations."""
        return await super().get_all(db, skip, limit, [ChefDOeuvreModel.utilisateur, ChefDOeuvreModel.module])

    async def update(self, db: AsyncSession, id: int, obj_in: ChefDOeuvreUpdate) -> ChefDOeuvre:
        """Met à jour un chef-d'œuvre avec validation."""
        if obj_in.utilisateur_id is not None:
            await self.get_or_404(db, obj_in.utilisateur_id, UtilisateurModel, "Utilisateur")
        if obj_in.module_id is not None:
            await self.get_or_404(db, obj_in.module_id, ModuleModel, "Module")
        return await super().update(db, id, obj_in)

       

# ============================================================================
# ========================= SERVICE DES PROJETS COLLECTIFS ===================
# ============================================================================

class ProjetCollectifService(BaseService[ProjetCollectifModel, ProjetCollectif, ProjetCollectifCreate, ProjetCollectifUpdate]):
    """Service pour la gestion des projets collectifs."""
    def __init__(self):
        super().__init__(ProjetCollectifModel, ProjetCollectif, ProjetCollectifLight)

    async def create(self, db: AsyncSession, obj_in: ProjetCollectifCreate) -> ProjetCollectifLight:
        """Crée un nouveau projet collectif avec ses membres."""
        async with db.begin():
            try:
                await self.get_or_404(db, obj_in.formation_id, FormationModel, "Formation")
                db_obj = ProjetCollectifModel(**obj_in.dict(exclude={"membres_ids"}))
                db.add(db_obj)
                await db.flush()
                if obj_in.membres_ids:
                    membres = await db.execute(
                        select(UtilisateurModel).filter(UtilisateurModel.id.in_(obj_in.membres_ids))
                    )
                    db_obj.membres = membres.scalars().all()
                await db.flush()
                await db.refresh(db_obj)
                return ProjetCollectifLight.from_orm(db_obj)
            except SQLAlchemyError as e:
                logger.error(f"Erreur lors de la création du projet collectif: {str(e)}")
                raise HTTPException(
                    status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                    detail="Erreur lors de la création du projet collectif"
                )

    async def get_all(self, db: AsyncSession, skip: int = 0, limit: int = 100) -> List[ProjetCollectif]:
        """Récupère tous les projets collectifs avec leurs relations."""
        return await super().get_all(db, skip, limit, [ProjetCollectifModel.formation, ProjetCollectifModel.membres])

    async def update(self, db: AsyncSession, id: int, obj_in: ProjetCollectifUpdate) -> ProjetCollectif:
        """Met à jour un projet collectif avec ses membres."""
        async with db.begin():
            try:
                db_obj = await self.get_or_404(db, id)
                update_data = obj_in.dict(exclude_unset=True)
                if update_data.get("formation_id"):
                    await self.get_or_404(db, update_data["formation_id"], FormationModel, "Formation")
                if "membres_ids" in update_data:
                    membres = await db.execute(
                        select(UtilisateurModel).filter(UtilisateurModel.id.in_(obj_in.membres_ids))
                    )
                    db_obj.membres = membres.scalars().all()
                    del update_data["membres_ids"]
                for key, value in update_data.items():
                    setattr(db_obj, key, value)
                await db.flush()
                await db.refresh(db_obj)
                return ProjetCollectif.from_orm(db_obj)
            except SQLAlchemyError as e:
                logger.error(f"Erreur lors de la mise à jour du projet collectif: {str(e)}")
                raise HTTPException(
                    status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                    detail="Erreur lors de la mise à jour du projet collectif"
                )

    async def add_membre(self, db: AsyncSession, projet_id: int, utilisateur_id: int) -> ProjetCollectif:
        """Ajoute un membre à un projet collectif."""
        return await self.assign_relationship(db, projet_id, utilisateur_id, UtilisateurModel, "membres", "Utilisateur")

    async def remove_membre(self, db: AsyncSession, projet_id: int, utilisateur_id: int) -> ProjetCollectif:
        """Supprime un membre d'un projet collectif."""
        return await self.revoke_relationship(db, projet_id, utilisateur_id, UtilisateurModel, "membres", "Utilisateur")

# ============================================================================
# ========================= SERVICE DES ÉVALUATIONS ==========================
# ============================================================================

class EvaluationService(BaseService[EvaluationModel, Evaluation, EvaluationCreate, EvaluationUpdate]):
    """Service pour la gestion des évaluations."""
    def __init__(self):
        super().__init__(EvaluationModel, Evaluation, EvaluationLight)

    async def create(self, db: AsyncSession, obj_in: EvaluationCreate) -> EvaluationLight:
        """Crée une nouvelle évaluation avec validation."""
        await self.get_or_404(db, obj_in.module_id, ModuleModel, "Module")
        return await super().create(db, obj_in)

    async def get_all(self, db: AsyncSession, skip: int = 0, limit: int = 100) -> List[Evaluation]:
        """Récupère toutes les évaluations avec leurs relations."""
        return await super().get_all(db, skip, limit, [EvaluationModel.module, EvaluationModel.questions, EvaluationModel.resultats])

    async def update(self, db: AsyncSession, id: int, obj_in: EvaluationUpdate) -> Evaluation:
        """Met à jour une évaluation avec validation."""
        if obj_in.module_id is not None:
            await self.get_or_404(db, obj_in.module_id, ModuleModel, "Module")
        return await super().update(db, id, obj_in)

# ============================================================================
# ========================= SERVICE DES QUESTIONS ============================
# ============================================================================

class QuestionService(BaseService[QuestionModel, Question, QuestionCreate, QuestionUpdate]):
    """Service pour la gestion des questions d'évaluation."""
    def __init__(self):
        super().__init__(QuestionModel, Question, QuestionLight)

    async def create(self, db: AsyncSession, obj_in: QuestionCreate) -> QuestionLight:
        """Crée une nouvelle question avec ses propositions."""
        async with db.begin():
            try:
                await self.get_or_404(db, obj_in.evaluation_id, EvaluationModel, "Évaluation")
                db_obj = QuestionModel(**obj_in.dict(exclude={"propositions"}))
                db.add(db_obj)
                await db.flush()
                if obj_in.propositions:
                    for prop in obj_in.propositions:
                        db_prop = PropositionModel(**prop.dict(), question_id=db_obj.id)
                        db.add(db_prop)
                await db.flush()
                await db.refresh(db_obj)
                return QuestionLight.from_orm(db_obj)
            except SQLAlchemyError as e:
                logger.error(f"Erreur lors de la création de la question: {str(e)}")
                raise HTTPException(
                    status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                    detail="Erreur lors de la création de la question"
                )

    async def get_all(self, db: AsyncSession, skip: int = 0, limit: int = 100) -> List[Question]:
        """Récupère toutes les questions avec leurs relations."""
        return await super().get_all(db, skip, limit, [QuestionModel.evaluation, QuestionModel.propositions])

    async def update(self, db: AsyncSession, id: int, obj_in: QuestionUpdate) -> Question:
        """Met à jour une question avec ses propositions."""
        async with db.begin():
            try:
                db_obj = await self.get_or_404(db, id)
                update_data = obj_in.dict(exclude_unset=True)
                if update_data.get("evaluation_id"):
                    await self.get_or_404(db, update_data["evaluation_id"], EvaluationModel, "Évaluation")
                if "propositions" in update_data:
                    db_obj.propositions = []
                    for prop in obj_in.propositions:
                        db_prop = PropositionModel(**prop.dict(), question_id=db_obj.id)
                        db_obj.propositions.append(db_prop)
                    del update_data["propositions"]
                for key, value in update_data.items():
                    setattr(db_obj, key, value)
                await db.flush()
                await db.refresh(db_obj)
                return Question.from_orm(db_obj)
            except SQLAlchemyError as e:
                logger.error(f"Erreur lors de la mise à jour de la question: {str(e)}")
                raise HTTPException(
                    status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                    detail="Erreur lors de la mise à jour de la question"
                )

# ============================================================================
# ========================= SERVICE DES PROPOSITIONS =========================
# ============================================================================

class PropositionService(BaseService[PropositionModel, Proposition, PropositionCreate, PropositionUpdate]):
    """Service pour la gestion des propositions de questions."""
    def __init__(self):
        super().__init__(PropositionModel, Proposition, PropositionLight)

    async def create(self, db: AsyncSession, obj_in: PropositionCreate) -> PropositionLight:
        """Crée une nouvelle proposition avec validation."""
        await self.get_or_404(db, obj_in.question_id, QuestionModel, "Question")
        return await super().create(db, obj_in)

    async def get_all(self, db: AsyncSession, skip: int = 0, limit: int = 100) -> List[Proposition]:
        """Récupère toutes les propositions avec leurs relations."""
        return await super().get_all(db, skip, limit, [PropositionModel.question])

    async def update(self, db: AsyncSession, id: int, obj_in: PropositionUpdate) -> Proposition:
        """Met à jour une proposition avec validation."""
        if obj_in.question_id is not None:
            await self.get_or_404(db, obj_in.question_id, QuestionModel, "Question")
        return await super().update(db, id, obj_in)

# ============================================================================
# ========================= SERVICE DES RÉSULTATS D'ÉVALUATION ===============
# ============================================================================

class ResultatEvaluationService(BaseService[ResultatEvaluationModel, ResultatEvaluation, ResultatEvaluationCreate, ResultatEvaluationUpdate]):
    """Service pour la gestion des résultats d'évaluation."""
    def __init__(self):
        super().__init__(ResultatEvaluationModel, ResultatEvaluation, ResultatEvaluationLight)

    async def create(self, db: AsyncSession, obj_in: ResultatEvaluationCreate) -> ResultatEvaluationLight:
        """Crée un nouveau résultat d'évaluation avec validation."""
        await self.get_or_404(db, obj_in.utilisateur_id, UtilisateurModel, "Utilisateur")
        await self.get_or_404(db, obj_in.evaluation_id, EvaluationModel, "Évaluation")
        return await super().create(db, obj_in)

    async def get_all(self, db: AsyncSession, skip: int = 0, limit: int = 100) -> List[ResultatEvaluation]:
        """Récupère tous les résultats d'évaluation avec leurs relations."""
        return await super().get_all(db, skip, limit, [ResultatEvaluationModel.utilisateur, ResultatEvaluationModel.evaluation])

    async def update(self, db: AsyncSession, id: int, obj_in: ResultatEvaluationUpdate) -> ResultatEvaluation:
        """Met à jour un résultat d'évaluation avec validation."""
        if obj_in.utilisateur_id is not None:
            await self.get_or_404(db, obj_in.utilisateur_id, UtilisateurModel, "Utilisateur")
        if obj_in.evaluation_id is not None:
            await self.get_or_404(db, obj_in.evaluation_id, EvaluationModel, "Évaluation")
        return await super().update(db, id, obj_in)

# ============================================================================
# ========================= SERVICE DES GÉNOTYPES ============================
# ============================================================================

class GenotypeIndividuelService(BaseService[GenotypeIndividuelModel, GenotypeIndividuel, GenotypeIndividuelCreate, GenotypeIndividuelUpdate]):
    """Service pour la gestion des génotypes individuels."""
    def __init__(self):
        super().__init__(GenotypeIndividuelModel, GenotypeIndividuel, GenotypeIndividuelLight)

    async def create(self, db: AsyncSession, obj_in: GenotypeIndividuelCreate) -> GenotypeIndividuelLight:
        """Crée un nouveau génotype individuel avec validation."""
        await self.get_or_404(db, obj_in.utilisateur_id, UtilisateurModel, "Utilisateur")
        return await super().create(db, obj_in)

    async def get_all(self, db: AsyncSession, skip: int = 0, limit: int = 100) -> List[GenotypeIndividuel]:
        """Récupère tous les génotypes individuels avec leurs relations."""
        return await super().get_all(db, skip, limit, [
            GenotypeIndividuelModel.utilisateur, GenotypeIndividuelModel.ascendance,
            GenotypeIndividuelModel.sante, GenotypeIndividuelModel.education
        ])

    async def update(self, db: AsyncSession, id: int, obj_in: GenotypeIndividuelUpdate) -> GenotypeIndividuel:
        """Met à jour un génotype individuel avec validation."""
        if obj_in.utilisateur_id is not None:
            await self.get_or_404(db, obj_in.utilisateur_id, UtilisateurModel, "Utilisateur")
        return await super().update(db, id, obj_in)

# ============================================================================
# ========================= SERVICE DES ASCENDANCES ==========================
# ============================================================================

class AscendanceGenotypeService(BaseService[AscendanceGenotypeModel, AscendanceGenotype, AscendanceGenotypeCreate, AscendanceGenotypeUpdate]):
    """Service pour la gestion des informations d'ascendance des génotypes."""
    def __init__(self):
        super().__init__(AscendanceGenotypeModel, AscendanceGenotype, AscendanceGenotypeLight)

    async def create(self, db: AsyncSession, obj_in: AscendanceGenotypeCreate) -> AscendanceGenotypeLight:
        """Crée une nouvelle ascendance de génotype avec validation."""
        await self.get_or_404(db, obj_in.genotype_id, GenotypeIndividuelModel, "Génotype")
        return await super().create(db, obj_in)

    async def get_all(self, db: AsyncSession, skip: int = 0, limit: int = 100) -> List[AscendanceGenotype]:
        """Récupère toutes les ascendances de génotypes avec leurs relations."""
        return await super().get_all(db, skip, limit, [AscendanceGenotypeModel.genotype])

    async def update(self, db: AsyncSession, id: int, obj_in: AscendanceGenotypeUpdate) -> AscendanceGenotype:
        """Met à jour une ascendance de génotype avec validation."""
        if obj_in.genotype_id is not None:
            await self.get_or_404(db, obj_in.genotype_id, GenotypeIndividuelModel, "Génotype")
        return await super().update(db, id, obj_in)

# ============================================================================
# ========================= SERVICE DES SANTÉS GÉNOTYPE ======================
# ============================================================================

class SanteGenotypeService(BaseService[SanteGenotypeModel, SanteGenotype, SanteGenotypeCreate, SanteGenotypeUpdate]):
    """Service pour la gestion des informations de santé des génotypes."""
    def __init__(self):
        super().__init__(SanteGenotypeModel, SanteGenotype, SanteGenotypeLight)

    async def create(self, db: AsyncSession, obj_in: SanteGenotypeCreate) -> SanteGenotypeLight:
        """Crée une nouvelle information de santé de génotype avec validation."""
        await self.get_or_404(db, obj_in.genotype_id, GenotypeIndividuelModel, "Génotype")
        return await super().create(db, obj_in)

    async def get_all(self, db: AsyncSession, skip: int = 0, limit: int = 100) -> List[SanteGenotype]:
        """Récupère toutes les informations de santé des génotypes avec leurs relations."""
        return await super().get_all(db, skip, limit, [SanteGenotypeModel.genotype])

    async def update(self, db: AsyncSession, id: int, obj_in: SanteGenotypeUpdate) -> SanteGenotype:
        """Met à jour une information de santé de génotype avec validation."""
        if obj_in.genotype_id is not None:
            await self.get_or_404(db, obj_in.genotype_id, GenotypeIndividuelModel, "Génotype")
        return await super().update(db, id, obj_in)

# ============================================================================
# ========================= SERVICE DES ÉDUCATIONS GÉNOTYPE ==================
# ============================================================================

class EducationGenotypeService(BaseService[EducationGenotypeModel, EducationGenotype, EducationGenotypeCreate, EducationGenotypeUpdate]):
    """Service pour la gestion des informations d'éducation des génotypes."""
    def __init__(self):
        super().__init__(EducationGenotypeModel, EducationGenotype, EducationGenotypeLight)

    async def create(self, db: AsyncSession, obj_in: EducationGenotypeCreate) -> EducationGenotypeLight:
        """Crée une nouvelle information d'éducation de génotype avec validation."""
        await self.get_or_404(db, obj_in.genotype_id, GenotypeIndividuelModel, "Génotype")
        return await super().create(db, obj_in)

    async def get_all(self, db: AsyncSession, skip: int = 0, limit: int = 100) -> List[EducationGenotype]:
        """Récupère toutes les informations d'éducation des génotypes avec leurs relations."""
        return await super().get_all(db, skip, limit, [EducationGenotypeModel.genotype])

    async def update(self, db: AsyncSession, id: int, obj_in: EducationGenotypeUpdate) -> EducationGenotype:
        """Met à jour une information d'éducation de génotype avec validation."""
        if obj_in.genotype_id is not None:
            await self.get_or_404(db, obj_in.genotype_id, GenotypeIndividuelModel, "Génotype")
        return await super().update(db, id, obj_in)

# ============================================================================
# ========================= SERVICE DES PLANS D'INTERVENTION =================
# ============================================================================

class PlanInterventionIndividualiseService(BaseService[PlanInterventionIndividualiseModel, PlanInterventionIndividualise, PlanInterventionIndividualiseCreate, PlanInterventionIndividualiseUpdate]):
    """Service pour la gestion des plans d'intervention individualisés."""
    def __init__(self):
        super().__init__(PlanInterventionIndividualiseModel, PlanInterventionIndividualise, PlanInterventionIndividualiseLight)

    async def create(self, db: AsyncSession, obj_in: PlanInterventionIndividualiseCreate) -> PlanInterventionIndividualiseLight:
        """Crée un nouveau plan d'intervention avec validation."""
        await self.get_or_404(db, obj_in.utilisateur_id, UtilisateurModel, "Utilisateur")
        return await super().create(db, obj_in)

    async def get_all(self, db: AsyncSession, skip: int = 0, limit: int = 100) -> List[PlanInterventionIndividualise]:
        """Récupère tous les plans d'intervention avec leurs relations."""
        return await super().get_all(db, skip, limit, [PlanInterventionIndividualiseModel.utilisateur])

    async def update(self, db: AsyncSession, id: int, obj_in: PlanInterventionIndividualiseUpdate) -> PlanInterventionIndividualise:
        """Met à jour un plan d'intervention avec validation."""
        if obj_in.utilisateur_id is not None:
            await self.get_or_404(db, obj_in.utilisateur_id, UtilisateurModel, "Utilisateur")
        return await super().update(db, id, obj_in)

# ============================================================================
# ========================= SERVICE DES ACCRÉDITATIONS =======================
# ============================================================================

class AccreditationService(BaseService[AccreditationModel, Accreditation, AccreditationCreate, AccreditationUpdate]):
    """Service pour la gestion des accréditations."""
    def __init__(self):
        super().__init__(AccreditationModel, Accreditation, AccreditationLight)

    async def create(self, db: AsyncSession, obj_in: AccreditationCreate) -> AccreditationLight:
        """Crée une nouvelle accréditation avec validation."""
        await self.get_or_404(db, obj_in.utilisateur_id, UtilisateurModel, "Utilisateur")
        await self.get_or_404(db, obj_in.formation_id, FormationModel, "Formation")
        return await super().create(db, obj_in)

    async def get_all(self, db: AsyncSession, skip: int = 0, limit: int = 100) -> List[Accreditation]:
        """Récupère toutes les accréditations avec leurs relations."""
        return await super().get_all(db, skip, limit, [AccreditationModel.utilisateur, AccreditationModel.formation])

    async def update(self, db: AsyncSession, id: int, obj_in: AccreditationUpdate) -> Accreditation:
        """Met à jour une accréditation avec validation."""
        if obj_in.utilisateur_id is not None:
            await self.get_or_404(db, obj_in.utilisateur_id, UtilisateurModel, "Utilisateur")
        if obj_in.formation_id is not None:
            await self.get_or_404(db, obj_in.formation_id, FormationModel, "Formation")
        return await super().update(db, id, obj_in)

# ============================================================================
# ========================= SERVICE DES ACTUALITÉS ===========================
# ============================================================================

class ActualiteService(BaseService[ActualiteModel, Actualite, ActualiteCreate, ActualiteUpdate]):
    """Service pour la gestion des actualités."""
    def __init__(self):
        super().__init__(ActualiteModel, Actualite, ActualiteLight)

    async def create(self, db: AsyncSession, obj_in: ActualiteCreate) -> ActualiteLight:
        """Crée une nouvelle actualité avec validation de l'unicité du slug."""
        await self.check_unique(db, "slug", obj_in.slug, "slug")
        await self.get_or_404(db, obj_in.utilisateur_id, UtilisateurModel, "Utilisateur")
        return await super().create(db, obj_in)

    async def get_all(self, db: AsyncSession, skip: int = 0, limit: int = 100) -> List[Actualite]:
        """Récupère toutes les actualités avec leurs relations."""
        return await super().get_all(db, skip, limit, [ActualiteModel.utilisateur])

    async def update(self, db: AsyncSession, id: int, obj_in: ActualiteUpdate) -> Actualite:
        """Met à jour une actualité avec validation."""
        if obj_in.slug:
            db_obj = await self.get_or_404(db, id)
            if obj_in.slug != db_obj.slug:
                await self.check_unique(db, "slug", obj_in.slug, "slug")
        if obj_in.utilisateur_id is not None:
            await self.get_or_404(db, obj_in.utilisateur_id, UtilisateurModel, "Utilisateur")
        return await super().update(db, id, obj_in)
       
       
                
                