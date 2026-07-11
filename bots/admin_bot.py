# bots/admin_bot.py
from telegram import (
    Update, InlineKeyboardButton, InlineKeyboardMarkup,
    ReplyKeyboardMarkup, KeyboardButton
)
from telegram.ext import (
    Application, CommandHandler, MessageHandler, CallbackQueryHandler,
    ConversationHandler, filters, ContextTypes
)
from telegram.constants import ParseMode
from datetime import datetime, timedelta
from typing import Optional, Dict, Any, List
from loguru import logger
import pandas as pd
from io import BytesIO
import json

from core.config.settings import settings
from core.database.connection import get_db_context, init_db
from core.database.models import (
    User, Product, Category, Plan, Order, OrderItem,
    OrderStatus, Payment, Form, FormField, FormResponse,
    Button, Menu, SystemLog, Notification, AdminUser,
    AIConfig
)
from modules.payments.mercadopago import mercadopago_service
from modules.ai.openai_service import openai_service
from utils.helpers import format_currency, format_date, generate_pdf_report

# Estados da conversa
(
    ADMIN_MENU, USER_MANAGEMENT, PRODUCT_MANAGEMENT,
    PLAN_MANAGEMENT, FORM_MANAGEMENT, BUTTON_MANAGEMENT,
    REPORT_GENERATION, SETTINGS, BROADCAST
) = range(9)

