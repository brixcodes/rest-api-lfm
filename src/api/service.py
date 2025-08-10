from datetime import datetime, timedelta, timezone
import os
import traceback
import aiofiles
from pathlib import Path
import secrets
import string
from typing import TypeVar, Generic, List, Type, Any, Optional
from uuid import uuid4
import uuid
from pydantic import ValidationError
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from sqlalchemy.orm import selectinload
from sqlalchemy.exc import IntegrityError, SQLAlchemyError
from sqlalchemy import func, insert, delete
from fastapi import HTTPException, Request, UploadFile, status
from passlib.context import CryptContext
import logging
from jose import JWTError, jwt
from src.util.database.setting import settings
from src.util.helper.enum import (
    FileTypeEnum, StatutCompteEnum, StatutFormationEnum, StatutInscriptionEnum,
    StatutProjetIndividuelEnum, StatutProjetCollectifEnum, StatutEnum,
    PermissionEnum, RoleEnum, EvaluationTypeEnum, GenotypeTypeEnum,
    SexeEnum, StatutPaiementEnum, MethodePaiementEnum
)
from src.api.schema import (
    Permission, PermissionLight, PermissionCreate, PermissionUpdate,
    Role, RoleLight, RoleCreate, RoleUpdate, PermissionMinLight,
    Utilisateur, UtilisateurLight, UtilisateurCreate, UtilisateurMinLight, UtilisateurUpdate,
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
from src.util.helper.email.email import EmailService

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
        query = select(model).filter(model.id == id).options(
            selectinload("*")  # Charge toutes les relations définies
        )
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
        try:
            db_obj = self.model(**obj_in.dict(exclude_unset=True))
            db.add(db_obj)
            await db.flush()
            await db.refresh(db_obj)
            return await self._safe_from_orm(db_obj, self.light_schema)
        except IntegrityError as e:
            logger.error(f"Erreur d'intégrité lors de la création de {self.entity_name}: {str(e)}", exc_info=True)
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
        """Récupère une entité par ID avec ses relations."""
        try:
            query = select(self.model).filter(self.model.id == id).options(
                selectinload("*")  # Charge toutes les relations définies
            )
            result = await db.execute(query)
            db_obj = result.scalars().first()
            if not db_obj:
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail=f"{self.entity_name} avec l'ID {id} non trouvé"
                )
            return await self._safe_from_orm(db_obj, self.schema)
        except SQLAlchemyError as e:
            logger.error(f"Erreur de base de données lors de la récupération de {self.entity_name}: {str(e)}", exc_info=True)
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
            return [await self._safe_from_orm(obj, self.schema) for obj in result.scalars().all()]
        except SQLAlchemyError as e:
            logger.error(f"Erreur de base de données lors de la récupération des {self.entity_name}s: {str(e)}", exc_info=True)
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"Erreur de base de données lors de la récupération des {self.entity_name}s"
            )

    async def _safe_from_orm(self, db_obj, schema_class):
        """Sérialise un objet SQLAlchemy de manière sûre en évitant les relations lazy."""
        try:
            return schema_class.model_validate(db_obj)
        except Exception as e:
            if "MissingGreenlet" in str(e) or "greenlet_spawn" in str(e):
                # Si c'est un problème de relation lazy, utiliser le light_schema
                return self.light_schema.model_validate(db_obj)
            else:
                raise e

    async def update(self, db: AsyncSession, id: int, obj_in: UpdateSchemaType) -> SchemaType:
        """Met à jour une entité."""
        try:
            db_obj = await self.get_or_404(db, id)
            update_data = obj_in.model_dump(exclude_unset=True)
            for key, value in update_data.items():
                setattr(db_obj, key, value)
            db.add(db_obj)
            await db.flush()
            await db.refresh(db_obj)
            # Utiliser la méthode sûre pour éviter les problèmes de relations lazy
            return await self._safe_from_orm(db_obj, self.schema)
        except IntegrityError as e:
            logger.error(f"Erreur d'intégrité lors de la mise à jour de {self.entity_name}: {str(e)}", exc_info=True)
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail=f"{self.entity_name} existe déjà"
            )
        except SQLAlchemyError as e:
            logger.error(f"Erreur de base de données lors de la mise à jour de {self.entity_name}: {str(e)}", exc_info=True)
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"Erreur de base de données lors de la mise à jour de {self.entity_name}"
            )

    async def delete(self, db: AsyncSession, id: int) -> None:
        """Supprime une entité."""
        try:
            db_obj = await self.get_or_404(db, id)
            await db.delete(db_obj)
            await db.flush()
        except SQLAlchemyError as e:
            logger.error(f"Erreur de base de données lors de la suppression de {self.entity_name}: {str(e)}", exc_info=True)
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"Erreur de base de données lors de la suppression de {self.entity_name}"
            )

    async def assign_relationship(self, db: AsyncSession, id: int, related_id: int, related_model: Type, related_field: str, related_name: str) -> SchemaType:
        """Assigne une relation à une entité."""
        try:
            db_obj = await self.get_or_404(db, id)
            related_obj = await self.get_or_404(db, related_id, related_model, related_name)
            related_list = getattr(db_obj, related_field)
            if related_obj not in related_list:
                related_list.append(related_obj)
                await db.flush()
            return await self._safe_from_orm(db_obj, self.schema)
        except SQLAlchemyError as e:
            logger.error(f"Erreur lors de l'assignation de {related_name} à {self.entity_name}: {str(e)}", exc_info=True)
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"Erreur lors de l'assignation de {related_name} à {self.entity_name}"
            )

    async def revoke_relationship(self, db: AsyncSession, id: int, related_id: int, related_model: Type, related_field: str, related_name: str) -> SchemaType:
        """Révoque une relation d'une entité."""
        try:
            db_obj = await self.get_or_404(db, id)
            related_obj = await self.get_or_404(db, related_id, related_model, related_name)
            related_list = getattr(db_obj, related_field)
            if related_obj in related_list:
                related_list.remove(related_obj)
                await db.flush()
            return await self._safe_from_orm(db_obj, self.schema)
        except SQLAlchemyError as e:
            logger.error(f"Erreur lors de la révocation de {related_name} de {self.entity_name}: {str(e)}", exc_info=True)
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
            "storage_path": "static/documents",
            "url_prefix": "/static/documents",
        },
        FileTypeEnum.IMAGE: {
            "extensions": {".jpg", ".jpeg", ".png"},
            "max_size_mb": 20,
            "storage_path": "static/images",
            "url_prefix": "/static/images",
        },
        FileTypeEnum.AUDIO: {
            "extensions": {".mp3", ".wav", ".ogg"},
            "max_size_mb": 150,
            "storage_path": "static/audios",
            "url_prefix": "/static/audios",
        },
        FileTypeEnum.VIDEO: {
            "extensions": {".mp4", ".avi", ".mkv"},
            "max_size_mb": 300,
            "storage_path": "static/videos",
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
                if not storage_path.exists():
                    storage_path.mkdir(parents=True, exist_ok=True)
                    logger.info(f"Répertoire {storage_path} créé pour {file_type.value}.")
                else:
                    logger.info(f"Répertoire {storage_path} existe déjà pour {file_type.value}.")

                # Essayer de définir les permissions, mais ne pas échouer si impossible
                if os.name != "nt":
                    try:
                        os.chmod(storage_path, 0o755)
                        logger.debug(f"Permissions 755 appliquées à {storage_path}")
                    except PermissionError as e:
                        logger.warning(f"Impossible de changer les permissions pour {storage_path}: {e}")

            except PermissionError as e:
                # Si le répertoire existe déjà, continuer sans erreur
                if storage_path.exists():
                    logger.warning(f"Le répertoire {storage_path} existe mais permissions insuffisantes pour le modifier: {e}")
                else:
                    # Si on ne peut pas créer le répertoire, log l'erreur mais ne pas faire planter l'app
                    logger.error(f"Impossible de créer le répertoire {storage_path} pour {file_type.value}: {e}")
                    logger.warning(f"L'upload de fichiers {file_type.value} pourrait ne pas fonctionner correctement.")

            except Exception as e:
                logger.error(f"Erreur inattendue lors de la création du répertoire {storage_path} pour {file_type.value}: {e}")
                logger.warning(f"L'upload de fichiers {file_type.value} pourrait ne pas fonctionner correctement.")

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

    async def upload_file(self, request: Request, file: UploadFile, file_type: FileTypeEnum) -> dict:
        """Upload un fichier unique et retourne un dictionnaire avec les informations du fichier."""
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
            return {
                "filename": unique_filename,
                "original_filename": file.filename,
                "url": url,
                "file_type": file_type.value,
                "size": len(content),
                "path": str(file_path)
            }
        except Exception as e:
            logger.error(f"Erreur upload fichier {file.filename}: {e}\n{traceback.format_exc()}")
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"Erreur lors de l'upload du fichier '{file.filename}' pour '{file_type.value}'."
            )
        finally:
            await file.close()

    async def upload_files(self, request: Request, files: List[UploadFile], file_type: FileTypeEnum) -> List[dict]:
        """Upload plusieurs fichiers et retourne une liste de dictionnaires avec les informations des fichiers."""
        if not files:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Aucun fichier fourni pour l'upload."
            )
        results = []
        for file in files:
            result = await self.upload_file(request, file, file_type)
            results.append(result)
        return results

    async def delete_file(self, file_url: str, file_type: FileTypeEnum) -> str:
        """Supprime un fichier à partir de son URL et retourne un message."""
        if file_type not in self.FILE_CONFIG:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Type de fichier '{file_type.value}' non supporté."
            )
        
        config = self.FILE_CONFIG[file_type]
        
        # Extraire le nom de fichier de l'URL
        try:
            filename = file_url.split("/")[-1]
            if not filename or filename == "":
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="URL de fichier invalide"
                )
        except Exception:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="URL de fichier invalide"
            )
        
        file_path = Path(config["storage_path"]) / filename
        
        try:
            if file_path.exists():
                # Vérifier que le fichier est bien dans le bon répertoire
                if not str(file_path).startswith(str(Path(config["storage_path"]))):
                    raise HTTPException(
                        status_code=status.HTTP_400_BAD_REQUEST,
                        detail="Chemin de fichier non autorisé"
                    )
                
                file_path.unlink()
                logger.info(f"Fichier {file_path} supprimé avec succès.")
                return f"Fichier {filename} supprimé avec succès."
            else:
                logger.warning(f"Fichier {file_path} non trouvé pour suppression.")
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail=f"Fichier {filename} non trouvé"
                )
        except HTTPException:
            raise
        except PermissionError:
            logger.error(f"Erreur de permission lors de la suppression du fichier {file_url}")
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Erreur de permission lors de la suppression du fichier"
            )
        except Exception as e:
            logger.error(f"Erreur suppression fichier {file_url}: {e}")
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"Erreur lors de la suppression du fichier '{filename}'"
            )

    async def delete_file_by_url(self, file_url: str, file_type: FileTypeEnum) -> str:
        """Supprime un fichier à partir de son URL et retourne un message."""
        return await self.delete_file(file_url, file_type)

    async def delete_multiple_files(self, file_urls: List[str], file_type: FileTypeEnum) -> List[str]:
        """Supprime plusieurs fichiers à partir de leurs URLs et retourne une liste de messages."""
        results = []
        for file_url in file_urls:
            try:
                result = await self.delete_file(file_url, file_type)
                results.append(result)
            except HTTPException as e:
                results.append(f"Erreur: {e.detail}")
            except Exception as e:
                results.append(f"Erreur inattendue: {str(e)}")
        return results

    async def list_files(self, file_type: FileTypeEnum, request: Request) -> List[dict]:
        """Liste tous les fichiers d'un type donné avec leurs URLs."""
        if file_type not in self.FILE_CONFIG:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Type de fichier '{file_type.value}' non supporté."
            )
        
        config = self.FILE_CONFIG[file_type]
        storage_path = Path(config["storage_path"])
        
        try:
            if not storage_path.exists():
                return []
            
            files = []
            for file_path in storage_path.iterdir():
                if file_path.is_file():
                    base_url = str(request.base_url).rstrip("/")
                    file_url = f"{base_url}{config['url_prefix'].rstrip('/')}/{file_path.name}"
                    files.append({
                        "filename": file_path.name,
                        "url": file_url,
                        "size": file_path.stat().st_size,
                        "created_at": datetime.fromtimestamp(file_path.stat().st_ctime).isoformat(),
                        "modified_at": datetime.fromtimestamp(file_path.stat().st_mtime).isoformat()
                    })
            
            return files
        except Exception as e:
            logger.error(f"Erreur lors de la liste des fichiers {file_type.value}: {e}")
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"Erreur lors de la liste des fichiers {file_type.value}"
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

    async def get(self, db: AsyncSession, id: int) -> PermissionLight:
        """Récupère une permission par ID (avec rôles)."""
        try:
            result = await db.execute(
                select(self.model).options(selectinload(self.model.roles)).where(self.model.id == id)
            )
            db_obj = result.scalars().first()
            if not db_obj:
                raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Permission non trouvée")
            return await self._safe_from_orm(db_obj, self.light_schema)
        except SQLAlchemyError as e:
            logger.error(f"Erreur lors de la récupération de la permission: {str(e)}")
            raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Erreur lors de la récupération de la permission")

    async def get_all(self, db: AsyncSession, skip: int = 0, limit: int = 100) -> List[PermissionLight]:
        """Récupère toutes les permissions (avec rôles)."""
        try:
            result = await db.execute(
                select(self.model)
                .options(selectinload(self.model.roles))
                .offset(skip)
                .limit(limit)
            )
            db_objects = result.scalars().all()
            return [await self._safe_from_orm(obj, self.light_schema) for obj in db_objects]
        except SQLAlchemyError as e:
            logger.error(f"Erreur lors de la récupération des permissions: {str(e)}")
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Erreur lors de la récupération des permissions"
            )

    async def update(self, db: AsyncSession, id: int, obj_in: PermissionUpdate) -> PermissionLight:
        """Met à jour une permission avec validation de l'unicité du nom."""
        try:
            # Vérifier l'unicité du nom si modifié
            if obj_in.nom:
                db_obj = await self.get_or_404(db, id)
                if obj_in.nom != db_obj.nom:
                    await self.check_unique(db, "nom", obj_in.nom, "nom")
                
                # Récupérer l'objet à mettre à jour
                db_obj = await self.get_or_404(db, id)
                
                # Mettre à jour les champs
                update_data = obj_in.model_dump(exclude_unset=True)
                for key, value in update_data.items():
                    setattr(db_obj, key, value)
                
                # Sauvegarder les changements
                db.add(db_obj)
                await db.flush()
                await db.refresh(db_obj)
                
                # Retourner en utilisant le light_schema
                return await self._safe_from_orm(db_obj, self.light_schema)
        except SQLAlchemyError as e:
            logger.error(f"Erreur lors de la mise à jour de la permission: {str(e)}")
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Erreur lors de la mise à jour de la permission"
            )

    async def delete(self, db: AsyncSession, id: int) -> str:
        """Supprime une permission et retourne un message personnalisé."""
        try:
            db_obj = await self.get_or_404(db, id)
            nom = db_obj.nom
            await db.delete(db_obj)
            await db.flush()
            return f"Permission '{nom.value}' supprimée avec succès."
        except SQLAlchemyError as e:
            logger.error(f"Erreur lors de la suppression de la permission: {str(e)}")
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Erreur lors de la suppression de la permission"
            )

    async def create_all_permissions_and_roles(self, db: AsyncSession) -> str:
        """Crée toutes les permissions, tous les rôles et affecte les permissions aux rôles de manière logique."""
        from src.util.helper.enum import PermissionEnum, RoleEnum
        from sqlalchemy import select
        from sqlalchemy.orm import selectinload
        created_permissions = []
        created_roles = []
        assigned = []
        
        # 1. Créer toutes les permissions
        for perm in PermissionEnum:
            exists = await db.execute(select(PermissionModel).where(PermissionModel.nom == perm))
            if not exists.scalars().first():
                db_perm = PermissionModel(nom=perm)
                db.add(db_perm)
                created_permissions.append(perm.value)
        
        # 2. Créer tous les rôles
        for role in RoleEnum:
            exists = await db.execute(select(RoleModel).where(RoleModel.nom == role))
            if not exists.scalars().first():
                db_role = RoleModel(nom=role)
                db.add(db_role)
                created_roles.append(role.value)
        
        await db.flush()
        
        # 3. Récupérer les objets créés avec leurs permissions chargées
        roles_result = await db.execute(
            select(RoleModel).options(selectinload(RoleModel.permissions))
        )
        roles = {r.nom: r for r in roles_result.scalars().all()}
        permissions_result = await db.execute(select(PermissionModel))
        permissions = {p.nom: p for p in permissions_result.scalars().all()}
        
        # 4. Affecter les permissions aux rôles de manière logique
        role_permissions = {
            RoleEnum.ADMIN: [
                # Toutes les permissions système
                PermissionEnum.LIRE_UTILISATEUR, PermissionEnum.MODIFIER_UTILISATEUR,
                PermissionEnum.CREER_UTILISATEUR, PermissionEnum.SUPPRIMER_UTILISATEUR,
                PermissionEnum.REINITIALISER_MOT_DE_PASSE, PermissionEnum.CHANGER_MOT_DE_PASSE,
                PermissionEnum.LIRE_PERMISSION, PermissionEnum.MODIFIER_PERMISSION,
                PermissionEnum.CREER_PERMISSION, PermissionEnum.SUPPRIMER_PERMISSION,
                PermissionEnum.LIRE_ROLE, PermissionEnum.MODIFIER_ROLE,
                PermissionEnum.CREER_ROLE, PermissionEnum.SUPPRIMER_ROLE,
                # Toutes les permissions métier
                PermissionEnum.LIRE_FORMATION, PermissionEnum.MODIFIER_FORMATION,
                PermissionEnum.CREER_FORMATION, PermissionEnum.SUPPRIMER_FORMATION,
                PermissionEnum.LIRE_INSCRIPTION, PermissionEnum.MODIFIER_INSCRIPTION,
                PermissionEnum.CREER_INSCRIPTION, PermissionEnum.SUPPRIMER_INSCRIPTION,
                PermissionEnum.LIRE_PAIEMENT, PermissionEnum.MODIFIER_PAIEMENT,
                PermissionEnum.CREER_PAIEMENT, PermissionEnum.SUPPRIMER_PAIEMENT,
                PermissionEnum.LIRE_MODULE, PermissionEnum.MODIFIER_MODULE,
                PermissionEnum.CREER_MODULE, PermissionEnum.SUPPRIMER_MODULE,
                PermissionEnum.LIRE_RESSOURCE, PermissionEnum.MODIFIER_RESSOURCE,
                PermissionEnum.CREER_RESSOURCE, PermissionEnum.SUPPRIMER_RESSOURCE,
                PermissionEnum.LIRE_CHEF_D_OEUVRE, PermissionEnum.MODIFIER_CHEF_D_OEUVRE,
                PermissionEnum.CREER_CHEF_D_OEUVRE, PermissionEnum.SUPPRIMER_CHEF_D_OEUVRE,
                PermissionEnum.LIRE_PROJET_COLLECTIF, PermissionEnum.MODIFIER_PROJET_COLLECTIF,
                PermissionEnum.CREER_PROJET_COLLECTIF, PermissionEnum.SUPPRIMER_PROJET_COLLECTIF,
                PermissionEnum.LIRE_EVALUATION, PermissionEnum.MODIFIER_EVALUATION,
                PermissionEnum.CREER_EVALUATION, PermissionEnum.SUPPRIMER_EVALUATION,
                PermissionEnum.LIRE_QUESTION, PermissionEnum.MODIFIER_QUESTION,
                PermissionEnum.CREER_QUESTION, PermissionEnum.SUPPRIMER_QUESTION,
                PermissionEnum.LIRE_PROPOSITION, PermissionEnum.MODIFIER_PROPOSITION,
                PermissionEnum.CREER_PROPOSITION, PermissionEnum.SUPPRIMER_PROPOSITION,
                PermissionEnum.LIRE_RESULTAT_EVALUATION, PermissionEnum.MODIFIER_RESULTAT_EVALUATION,
                PermissionEnum.CREER_RESULTAT_EVALUATION, PermissionEnum.SUPPRIMER_RESULTAT_EVALUATION,
                PermissionEnum.LIRE_GENOTYPE, PermissionEnum.MODIFIER_GENOTYPE,
                PermissionEnum.CREER_GENOTYPE, PermissionEnum.SUPPRIMER_GENOTYPE,
                PermissionEnum.LIRE_ASCENDANCE_GENOTYPE, PermissionEnum.MODIFIER_ASCENDANCE_GENOTYPE,
                PermissionEnum.CREER_ASCENDANCE_GENOTYPE, PermissionEnum.SUPPRIMER_ASCENDANCE_GENOTYPE,
                PermissionEnum.LIRE_SANTE_GENOTYPE, PermissionEnum.MODIFIER_SANTE_GENOTYPE,
                PermissionEnum.CREER_SANTE_GENOTYPE, PermissionEnum.SUPPRIMER_SANTE_GENOTYPE,
                PermissionEnum.LIRE_EDUCATION_GENOTYPE, PermissionEnum.MODIFIER_EDUCATION_GENOTYPE,
                PermissionEnum.CREER_EDUCATION_GENOTYPE, PermissionEnum.SUPPRIMER_EDUCATION_GENOTYPE,
                PermissionEnum.LIRE_PLAN_INTERVENTION, PermissionEnum.MODIFIER_PLAN_INTERVENTION,
                PermissionEnum.CREER_PLAN_INTERVENTION, PermissionEnum.SUPPRIMER_PLAN_INTERVENTION,
                PermissionEnum.LIRE_ACCREDITATION, PermissionEnum.MODIFIER_ACCREDITATION,
                PermissionEnum.CREER_ACCREDITATION, PermissionEnum.SUPPRIMER_ACCREDITATION,
                PermissionEnum.LIRE_ACTUALITE, PermissionEnum.MODIFIER_ACTUALITE,
                PermissionEnum.CREER_ACTUALITE, PermissionEnum.SUPPRIMER_ACTUALITE,
                PermissionEnum.LIRE_FICHIER, PermissionEnum.TELEVERSER_FICHIER,
                PermissionEnum.SUPPRIMER_FICHIER
            ],
            
            RoleEnum.COORDONNATEUR: [
                # Gestion des utilisateurs (sauf suppression)
                PermissionEnum.LIRE_UTILISATEUR, PermissionEnum.MODIFIER_UTILISATEUR,
                PermissionEnum.CREER_UTILISATEUR, PermissionEnum.REINITIALISER_MOT_DE_PASSE,
                PermissionEnum.CHANGER_MOT_DE_PASSE,
                # Gestion des formations et contenus
                PermissionEnum.LIRE_FORMATION, PermissionEnum.MODIFIER_FORMATION,
                PermissionEnum.CREER_FORMATION,
                PermissionEnum.LIRE_INSCRIPTION, PermissionEnum.MODIFIER_INSCRIPTION,
                PermissionEnum.CREER_INSCRIPTION,
                PermissionEnum.LIRE_PAIEMENT, PermissionEnum.MODIFIER_PAIEMENT,
                PermissionEnum.CREER_PAIEMENT,
                PermissionEnum.LIRE_MODULE, PermissionEnum.MODIFIER_MODULE,
                PermissionEnum.CREER_MODULE,
                PermissionEnum.LIRE_RESSOURCE, PermissionEnum.MODIFIER_RESSOURCE,
                PermissionEnum.CREER_RESSOURCE,
                PermissionEnum.LIRE_CHEF_D_OEUVRE, PermissionEnum.MODIFIER_CHEF_D_OEUVRE,
                PermissionEnum.CREER_CHEF_D_OEUVRE,
                PermissionEnum.LIRE_PROJET_COLLECTIF, PermissionEnum.MODIFIER_PROJET_COLLECTIF,
                PermissionEnum.CREER_PROJET_COLLECTIF,
                PermissionEnum.LIRE_EVALUATION, PermissionEnum.MODIFIER_EVALUATION,
                PermissionEnum.CREER_EVALUATION,
                PermissionEnum.LIRE_QUESTION, PermissionEnum.MODIFIER_QUESTION,
                PermissionEnum.CREER_QUESTION,
                PermissionEnum.LIRE_PROPOSITION, PermissionEnum.MODIFIER_PROPOSITION,
                PermissionEnum.CREER_PROPOSITION,
                PermissionEnum.LIRE_RESULTAT_EVALUATION, PermissionEnum.MODIFIER_RESULTAT_EVALUATION,
                PermissionEnum.CREER_RESULTAT_EVALUATION,
                # Génotypes et plans d'intervention
                PermissionEnum.LIRE_GENOTYPE, PermissionEnum.MODIFIER_GENOTYPE,
                PermissionEnum.CREER_GENOTYPE,
                PermissionEnum.LIRE_ASCENDANCE_GENOTYPE, PermissionEnum.MODIFIER_ASCENDANCE_GENOTYPE,
                PermissionEnum.CREER_ASCENDANCE_GENOTYPE,
                PermissionEnum.LIRE_SANTE_GENOTYPE, PermissionEnum.MODIFIER_SANTE_GENOTYPE,
                PermissionEnum.CREER_SANTE_GENOTYPE,
                PermissionEnum.LIRE_EDUCATION_GENOTYPE, PermissionEnum.MODIFIER_EDUCATION_GENOTYPE,
                PermissionEnum.CREER_EDUCATION_GENOTYPE,
                PermissionEnum.LIRE_PLAN_INTERVENTION, PermissionEnum.MODIFIER_PLAN_INTERVENTION,
                PermissionEnum.CREER_PLAN_INTERVENTION,
                # Accréditations et actualités
                PermissionEnum.LIRE_ACCREDITATION, PermissionEnum.MODIFIER_ACCREDITATION,
                PermissionEnum.CREER_ACCREDITATION,
                PermissionEnum.LIRE_ACTUALITE, PermissionEnum.MODIFIER_ACTUALITE,
                PermissionEnum.CREER_ACTUALITE,
                # Fichiers
                PermissionEnum.LIRE_FICHIER, PermissionEnum.TELEVERSER_FICHIER
            ],
            
            RoleEnum.FORMATEUR: [
                # Lecture des utilisateurs
                PermissionEnum.LIRE_UTILISATEUR, PermissionEnum.CHANGER_MOT_DE_PASSE,
                # Gestion des formations et contenus pédagogiques
                PermissionEnum.LIRE_FORMATION, PermissionEnum.MODIFIER_FORMATION,
                PermissionEnum.LIRE_INSCRIPTION, PermissionEnum.MODIFIER_INSCRIPTION,
                PermissionEnum.LIRE_PAIEMENT,
                PermissionEnum.LIRE_MODULE, PermissionEnum.MODIFIER_MODULE,
                PermissionEnum.CREER_MODULE,
                PermissionEnum.LIRE_RESSOURCE, PermissionEnum.MODIFIER_RESSOURCE,
                PermissionEnum.CREER_RESSOURCE,
                PermissionEnum.LIRE_CHEF_D_OEUVRE, PermissionEnum.MODIFIER_CHEF_D_OEUVRE,
                PermissionEnum.CREER_CHEF_D_OEUVRE,
                PermissionEnum.LIRE_PROJET_COLLECTIF, PermissionEnum.MODIFIER_PROJET_COLLECTIF,
                PermissionEnum.CREER_PROJET_COLLECTIF,
                PermissionEnum.LIRE_EVALUATION, PermissionEnum.MODIFIER_EVALUATION,
                PermissionEnum.CREER_EVALUATION,
                PermissionEnum.LIRE_QUESTION, PermissionEnum.MODIFIER_QUESTION,
                PermissionEnum.CREER_QUESTION,
                PermissionEnum.LIRE_PROPOSITION, PermissionEnum.MODIFIER_PROPOSITION,
                PermissionEnum.CREER_PROPOSITION,
                PermissionEnum.LIRE_RESULTAT_EVALUATION, PermissionEnum.MODIFIER_RESULTAT_EVALUATION,
                PermissionEnum.CREER_RESULTAT_EVALUATION,
                # Génotypes et plans d'intervention
                PermissionEnum.LIRE_GENOTYPE, PermissionEnum.MODIFIER_GENOTYPE,
                PermissionEnum.CREER_GENOTYPE,
                PermissionEnum.LIRE_ASCENDANCE_GENOTYPE, PermissionEnum.MODIFIER_ASCENDANCE_GENOTYPE,
                PermissionEnum.CREER_ASCENDANCE_GENOTYPE,
                PermissionEnum.LIRE_SANTE_GENOTYPE, PermissionEnum.MODIFIER_SANTE_GENOTYPE,
                PermissionEnum.CREER_SANTE_GENOTYPE,
                PermissionEnum.LIRE_EDUCATION_GENOTYPE, PermissionEnum.MODIFIER_EDUCATION_GENOTYPE,
                PermissionEnum.CREER_EDUCATION_GENOTYPE,
                PermissionEnum.LIRE_PLAN_INTERVENTION, PermissionEnum.MODIFIER_PLAN_INTERVENTION,
                PermissionEnum.CREER_PLAN_INTERVENTION,
                # Fichiers
                PermissionEnum.LIRE_FICHIER, PermissionEnum.TELEVERSER_FICHIER
            ],
            
            RoleEnum.REFERENT: [
                # Lecture des utilisateurs
                PermissionEnum.LIRE_UTILISATEUR, PermissionEnum.CHANGER_MOT_DE_PASSE,
                # Gestion des formations et contenus pédagogiques
                PermissionEnum.LIRE_FORMATION, PermissionEnum.MODIFIER_FORMATION,
                PermissionEnum.LIRE_INSCRIPTION, PermissionEnum.MODIFIER_INSCRIPTION,
                PermissionEnum.LIRE_PAIEMENT,
                PermissionEnum.LIRE_MODULE, PermissionEnum.MODIFIER_MODULE,
                PermissionEnum.CREER_MODULE,
                PermissionEnum.LIRE_RESSOURCE, PermissionEnum.MODIFIER_RESSOURCE,
                PermissionEnum.CREER_RESSOURCE,
                PermissionEnum.LIRE_CHEF_D_OEUVRE, PermissionEnum.MODIFIER_CHEF_D_OEUVRE,
                PermissionEnum.CREER_CHEF_D_OEUVRE,
                PermissionEnum.LIRE_PROJET_COLLECTIF, PermissionEnum.MODIFIER_PROJET_COLLECTIF,
                PermissionEnum.CREER_PROJET_COLLECTIF,
                PermissionEnum.LIRE_EVALUATION, PermissionEnum.MODIFIER_EVALUATION,
                PermissionEnum.CREER_EVALUATION,
                PermissionEnum.LIRE_QUESTION, PermissionEnum.MODIFIER_QUESTION,
                PermissionEnum.CREER_QUESTION,
                PermissionEnum.LIRE_PROPOSITION, PermissionEnum.MODIFIER_PROPOSITION,
                PermissionEnum.CREER_PROPOSITION,
                PermissionEnum.LIRE_RESULTAT_EVALUATION, PermissionEnum.MODIFIER_RESULTAT_EVALUATION,
                PermissionEnum.CREER_RESULTAT_EVALUATION,
                # Génotypes et plans d'intervention
                PermissionEnum.LIRE_GENOTYPE, PermissionEnum.MODIFIER_GENOTYPE,
                PermissionEnum.CREER_GENOTYPE,
                PermissionEnum.LIRE_ASCENDANCE_GENOTYPE, PermissionEnum.MODIFIER_ASCENDANCE_GENOTYPE,
                PermissionEnum.CREER_ASCENDANCE_GENOTYPE,
                PermissionEnum.LIRE_SANTE_GENOTYPE, PermissionEnum.MODIFIER_SANTE_GENOTYPE,
                PermissionEnum.CREER_SANTE_GENOTYPE,
                PermissionEnum.LIRE_EDUCATION_GENOTYPE, PermissionEnum.MODIFIER_EDUCATION_GENOTYPE,
                PermissionEnum.CREER_EDUCATION_GENOTYPE,
                PermissionEnum.LIRE_PLAN_INTERVENTION, PermissionEnum.MODIFIER_PLAN_INTERVENTION,
                PermissionEnum.CREER_PLAN_INTERVENTION,
                # Fichiers
                PermissionEnum.LIRE_FICHIER, PermissionEnum.TELEVERSER_FICHIER
            ],
            
            RoleEnum.APPRENANT: [
                # Lecture de son propre profil
                PermissionEnum.LIRE_UTILISATEUR, PermissionEnum.CHANGER_MOT_DE_PASSE,
                # Lecture des formations et contenus
                PermissionEnum.LIRE_FORMATION,
                PermissionEnum.LIRE_INSCRIPTION,
                PermissionEnum.LIRE_PAIEMENT,
                PermissionEnum.LIRE_MODULE,
                PermissionEnum.LIRE_RESSOURCE,
                # Gestion de ses propres chefs-d'œuvre
                PermissionEnum.LIRE_CHEF_D_OEUVRE, PermissionEnum.MODIFIER_CHEF_D_OEUVRE,
                PermissionEnum.CREER_CHEF_D_OEUVRE,
                # Gestion de ses propres projets collectifs
                PermissionEnum.LIRE_PROJET_COLLECTIF, PermissionEnum.MODIFIER_PROJET_COLLECTIF,
                PermissionEnum.CREER_PROJET_COLLECTIF,
                # Lecture des évaluations et questions
                PermissionEnum.LIRE_EVALUATION,
                PermissionEnum.LIRE_QUESTION,
                PermissionEnum.LIRE_PROPOSITION,
                # Gestion de ses propres résultats d'évaluation
                PermissionEnum.LIRE_RESULTAT_EVALUATION, PermissionEnum.MODIFIER_RESULTAT_EVALUATION,
                PermissionEnum.CREER_RESULTAT_EVALUATION,
                # Génotypes et plans d'intervention (lecture seulement)
                PermissionEnum.LIRE_GENOTYPE,
                PermissionEnum.LIRE_ASCENDANCE_GENOTYPE,
                PermissionEnum.LIRE_SANTE_GENOTYPE,
                PermissionEnum.LIRE_EDUCATION_GENOTYPE,
                PermissionEnum.LIRE_PLAN_INTERVENTION,
                # Lecture des actualités
                PermissionEnum.LIRE_ACTUALITE,
                # Fichiers (lecture seulement)
                PermissionEnum.LIRE_FICHIER
            ]
        }
        
        # 5. Appliquer les affectations sans lazy load
        for role_enum, perm_list in role_permissions.items():
            if role_enum in roles:
                role_obj = roles[role_enum]
                role_obj.permissions.clear()
                role_obj.permissions.extend([permissions[perm] for perm in perm_list if perm in permissions])
                assigned.append(f"{role_enum.value}: {len(role_obj.permissions)} permissions")
        
        await db.flush()
        
        return (
            f"✅ Permissions créées: {len(created_permissions)}\n"
            f"✅ Rôles créés: {len(created_roles)}\n"
            f"✅ Affectations appliquées:\n" + "\n".join(f"  - {a}" for a in assigned)
        )

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
                user_count_query = select(func.count(UtilisateurModel.id)).filter(UtilisateurModel.role_id == db_obj.id)
                user_count_result = await db.execute(user_count_query)
                user_count = user_count_result.scalar()
                return RoleLight(
                    id=db_obj.id,
                    nom=db_obj.nom,
                    permissions=[PermissionMinLight(id=perm.id, nom=perm.nom) for perm in db_obj.permissions],
                    user_count=user_count
                )
            except IntegrityError:
                logger.error(f"Erreur d'intégrité lors de la création du rôle: {obj_in.nom}")
                raise HTTPException(
                    status_code=status.HTTP_409_CONFLICT,
                    detail=f"Rôle avec nom '{obj_in.nom}' existe déjà"
                )
            except SQLAlchemyError as e:
                logger.error(f"Erreur lors de la création du rôle: {str(e)}")
                raise HTTPException(
                    status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                    detail="Erreur lors de la création du rôle"
                )

    async def get(self, db: AsyncSession, id: int) -> RoleLight:
        """Récupère un rôle par ID avec ses permissions et le nombre d'utilisateurs."""
        try:
            query = select(self.model).filter(self.model.id == id).options(
                selectinload(self.model.permissions)
            )
            result = await db.execute(query)
            db_obj = result.scalars().first()
            if not db_obj:
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail=f"{self.entity_name} avec l'ID {id} non trouvé"
                )
            user_count_query = select(func.count(UtilisateurModel.id)).filter(UtilisateurModel.role_id == db_obj.id)
            user_count_result = await db.execute(user_count_query)
            user_count = user_count_result.scalar()
            return RoleLight(
                id=db_obj.id,
                nom=db_obj.nom,
                permissions=[PermissionMinLight(id=perm.id, nom=perm.nom) for perm in db_obj.permissions],
                user_count=user_count
            )
        except SQLAlchemyError as e:
            logger.error(f"Erreur de base de données lors de la récupération de {self.entity_name}: {str(e)}", exc_info=True)
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"Erreur de base de données lors de la récupération de {self.entity_name}"
            )

    async def get_all(self, db: AsyncSession, skip: int = 0, limit: int = 100) -> List[RoleLight]:
        """Récupère tous les rôles avec leurs permissions et le nombre d'utilisateurs associés."""
        try:
            query = select(self.model).offset(skip).limit(limit).options(
                selectinload(self.model.permissions)
            )
            result = await db.execute(query)
            roles = result.scalars().all()
            role_list = []
            for role in roles:
                user_count_query = select(func.count(UtilisateurModel.id)).filter(UtilisateurModel.role_id == role.id)
                user_count_result = await db.execute(user_count_query)
                user_count = user_count_result.scalar()
                role_light = RoleLight(
                    id=role.id,
                    nom=role.nom,
                    permissions=[PermissionMinLight(id=perm.id, nom=perm.nom) for perm in role.permissions],
                    user_count=user_count
                )
                role_list.append(role_light)
            return role_list
        except SQLAlchemyError as e:
            logger.error(f"Erreur de base de données lors de la récupération des {self.entity_name}s: {str(e)}", exc_info=True)
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"Erreur de base de données lors de la récupération des {self.entity_name}s"
            )

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
                return await self._safe_from_orm(db_obj, self.schema)
            except IntegrityError:
                logger.error(f"Erreur d'intégrité lors de la mise à jour du rôle: {id}")
                raise HTTPException(
                    status_code=status.HTTP_409_CONFLICT,
                    detail=f"Rôle avec nom existe déjà"
                )
            except SQLAlchemyError as e:
                logger.error(f"Erreur lors de la mise à jour du rôle: {str(e)}")
                raise HTTPException(
                    status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                    detail="Erreur lors de la mise à jour du rôle"
                )

    async def delete(self, db: AsyncSession, id: int) -> None:
        """Supprime un rôle par ID."""
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

    async def assign_permission(self, db: AsyncSession, role_id: int, permission_ids: List[int]) -> str:
        """Assigne plusieurs permissions à un rôle sans doublons."""
        async with db.begin():
            try:
                result = await db.execute(
                    select(RoleModel).options(selectinload(RoleModel.permissions)).where(RoleModel.id == role_id)
                )
                db_role = result.scalars().first()
                if not db_role:
                    raise HTTPException(
                        status_code=status.HTTP_404_NOT_FOUND,
                        detail=f"Rôle avec ID {role_id} non trouvé"
                    )
                
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
                
                for permission in permissions:
                    await db.execute(
                        insert(association_roles_permissions).values(
                            role_id=role_id,
                            permission_id=permission.id
                        )
                    )
                await db.flush()
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
                result = await db.execute(
                    select(RoleModel).options(selectinload(RoleModel.permissions)).where(RoleModel.id == role_id)
                )
                db_role = result.scalars().first()
                if not db_role:
                    raise HTTPException(
                        status_code=status.HTTP_404_NOT_FOUND,
                        detail=f"Rôle avec ID {role_id} non trouvé"
                    )
                
                existing_permission_ids = {p.id for p in db_role.permissions}
                permissions_to_remove = set(permission_ids) & existing_permission_ids
                
                if not permissions_to_remove:
                    return f"Aucune permission à révoquer pour le rôle {db_role.nom}"
                
                for permission_id in permissions_to_remove:
                    await db.execute(
                        delete(association_roles_permissions).where(
                            (association_roles_permissions.c.role_id == role_id) &
                            (association_roles_permissions.c.permission_id == permission_id)
                        )
                    )
                
                await db.flush()
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
        """Génère un mot de passe aléatoire (lettres + chiffres uniquement)."""
        alphabet = string.ascii_letters + string.digits
        return ''.join(secrets.choice(alphabet) for _ in range(12))

    # Ajouter cette méthode dans la classe UtilisateurService
    async def _check_role_by_name(self, db: AsyncSession, role_name: str) -> RoleLight:
        """Vérifie si un rôle existe par son nom et retourne l'objet RoleModel."""
        query = select(RoleModel).filter(RoleModel.nom == role_name)
        result = await db.execute(query)
        role = result.scalars().first()
        if not role:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Rôle avec le nom '{role_name}' non trouvé"
            )
        return role

    async def create(self, db: AsyncSession, obj_in: UtilisateurCreate) -> UtilisateurLight:
        """Crée un nouvel utilisateur avec validation et envoie un email avec le mot de passe."""
        async with db.begin():
            try:
                # Vérifier l'unicité de l'email
                await self.check_unique(db, "email", obj_in.email, "email")
                role = await self._check_role_by_name(db, obj_in.role_name)

                # Générer un mot de passe si non fourni
                password = self._generate_password()
                hashed_password = pwd_context.hash(password)

                # Préparer les données de l'utilisateur
                obj_data = obj_in.model_dump(exclude_unset=True)
                obj_data['password'] = hashed_password
                obj_data['role_id'] = role.id
                obj_data['statut'] = StatutCompteEnum.ACTIF
                obj_data['est_actif'] = True
                if 'role_name' in obj_data:
                    del obj_data['role_name']

                db_obj = self.model(**obj_data)
                db.add(db_obj)
                await db.flush()

                # Recharger l'utilisateur avec ses relations pour éviter MissingGreenlet
                query = select(self.model).filter(self.model.id == db_obj.id).options(
                    selectinload(self.model.role).selectinload(RoleModel.permissions),
                    selectinload(self.model.permissions)
                )
                result = await db.execute(query)
                db_obj = result.scalars().first()

                # Construire la réponse manuellement pour éviter les problèmes de lazy loading
                role_light = None
                if db_obj.role:
                    role_light = RoleLight(
                        id=db_obj.role.id,
                        nom=db_obj.role.nom,
                        permissions=[PermissionMinLight(id=perm.id, nom=perm.nom) for perm in db_obj.role.permissions],
                        user_count=(await db.execute(
                            select(func.count(UtilisateurModel.id)).filter(UtilisateurModel.role_id == db_obj.role.id)
                        )).scalar()
                    )

                user_light = UtilisateurLight(
                    id=db_obj.id,
                    nom=db_obj.nom,
                    prenom=db_obj.prenom,
                    sexe=db_obj.sexe,
                    email=db_obj.email,
                    statut=db_obj.statut,
                    est_actif=db_obj.est_actif,
                    date_naissance=db_obj.date_naissance,
                    created_at=db_obj.created_at,
                    updated_at=db_obj.updated_at,
                    role=role_light,
                    permissions=[PermissionLight(id=perm.id, nom=perm.nom) for perm in db_obj.permissions]
                )

                # Envoi de l'email de bienvenue avec le mot de passe (en arrière-plan)
                try:
                    email_service = EmailService()
                    await email_service.send_new_user_email(obj_in.email, password, "fr")
                    await email_service.close()
                except Exception as e:
                    logger.warning(f"Échec de l'envoi de l'email à {obj_in.email}: {str(e)}")
                    # Ne pas échouer la création si l'email ne s'envoie pas

                return user_light
            except IntegrityError as e:
                logger.error(f"Erreur d'intégrité lors de la création de l'utilisateur: {str(e)}", exc_info=True)
                raise HTTPException(
                    status_code=status.HTTP_409_CONFLICT,
                    detail="Utilisateur avec cet email existe déjà"
                )
            except SQLAlchemyError as e:
                logger.error(f"Erreur de base de données lors de la création de l'utilisateur: {str(e)}", exc_info=True)
                raise HTTPException(
                    status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                    detail="Erreur de base de données lors de la création de l'utilisateur"
                )
    
    async def update(self, db: AsyncSession, id: int, obj_in: UtilisateurUpdate) -> Utilisateur:
        """Met à jour un utilisateur avec validation."""
        async with db.begin():
            try:
                db_obj = await self.get_or_404(db, id)
                if obj_in.email and obj_in.email != db_obj.email:
                    await self.check_unique(db, "email", obj_in.email, "email")
                update_data = obj_in.model_dump(exclude_unset=True)
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
                # Use eager loading to avoid lazy loading issues
                query = select(UtilisateurModel).filter(UtilisateurModel.id == id).options(
                    selectinload(UtilisateurModel.role).selectinload(RoleModel.permissions),
                    selectinload(UtilisateurModel.permissions),
                    selectinload(UtilisateurModel.inscriptions).selectinload(InscriptionFormationModel.formation),
                    selectinload(UtilisateurModel.inscriptions).selectinload(InscriptionFormationModel.paiements),
                    selectinload(UtilisateurModel.genotypes),
                    selectinload(UtilisateurModel.plans_intervention),
                    selectinload(UtilisateurModel.actualites),
                    selectinload(UtilisateurModel.accreditations),
                    selectinload(UtilisateurModel.chefs_d_oeuvre),
                    selectinload(UtilisateurModel.projets_collectifs),
                    selectinload(UtilisateurModel.resultats_evaluations)
                )
                result = await db.execute(query)
                updated_user = result.scalars().first()

                # Construire la réponse manuellement pour éviter les problèmes de lazy loading
                role = None
                if updated_user.role:
                    role = RoleLight(
                        id=updated_user.role.id,
                        nom=updated_user.role.nom,
                        permissions=[PermissionMinLight(id=perm.id, nom=perm.nom) for perm in updated_user.role.permissions],
                        user_count=(await db.execute(
                            select(func.count(UtilisateurModel.id)).filter(UtilisateurModel.role_id == updated_user.role.id)
                        )).scalar()
                    )

                # Serialize inscriptions with explicit handling
                inscriptions = []
                for inscription in updated_user.inscriptions:
                    formation = None
                    if inscription.formation:
                        formation = FormationLight(
                            id=inscription.formation.id,
                            titre=inscription.formation.titre,
                            specialite=inscription.formation.specialite,
                            statut=inscription.formation.statut,
                            frais=inscription.formation.frais,
                            photo_couverture=inscription.formation.photo_couverture,
                            description=inscription.formation.description
                        )
                    paiements = [
                        PaiementLight(
                            id=paiement.id,
                            inscription_id=paiement.inscription_id,
                            montant=paiement.montant,
                            methode_paiement=paiement.methode_paiement,
                            reference_transaction=paiement.reference_transaction,
                            date_paiement=paiement.date_paiement,
                            created_at=paiement.created_at,
                            updated_at=paiement.updated_at
                        ) for paiement in inscription.paiements
                    ]
                    inscriptions.append(InscriptionFormationLight(
                        id=inscription.id,
                        utilisateur_id=inscription.utilisateur_id,
                        formation_id=inscription.formation_id,
                        statut=inscription.statut,
                        progression=inscription.progression,
                        date_inscription=inscription.date_inscription,
                        date_dernier_acces=inscription.date_dernier_acces,
                        note_finale=inscription.note_finale,
                        heures_formation=inscription.heures_formation,
                        montant_verse=inscription.montant_verse,
                        statut_paiement=inscription.statut_paiement,
                        created_at=inscription.created_at,
                        updated_at=inscription.updated_at,
                        formation=formation,
                        paiements=paiements
                    ))

                return Utilisateur(
                    id=updated_user.id,
                    nom=updated_user.nom,
                    prenom=updated_user.prenom,
                    sexe=updated_user.sexe,
                    email=updated_user.email,
                    password=updated_user.password,
                    statut=updated_user.statut,
                    est_actif=updated_user.est_actif,
                    last_password_change=updated_user.last_password_change,
                    date_naissance=updated_user.date_naissance,
                    created_at=updated_user.created_at,
                    updated_at=updated_user.updated_at,
                    role=role,
                    permissions=[PermissionLight(id=perm.id, nom=perm.nom, roles=[]) for perm in updated_user.permissions],
                    inscriptions=inscriptions,
                    genotypes=[GenotypeIndividuelLight(
                        id=g.id,
                        utilisateur_id=g.utilisateur_id,
                        type_genotype=g.type_genotype,
                        created_at=g.created_at,
                        updated_at=g.updated_at
                    ) for g in updated_user.genotypes],
                    plans_intervention=[PlanInterventionIndividualiseLight(
                        id=p.id,
                        utilisateur_id=p.utilisateur_id,
                        objectifs=p.objectifs,
                        strategies=p.strategies,
                        ressources=p.ressources,
                        echeances=p.echeances,
                        created_at=p.created_at,
                        updated_at=p.updated_at
                    ) for p in updated_user.plans_intervention],
                    actualites=[ActualiteLight(
                        id=a.id,
                        utilisateur_id=a.utilisateur_id,
                        titre=a.titre,
                        contenu=a.contenu,
                        date_publication=a.date_publication,
                        created_at=a.created_at,
                        updated_at=a.updated_at
                    ) for a in updated_user.actualites],
                    accreditations=[AccreditationLight(
                        id=acc.id,
                        utilisateur_id=acc.utilisateur_id,
                        nom=acc.nom,
                        organisme=acc.organisme,
                        date_obtention=acc.date_obtention,
                        date_expiration=acc.date_expiration,
                        created_at=acc.created_at,
                        updated_at=acc.updated_at
                    ) for acc in updated_user.accreditations]
                )
            except SQLAlchemyError as e:
                logger.error(f"Erreur lors de la mise à jour de l'utilisateur: {str(e)}")
                raise HTTPException(
                    status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                    detail="Erreur lors de la mise à jour de l'utilisateur"
                )

    async def get_all(self, db: AsyncSession, skip: int = 0, limit: int = 100) -> List[UtilisateurLight]:
        """Récupère tous les utilisateurs avec leurs relations."""
        try:
            query = select(self.model).offset(skip).limit(limit).options(
                selectinload(self.model.role).selectinload(RoleModel.permissions),
                selectinload(self.model.permissions),
                selectinload(self.model.inscriptions),
                selectinload(self.model.genotypes),
                selectinload(self.model.plans_intervention),
                selectinload(self.model.actualites),
                selectinload(self.model.accreditations),
                selectinload(self.model.chefs_d_oeuvre),
                selectinload(self.model.projets_collectifs),
                selectinload(self.model.resultats_evaluations)
            )
            result = await db.execute(query)
            users = result.scalars().all()
            user_list = []
            for user in users:
                role_light = None
                if user.role:
                    role_light = RoleLight(
                        id=user.role.id,
                        nom=user.role.nom,
                        permissions=[PermissionMinLight(id=perm.id, nom=perm.nom) for perm in user.role.permissions],
                        user_count=(await db.execute(
                            select(func.count(UtilisateurModel.id)).filter(UtilisateurModel.role_id == user.role.id)
                        )).scalar()
                    )
                user_light = UtilisateurLight(
                    id=user.id,
                    nom=user.nom,
                    prenom=user.prenom,
                    sexe=user.sexe,
                    email=user.email,
                    statut=user.statut,
                    est_actif=user.est_actif,
                    date_naissance=user.date_naissance,
                    created_at=user.created_at,
                    updated_at=user.updated_at,
                    role=role_light,
                    permissions=[PermissionLight(id=perm.id, nom=perm.nom, roles=[]) for perm in user.permissions]
                )
                user_list.append(user_light)
            return user_list
        except SQLAlchemyError as e:
            logger.error(f"Erreur de base de données lors de la récupération des utilisateurs: {str(e)}", exc_info=True)
            raise HTTPException(
                status_code=500,
                detail="Erreur de base de données lors de la récupération des utilisateurs"
            )

    async def change_user_status(self, db: AsyncSession, user_id: int, statut: StatutCompteEnum) -> UtilisateurLight:
        """Change le statut d'un utilisateur et retourne l'utilisateur mis à jour."""
        try:
            query = select(self.model).filter(self.model.id == user_id).options(
                selectinload(self.model.role).selectinload(RoleModel.permissions),
                selectinload(self.model.permissions)
            )
            result = await db.execute(query)
            db_obj = result.scalars().first()
            if not db_obj:
                raise HTTPException(
                    status_code=404,
                    detail="Utilisateur non trouvé"
                )
            db_obj.statut = statut
            db.add(db_obj)
            await db.flush()
            # Manual serialization
            role_light = None
            if db_obj.role:
                role_light = RoleLight(
                    id=db_obj.role.id,
                    nom=db_obj.role.nom,
                    permissions=[PermissionMinLight(id=perm.id, nom=perm.nom) for perm in db_obj.role.permissions],
                    user_count=(await db.execute(
                        select(func.count(UtilisateurModel.id)).filter(UtilisateurModel.role_id == db_obj.role.id)
                    )).scalar()
                )
            return UtilisateurLight(
                id=db_obj.id,
                nom=db_obj.nom,
                prenom=db_obj.prenom,
                sexe=db_obj.sexe,
                email=db_obj.email,
                statut=db_obj.statut,
                est_actif=db_obj.est_actif,
                date_naissance=db_obj.date_naissance,
                created_at=db_obj.created_at,
                updated_at=db_obj.updated_at,
                role=role_light,
                permissions=[PermissionLight(id=perm.id, nom=perm.nom, roles=[]) for perm in db_obj.permissions]
            )
        except SQLAlchemyError as e:
            logger.error(f"Erreur lors du changement de statut de l'utilisateur: {str(e)}")
            raise HTTPException(
                status_code=500,
                detail="Erreur lors du changement de statut de l'utilisateur"
            )



    async def change_password(self, db: AsyncSession, utilisateur_id: int, current_password: str, new_password: str) -> str:
        """Change le mot de passe d'un utilisateur après vérification."""
        try:
            db_obj = await self.get_or_404(db, utilisateur_id)

            # Debug: log pour vérifier les mots de passe
            logger.info(f"Tentative de changement de mot de passe pour utilisateur ID: {utilisateur_id}")
            logger.info(f"Mot de passe fourni: {current_password}")
            logger.info(f"Hash en base: {db_obj.password}")

            # Utiliser la même logique que le login
            if not pwd_context.verify(current_password, db_obj.password):
                logger.warning(f"Mot de passe incorrect pour l'utilisateur ID: {utilisateur_id}")
                raise HTTPException(
                    status_code=401,
                    detail="Mot de passe actuel incorrect"
                )

            # Hasher le nouveau mot de passe
            db_obj.password = pwd_context.hash(new_password)
            await db.commit()
            return f"Le mot de passe de l'utilisateur {db_obj.nom} {db_obj.prenom} a été changé avec succès"
        except SQLAlchemyError as e:
                logger.error(f"Erreur lors du changement de mot de passe: {str(e)}")
                raise HTTPException(
                    status_code=500,
                    detail="Erreur lors du changement de mot de passe"
                )

    async def confirm_reset_password(self, db: AsyncSession, reset_token: str) -> None:
        """Confirme la réinitialisation du mot de passe avec un token."""
        async with db.begin():
            try:
                query = select(self.model).filter(self.model.reset_token == reset_token).options(
                    selectinload(self.model.role).selectinload(RoleModel.permissions),
                    selectinload(self.model.permissions)
                )
                result = await db.execute(query)
                db_obj = result.scalars().first()
                if not db_obj or db_obj.reset_token_expiry < datetime.now(timezone.utc):
                    raise HTTPException(
                        status_code=400,
                        detail="Token de réinitialisation invalide ou expiré"
                    )
                new_password = self._generate_password()
                db_obj.password = pwd_context.hash(new_password)  # Changed from hashed_password to password
                db_obj.reset_token = None
                db_obj.reset_token_expiry = None
                await db.flush()
                email_service = EmailService()
                try:
                    await email_service.send_password_reset(db_obj.email, new_password, "fr")
                finally:
                    await email_service.close()
            except SQLAlchemyError as e:
                logger.error(f"Erreur lors de la confirmation de réinitialisation: {str(e)}")
                raise HTTPException(
                    status_code=500,
                    detail="Erreur lors de la confirmation de réinitialisation"
                )

    async def assign_permissions(self, db: AsyncSession, user_id: int, permission_ids: List[int]) -> str:
        """Assigne des permissions directement à un utilisateur."""
        try:
            db_obj = await self.get_or_404(db, user_id)
            permissions = await db.execute(
                select(PermissionModel).filter(PermissionModel.id.in_(permission_ids))
            )
            permission_objects = permissions.scalars().all()
            if not permission_objects:
                all_permissions = await db.execute(select(PermissionModel))
                available_permissions = all_permissions.scalars().all()
                available_ids = [p.id for p in available_permissions]
                available_names = [p.nom.value for p in available_permissions]
                raise HTTPException(
                    status_code=400,
                    detail=f"Aucune permission valide fournie. IDs demandés: {permission_ids}. Permissions disponibles: {available_names} (IDs: {available_ids})"
                )
            user_permissions_query = await db.execute(
                select(PermissionModel)
                .join(association_utilisateurs_permissions)
                .filter(association_utilisateurs_permissions.c.utilisateur_id == user_id)
            )
            current_permission_ids = {p.id for p in user_permissions_query.scalars().all()}
            for permission in permission_objects:
                if permission.id not in current_permission_ids:
                    await db.execute(
                        insert(association_utilisateurs_permissions).values(
                            utilisateur_id=user_id,
                            permission_id=permission.id
                        )
                    )
            await db.flush()
            permission_names = [p.nom.value for p in permission_objects]
            return f"Permissions {', '.join(permission_names)} assignées avec succès à l'utilisateur {db_obj.nom} {db_obj.prenom}"
        except SQLAlchemyError as e:
            logger.error(f"Erreur lors de l'assignation des permissions: {str(e)}")
            raise HTTPException(
                status_code=500,
                detail="Erreur lors de l'assignation des permissions"
            )

    async def revoke_permissions(self, db: AsyncSession, user_id: int, permission_ids: List[int]) -> str:
        """Révoque des permissions directement d'un utilisateur."""
        try:
            db_obj = await self.get_or_404(db, user_id)
            permissions = await db.execute(
                select(PermissionModel).filter(PermissionModel.id.in_(permission_ids))
            )
            permission_objects = permissions.scalars().all()
            if not permission_objects:
                all_permissions = await db.execute(select(PermissionModel))
                available_permissions = all_permissions.scalars().all()
                available_ids = [p.id for p in available_permissions]
                available_names = [p.nom.value for p in available_permissions]
                raise HTTPException(
                    status_code=400,
                    detail=f"Aucune permission valide fournie. IDs demandés: {permission_ids}. Permissions disponibles: {available_names} (IDs: {available_ids})"
                )
            user_permissions_query = await db.execute(
                select(PermissionModel)
                .join(association_utilisateurs_permissions)
                .filter(association_utilisateurs_permissions.c.utilisateur_id == user_id)
            )
            current_permission_ids = {p.id: p for p in user_permissions_query.scalars().all()}
            revoked_permissions = []
            for permission in permission_objects:
                if permission.id in current_permission_ids:
                    await db.execute(
                        delete(association_utilisateurs_permissions).where(
                            (association_utilisateurs_permissions.c.utilisateur_id == user_id) &
                            (association_utilisateurs_permissions.c.permission_id == permission.id)
                        )
                    )
                    revoked_permissions.append(permission)
            await db.flush()
            if revoked_permissions:
                permission_names = [p.nom.value for p in revoked_permissions]
                return f"Permissions {', '.join(permission_names)} révoquées avec succès de l'utilisateur {db_obj.nom} {db_obj.prenom}"
            return f"Aucune permission n'a été révoquée de l'utilisateur {db_obj.nom} {db_obj.prenom}"
        except SQLAlchemyError as e:
            logger.error(f"Erreur lors de la révocation des permissions: {str(e)}")
            raise HTTPException(
                status_code=500,
                detail="Erreur lors de la révocation des permissions"
            )

    async def login(self, db: AsyncSession, account: loginSchema) -> dict:
        """Authentifie un utilisateur et retourne un token JWT."""
        try:
            query = select(self.model).filter(self.model.email == account.email).options(
                selectinload(self.model.role).selectinload(RoleModel.permissions),
                selectinload(self.model.permissions)
            )
            result = await db.execute(query)
            db_obj = result.scalars().first()
            if not db_obj:
                logger.warning(f"Tentative de connexion avec email non trouvé: {account.email}")
                raise HTTPException(
                    status_code=401,
                    detail="Email ou mot de passe incorrect"
                )
            if not pwd_context.verify(account.password, db_obj.password):  # Changed from hashed_password to password
                logger.warning(f"Mot de passe incorrect pour l'utilisateur: {account.email}")
                raise HTTPException(
                    status_code=401,
                    detail="Email ou mot de passe incorrect"
                )
            if db_obj.statut != StatutCompteEnum.ACTIF:
                logger.warning(f"Tentative de connexion avec un compte inactif: {account.email}, statut: {db_obj.statut}")
                raise HTTPException(
                    status_code=403,
                    detail="Votre compte n'est pas actif. Veuillez contacter l'administrateur."
                )
            payload = {
                "sub": str(db_obj.id),
                "email": db_obj.email,
                "exp": datetime.now(timezone.utc) + timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)
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
                status_code=500,
                detail="Erreur lors de la connexion"
            )

    async def get_current_user(self, db: AsyncSession, token: str):
        """Récupère l'utilisateur connecté à partir du token JWT."""
        try:
            payload = jwt.decode(token, settings.SECRET_KEY, algorithms=[settings.ALGORITHM])
            user_id = int(payload.get("sub"))
            if user_id is None:
                raise HTTPException(status_code=401, detail="Token invalide")
        except JWTError:
            raise HTTPException(status_code=401, detail="Token invalide")
        query = select(self.model).filter(self.model.id == user_id).options(
            selectinload(self.model.role).selectinload(RoleModel.permissions),
            selectinload(self.model.permissions)
        )
        result = await db.execute(query)
        user = result.scalars().first()
        if user is None:
            raise HTTPException(status_code=404, detail="Utilisateur non trouvé")
        role_light = None
        if user.role:
            role_light = RoleLight(
                id=user.role.id,
                nom=user.role.nom,
                permissions=[PermissionMinLight(id=perm.id, nom=perm.nom) for perm in user.role.permissions],
                user_count=(await db.execute(
                    select(func.count(UtilisateurModel.id)).filter(UtilisateurModel.role_id == user.role.id)
                )).scalar()
            )
        return UtilisateurLight(
            id=user.id,
            nom=user.nom,
            prenom=user.prenom,
            sexe=user.sexe,
            email=user.email,
            statut=user.statut,
            est_actif=user.est_actif,
            date_naissance=user.date_naissance,
            created_at=user.created_at,
            updated_at=user.updated_at,
            role=role_light,
            permissions=[PermissionLight(id=perm.id, nom=perm.nom, roles=[]) for perm in user.permissions]
        )

    async def send_reset_link(self, db: AsyncSession, email: str, request: Request) -> None:
        """Envoie un lien de réinitialisation de mot de passe."""
        try:
            query = select(self.model).filter(self.model.email == email).options(
                selectinload(self.model.role).selectinload(RoleModel.permissions),
                selectinload(self.model.permissions)
            )
            result = await db.execute(query)
            db_obj = result.scalars().first()
            if not db_obj:
                return
            reset_token = str(uuid4())
            db_obj.reset_token = reset_token
            db_obj.reset_token_expiry = datetime.now(timezone.utc) + timedelta(hours=1)
            await db.flush()
            base_url = str(request.base_url).rstrip("/")
            reset_link = f"{base_url}/reset-password-confirm?token={reset_token}"
            email_service = EmailService()
            content = f"Pour réinitialiser votre mot de passe, cliquez sur ce lien : <a href='{reset_link}'>Réinitialiser le mot de passe</a>\nCe lien expirera dans 1 heure."
            try:
                await email_service.send_custom_email(db_obj.email, "Réinitialisation de mot de passe", content, title="Réinitialisation de mot de passe", language="fr")
            finally:
                await email_service.close()
        except SQLAlchemyError as e:
            logger.error(f"Erreur lors de l'envoi du lien de réinitialisation: {str(e)}")
            # Do not raise exception to avoid revealing email existence
            
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
    
    async def get_all(self, db: AsyncSession, skip: int = 0, limit: int = 100) -> List[FormationLight]:
        try:
            result = await db.execute(
                select(self.model)
                .offset(skip)
                .limit(limit)
            )
            formations = result.scalars().all()
            if not formations:
                return []
            return [self.light_schema.from_orm(formation) for formation in formations]
        except SQLAlchemyError as e:
            logger.error(f"Erreur de base de données lors de la récupération des formations: {str(e)}", exc_info=True)
            raise HTTPException(
                status_code=500,
                detail=f"Erreur de base de données lors de la récupération des formations: {str(e)}"
            )


