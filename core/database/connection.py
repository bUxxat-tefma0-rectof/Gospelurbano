# core/database/connection.py
from sqlalchemy import create_engine, event
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker, Session
from sqlalchemy.pool import QueuePool
from typing import Generator
from contextlib import contextmanager
from loguru import logger
from core.config.settings import settings

# Criar engine com pool de conexões
engine = create_engine(
    settings.DATABASE_URL,
    poolclass=QueuePool,
    pool_size=settings.database_pool_size,
    max_overflow=10,
    pool_pre_ping=True,
    pool_recycle=3600,
    echo=False
)

# Event listeners para monitoramento
@event.listens_for(engine, "connect")
def receive_connect(dbapi_connection, connection_record):
    logger.info("Nova conexão estabelecida com o banco de dados")

@event.listens_for(engine, "checkout")
def receive_checkout(dbapi_connection, connection_record, connection_proxy):
    logger.debug("Conexão check-out do pool")

@event.listens_for(engine, "checkin")
def receive_checkin(dbapi_connection, connection_record):
    logger.debug("Conexão retornada ao pool")

# Criar session factory
SessionLocal = sessionmaker(
    autocommit=False,
    autoflush=False,
    bind=engine,
    expire_on_commit=False
)

# Base para modelos
Base = declarative_base()

def get_db() -> Generator[Session, None, None]:
    """
    Dependency para obter sessão do banco de dados
    """
    db = SessionLocal()
    try:
        yield db
        db.commit()
    except Exception as e:
        db.rollback()
        logger.error(f"Erro na transação: {e}")
        raise
    finally:
        db.close()

@contextmanager
def get_db_context() -> Generator[Session, None, None]:
    """
    Context manager para uso com with
    """
    db = SessionLocal()
    try:
        yield db
        db.commit()
    except Exception as e:
        db.rollback()
        logger.error(f"Erro na transação: {e}")
        raise
    finally:
        db.close()

def init_db():
    """
    Inicializar banco de dados criando todas as tabelas
    """
    try:
        # Importar todos os modelos antes de criar tabelas
        from core.database.models import (
            User, Product, Category, Plan, Order, Payment,
            Form, FormField, FormResponse, Button, Menu,
            AIConfig, SystemLog, Notification, AdminUser
        )
        
        Base.metadata.create_all(bind=engine)
        logger.info("Banco de dados inicializado com sucesso")
        
        # Criar admin padrão se não existir
        with get_db_context() as db:
            from core.database.models import AdminUser
            if not db.query(AdminUser).filter(AdminUser.telegram_id == settings.ADMIN_TELEGRAM_ID).first():
                admin = AdminUser(
                    telegram_id=settings.ADMIN_TELEGRAM_ID,
                    username="admin",
                    permissions={"all": True},
                    is_active=True
                )
                db.add(admin)
                logger.info(f"Admin padrão criado: {settings.ADMIN_TELEGRAM_ID}")
                
    except Exception as e:
        logger.error(f"Erro ao inicializar banco de dados: {e}")
        raise