class AdminBot:
    """
    Bot administrador para gerenciamento do sistema
    """
    
    def __init__(self):
        """Inicializar bot admin"""
        self.application = None
        logger.info("AdminBot inicializado")
    
    async def start(self):
        """Iniciar bot admin"""
        logger.info("Iniciando AdminBot...")
        
        # Inicializar banco de dados
        init_db()
        
        # Criar application
        self.application = Application.builder().token(settings.ADMIN_BOT_TOKEN).build()
        
        # Adicionar handlers
        self.setup_handlers()
        
        # Iniciar polling
        await self.application.initialize()
        await self.application.start()
        await self.application.updater.start_polling()
        
        logger.info("AdminBot iniciado com sucesso!")
    
    def setup_handlers(self):
        """Configurar handlers do bot admin"""
        
        # Comandos básicos
        self.application.add_handler(CommandHandler("start", self.cmd_start))
        self.application.add_handler(CommandHandler("admin", self.cmd_admin))
        self.application.add_handler(CommandHandler("dashboard", self.cmd_dashboard))
        self.application.add_handler(CommandHandler("users", self.cmd_users))
        self.application.add_handler(CommandHandler("products", self.cmd_products))
        self.application.add_handler(CommandHandler("plans", self.cmd_plans))
        self.application.add_handler(CommandHandler("orders", self.cmd_orders))
        self.application.add_handler(CommandHandler("reports", self.cmd_reports))
        self.application.add_handler(CommandHandler("broadcast", self.cmd_broadcast))
        
        # Callback queries
        self.application.add_handler(CallbackQueryHandler(
            self.handle_admin_callback, pattern="^admin_"
        ))
        self.application.add_handler(CallbackQueryHandler(
            self.handle_user_callback, pattern="^user_"
        ))
        self.application.add_handler(CallbackQueryHandler(
            self.handle_product_callback, pattern="^prod_"
        ))
        self.application.add_handler(CallbackQueryHandler(
            self.handle_plan_callback, pattern="^plan_"
        ))
        self.application.add_handler(CallbackQueryHandler(
            self.handle_form_callback, pattern="^form_"
        ))
        
        # Erro handler
        self.application.add_error_handler(self.error_handler)
    
    async def is_admin(self, user_id: int) -> bool:
        """
        Verificar se usuário é administrador
        
        Args:
            user_id: ID do Telegram
            
        Returns:
            True se for admin
        """
        try:
            with get_db_context() as db:
                admin = db.query(AdminUser).filter(
                    AdminUser.telegram_id == user_id,
                    AdminUser.is_active == True
                ).first()
                
                return admin is not None
                
        except Exception as e:
            logger.error(f"Erro ao verificar admin: {e}")
            return False
    
    async def cmd_start(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Comando start do admin"""
        user = update.effective_user
        
        # Verificar se é admin
        if not await self.is_admin(user.id):
            await update.message.reply_text(
                "⛔ Acesso negado. Você não tem permissão de administrador."
            )
            return
        
        await self.show_dashboard(update, context)
    
    async def cmd_admin(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Painel administrativo"""
        user = update.effective_user
        
        if not await self.is_admin(user.id):
            await update.message.reply_text("⛔ Acesso negado.")
            return
        
        await self.show_admin_menu(update, context)
    
    async def cmd_dashboard(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Dashboard administrativo"""
        user = update.effective_user
        
        if not await self.is_admin(user.id):
            await update.message.reply_text("⛔ Acesso negado.")
            return
        
        await self.show_dashboard(update, context)
    
    async def show_dashboard(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Mostrar dashboard"""
        try:
            with get_db_context() as db:
                # Estatísticas gerais
                total_users = db.query(User).count()
                active_users = db.query(User).filter(User.status == UserStatus.ACTIVE).count()
                new_today = db.query(User).filter(
                    User.created_at >= datetime.utcnow().date()
                ).count()
                
                total_products = db.query(Product).filter(Product.is_active == True).count()
                total_plans = db.query(Plan).filter(Plan.is_active == True).count()
                
                # Receita
                today = datetime.utcnow().date()
                
                today_revenue = db.query(Payment).filter(
                    Payment.status == "approved",
                    Payment.approved_at >= today
                ).with_entities(func.sum(Payment.amount)).scalar() or 0
                
                week_ago = today - timedelta(days=7)
                week_revenue = db.query(Payment).filter(
                    Payment.status == "approved",
                    Payment.approved_at >= week_ago
                ).with_entities(func.sum(Payment.amount)).scalar() or 0
                
                month_revenue = db.query(Payment).filter(
                    Payment.status == "approved",
                    func.extract('month', Payment.approved_at) == today.month,
                    func.extract('year', Payment.approved_at) == today.year
                ).with_entities(func.sum(Payment.amount)).scalar() or 0
                
                # Pedidos
                pending_orders = db.query(Order).filter(
                    Order.status == OrderStatus.PENDING
                ).count()
                
                paid_orders = db.query(Order).filter(
                    Order.status == OrderStatus.PAID
                ).count()
                
                # Mensagem do dashboard
                message = (
                    f"📊 *DASHBOARD ADMINISTRATIVO*\n\n"
                    f"👥 *Usuários*\n"
                    f"• Total: {total_users}\n"
                    f"• Ativos: {active_users}\n"
                    f"• Novos hoje: {new_today}\n\n"
                    f"📦 *Catálogo*\n"
                    f"• Produtos: {total_products}\n"
                    f"• Planos: {total_plans}\n\n"
                    f"💰 *Financeiro*\n"
                    f"• Receita hoje: R$ {today_revenue:.2f}\n"
                    f"• Receita 7 dias: R$ {week_revenue:.2f}\n"
                    f"• Receita mês: R$ {month_revenue:.2f}\n\n"
                    f"🛒 *Pedidos*\n"
                    f"• Pendentes: {pending_orders}\n"
                    f"• Concluídos: {paid_orders}\n\n"
                    f"🕐 Atualizado: {datetime.now().strftime('%d/%m/%Y %H:%M')}"
                )
                
                # Teclado admin
                keyboard = [
                    [InlineKeyboardButton("👥 Usuários", callback_data="admin_users")],
                    [InlineKeyboardButton("📦 Produtos", callback_data="admin_products"),
                     InlineKeyboardButton("💎 Planos", callback_data="admin_plans")],
                    [InlineKeyboardButton("🛒 Pedidos", callback_data="admin_orders")],
                    [InlineKeyboardButton("📝 Formulários", callback_data="admin_forms")],
                    [InlineKeyboardButton("🔘 Menus/Botões", callback_data="admin_buttons")],
                    [InlineKeyboardButton("📊 Relatórios", callback_data="admin_reports")],
                    [InlineKeyboardButton("⚙️ Configurações", callback_data="admin_settings")],
                    [InlineKeyboardButton("📢 Broadcast", callback_data="admin_broadcast")],
                    [InlineKeyboardButton("🤖 IA Config", callback_data="admin_ai")]
                ]
                
                await update.message.reply_text(
                    message,
                    reply_markup=InlineKeyboardMarkup(keyboard),
                    parse_mode=ParseMode.MARKDOWN
                )
                
        except Exception as e:
            logger.error(f"Erro ao mostrar dashboard: {e}")
            await update.message.reply_text("❌ Erro ao carregar dashboard.")
    
    async def show_admin_menu(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Mostrar menu administrativo"""
        keyboard = [
            [InlineKeyboardButton("📊 Dashboard", callback_data="admin_dashboard")],
            [InlineKeyboardButton("👥 Gestão de Usuários", callback_data="admin_users")],
            [InlineKeyboardButton("📦 Gestão de Produtos", callback_data="admin_products")],
            [InlineKeyboardButton("💎 Gestão de Planos", callback_data="admin_plans")],
            [InlineKeyboardButton("🛒 Gestão de Pedidos", callback_data="admin_orders")],
            [InlineKeyboardButton("📝 Gestão de Formulários", callback_data="admin_forms")],
            [InlineKeyboardButton("🔘 Gestão de Menus", callback_data="admin_buttons")],
            [InlineKeyboardButton("📊 Relatórios", callback_data="admin_reports")],
            [InlineKeyboardButton("📢 Broadcast", callback_data="admin_broadcast")],
            [InlineKeyboardButton("⚙️ Configurações", callback_data="admin_settings")]
        ]
        
        await update.message.reply_text(
            "⚙️ *Painel Administrativo*\n\nSelecione uma opção:",
            reply_markup=InlineKeyboardMarkup(keyboard),
            parse_mode=ParseMode.MARKDOWN
        )
    
    async def handle_admin_callback(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Processar callbacks do admin"""
        query = update.callback_query
        await query.answer()
        
        action = query.data.replace("admin_", "")
        
        if action == "dashboard":
            await self.show_dashboard(update, context)
        
        elif action == "users":
            await self.show_user_management(update, context)
        
        elif action == "products":
            await self.show_product_management(update, context)
        
        elif action == "plans":
            await self.show_plan_management(update, context)
        
        elif action == "orders":
            await self.show_order_management(update, context)
        
        elif action == "forms":
            await self.show_form_management(update, context)
        
        elif action == "buttons":
            await self.show_button_management(update, context)
        
        elif action == "reports":
            await self.show_report_menu(update, context)
        
        elif action == "broadcast":
            await self.start_broadcast(update, context)
        
        elif action == "settings":
            await self.show_settings(update, context)
        
        elif action == "ai":
            await self.show_ai_config(update, context)
    
    async def show_user_management(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Gestão de usuários"""
        try:
            with get_db_context() as db:
                # Buscar últimos 10 usuários
                users = db.query(User).order_by(User.created_at.desc()).limit(10).all()
                
                message = "👥 *Gestão de Usuários*\n\n"
                message += f"Total de usuários: {db.query(User).count()}\n\n"
                message += "*Últimos cadastros:*\n"
                
                for user in users:
                    message += f"• {user.first_name} (@{user.username})\n"
                    message += f"  ID: {user.telegram_id} | Status: {user.status.value}\n\n"
                
                keyboard = [
                    [InlineKeyboardButton("🔍 Buscar Usuário", callback_data="user_search")],
                    [InlineKeyboardButton("📊 Exportar Lista", callback_data="user_export")],
                    [InlineKeyboardButton("📢 Enviar Broadcast", callback_data="admin_broadcast")],
                    [InlineKeyboardButton("🔙 Voltar", callback_data="admin_dashboard")]
                ]
                
                await query.edit_message_text(
                    message,
                    reply_markup=InlineKeyboardMarkup(keyboard),
                    parse_mode=ParseMode.MARKDOWN
                )
                
        except Exception as e:
            logger.error(f"Erro na gestão de usuários: {e}")
    
    async def show_product_management(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Gestão de produtos"""
        try:
            with get_db_context() as db:
                products = db.query(Product).order_by(Product.display_order).all()
                
                message = "📦 *Gestão de Produtos*\n\n"
                message += f"Total: {len(products)} produtos\n\n"
                
                for product in products[:20]:
                    status = "✅" if product.is_active else "❌"
                    message += f"{status} {product.name} - R$ {product.price:.2f}\n"
                
                keyboard = [
                    [InlineKeyboardButton("➕ Adicionar Produto", callback_data="prod_add")],
                    [InlineKeyboardButton("📋 Listar Todos", callback_data="prod_list")],
                    [InlineKeyboardButton("🔙 Voltar", callback_data="admin_dashboard")]
                ]
                
                await query.edit_message_text(
                    message,
                    reply_markup=InlineKeyboardMarkup(keyboard),
                    parse_mode=ParseMode.MARKDOWN
                )
                
        except Exception as e:
            logger.error(f"Erro na gestão de produtos: {e}")
    
    async def show_order_management(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Gestão de pedidos"""
        try:
            with get_db_context() as db:
                orders = db.query(Order).order_by(Order.created_at.desc()).limit(10).all()
                
                message = "🛒 *Gestão de Pedidos*\n\n"
                message += f"Total: {db.query(Order).count()} pedidos\n\n"
                
                for order in orders:
                    user = order.user
                    message += f"*Pedido #{order.id}*\n"
                    message += f"Cliente: {user.first_name}\n"
                    message += f"Valor: R$ {order.final_amount:.2f}\n"
                    message += f"Status: {order.status.value}\n"
                    message += f"Data: {order.created_at.strftime('%d/%m/%Y')}\n\n"
                
                keyboard = [
                    [InlineKeyboardButton("🔍 Buscar Pedido", callback_data="order_search")],
                    [InlineKeyboardButton("💰 Reembolsos", callback_data="order_refunds")],
                    [InlineKeyboardButton("🔙 Voltar", callback_data="admin_dashboard")]
                ]
                
                await query.edit_message_text(
                    message,
                    reply_markup=InlineKeyboardMarkup(keyboard),
                    parse_mode=ParseMode.MARKDOWN
                )
                
        except Exception as e:
            logger.error(f"Erro na gestão de pedidos: {e}")
    
    async def show_report_menu(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Menu de relatórios"""
        query = update.callback_query
        
        keyboard = [
            [InlineKeyboardButton("📊 Relatório de Vendas", callback_data="report_sales")],
            [InlineKeyboardButton("👥 Relatório de Usuários", callback_data="report_users")],
            [InlineKeyboardButton("📦 Relatório de Produtos", callback_data="report_products")],
            [InlineKeyboardButton("💰 Relatório Financeiro", callback_data="report_financial")],
            [InlineKeyboardButton("📝 Respostas Formulários", callback_data="report_forms")],
            [InlineKeyboardButton("🔙 Voltar", callback_data="admin_dashboard")]
        ]
        
        await query.edit_message_text(
            "📊 *Relatórios*\n\nSelecione o tipo de relatório:",
            reply_markup=InlineKeyboardMarkup(keyboard),
            parse_mode=ParseMode.MARKDOWN
        )
    
    async def cmd_reports(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Gerar relatórios"""
        if not await self.is_admin(update.effective_user.id):
            return
        
        await self.show_report_menu(update, context)
    
    async def cmd_broadcast(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Enviar mensagem em massa"""
        if not await self.is_admin(update.effective_user.id):
            return
        
        context.user_data['awaiting_broadcast'] = True
        
        await update.message.reply_text(
            "📢 *Broadcast*\n\n"
            "Digite a mensagem que deseja enviar para todos os usuários.\n\n"
            "*Formato suportado:* Markdown\n"
            "*Cancelar:* /cancel",
            parse_mode=ParseMode.MARKDOWN
        )
    
    async def error_handler(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Tratamento de erros"""
        logger.error(f"Erro no bot admin: {context.error}")
        
        try:
            if update and update.effective_message:
                await update.effective_message.reply_text(
                    "❌ Erro administrativo. Verifique os logs."
                )
        except:
            pass

# Instância global
admin_bot = AdminBot()
