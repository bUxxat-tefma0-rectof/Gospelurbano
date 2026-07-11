import os
import logging
from dotenv import load_dotenv
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Application, CommandHandler, CallbackQueryHandler, MessageHandler, ContextTypes, ConversationHandler, filters
import psycopg2
from psycopg2.extras import Json

load_dotenv()

TOKEN = os.getenv("BOT_PUBLIC_TOKEN")

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Estados do formulário
NAME, PHONE, DETAILS = range(3)

def save_user_data(user_id, username, data):
    try:
        conn = psycopg2.connect(os.getenv("DB_URL"))
        cur = conn.cursor()
        cur.execute("""
            INSERT INTO users (user_id, username, data) 
            VALUES (%s, %s, %s) 
            ON CONFLICT (user_id) DO UPDATE SET data = %s
        """, (user_id, username, Json(data), Json(data)))
        conn.commit()
        cur.close()
        conn.close()
        logger.info(f"Dados salvos para user {user_id}")
    except Exception as e:
        logger.error(f"Erro ao salvar dados: {e}")

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    keyboard = [
        [InlineKeyboardButton("📦 Ver Planos", callback_data="plans")],
        [InlineKeyboardButton("📝 Marcar Análise", callback_data="analysis")]
    ]
    await update.message.reply_text("👋 Bem-vindo ao Xixa Marketing Bot!", reply_markup=InlineKeyboardMarkup(keyboard))

async def button_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    if query.data == "plans":
        await query.edit_message_text("Básico R$2\nPremium R$30\n\nUse /comprar basico")
    elif query.data == "analysis":
        await query.edit_message_text("Vamos iniciar o formulário.\nQual é o seu nome?")
        return NAME

# Formulário
async def get_name(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data['name'] = update.message.text
    await update.message.reply_text("Qual é o seu telefone?")
    return PHONE

async def get_phone(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data['phone'] = update.message.text
    await update.message.reply_text("Descreva o que precisa na análise:")
    return DETAILS

async def get_details(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data['details'] = update.message.text
    user = update.effective_user
    save_user_data(user.id, user.username, context.user_data)
    await update.message.reply_text("✅ Formulário salvo com sucesso! O administrador foi notificado.")
    return ConversationHandler.END

def main():
    app = Application.builder().token(TOKEN).build()
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CallbackQueryHandler(button_handler))

    conv_handler = ConversationHandler(
        entry_points=[CallbackQueryHandler(button_handler, pattern="^analysis$")],
        states={
            NAME: [MessageHandler(filters.TEXT & ~filters.COMMAND, get_name)],
            PHONE: [MessageHandler(filters.TEXT & ~filters.COMMAND, get_phone)],
            DETAILS: [MessageHandler(filters.TEXT & ~filters.COMMAND, get_details)],
        },
        fallbacks=[]
    )
    app.add_handler(conv_handler)

    logger.info("✅ Bot Público com formulário iniciado!")
    app.run_polling(drop_pending_updates=True)

if __name__ == '__main__':
    main()
