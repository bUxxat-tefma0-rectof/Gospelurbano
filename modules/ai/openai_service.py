# modules/ai/openai_service.py
import openai
from typing import List, Dict, Optional, Any
from datetime import datetime, timedelta
from loguru import logger
from core.config.settings import settings
from core.database.connection import get_db_context
from core.database.models import AIConfig, ChatHistory, SystemLog

class OpenAIService:
    """
    Serviço de integração com OpenAI
    """
    
    def __init__(self):
        """Inicializar cliente OpenAI"""
        self.client = openai.OpenAI(api_key=settings.OPENAI_API_KEY)
        self.conversations = {}  # Cache de conversas em memória
        logger.info("OpenAIService inicializado")
    
    async def get_ai_config(self) -> Optional[Dict[str, Any]]:
        """
        Obter configuração ativa da IA
        
        Returns:
            Dict com configuração ou None
        """
        try:
            with get_db_context() as db:
                config = db.query(AIConfig).filter(AIConfig.is_active == True).first()
                
                if config:
                    return {
                        "id": config.id,
                        "model": config.model,
                        "temperature": config.temperature,
                        "max_tokens": config.max_tokens,
                        "system_prompt": config.system_prompt,
                        "behavior": config.behavior,
                        "daily_limit": config.daily_limit
                    }
        except Exception as e:
            logger.error(f"Erro ao obter configuração IA: {e}")
        
        return None
    
    async def check_daily_limit(self, user_id: int) -> bool:
        """
        Verificar limite diário de requisições
        
        Args:
            user_id: ID do usuário
            
        Returns:
            True se ainda tem limite disponível
        """
        try:
            with get_db_context() as db:
                # Contar requisições do dia
                today = datetime.utcnow().date()
                count = db.query(ChatHistory).filter(
                    ChatHistory.user_id == user_id,
                    ChatHistory.is_ai == True,
                    ChatHistory.created_at >= today
                ).count()
                
                # Obter limite configurado
                config = db.query(AIConfig).filter(AIConfig.is_active == True).first()
                limit = config.daily_limit if config else 100
                
                return count < limit
                
        except Exception as e:
            logger.error(f"Erro ao verificar limite diário: {e}")
            return True  # Permitir em caso de erro
    
    async def chat(
        self,
        user_id: int,
        message: str,
        username: str = "Cliente"
    ) -> Dict[str, Any]:
        """
        Enviar mensagem para IA e obter resposta
        
        Args:
            user_id: ID do usuário
            message: Mensagem do usuário
            username: Nome do usuário
            
        Returns:
            Dict com resposta da IA
        """
        try:
            # Verificar limite diário
            if not await self.check_daily_limit(user_id):
                return {
                    "success": False,
                    "error": "Limite diário de requisições atingido",
                    "needs_human": True
                }
            
            # Obter configuração
            config = await self.get_ai_config()
            if not config:
                return {
                    "success": False,
                    "error": "IA não configurada",
                    "needs_human": True
                }
            
            # Obter ou criar histórico da conversa
            conversation_key = f"user_{user_id}"
            if conversation_key not in self.conversations:
                self.conversations[conversation_key] = []
                
                # Adicionar mensagem do sistema
                system_message = config.get("system_prompt", 
                    "Você é um assistente virtual profissional. "
                    "Responda de forma clara, educada e objetiva."
                )
                
                self.conversations[conversation_key].append({
                    "role": "system",
                    "content": system_message
                })
            
            # Adicionar mensagem do usuário
            self.conversations[conversation_key].append({
                "role": "user",
                "content": message
            })
            
            # Limitar histórico (últimas 20 mensagens)
            if len(self.conversations[conversation_key]) > 21:  # 1 system + 20 mensagens
                # Manter system message e remover as mais antigas
                system_msg = self.conversations[conversation_key][0]
                self.conversations[conversation_key] = (
                    [system_msg] + self.conversations[conversation_key][-20:]
                )
            
            # Chamar OpenAI
            response = self.client.chat.completions.create(
                model=config.get("model", "gpt-3.5-turbo"),
                messages=self.conversations[conversation_key],
                temperature=config.get("temperature", 0.7),
                max_tokens=config.get("max_tokens", 500)
            )
            
            # Obter resposta
            ai_response = response.choices[0].message.content
            
            # Adicionar resposta ao histórico
            self.conversations[conversation_key].append({
                "role": "assistant",
                "content": ai_response
            })
            
            # Salvar no banco de dados
            await self.save_chat_history(user_id, message, ai_response)
            
            # Verificar se precisa de atendimento humano
            needs_human = self.detect_human_need(message, ai_response)
            
            return {
                "success": True,
                "response": ai_response,
                "needs_human": needs_human,
                "usage": {
                    "prompt_tokens": response.usage.prompt_tokens,
                    "completion_tokens": response.usage.completion_tokens,
                    "total_tokens": response.usage.total_tokens
                }
            }
            
        except Exception as e:
            logger.error(f"Erro ao processar chat IA: {e}")
            return {
                "success": False,
                "error": str(e),
                "needs_human": True
            }
    
    def detect_human_need(self, user_message: str, ai_response: str) -> bool:
        """
        Detectar se a conversa precisa de atendimento humano
        
        Args:
            user_message: Mensagem do usuário
            ai_response: Resposta da IA
            
        Returns:
            True se precisa de humano
        """
        # Palavras-chave que indicam necessidade de atendimento humano
        human_keywords = [
            "falar com atendente",
            "atendimento humano",
            "pessoa real",
            "gerente",
            "supervisor",
            "reclamação",
            "reclamar",
            "cancelar tudo",
            "estorno",
            "processo judicial",
            "advogado",
            "procon"
        ]
        
        # Verificar se usuário pediu explicitamente
        message_lower = user_message.lower()
        for keyword in human_keywords:
            if keyword in message_lower:
                return True
        
        # Verificar se IA não conseguiu responder adequadamente
        uncertainty_phrases = [
            "não sei",
            "não posso",
            "não tenho certeza",
            "não consigo",
            "infelizmente não"
        ]
        
        response_lower = ai_response.lower()
        for phrase in uncertainty_phrases:
            if phrase in response_lower:
                return True
        
        return False
    
    async def save_chat_history(self, user_id: int, message: str, response: str):
        """
        Salvar histórico da conversa
        
        Args:
            user_id: ID do usuário
            message: Mensagem do usuário
            response: Resposta da IA
        """
        try:
            with get_db_context() as db:
                # Salvar mensagem do usuário
                user_chat = ChatHistory(
                    user_id=user_id,
                    message=message,
                    is_ai=False
                )
                db.add(user_chat)
                
                # Salvar resposta da IA
                ai_chat = ChatHistory(
                    user_id=user_id,
                    message=response,
                    response=response,
                    is_ai=True
                )
                db.add(ai_chat)
                
                logger.debug(f"Histórico salvo para usuário {user_id}")
                
        except Exception as e:
            logger.error(f"Erro ao salvar histórico: {e}")
    
    def clear_conversation(self, user_id: int):
        """
        Limpar conversa da memória
        
        Args:
            user_id: ID do usuário
        """
        conversation_key = f"user_{user_id}"
        if conversation_key in self.conversations:
            del self.conversations[conversation_key]
            logger.info(f"Conversa limpa para usuário {user_id}")
    
    async def generate_suggestions(self, context: str) -> List[str]:
        """
        Gerar sugestões baseadas no contexto
        
        Args:
            context: Contexto atual
            
        Returns:
            Lista de sugestões
        """
        try:
            config = await self.get_ai_config()
            if not config:
                return []
            
            prompt = f"""
            Baseado no seguinte contexto, sugira 3 perguntas ou ações relevantes:
            
            Contexto: {context}
            
            Gere apenas as sugestões, uma por linha, sem numeração.
            """
            
            response = self.client.chat.completions.create(
                model=config.get("model", "gpt-3.5-turbo"),
                messages=[{"role": "user", "content": prompt}],
                temperature=0.8,
                max_tokens=200
            )
            
            suggestions = response.choices[0].message.content.strip().split("\n")
            return [s.strip() for s in suggestions if s.strip()][:3]
            
        except Exception as e:
            logger.error(f"Erro ao gerar sugestões: {e}")
            return []

# Instância global
openai_service = OpenAIService()
