from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from jose import JWTError, jwt
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from sqlalchemy.orm import selectinload
from datetime import datetime, timezone
from typing import List
import logging

from src.api.model import Role, Utilisateur as UtilisateurModel, Permission as PermissionModel
from src.api.schema import PermissionLight, UtilisateurLight
from src.util.database.database import get_async_db
from src.util.helper.enum import StatutCompteEnum
from src.util.database.setting import settings

logger = logging.getLogger(__name__)

# OAuth2 scheme pour le Bearer Token
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/login")

async def get_current_user(token: str = Depends(oauth2_scheme), db: AsyncSession = Depends(get_async_db)) -> UtilisateurLight:
    """Récupère l'utilisateur courant à partir d'un token JWT avec ses permissions."""
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Token invalide ou expiré",
        headers={"WWW-Authenticate": "Bearer"},
    )
    try:
        payload = jwt.decode(token, settings.SECRET_KEY, algorithms=[settings.ALGORITHM])
        user_id: str = payload.get("sub")
        if user_id is None:
            logger.warning("Token JWT sans 'sub' (ID utilisateur)")
            raise credentials_exception
        if payload.get("exp") < datetime.now(timezone.utc).timestamp():
            logger.warning(f"Token JWT expiré pour l'utilisateur ID: {user_id}")
            raise credentials_exception
    except JWTError as e:
        logger.error(f"Erreur de décodage du token JWT: {str(e)}")
        raise credentials_exception

    try:
        query = select(UtilisateurModel).filter(UtilisateurModel.id == int(user_id)).options(
            selectinload(UtilisateurModel.permissions),  # Permissions directes
            selectinload(UtilisateurModel.role).selectinload(Role.permissions)  # Permissions via le rôle
        )
        result = await db.execute(query)
        user = result.scalars().first()
        if user is None:
            logger.warning(f"Utilisateur ID {user_id} non trouvé")
            raise credentials_exception
        
        # Combiner les permissions directes et celles du rôle
        permissions = user.permissions[:]
        if user.role:
            role_permissions = user.role.permissions
            permission_ids = {p.id for p in permissions}
            # Ajouter les permissions du rôle qui ne sont pas déjà dans les permissions directes
            permissions.extend([p for p in role_permissions if p.id not in permission_ids])
        
        user_light = UtilisateurLight.from_orm(user)
        user_light.permissions = [PermissionLight.from_orm(p) for p in permissions]
        return user_light
    except Exception as e:
        logger.error(f"Erreur lors de la récupération de l'utilisateur: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Erreur lors de la récupération de l'utilisateur"
        )

async def get_current_active_user(current_user: UtilisateurLight = Depends(get_current_user)) -> UtilisateurLight:
    """Vérifie que l'utilisateur courant est actif."""
    if current_user.statut != StatutCompteEnum.ACTIF:
        logger.warning(f"Tentative d'accès par un utilisateur inactif: {current_user.email}")
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Utilisateur inactif"
        )
    return current_user

def has_permission(user: UtilisateurLight, required_permissions: List[str]) -> bool:
    """Vérifie si l'utilisateur possède toutes les permissions requises."""
    user_permission_names = {perm.nom.value for perm in user.permissions}
    required_permission_set = set(required_permissions)
    return required_permission_set.issubset(user_permission_names)

def require_permissions(required_permissions: List[str]):
    """Factory FastAPI pour vérifier les permissions requises."""
    async def dependency(current_user: UtilisateurLight = Depends(get_current_active_user)) -> UtilisateurLight:
        if not has_permission(current_user, required_permissions):
            missing_permissions = set(required_permissions) - {perm.nom.value for perm in current_user.permissions}
            logger.warning(
                f"Utilisateur {current_user.email} n'a pas les permissions requises: {missing_permissions}"
            )
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Permissions manquantes: {', '.join(missing_permissions)}"
            )
        return current_user

    return dependency
