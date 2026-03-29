# ============================================================
# IMPORTACIONES
# ============================================================

from flask import Flask, request, jsonify
import requests
import os
import json
# json → para convertir la lista del historial a texto
# y guardarlo en Redis (Redis solo guarda texto, no listas)

from dotenv import load_dotenv
from openai import OpenAI
import redis
# Cliente de Redis para guardar y leer el historial
# de cada conversación por número de teléfono


# ============================================================
# CONFIGURACIÓN INICIAL
# ============================================================

load_dotenv()

app = Flask(__name__)

PHONE_NUMBER_ID = os.getenv("PHONE_NUMBER_ID")
ACCESS_TOKEN    = os.getenv("ACCESS_TOKEN")
VERIFY_TOKEN    = os.getenv("VERIFY_TOKEN")
OPENAI_API_KEY  = os.getenv("OPENAI_API_KEY")
REDIS_URL       = os.getenv("REDIS_URL")

cliente_openai = OpenAI(api_key=OPENAI_API_KEY)

cliente_redis = redis.from_url(REDIS_URL)
# Crea la conexión a Redis usando la URL
# from_url detecta automáticamente host, puerto y contraseña
# desde la URL — más simple que configurar todo por separado

# Cuántos mensajes recordar por conversación
# 10 = 5 intercambios (5 del usuario + 5 del bot)
# Más mensajes = más contexto pero más costo en OpenAI
MAX_MENSAJES_HISTORIAL = 10

SYSTEM_PROMPT = """
Eres un asistente virtual amigable que responde por WhatsApp.
Responde siempre en español, de forma concisa (máximo 3 párrafos cortos).
Sé útil, amable y directo. No uses markdown como asteriscos o corchetes
porque WhatsApp no los renderiza bien.
"""


# ============================================================
# FUNCIONES DE MEMORIA
# Guardan y leen el historial de cada usuario en Redis
# ============================================================

def obtener_historial(numero_usuario):
    """
    Lee el historial de conversación de un usuario desde Redis.
    Cada usuario tiene su propio historial identificado por su número.
    """
    clave = f"historial:{numero_usuario}"
    # La clave en Redis es única por usuario
    # Ejemplo: "historial:573204281555"
    # Así cada persona tiene su propia memoria separada

    datos = cliente_redis.get(clave)
    # .get() busca el valor en Redis
    # Si no existe (primera vez que escribe) devuelve None

    if datos:
        return json.loads(datos)
        # json.loads convierte el texto guardado en Redis
        # de vuelta a una lista de Python
        # Ejemplo: '[{"role":"user","content":"hola"}]' → lista Python
    return []
    # Si es la primera vez que escribe, devolvemos lista vacía


def guardar_historial(numero_usuario, historial):
    """
    Guarda el historial actualizado de un usuario en Redis.
    Limita el historial para no crecer infinitamente.
    """
    clave = f"historial:{numero_usuario}"

    # Limitamos el historial a los últimos MAX_MENSAJES_HISTORIAL
    # Si hay más, eliminamos los más antiguos (pero nunca el system prompt)
    # Esto controla el costo de OpenAI y el tamaño en Redis
    if len(historial) > MAX_MENSAJES_HISTORIAL:
        historial = historial[-MAX_MENSAJES_HISTORIAL:]
        # [-10:] = toma solo los últimos 10 elementos de la lista

    cliente_redis.setex(
        clave,
        86400,         # Tiempo de expiración en segundos
                       # 86400 = 24 horas
                       # Después de 24 horas de inactividad
                       # la conversación se "olvida" automáticamente
        json.dumps(historial)
        # json.dumps convierte la lista Python a texto JSON
        # para poder guardarlo en Redis
        # Ejemplo: lista Python → '[{"role":"user","content":"hola"}]'
    )


# ============================================================
# WEBHOOK
# ============================================================

