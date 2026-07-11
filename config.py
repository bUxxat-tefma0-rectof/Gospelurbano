import os
from dotenv import load_dotenv

load_dotenv()

PUBLIC_TOKEN = os.getenv("BOT_PUBLIC_TOKEN")
ADMIN_TOKEN = os.getenv("BOT_ADMIN_TOKEN")
OWNER_ID = int(os.getenv("OWNER_ID"))
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
MP_ACCESS_TOKEN = os.getenv("MERCADO_PAGO_ACCESS_TOKEN")
DB_URL = os.getenv("DB_URL")
