# main.py
import asyncio
import signal
import sys
from loguru import logger
from core.config.settings import settings
from bots.public_bot import public_bot
from bots.admin_bot import admin_bot
from services.monitor import MonitorService

class Application:
    """
    Aplicação principal que gerencia ambos os bots
    """
    
    def __init__(self):
        """Inicializar aplicação"""
        self.monitor = MonitorService()
        self.running = False
        logger.info("Aplicação principal inicializada")
    
    async def start(self):
        """Iniciar todos os serviços"""
        try:
            logger.info("=" * 50)
            logger.info("Iniciando Plataforma Marketing Xixa...")
            logger.info("=" * 50)
            
            # Iniciar monitor
            await self.monitor.start()
            
            # Iniciar bots
            await asyncio.gather(
                public_bot.start(),
                admin_bot.start()
            )
            
            self.running = True
            logger.info("✅ Plataforma iniciada com sucesso!")
            
            # Configurar handlers de sinal para graceful shutdown
            signal.signal(signal.SIGINT, self.signal_handler)
            signal.signal(signal.SIGTERM, self.signal_handler)
            
            # Manter aplicação rodando
            while self.running:
                await asyncio.sleep(1)
                
        except Exception as e:
            logger.error(f"Erro fatal ao iniciar aplicação: {e}")
            await self.shutdown()
    
    async def shutdown(self):
        """Desligar todos os serviços"""
        logger.info("Iniciando shutdown...")
        
        self.running = False
        
        # Parar bots
        if public_bot.application:
            await public_bot.application.stop()
            await public_bot.application.shutdown()
        
        if admin_bot.application:
            await admin_bot.application.stop()
            await admin_bot.application.shutdown()
        
        # Parar monitor
        await self.monitor.stop()
        
        logger.info("✅ Plataforma desligada com sucesso!")
    
    def signal_handler(self, signum, frame):
        """Handler para sinais do sistema"""
        logger.info(f"Sinal recebido: {signum}")
        asyncio.create_task(self.shutdown())

async def main():
    """Função principal"""
    app = Application()
    
    try:
        await app.start()
    except KeyboardInterrupt:
        logger.info("KeyboardInterrupt recebido")
    except Exception as e:
        logger.error(f"Erro na aplicação: {e}")
    finally:
        await app.shutdown()

if __name__ == "__main__":
    # Configurar política de eventos para Windows
    if sys.platform == "win32":
        asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())
    
    # Executar aplicação
    asyncio.run(main())
