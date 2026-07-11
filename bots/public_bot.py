# bots/public_bot.py
from telegram import (
    Update, InlineKeyboardButton, InlineKeyboardMarkup,
    ReplyKeyboardMarkup, KeyboardButton, WebAppInfo
)
from telegram.ext import (
    Application, CommandHandler, MessageHandler, CallbackQueryHandler,
    ConversationHandler, filters, ContextTypes
)
from telegram.constants import ParseMode
from datetime import datetime
from typing import Optional, Dict, Any
from loguru import logger
import asyncio

from core.config.settings import settings
from core.database.connection import get_db_context, init_db
from core.database.models import (
    User, Product, Category, Plan, Order, OrderItem,
    OrderStatus, Payment, Form, FormField, FormResponse,
    Button, Menu, SystemLog, Notification, UserStatus
)
from modules.payments.mercadopago import mercadopago_service
from modules.ai.openai_service import openai_service

# Estados da conversa
(
    MAIN_MENU, CATALOG, PRODUCT_DETAIL, CART, CHECKOUT,
    PAYMENT, FORM_FILLING, PROFILE, SUPPORT_CHAT
) = range(9)

class PublicBot:
    """
    Bot público para interação com clientes
    """
    
    def __init__(self):
        """Inicializar bot público"""
        self.application = None
        logger.info("PublicBot inicializado")
    
    async def start(self):
        """Iniciar bot"""
        logger.info("Iniciando PublicBot...")
        
        # Inicializar banco de dados
        init_db()
        
        # Criar application
        self.application = Application.builder().token(settings.PUBLIC_BOT_TOKEN).build()
        
        # Adicionar handlers
        self.setup_handlers()
        
        # Iniciar polling
        await self.application.initialize()
        await self.application.start()
        await self.application.updater.start_polling()
        
        logger.info("PublicBot iniciado com sucesso!")
    
    def setup_handlers(self):
        """Configurar handlers do bot"""
        
        # Comandos básicos
        self.application.add_handler(CommandHandler("start", self.cmd_start))
        self.application.add_handler(CommandHandler("menu", self.cmd_menu))
        self.application.add_handler(CommandHandler("help", self.cmd_help))
        self.application.add_handler(CommandHandler("catalog", self.cmd_catalog))
        self.application.add_handler(CommandHandler("cart", self.cmd_cart))
        self.application.add_handler(CommandHandler("profile", self.cmd_profile))
        self.application.add_handler(CommandHandler("support", self.cmd_support))
        
        # Conversation handler para compras
        conv_handler = ConversationHandler(
            entry_points=[
                CommandHandler("buy", self.cmd_buy),
                CallbackQueryHandler(self.handle_buy_callback, pattern="^buy_")
            ],
            states={
                CATALOG: [
                    CallbackQueryHandler(self.show_catalog),
                    CallbackQueryHandler(self.show_product, pattern="^product_")
                ],
                PRODUCT_DETAIL: [
                    CallbackQueryHandler(self.add_to_cart, pattern="^add_cart_"),
                    CallbackQueryHandler(self.show_catalog, pattern="^back_catalog")
                ],
                CART: [
                    CallbackQueryHandler(self.view_cart, pattern="^view_cart"),
                    CallbackQueryHandler(self.checkout, pattern="^checkout"),
                    CallbackQueryHandler(self.remove_from_cart, pattern="^remove_")
                ],
                CHECKOUT: [
                    CallbackQueryHandler(self.process_payment, pattern="^pay_")
                ],
                PAYMENT: [
                    CallbackQueryHandler(self.check_payment_status, pattern="^check_payment_")
                ]
            },
            fallbacks=[
                CommandHandler("cancel", self.cmd_cancel),
                CommandHandler("menu", self.cmd_menu)
            ]
        )
        
        self.application.add_handler(conv_handler)
        
        # Callback queries gerais
        self.application.add_handler(CallbackQueryHandler(
            self.handle_menu_callback, pattern="^menu_"
        ))
        self.application.add_handler(CallbackQueryHandler(
            self.handle_general_callback, pattern="^action_"
        ))
        
        # Mensagens de texto para suporte
        self.application.add_handler(MessageHandler(
            filters.TEXT & ~filters.COMMAND, self.handle_message
        ))
        
        # Erro handler
        self.application.add_error_handler(self.error_handler)
    
    async def cmd_start(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Comando /start"""
        user = update.effective_user
        
        try:
            # Registrar usuário
            with get_db_context() as db:
                # Verificar se usuário já existe
                db_user = db.query(User).filter(
                    User.telegram_id == user.id
                ).first()
                
                if not db_user:
                    # Criar novo usuário
                    db_user = User(
                        telegram_id=user.id,
                        username=user.username,
                        first_name=user.first_name,
                        last_name=user.last_name,
                        language=user.language_code or "pt",
                        source="telegram_bot",
                        last_access=datetime.utcnow()
                    )
                    db.add(db_user)
                    logger.info(f"Novo usuário registrado: {user.id} - @{user.username}")
                    
                    # Log
                    log = SystemLog(
                        user_id=db_user.id,
                        action="user_register",
                        details={"telegram_id": user.id, "username": user.username},
                        status="success"
                    )
                    db.add(log)
                else:
                    # Atualizar último acesso
                    db_user.last_access = datetime.utcnow()
                    if db_user.username != user.username:
                        db_user.username = user.username
                    
                    logger.info(f"Usuário existente: {user.id}")
            
            # Mensagem de boas-vindas
            welcome_message = (
                f"👋 *Bem-vindo(a) ao Marketing Xixa!*\n\n"
                f"Olá {user.first_name}, somos uma plataforma completa "
                f"de marketing digital e automação.\n\n"
                f"*O que você deseja fazer?*\n"
                f"📦 Ver nosso catálogo\n"
                f"💰 Conferir planos\n"
                f"🛒 Fazer um pedido\n"
                f"❓ Tirar dúvidas\n"
                f"👤 Acessar seu perfil"
            )
            
            # Criar menu principal
            keyboard = await self.get_main_menu(is_admin=False)
            
            await update.message.reply_text(
                welcome_message,
                reply_markup=keyboard,
                parse_mode=ParseMode.MARKDOWN
            )
            
        except Exception as e:
            logger.error(f"Erro no comando start: {e}")
            await update.message.reply_text(
                "❌ Ocorreu um erro ao iniciar. Por favor, tente novamente."
            )
    
    async def cmd_menu(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Mostrar menu principal"""
        try:
            keyboard = await self.get_main_menu(is_admin=False)
            
            await update.message.reply_text(
                "📋 *Menu Principal*\n\nSelecione uma opção:",
                reply_markup=keyboard,
                parse_mode=ParseMode.MARKDOWN
            )
            
        except Exception as e:
            logger.error(f"Erro ao mostrar menu: {e}")
    
    async def get_main_menu(self, is_admin: bool = False) -> InlineKeyboardMarkup:
        """
        Obter menu principal do banco de dados
        
        Args:
            is_admin: Se é menu admin
            
        Returns:
            InlineKeyboardMarkup
        """
        try:
            with get_db_context() as db:
                # Buscar menu principal
                menu = db.query(Menu).filter(
                    Menu.is_main == True,
                    Menu.is_active == True
                ).first()
                
                if menu and menu.buttons:
                    keyboard = []
                    buttons = db.query(Button).filter(
                        Button.id.in_(menu.buttons),
                        Button.is_active == True
                    ).order_by(Button.order).all()
                    
                    for button in buttons:
                        if button.for_admin and not is_admin:
                            continue
                        
                        text = button.text
                        if button.emoji:
                            text = f"{button.emoji} {text}"
                        
                        if button.url:
                            keyboard.append([
                                InlineKeyboardButton(text, url=button.url)
                            ])
                        elif button.callback_data:
                            keyboard.append([
                                InlineKeyboardButton(
                                    text,
                                    callback_data=button.callback_data
                                )
                            ])
                    
                    return InlineKeyboardMarkup(keyboard)
            
            # Menu padrão se não encontrar no banco
            keyboard = [
                [InlineKeyboardButton("📦 Catálogo", callback_data="menu_catalog")],
                [InlineKeyboardButton("💎 Planos", callback_data="menu_plans")],
                [InlineKeyboardButton("🛒 Meu Carrinho", callback_data="menu_cart")],
                [InlineKeyboardButton("👤 Meu Perfil", callback_data="menu_profile")],
                [InlineKeyboardButton("❓ Suporte", callback_data="menu_support")],
            ]
            
            return InlineKeyboardMarkup(keyboard)
            
        except Exception as e:
            logger.error(f"Erro ao obter menu: {e}")
            return InlineKeyboardMarkup([
                [InlineKeyboardButton("📋 Menu", callback_data="menu_main")]
            ])
    
    async def cmd_catalog(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Mostrar catálogo de produtos"""
        try:
            await self.show_catalog(update, context)
            
        except Exception as e:
            logger.error(f"Erro ao mostrar catálogo: {e}")
    
    async def show_catalog(self, update_or_query, context: ContextTypes.DEFAULT_TYPE):
        """Mostrar catálogo com categorias"""
        try:
            with get_db_context() as db:
                # Buscar categorias ativas
                categories = db.query(Category).filter(
                    Category.is_active == True
                ).order_by(Category.order).all()
                
                if categories:
                    keyboard = []
                    
                    for category in categories:
                        emoji = "📁"
                        if "premium" in category.name.lower():
                            emoji = "⭐"
                        elif "básico" in category.name.lower():
                            emoji = "📦"
                        
                        keyboard.append([
                            InlineKeyboardButton(
                                f"{emoji} {category.name}",
                                callback_data=f"category_{category.id}"
                            )
                        ])
                    
                    keyboard.append([
                        InlineKeyboardButton("🔙 Voltar", callback_data="menu_main")
                    ])
                    
                    message = "📦 *Catálogo de Produtos*\n\nSelecione uma categoria:"
                    
                else:
                    # Buscar produtos diretamente
                    products = db.query(Product).filter(
                        Product.is_active == True
                    ).order_by(Product.display_order).all()
                    
                    if products:
                        keyboard = []
                        
                        for product in products[:10]:  # Limitar a 10 produtos
                            price = product.promotional_price or product.price
                            keyboard.append([
                                InlineKeyboardButton(
                                    f"{product.name} - R$ {price:.2f}",
                                    callback_data=f"product_{product.id}"
                                )
                            ])
                        
                        keyboard.append([
                            InlineKeyboardButton("🔙 Voltar", callback_data="menu_main")
                        ])
                        
                        message = "📦 *Nossos Produtos*\n\nSelecione um produto:"
                    else:
                        keyboard = [[
                            InlineKeyboardButton("🔙 Voltar", callback_data="menu_main")
                        ]]
                        message = "📦 *Catálogo*\n\nNenhum produto disponível no momento."
                
                # Enviar mensagem
                if hasattr(update_or_query, 'message'):
                    await update_or_query.message.reply_text(
                        message,
                        reply_markup=InlineKeyboardMarkup(keyboard),
                        parse_mode=ParseMode.MARKDOWN
                    )
                else:
                    await update_or_query.edit_message_text(
                        message,
                        reply_markup=InlineKeyboardMarkup(keyboard),
                        parse_mode=ParseMode.MARKDOWN
                    )
                    
        except Exception as e:
            logger.error(f"Erro ao mostrar catálogo: {e}")
    
    async def show_product(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Mostrar detalhes do produto"""
        query = update.callback_query
        await query.answer()
        
        try:
            product_id = int(query.data.split("_")[1])
            
            with get_db_context() as db:
                product = db.query(Product).filter(Product.id == product_id).first()
                
                if product and product.is_active:
                    # Construir mensagem
                    price = product.promotional_price or product.price
                    original_price = product.price if product.promotional_price else None
                    
                    message = f"*{product.name}*\n\n"
                    message += f"{product.description}\n\n" if product.description else ""
                    
                    if product.benefits:
                        message += "*Benefícios:*\n"
                        for benefit in product.benefits:
                            message += f"✅ {benefit}\n"
                        message += "\n"
                    
                    if original_price:
                        message += f"💰 De: ~~R$ {original_price:.2f}~~\n"
                        message += f"🔥 Por: R$ {price:.2f}\n\n"
                    else:
                        message += f"💰 Preço: R$ {price:.2f}\n\n"
                    
                    if product.stock > 0:
                        message += f"📦 Estoque: {product.stock} unidades\n\n"
                    
                    # Botões
                    keyboard = [
                        [InlineKeyboardButton(
                            "🛒 Adicionar ao Carrinho",
                            callback_data=f"add_cart_{product.id}"
                        )],
                        [InlineKeyboardButton(
                            "🔙 Voltar ao Catálogo",
                            callback_data="back_catalog"
                        )]
                    ]
                    
                    # Enviar imagem se existir
                    if product.images:
                        try:
                            await query.message.reply_photo(
                                product.images[0],
                                caption=message,
                                reply_markup=InlineKeyboardMarkup(keyboard),
                                parse_mode=ParseMode.MARKDOWN
                            )
                            await query.message.delete()
                            return
                        except:
                            pass
                    
                    await query.edit_message_text(
                        message,
                        reply_markup=InlineKeyboardMarkup(keyboard),
                        parse_mode=ParseMode.MARKDOWN
                    )
                    
                else:
                    await query.edit_message_text(
                        "❌ Produto não encontrado ou indisponível.",
                        reply_markup=InlineKeyboardMarkup([[
                            InlineKeyboardButton("🔙 Voltar", callback_data="menu_catalog")
                        ]])
                    )
                    
        except Exception as e:
            logger.error(f"Erro ao mostrar produto: {e}")
    
    async def add_to_cart(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Adicionar produto ao carrinho"""
        query = update.callback_query
        await query.answer()
        
        try:
            product_id = int(query.data.split("_")[2])
            user_id = update.effective_user.id
            
            with get_db_context() as db:
                # Verificar produto
                product = db.query(Product).filter(
                    Product.id == product_id,
                    Product.is_active == True
                ).first()
                
                if not product:
                    await query.answer("❌ Produto indisponível!")
                    return
                
                # Inicializar carrinho se não existir
                if 'cart' not in context.user_data:
                    context.user_data['cart'] = []
                
                # Verificar se já está no carrinho
                for item in context.user_data['cart']:
                    if item['product_id'] == product_id:
                        await query.answer("✅ Produto já está no carrinho!")
                        return
                
                # Adicionar ao carrinho
                price = product.promotional_price or product.price
                context.user_data['cart'].append({
                    'product_id': product_id,
                    'name': product.name,
                    'price': price,
                    'quantity': 1
                })
                
                # Log
                db_user = db.query(User).filter(User.telegram_id == user_id).first()
                if db_user:
                    log = SystemLog(
                        user_id=db_user.id,
                        action="add_to_cart",
                        details={"product_id": product_id, "product_name": product.name},
                        status="success"
                    )
                    db.add(log)
                
                await query.answer("✅ Produto adicionado ao carrinho!")
                
                # Mostrar carrinho
                await self.view_cart(update, context)
                
        except Exception as e:
            logger.error(f"Erro ao adicionar ao carrinho: {e}")
            await query.answer("❌ Erro ao adicionar produto!")
    
    async def view_cart(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Visualizar carrinho"""
        query = update.callback_query if hasattr(update, 'callback_query') else None
        
        try:
            cart = context.user_data.get('cart', [])
            
            if not cart:
                message = "🛒 *Seu Carrinho*\n\nSeu carrinho está vazio."
                keyboard = [[
                    InlineKeyboardButton("📦 Ver Catálogo", callback_data="menu_catalog")
                ]]
            else:
                total = sum(item['price'] * item['quantity'] for item in cart)
                
                message = "🛒 *Seu Carrinho*\n\n"
                for i, item in enumerate(cart, 1):
                    subtotal = item['price'] * item['quantity']
                    message += f"{i}. {item['name']}\n"
                    message += f"   R$ {item['price']:.2f} x {item['quantity']} = R$ {subtotal:.2f}\n\n"
                
                message += f"*Total: R$ {total:.2f}*"
                
                keyboard = [
                    [InlineKeyboardButton(
                        "💳 Finalizar Compra",
                        callback_data="checkout"
                    )],
                    [InlineKeyboardButton(
                        "📦 Continuar Comprando",
                        callback_data="menu_catalog"
                    )],
                    [InlineKeyboardButton(
                        "🗑️ Limpar Carrinho",
                        callback_data="clear_cart"
                    )]
                ]
            
            if query:
                await query.edit_message_text(
                    message,
                    reply_markup=InlineKeyboardMarkup(keyboard),
                    parse_mode=ParseMode.MARKDOWN
                )
            else:
                await update.message.reply_text(
                    message,
                    reply_markup=InlineKeyboardMarkup(keyboard),
                    parse_mode=ParseMode.MARKDOWN
                )
                
        except Exception as e:
            logger.error(f"Erro ao ver carrinho: {e}")
    
    async def checkout(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Processar checkout"""
        query = update.callback_query
        await query.answer()
        
        try:
            cart = context.user_data.get('cart', [])
            
            if not cart:
                await query.answer("❌ Carrinho vazio!")
                return
            
            total = sum(item['price'] * item['quantity'] for item in cart)
            
            # Criar pedido no banco
            with get_db_context() as db:
                user = db.query(User).filter(
                    User.telegram_id == update.effective_user.id
                ).first()
                
                if not user:
                    await query.answer("❌ Erro: Usuário não encontrado!")
                    return
                
                # Criar pedido
                order = Order(
                    user_id=user.id,
                    total_amount=total,
                    final_amount=total,
                    expires_at=datetime.utcnow() + timedelta(minutes=30)
                )
                db.add(order)
                db.flush()
                
                # Adicionar itens
                for item in cart:
                    order_item = OrderItem(
                        order_id=order.id,
                        product_id=item['product_id'],
                        quantity=item['quantity'],
                        unit_price=item['price'],
                        total_price=item['price'] * item['quantity']
                    )
                    db.add(order_item)
                
                # Guardar order_id no contexto
                context.user_data['current_order_id'] = order.id
                
                message = f"💳 *Resumo do Pedido #{order.id}*\n\n"
                for item in cart:
                    message += f"✅ {item['name']} - R$ {item['price']:.2f}\n"
                
                message += f"\n*Total: R$ {total:.2f}*\n\n"
                message += "Escolha a forma de pagamento:"
                
                keyboard = [
                    [InlineKeyboardButton(
                        "📱 PIX",
                        callback_data=f"pay_pix_{order.id}"
                    )],
                    [InlineKeyboardButton(
                        "🔙 Voltar ao Carrinho",
                        callback_data="view_cart"
                    )]
                ]
                
                await query.edit_message_text(
                    message,
                    reply_markup=InlineKeyboardMarkup(keyboard),
                    parse_mode=ParseMode.MARKDOWN
                )
                
        except Exception as e:
            logger.error(f"Erro no checkout: {e}")
            await query.answer("❌ Erro ao processar checkout!")
    
    async def process_payment(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Processar pagamento PIX"""
        query = update.callback_query
        await query.answer()
        
        try:
            order_id = int(query.data.split("_")[2])
            
            with get_db_context() as db:
                order = db.query(Order).filter(Order.id == order_id).first()
                user = db.query(User).filter(User.id == order.user_id).first()
                
                if not order or not user:
                    await query.answer("❌ Pedido não encontrado!")
                    return
                
                # Criar pagamento PIX
                payment_result = await mercadopago_service.create_pix_payment(
                    amount=order.final_amount,
                    description=f"Pedido #{order.id} - Marketing Xixa",
                    payer_email=user.email or f"{user.telegram_id}@telegram.com"
                )
                
                if payment_result["success"]:
                    # Salvar pagamento no banco
                    payment = Payment(
                        order_id=order.id,
                        user_id=user.id,
                        amount=order.final_amount,
                        method="pix",
                        status="pending",
                        external_id=payment_result["payment_id"],
                        pix_qr_code=payment_result["qr_code_base64"],
                        pix_copy_paste=payment_result["copy_paste"],
                        pix_expiration=payment_result["expiration_date"]
                    )
                    db.add(payment)
                    
                    # Enviar QR Code
                    message = f"📱 *Pagamento PIX*\n\n"
                    message += f"Pedido: #{order.id}\n"
                    message += f"Valor: R$ {order.final_amount:.2f}\n\n"
                    message += f"*PIX Copia e Cola:*\n"
                    message += f"`{payment_result['copy_paste']}`\n\n"
                    message += f"⏰ Expira em: {payment_result['expiration_date'].strftime('%d/%m/%Y %H:%M')}"
                    
                    keyboard = [
                        [InlineKeyboardButton(
                            "🔄 Verificar Pagamento",
                            callback_data=f"check_payment_{payment.id}"
                        )],
                        [InlineKeyboardButton(
                            "🔙 Voltar",
                            callback_data="menu_main"
                        )]
                    ]
                    
                    # Enviar QR Code como imagem
                    try:
                        # Decodificar base64 e enviar como foto
                        import base64
                        qr_image = base64.b64decode(payment_result["qr_code_base64"])
                        
                        from io import BytesIO
                        await query.message.reply_photo(
                            BytesIO(qr_image),
                            caption=message,
                            reply_markup=InlineKeyboardMarkup(keyboard),
                            parse_mode=ParseMode.MARKDOWN
                        )
                        await query.message.delete()
                    except:
                        await query.edit_message_text(
                            message,
                            reply_markup=InlineKeyboardMarkup(keyboard),
                            parse_mode=ParseMode.MARKDOWN
                        )
                    
                else:
                    await query.answer("❌ Erro ao gerar pagamento PIX!")
                    
        except Exception as e:
            logger.error(f"Erro ao processar pagamento: {e}")
            await query.answer("❌ Erro ao processar pagamento!")
    
    async def check_payment_status(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Verificar status do pagamento"""
        query = update.callback_query
        await query.answer()
        
        try:
            payment_id = int(query.data.split("_")[2])
            
            with get_db_context() as db:
                payment = db.query(Payment).filter(Payment.id == payment_id).first()
                
                if not payment:
                    await query.answer("❌ Pagamento não encontrado!")
                    return
                
                # Verificar no Mercado Pago
                status = await mercadopago_service.check_payment_status(
                    payment.external_id
                )
                
                if status["success"]:
                    mp_status = status["status"]
                    
                    if mp_status == "approved":
                        # Atualizar pagamento
                        payment.status = "approved"
                        payment.approved_at = datetime.utcnow()
                        
                        # Atualizar pedido
                        order = payment.order
                        order.status = OrderStatus.PAID
                        order.paid_at = datetime.utcnow()
                        
                        # Adicionar saldo se necessário
                        # user = payment.user
                        # user.balance += order.final_amount
                        
                        message = "✅ *Pagamento Aprovado!*\n\n"
                        message += f"Pedido #{order.id} confirmado.\n"
                        message += "Obrigado pela compra! 🎉"
                        
                        # Limpar carrinho
                        if 'cart' in context.user_data:
                            del context.user_data['cart']
                        
                    elif mp_status == "pending":
                        message = "⏳ *Pagamento Pendente*\n\n"
                        message += "Aguardando confirmação do pagamento.\n"
                        message += "Clique novamente para verificar."
                        
                    elif mp_status in ["rejected", "cancelled"]:
                        payment.status = "cancelled"
                        order = payment.order
                        order.status = OrderStatus.CANCELLED
                        
                        message = "❌ *Pagamento Cancelado*\n\n"
                        message += "O pagamento foi cancelado ou rejeitado."
                        
                    else:
                        message = f"ℹ️ Status: {mp_status}"
                    
                    keyboard = [[
                        InlineKeyboardButton("🔙 Menu Principal", callback_data="menu_main")
                    ]]
                    
                    await query.edit_message_text(
                        message,
                        reply_markup=InlineKeyboardMarkup(keyboard),
                        parse_mode=ParseMode.MARKDOWN
                    )
                    
                else:
                    await query.answer("❌ Erro ao verificar pagamento!")
                    
        except Exception as e:
            logger.error(f"Erro ao verificar pagamento: {e}")
            await query.answer("❌ Erro ao verificar!")
    
    async def cmd_support(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Iniciar chat de suporte com IA"""
        try:
            # Limpar conversa anterior
            openai_service.clear_conversation(update.effective_user.id)
            
            message = (
                "💬 *Suporte Inteligente*\n\n"
                "Olá! Eu sou o assistente virtual da Marketing Xixa.\n"
                "Como posso ajudá-lo hoje?\n\n"
                "*Digite sua dúvida ou escolha uma opção:*"
            )
            
            keyboard = [
                [InlineKeyboardButton("📦 Produtos", callback_data="support_products")],
                [InlineKeyboardButton("💰 Preços", callback_data="support_prices")],
                [InlineKeyboardButton("📱 Pagamentos", callback_data="support_payment")],
                [InlineKeyboardButton("👤 Atendimento Humano", callback_data="support_human")],
                [InlineKeyboardButton("🔙 Voltar", callback_data="menu_main")]
            ]
            
            context.user_data['in_support'] = True
            
            await update.message.reply_text(
                message,
                reply_markup=InlineKeyboardMarkup(keyboard),
                parse_mode=ParseMode.MARKDOWN
            )
            
        except Exception as e:
            logger.error(f"Erro ao iniciar suporte: {e}")
    
    async def handle_message(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Processar mensagens de texto"""
        user_message = update.message.text
        user = update.effective_user
        
        try:
            # Verificar se está em modo suporte
            if context.user_data.get('in_support'):
                # Enviar para IA
                await update.message.chat.send_action("typing")
                
                response = await openai_service.chat(
                    user_id=user.id,
                    message=user_message,
                    username=user.first_name
                )
                
                if response["success"]:
                    message = response["response"]
                    
                    if response.get("needs_human"):
                        message += "\n\n*Nota:* Se precisar, podemos transferir para atendimento humano."
                    
                    await update.message.reply_text(
                        message,
                        parse_mode=ParseMode.MARKDOWN
                    )
                else:
                    await update.message.reply_text(
                        "Desculpe, não consegui processar sua mensagem. "
                        "Tente novamente ou digite /support para reiniciar."
                    )
            
        except Exception as e:
            logger.error(f"Erro ao processar mensagem: {e}")
    
    async def error_handler(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Tratamento de erros"""
        logger.error(f"Erro no bot público: {context.error}")
        
        try:
            if update and update.effective_message:
                await update.effective_message.reply_text(
                    "❌ Ocorreu um erro inesperado. Por favor, tente novamente."
                )
        except:
            pass

# Instância global
public_bot = PublicBot()
