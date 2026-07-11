# services/monitor.py
import asyncio
from datetime import datetime
from loguru import logger
from core.database.connection import engine, get_db_context
from sqlalchemy import text

class MonitorService:
    """
    Serviço de monitoramento do sistema
    """
    
    def __init__(self):
        """Inicializar monitor"""
        self.tasks = []
        logger.info("MonitorService inicializado")
    
    async def start(self):
        """Iniciar monitoramento"""
        logger.info("Iniciando serviços de monitoramento...")
        
        # Iniciar tarefas de monitoramento
        self.tasks = [
            asyncio.create_task(self.check_database_health()),
            asyncio.create_task(self.check_expired_orders()),
            asyncio.create_task(self.clean_old_logs())
        ]
        
        logger.info("Serviços de monitoramento iniciados")
    
    async def stop(self):
        """Parar monitoramento"""
        for task in self.tasks:
            task.cancel()
        
        logger.info("Serviços de monitoramento parados")
    
    async def check_database_health(self):
        """Verificar saúde do banco de dados"""
        while True:
            try:
                with get_db_context() as db:
                    # Executar query simples
                    result = db.execute(text("SELECT 1")).scalar()
                    
                    if result == 1:
                        logger.debug("✅ Database health check OK")
                    else:
                        logger.warning("⚠️ Database health check falhou")
                        
            except Exception as e:
                logger.error(f"❌ Database health check error: {e}")
            
            await asyncio.sleep(60)  # Verificar a cada 60 segundos
    
    async def check_expired_orders(self):
        """Verificar pedidos expirados"""
        while True:
            try:
                with get_db_context() as db:
                    now = datetime.utcnow()
                    
                    # Cancelar pedidos expirados
                    result = db.execute(text("""
                        UPDATE orders 
                        SET status = 'expired', updated_at = :now
                        WHERE status = 'pending' 
                        AND expires_at < :now
                    """), {"now": now})
                    
                    if result.rowcount > 0:
                        logger.info(f"📦 {result.rowcount} pedidos expirados cancelados")
                        
            except Exception as e:
                logger.error(f"Erro ao verificar pedidos expirados: {e}")
            
            await asyncio.sleep(300)  # Verificar a cada 5 minutos
    
    async def clean_old_logs(self):
        """Limpar logs antigos"""
        while True:
            try:
                with get_db_context() as db:
                    # Manter apenas 90 dias de logs
                    cutoff_date = datetime.utcnow() - timedelta(days=90)
                    
                    result = db.execute(text("""
                        DELETE FROM system_logs 
                        WHERE created_at < :cutoff_date
                    """), {"cutoff_date": cutoff_date})
                    
                    if result.rowcount > 0:
                        logger.info(f"🗑️ {result.rowcount} logs antigos removidos")
                        
            except Exception as e:
                logger.error(f"Erro ao limpar logs: {e}")
            
            await asyncio.sleep(86400)  # Executar uma vez por dia
