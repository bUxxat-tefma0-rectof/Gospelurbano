# modules/payments/mercadopago.py
import mercadopago
from typing import Dict, Optional, Any
from datetime import datetime, timedelta
from loguru import logger
from core.config.settings import settings

class MercadoPagoService:
    """
    Serviço de integração com Mercado Pago
    """
    
    def __init__(self):
        """Inicializar SDK do Mercado Pago"""
        self.sdk = mercadopago.SDK(settings.MERCADO_PAGO_ACCESS_TOKEN)
        logger.info("MercadoPagoService inicializado")
    
    async def create_pix_payment(
        self,
        amount: float,
        description: str,
        payer_email: str,
        expiration_minutes: int = 30
    ) -> Dict[str, Any]:
        """
        Criar pagamento PIX
        
        Args:
            amount: Valor do pagamento
            description: Descrição do pagamento
            payer_email: Email do pagador
            expiration_minutes: Minutos para expiração
            
        Returns:
            Dict com dados do pagamento PIX
        """
        try:
            # Calcular data de expiração
            expiration_date = datetime.utcnow() + timedelta(minutes=expiration_minutes)
            
            payment_data = {
                "transaction_amount": float(amount),
                "description": description,
                "payment_method_id": "pix",
                "payer": {
                    "email": payer_email
                },
                "date_of_expiration": expiration_date.strftime("%Y-%m-%dT%H:%M:%S.000-03:00")
            }
            
            # Criar pagamento
            payment_response = self.sdk.payment().create(payment_data)
            payment = payment_response["response"]
            
            logger.info(f"Pagamento PIX criado: {payment['id']}")
            
            return {
                "success": True,
                "payment_id": payment["id"],
                "status": payment["status"],
                "qr_code": payment["point_of_interaction"]["transaction_data"]["qr_code"],
                "qr_code_base64": payment["point_of_interaction"]["transaction_data"]["qr_code_base64"],
                "copy_paste": payment["point_of_interaction"]["transaction_data"]["qr_code"],
                "expiration_date": expiration_date
            }
            
        except Exception as e:
            logger.error(f"Erro ao criar pagamento PIX: {e}")
            return {"success": False, "error": str(e)}
    
    async def check_payment_status(self, payment_id: str) -> Dict[str, Any]:
        """
        Verificar status do pagamento
        
        Args:
            payment_id: ID do pagamento no Mercado Pago
            
        Returns:
            Dict com status do pagamento
        """
        try:
            payment_response = self.sdk.payment().get(payment_id)
            payment = payment_response["response"]
            
            return {
                "success": True,
                "payment_id": payment["id"],
                "status": payment["status"],
                "status_detail": payment.get("status_detail"),
                "amount": payment["transaction_amount"],
                "date_approved": payment.get("date_approved"),
                "date_created": payment["date_created"]
            }
            
        except Exception as e:
            logger.error(f"Erro ao verificar pagamento {payment_id}: {e}")
            return {"success": False, "error": str(e)}
    
    async def refund_payment(self, payment_id: str, amount: Optional[float] = None) -> Dict[str, Any]:
        """
        Reembolsar pagamento
        
        Args:
            payment_id: ID do pagamento
            amount: Valor a reembolsar (None = total)
            
        Returns:
            Dict com resultado do reembolso
        """
        try:
            refund_data = {}
            if amount:
                refund_data["amount"] = amount
            
            refund_response = self.sdk.refund().create(payment_id, refund_data)
            refund = refund_response["response"]
            
            logger.info(f"Reembolso criado para pagamento {payment_id}: {refund['id']}")
            
            return {
                "success": True,
                "refund_id": refund["id"],
                "amount": refund["amount"],
                "status": refund["status"]
            }
            
        except Exception as e:
            logger.error(f"Erro ao reembolsar pagamento {payment_id}: {e}")
            return {"success": False, "error": str(e)}
    
    async def process_webhook(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Processar webhook do Mercado Pago
        
        Args:
            data: Dados recebidos do webhook
            
        Returns:
            Dict com resultado do processamento
        """
        try:
            # Validar tipo de notificação
            if data.get("type") == "payment":
                payment_id = data.get("data", {}).get("id")
                
                if payment_id:
                    # Verificar status do pagamento
                    payment_status = await self.check_payment_status(payment_id)
                    
                    if payment_status["success"]:
                        logger.info(f"Webhook processado - Pagamento {payment_id}: {payment_status['status']}")
                        return {
                            "success": True,
                            "payment_id": payment_id,
                            "status": payment_status["status"],
                            "processed": True
                        }
            
            return {"success": True, "processed": False, "message": "Notificação não processada"}
            
        except Exception as e:
            logger.error(f"Erro ao processar webhook: {e}")
            return {"success": False, "error": str(e)}

# Instância global
mercadopago_service = MercadoPagoService()
