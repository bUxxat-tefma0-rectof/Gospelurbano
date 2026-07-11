import logging
from telegram import Update
from telegram.ext import Application, CommandHandler, ContextTypes
from config import ADMIN_TOKEN, OWNER_ID

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

async def start_admin(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id != OWNER_ID:
        await update.message.reply_text("Acesso negado.")
        return
    await update.message.reply_text("👑 Painel Admin\n\n/comandos para ver opções.")

def main():
    app = Application.builder().token(ADMIN_TOKEN).build()
    app.add_handler(CommandHandler("start", start_admin))
    logger.info("✅ Bot Admin iniciado!")
    app.run_polling(drop_pending_updates=True)

if __name__ == '__main__':
    main()
