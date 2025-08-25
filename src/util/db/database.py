import logging
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession, async_sessionmaker
from sqlalchemy.orm import declarative_base
from sqlalchemy.pool import AsyncAdaptedQueuePool
from src.util.db.setting import settings

logger = logging.getLogger(__name__)
logging.basicConfig(level=logging.INFO)

async_engine = create_async_engine(
    settings.DATABASE_URL,
    echo=False,
    future=True,
    poolclass=AsyncAdaptedQueuePool
)

AsyncSessionLocal = async_sessionmaker(
    bind=async_engine,
    class_=AsyncSession,
    expire_on_commit=False,
)

Base = declarative_base()

async def get_async_db():
    async with AsyncSessionLocal() as session:
        try:
            yield session
            await session.commit()
        except Exception as e:
            await session.rollback()
            logger.error(f"Erreur DB : {str(e)}", exc_info=True)
            if "connection" in str(e).lower() or "timeout" in str(e).lower():
                logger.error("Erreur de connexion à la base de données - tentative de reconnexion")
                await close_db()
                await init_db()
            raise

async def init_db():
    async with async_engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    logger.info("Base de données initialisée")

async def close_db():
    await async_engine.dispose()
    logger.info("Connexion à la base de données fermée")