@app.route("/webhook", methods=["GET", "POST"])
def webhook():

    if request.method == "GET":
        mode      = request.args.get("hub.mode")
        token     = request.args.get("hub.verify_token")
        challenge = request.args.get("hub.challenge")

        if mode == "subscribe" and token == VERIFY_TOKEN:
            print("✅ Webhook verificado")
            return challenge, 200
        else:
            return "Token inválido", 403

    if request.method == "POST":
        data = request.get_json()
        print("📩 Mensaje recibido:", data)

        try:
            entry    = data["entry"][0]
            changes  = entry["changes"][0]
            value    = changes["value"]
            messages = value.get("messages")

            if messages:
                tipo_mensaje = messages[0].get("type")

                if tipo_mensaje != "text":
                    print(f"⚠️ Tipo no soportado: {tipo_mensaje}")
                    return jsonify({"status": "ok"}), 200

                mensaje_recibido = messages[0]["text"]["body"]
                numero_usuario   = messages[0]["from"]

                print(f"👤 De: {numero_usuario} | 💬 {mensaje_recibido}")

                respuesta_ia = preguntar_a_openai(numero_usuario, mensaje_recibido)
                # Ahora pasamos también el número de usuario
                # para poder leer y guardar su historial específico

                enviar_mensaje(numero_usuario, respuesta_ia)

        except (KeyError, IndexError) as e:
            print(f"⚠️ Error procesando mensaje: {e}")

        return jsonify({"status": "ok"}), 200


# ============================================================
# FUNCIÓN: preguntar_a_openai (ahora con memoria)
# ============================================================

def preguntar_a_openai(numero_usuario, mensaje_usuario):

    # 1. Leemos el historial previo de este usuario
    historial = obtener_historial(numero_usuario)
    # Si es la primera vez, historial = []
    # Si ya conversó antes, historial tiene los mensajes anteriores

    # 2. Agregamos el mensaje nuevo del usuario al historial
    historial.append({
        "role": "user",
        "content": mensaje_usuario
    })
    # Ahora el historial tiene todos los mensajes anteriores
    # más el mensaje actual

    try:
        respuesta = cliente_openai.chat.completions.create(
            model="gpt-4o-mini",

            messages=[
                {"role": "system", "content": SYSTEM_PROMPT},
                # El system prompt va SIEMPRE primero
                # Le dice a ChatGPT cómo comportarse en toda la conversación

                *historial
                # El * "desempaqueta" la lista del historial
                # Es como escribir cada mensaje por separado
                # Ejemplo si historial tiene 3 mensajes:
                # {"role": "user", "content": "me llamo Alejandro"},
                # {"role": "assistant", "content": "Hola Alejandro!"},
                # {"role": "user", "content": "¿cómo me llamo?"}
            ],

            max_tokens=500,
            temperature=0.7
        )

        texto = respuesta.choices[0].message.content
        print(f"🤖 Respuesta IA: {texto}")

        # 3. Guardamos la respuesta del bot en el historial
        historial.append({
            "role": "assistant",
            "content": texto
        })
        # Ahora el historial queda completo:
        # [...mensajes anteriores, mensaje usuario, respuesta bot]

        # 4. Guardamos el historial actualizado en Redis
        guardar_historial(numero_usuario, historial)

        return texto

    except Exception as e:
        print(f"❌ Error con OpenAI: {e}")
        return "Lo siento, tuve un problema. Intenta de nuevo."


# ============================================================
# FUNCIÓN: enviar_mensaje (sin cambios)
# ============================================================

def enviar_mensaje(numero_destino, texto):
    url = f"https://graph.facebook.com/v18.0/{PHONE_NUMBER_ID}/messages"

    headers = {
        "Authorization": f"Bearer {ACCESS_TOKEN}",
        "Content-Type": "application/json"
    }

    body = {
        "messaging_product": "whatsapp",
        "to": numero_destino,
        "type": "text",
        "text": {"body": texto}
    }

    respuesta = requests.post(url, headers=headers, json=body)
    print(f"📤 Respuesta de Meta: {respuesta.status_code} - {respuesta.text}")


# ============================================================
# ARRANQUE
# ============================================================

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    app.run(debug=False, host="0.0.0.0", port=port)