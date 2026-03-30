# ============================================================
# config.py
# Responsabilidad: leer y centralizar todas las variables
# de entorno en un solo lugar.
#
# BENEFICIO: si una variable cambia de nombre, solo lo
# cambias aquí — no en 5 archivos diferentes.
# ============================================================

import os
from dotenv import load_dotenv

load_dotenv()
# Carga el .env una sola vez aquí
# Los demás archivos importan desde config.py
# y no necesitan llamar load_dotenv() ellos mismos

# Meta / WhatsApp
PHONE_NUMBER_ID = os.getenv("PHONE_NUMBER_ID")
ACCESS_TOKEN    = os.getenv("ACCESS_TOKEN")
VERIFY_TOKEN    = os.getenv("VERIFY_TOKEN")

# OpenAI
OPENAI_API_KEY  = os.getenv("OPENAI_API_KEY")

# Redis
REDIS_URL       = os.getenv("REDIS_URL")

# Configuración general del bot
MAX_MENSAJES_HISTORIAL = 10
# Centralizar este número aquí significa que si quieres
# cambiarlo de 10 a 20, lo cambias en un solo lugar