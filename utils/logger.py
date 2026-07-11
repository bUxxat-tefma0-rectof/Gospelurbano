# utils/logger.py
from loguru import logger
import sys
from core.config.settings import settings

def setup_logger():
    """
    Configurar sistema de logs
    """
    # Remover configuração padrão
    logger.remove()
    
    # Adicionar log no console
    logger.add(
        sys.stdout,
        format="<green>{time:YYYY-MM-DD HH:mm:ss}</green> | <level>{level: <8}</level> | <cyan>{name}</cyan>:<cyan>{function}</cyan>:<cyan>{line}</cyan> - <level>{message}</level>",
        level=settings.LOG_LEVEL,
        colorize=True
    )
    
    # Adicionar log em arquivo com rotação
    logger.add(
        "logs/app_{time:YYYY-MM-DD}.log",
        rotation="00:00",  # Rotacionar diariamente à meia-noite
        retention="30 days",  # Manter por 30 dias
        compression="zip",  # Comprimir logs antigos
        level="INFO",
        format="{time:YYYY-MM-DD HH:mm:ss} | {level: <8} | {name}:{function}:{line} - {message}"
    )
    
    # Log de erros separado
    logger.add(
        "logs/errors_{time:YYYY-MM-DD}.log",
        rotation="00:00",
        retention="90 days",
        compression="zip",
        level="ERROR",
        format="{time:YYYY-MM-DD HH:mm:ss} | {level: <8} | {name}:{function}:{line} - {message}\n{exception}"
    )
    
    logger.info("Sistema de logs configurado com sucesso")
    
    return logger

# Configurar logger
log = setup_logger()
