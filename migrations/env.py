import asyncio
from logging.config import fileConfig
import os
from sqlalchemy import engine_from_config, pool
from sqlalchemy.ext.asyncio import AsyncEngine
from dotenv import load_dotenv
from alembic import context
from pathlib import Path

from src.util.database.setting import settings

BASE_DIR = Path(__file__).resolve().parent.parent
os.sys.path.append(str(BASE_DIR))
load_dotenv(BASE_DIR / ".env")

# Configuration d'Alembic
config = context.config
if config.config_file_name is not None:
    fileConfig(config.config_file_name)

# Importer Base
from src.util.database.database import Base

from src.api.model import (
    Permission, Role, Utilisateur,
    InscriptionFormation, Formation,
    Module, Ressource, ChefDOeuvre,
    ProjetCollectif, Evaluation,
    Question, Proposition,
    ResultatEvaluation, GenotypeIndividuel,
    AscendanceGenotype, SanteGenotype,
    EducationGenotype, PlanInterventionIndividualise,
    Accreditation, Actualite,
    Paiement,
    association_roles_permissions, association_utilisateurs_permissions,
    association_projets_collectifs_membres
)

# Définir les métadonnées cibles
target_metadata = Base.metadata

# URL de la base de données depuis l'environnement
database_url = settings.DATABASE_URL

print(f"database_url: {database_url}")
if not database_url:
    raise ValueError("DATABASE_URL or required DB variables are not set in .env file")

config.set_main_option("sqlalchemy.url", database_url)

def run_migrations_offline() -> None:
    """Exécuter les migrations en mode hors ligne."""
    url = config.get_main_option("sqlalchemy.url")
    context.configure(
        url=url,
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
    )
    with context.begin_transaction():
        context.run_migrations()

async def run_migrations_online() -> None:
    """Exécuter les migrations en mode en ligne."""
    connectable = AsyncEngine(
        engine_from_config(
            config.get_section(config.config_ini_section, {}),
            prefix="sqlalchemy.",
            poolclass=pool.NullPool,
        )
    )
    async with connectable.connect() as connection:
        await connection.run_sync(do_run_migrations)

def do_run_migrations(connection) -> None:
    context.configure(
        connection=connection,
        target_metadata=target_metadata
    )
    with context.begin_transaction():
        context.run_migrations()

if context.is_offline_mode():
    run_migrations_offline()
else:
    asyncio.run(run_migrations_online())