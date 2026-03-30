# ============================================================
# services/whatsapp.py
# Responsabilidad: toda la comunicación con la API de Meta.
#
# BENEFICIO: todas las llamadas HTTP a Meta están aquí.
# Si Meta cambia su API, solo actualizas este archivo.
# ============================================================

import requests
from config import PHONE_NUMBER_ID, ACCESS_TOKEN

# URL base de la API — si Meta sube la versión (v18 → v19)
# solo la cambias aquí
API_URL = f"https://graph.facebook.com/v18.0/{PHONE_NUMBER_ID}/messages"

# Headers que van en TODAS las llamadas a Meta
# Los definimos una vez aquí para no repetirlos
HEADERS = {
    "Authorization": f"Bearer {ACCESS_TOKEN}",
    "Content-Type": "application/json"
}


def enviar_mensaje(numero_destino: str, texto: str) -> None:
    """
    Envía un mensaje de texto simple por WhatsApp.

    numero_destino: número en formato "573204281555"
    texto:          el contenido del mensaje
    """
    body = {
        "messaging_product": "whatsapp",
        "to": numero_destino,
        "type": "text",
        "text": {"body": texto}
    }

    respuesta = requests.post(API_URL, headers=HEADERS, json=body)
    print(f"📤 Mensaje: {respuesta.status_code} - {respuesta.text}")


def enviar_botones(numero_destino: str, texto_mensaje: str, botones: list) -> None:
    """
    Envía un mensaje con botones interactivos (máximo 3).

    numero_destino: número del usuario
    texto_mensaje:  texto que aparece arriba de los botones
    botones:        lista de dicts [{"id": "...", "title": "..."}]
    """
    botones_formateados = [
        {
            "type": "reply",
            "reply": {
                "id":    boton["id"],
                "title": boton["title"]
                # title tiene máximo 20 caracteres
            }
        }
        for boton in botones
    ]

    body = {
        "messaging_product": "whatsapp",
        "to": numero_destino,
        "type": "interactive",
        "interactive": {
            "type": "button",
            "body": {
                "text": texto_mensaje
            },
            "action": {
                "buttons": botones_formateados
            }
        }
    }

    respuesta = requests.post(API_URL, headers=HEADERS, json=body)
    print(f"📤 Botones: {respuesta.status_code} - {respuesta.text}")