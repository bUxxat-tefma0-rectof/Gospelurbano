import logging
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Application, CommandHandler, CallbackQueryHandler, ContextTypes
from config import PUBLIC_TOKEN

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    keyboard = [
        [InlineKeyboardButton("📦 Planos", callback_data="plans")],
        [InlineKeyboardButton("💬 Suporte IA", callback_data="support")],
        [InlineKeyboardButton("📝 Análise", callback_data="analysis")]
    ]
    await update.message.reply_text("👋 Bem-vindo ao Xixa Marketing!", reply_markup=InlineKeyboardMarkup(keyboard))

async def button_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    if query.data == "plans":
        await query.edit_message_text("Básico R$2\nPremium R$30\nUse /comprar basico")
    elif query.data == "support":
        await query.edit_message_text("Envie sua dúvida.")
    elif query.data == "analysis":
        await query.edit_message_text("Formulário em desenvolvimento.")

def main():
    app = Application.builder().token(PUBLIC_TOKEN).build()
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CallbackQueryHandler(button_handler))
    logger.info("✅ Bot Público iniciado!")
    app.run_polling(drop_pending_updates=True)

if __name__ == '__main__':
    main()