# ============================================================================
# ========================= SERVICE DES INSCRIPTIONS =========================
# ============================================================================

class InscriptionFormationService(BaseService[InscriptionFormationModel, InscriptionFormation, InscriptionFormationCreate, InscriptionFormationUpdate]):
    """Service pour la gestion des inscriptions aux formations."""
    def __init__(self):
        super().__init__(InscriptionFormationModel, InscriptionFormation, InscriptionFormationLight)

    async def create(self, db: AsyncSession, obj_in: InscriptionFormationCreate) -> InscriptionFormationLight:
        """Crée une nouvelle inscription avec validation."""
        await self.get_or_404(db, obj_in.utilisateur_id, UtilisateurModel, "Utilisateur")
        await self.get_or_404(db, obj_in.formation_id, FormationModel, "Formation")
        try:
            db_obj = self.model(**obj_in.dict(exclude_unset=True))
            db.add(db_obj)
            await db.flush()
            # Eagerly load the paiements relationship
            result = await db.execute(
                select(self.model)
                .filter(self.model.id == db_obj.id)
                .options(selectinload(self.model.paiements))
            )
            db_obj = result.scalars().first()
            if db_obj is None:
                raise HTTPException(
                    status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                    detail="Failed to retrieve newly created inscription"
                )
            return await self._safe_from_orm(db_obj, self.light_schema)
        except IntegrityError as e:
            logger.error(f"Erreur d'intégrité lors de la création de l'inscription: {str(e)}", exc_info=True)
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="Inscription existe déjà"
            )
        except SQLAlchemyError as e:
            logger.error(f"Erreur de base de données lors de la création de l'inscription: {str(e)}", exc_info=True)
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Erreur de base de données lors de la création de l'inscription"
            )

    async def get_all(self, db: AsyncSession, skip: int = 0, limit: int = 100) -> List[InscriptionFormationLight]:
        try:
            result = await db.execute(
                select(self.model)
                .options(
                    selectinload(self.model.utilisateur)
                        .selectinload(UtilisateurModel.role),
                    selectinload(self.model.utilisateur)
                        .selectinload(UtilisateurModel.permissions),
                    selectinload(self.model.formation),
                    selectinload(self.model.paiements)
                )
                .offset(skip)
                .limit(limit)
            )
            inscriptions = result.scalars().all()
            if not inscriptions:
                return []
            return [self.light_schema.from_orm(inscription) for inscription in inscriptions]
        except SQLAlchemyError as e:
            logger.error(f"Erreur de base de données lors de la récupération des inscriptions: {str(e)}", exc_info=True)
            raise HTTPException(
                status_code=500,
                detail=f"Erreur de base de données lors de la récupération des inscriptions: {str(e)}"
            )
        except Exception as e:
            logger.error(f"Erreur inattendue lors de la récupération des inscriptions: {str(e)}", exc_info=True)
            raise HTTPException(
                status_code=500,
                detail=f"Erreur inattendue: {str(e)}"
            )

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
                return await self._safe_from_orm(db_obj, InscriptionFormation)
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
            return await self._safe_from_orm(db_obj, InscriptionFormation)
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
                return await self._safe_from_orm(db_obj, PaiementLight)
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
                return await self._safe_from_orm(db_obj, Paiement)
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
            return [await self._safe_from_orm(obj, Paiement) for obj in result.scalars().all()]
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
                return await self._safe_from_orm(db_obj, ModuleLight)
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

    async def get_modules_by_formation(self, db: AsyncSession, formation_id: int, skip: int = 0, limit: int = 100) -> List[ModuleLight]:
        """Récupère tous les modules d'une formation spécifique."""
        try:
            # Vérifier que la formation existe
            await self.get_or_404(db, formation_id, FormationModel, "Formation")

            # Récupérer les modules de la formation, triés par ordre
            result = await db.execute(
                select(self.model)
                .filter(self.model.formation_id == formation_id)
                .order_by(self.model.ordre)
                .offset(skip)
                .limit(limit)
            )
            modules = result.scalars().all()

            if not modules:
                return []

            return [self.light_schema.model_validate(module) for module in modules]
        except SQLAlchemyError as e:
            logger.error(f"Erreur de base de données lors de la récupération des modules de la formation {formation_id}: {str(e)}", exc_info=True)
            raise HTTPException(
                status_code=500,
                detail=f"Erreur de base de données lors de la récupération des modules: {str(e)}"
            )

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
                return await self._safe_from_orm(db_obj, ProjetCollectifLight)
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
                return await self._safe_from_orm(db_obj, ProjetCollectif)
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
                return await self._safe_from_orm(db_obj, QuestionLight)
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
                return await self._safe_from_orm(db_obj, Question)
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
       
       
                
                 