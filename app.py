# ============================================================
# IMPORTACIONES
# Traemos las herramientas externas que necesita el programa
# ============================================================

from flask import Flask, request, jsonify
# Flask     → el framework que convierte tu Python en un servidor web
# request   → objeto que contiene todo lo que llega al servidor
#             (headers, body, parámetros de URL, etc.)
# jsonify   → convierte diccionarios Python {"key": "value"}
#             a formato JSON para responder a Meta

import requests
# Librería para hacer llamadas HTTP hacia afuera
# La usamos para llamar a la API de Meta y enviar mensajes
# (diferente a "request" de Flask que es para recibir)

import os
# Módulo nativo de Python para interactuar con el sistema operativo
# Lo usamos específicamente para leer variables de entorno
# como PHONE_NUMBER_ID, ACCESS_TOKEN, etc.

from dotenv import load_dotenv
# Lee el archivo .env de tu computadora local y carga
# las variables como si fueran variables del sistema
# En Render esto no hace nada — Render ya las inyecta solo

from openai import OpenAI
# Cliente oficial de OpenAI para Python
# Nos da una interfaz limpia para llamar a ChatGPT
# sin tener que construir las llamadas HTTP manualmente


# ============================================================
# CONFIGURACIÓN INICIAL
# Se ejecuta una sola vez cuando el servidor arranca
# ============================================================

load_dotenv()
# Busca el archivo .env en la carpeta actual y carga sus valores
# Ejemplo: OPENAI_API_KEY=sk-... se convierte en variable disponible
# con os.getenv("OPENAI_API_KEY")

app = Flask(__name__)
# Crea la aplicación web
# __name__ es una variable especial de Python que contiene
# el nombre del archivo actual ("app" en este caso)
# Flask lo necesita para saber desde dónde cargar recursos

# Leemos las credenciales desde las variables de entorno
# NUNCA escribas estos valores directamente en el código
# porque si subes el código a GitHub, quedan expuestos
PHONE_NUMBER_ID = os.getenv("PHONE_NUMBER_ID")
# El ID numérico de tu número de WhatsApp Business
# Ejemplo: "948259341714378"

ACCESS_TOKEN = os.getenv("ACCESS_TOKEN")
# El token de autenticación para la API de Meta
# Ejemplo: "EAAl...muy largo..."

VERIFY_TOKEN = os.getenv("VERIFY_TOKEN")
# Token que tú inventaste para verificar el webhook
# Meta te lo pregunta al configurar el webhook

OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
# Tu llave secreta de OpenAI
# Ejemplo: "sk-proj-..."

cliente_openai = OpenAI(api_key=OPENAI_API_KEY)
# Crea una instancia del cliente de OpenAI con tu API key
# A partir de aquí usamos "cliente_openai" para hacer
# todas las llamadas a ChatGPT


# ============================================================
# PERSONALIDAD DEL BOT
# Este texto le dice a ChatGPT cómo debe comportarse
# Puedes cambiarlo completamente según tu caso de uso
# ============================================================

SYSTEM_PROMPT = """
Eres un asistente virtual amigable que responde por WhatsApp.
Responde siempre en español, de forma concisa (máximo 3 párrafos cortos).
Sé útil, amable y directo. No uses markdown como asteriscos o corchetes
porque WhatsApp no los renderiza bien.
"""
# El "system prompt" es el rol que le asignas a la IA
# Es lo primero que lee ChatGPT antes de ver el mensaje del usuario
# Ejemplos de cómo puedes personalizarlo:
# - "Eres el asistente de soporte de la tienda X"
# - "Eres un experto en nutrición que da consejos saludables"
# - "Solo respondes preguntas sobre nuestros productos"


# ============================================================
# WEBHOOK — La puerta de entrada de todos los mensajes
# ============================================================

@app.route("/webhook", methods=["GET", "POST"])
# @app.route es un "decorador" — le dice a Flask:
# "cuando alguien visite la URL /webhook, ejecuta esta función"
# methods=["GET", "POST"] significa que acepta ambos tipos:
# GET  → Meta lo usa para verificar que el webhook es tuyo
# POST → Meta lo usa para enviarte los mensajes entrantes

def webhook():
    # Esta función se ejecuta cada vez que Meta llama a /webhook

    # ----------------------------------------------------------
    # BLOQUE GET: Verificación del webhook
    # Ocurre UNA SOLA VEZ cuando configuras el webhook en Meta
    # Meta envía 3 parámetros en la URL para verificar
    # ----------------------------------------------------------
    if request.method == "GET":

        mode = request.args.get("hub.mode")
        # "hub.mode" siempre vale "subscribe" si es Meta
        # request.args lee los parámetros de la URL
        # Ejemplo URL: /webhook?hub.mode=subscribe&hub.verify_token=...

        token = request.args.get("hub.verify_token")
        # El token que Meta recibió cuando configuraste el webhook
        # Lo comparamos con nuestro VERIFY_TOKEN para confirmar
        # que somos nosotros y no alguien más

        challenge = request.args.get("hub.challenge")
        # Un número aleatorio que Meta genera
        # Si lo devolvemos tal cual, Meta confirma la verificación
        # Es como un "apretón de manos" entre Meta y tu servidor

        if mode == "subscribe" and token == VERIFY_TOKEN:
            # Si el modo es correcto Y el token coincide
            # devolvemos el challenge — Meta lo espera para confirmar
            print("✅ Webhook verificado")
            return challenge, 200
            # 200 = código HTTP que significa "Todo OK"
        else:
            # Si el token no coincide, rechazamos la verificación
            # Esto protege tu webhook de llamadas no autorizadas
            return "Token inválido", 403
            # 403 = código HTTP que significa "No autorizado"

    # ----------------------------------------------------------
    # BLOQUE POST: Mensajes entrantes
    # Se ejecuta cada vez que alguien te escribe en WhatsApp
    # ----------------------------------------------------------
    if request.method == "POST":

        data = request.get_json()
        # Convierte el cuerpo del POST de texto JSON
        # a un diccionario Python que podemos navegar
        # Ejemplo: data["entry"][0]["changes"][0]...

        print("📩 Mensaje recibido:", data)
        # Imprimimos el JSON completo — muy útil para depurar
        # Lo puedes ver en los logs de Render en tiempo real

        try:
            # Navegamos la estructura anidada del JSON de Meta
            # Meta envía los datos muy profundos dentro del JSON
            # por eso necesitamos varios niveles de corchetes

            entry = data["entry"][0]
            # "entry" es una lista de eventos
            # [0] toma el primer evento (casi siempre solo hay uno)

            changes = entry["changes"][0]
            # "changes" contiene los cambios del evento
            # [0] toma el primer cambio

            value = changes["value"]
            # "value" contiene los datos reales del mensaje

            messages = value.get("messages")
            # .get() es más seguro que ["messages"] porque
            # si la clave no existe devuelve None en vez de crashear
            # A veces Meta envía eventos sin mensajes (ej: confirmaciones
            # de entrega) — en esos casos "messages" no existe

            if messages:
                # Solo procesamos si hay mensajes reales
                # Esto filtra eventos de estado como "delivered", "read"

                tipo_mensaje = messages[0].get("type")
                # El tipo puede ser: "text", "image", "audio",
                # "video", "document", "location", etc.
                # Por ahora solo manejamos texto

                if tipo_mensaje != "text":
                    # Si alguien manda una foto o audio, lo ignoramos
                    # En el futuro puedes agregar soporte para otros tipos
                    print(f"⚠️ Tipo no soportado: {tipo_mensaje}")
                    return jsonify({"status": "ok"}), 200

                mensaje_recibido = messages[0]["text"]["body"]
                # El texto que escribió el usuario
                # Ejemplo: "Hola, ¿cuáles son sus horarios?"

                numero_usuario = messages[0]["from"]
                # El número de WhatsApp de quien escribió
                # Formato internacional sin +: "573204281555"

                print(f"👤 De: {numero_usuario} | 💬 {mensaje_recibido}")

                respuesta_ia = preguntar_a_openai(mensaje_recibido)
                # Enviamos el mensaje a ChatGPT y recibimos la respuesta
                # Esta función está definida más abajo

                enviar_mensaje(numero_usuario, respuesta_ia)
                # Enviamos la respuesta de ChatGPT al usuario por WhatsApp

        except (KeyError, IndexError) as e:
            # KeyError   → intentamos acceder a una clave que no existe
            # IndexError → intentamos acceder a un índice fuera de rango
            # En vez de crashear el servidor, solo imprimimos el error
            print(f"⚠️ Error procesando mensaje: {e}")

        return jsonify({"status": "ok"}), 200
        # SIEMPRE devolvemos 200 a Meta, incluso si hubo un error interno
        # Si devolvemos otro código, Meta reintenta el envío
        # hasta 3 veces, lo que puede causar respuestas duplicadas


# ============================================================
# FUNCIÓN: preguntar_a_openai
# Recibe el mensaje del usuario y devuelve la respuesta de la IA
# ============================================================

def preguntar_a_openai(mensaje_usuario):

    try:
        respuesta = cliente_openai.chat.completions.create(
            # .chat.completions.create es el método para
            # conversar con ChatGPT (modelo de chat)

            model="gpt-4o-mini",
            # El modelo que usamos
            # gpt-4o-mini → más barato y rápido, ideal para bots
            # gpt-4o      → más inteligente pero más caro
            # Para un bot de WhatsApp, gpt-4o-mini es suficiente

            messages=[
                {"role": "system", "content": SYSTEM_PROMPT},
                # "system" → instrucciones de comportamiento para la IA
                # Se envía en cada llamada para que ChatGPT "recuerde"
                # cómo debe comportarse

                {"role": "user", "content": mensaje_usuario}
                # "user" → el mensaje que escribió la persona real
                # ChatGPT responde a este mensaje siguiendo
                # las instrucciones del system prompt
            ],

            max_tokens=500,
            # Límite de palabras en la respuesta
            # 500 tokens ≈ 375 palabras aproximadamente
            # Más tokens = más caro y más lento

            temperature=0.7
            # Controla la creatividad de la respuesta
            # 0.0 → muy literal y predecible (bueno para datos exactos)
            # 0.7 → balance entre precisión y naturalidad (recomendado)
            # 1.0 → muy creativo y variable (bueno para escritura)
        )

        texto = respuesta.choices[0].message.content
        # Navegamos la respuesta de OpenAI para sacar el texto
        # .choices[0]      → primera opción de respuesta (siempre hay 1)
        # .message.content → el texto de la respuesta

        print(f"🤖 Respuesta IA: {texto}")
        return texto
        # Devolvemos el texto para enviárselo al usuario

    except Exception as e:
        # Si OpenAI falla (sin créditos, timeout, etc.)
        # devolvemos un mensaje de error amigable
        # en vez de dejar al usuario sin respuesta
        print(f"❌ Error con OpenAI: {e}")
        return "Lo siento, tuve un problema procesando tu mensaje. Intenta de nuevo."


# ============================================================
# FUNCIÓN: enviar_mensaje
# Llama a la API de Meta para enviar un mensaje por WhatsApp
# ============================================================

def enviar_mensaje(numero_destino, texto):

    url = f"https://graph.facebook.com/v18.0/{PHONE_NUMBER_ID}/messages"
    # La URL de la API de Meta para enviar mensajes
    # v18.0 es la versión de la Graph API
    # {PHONE_NUMBER_ID} es tu número de WhatsApp Business
    # Esta URL es específica para tu número

    headers = {
        "Authorization": f"Bearer {ACCESS_TOKEN}",
        # "Bearer TOKEN" es el estándar para autenticarse en APIs modernas
        # Meta verifica este token antes de procesar la solicitud

        "Content-Type": "application/json"
        # Le dice a Meta que el cuerpo del mensaje es JSON
        # Sin esto Meta no sabe cómo leer los datos
    }

    body = {
        "messaging_product": "whatsapp",
        # Obligatorio — le dice a Meta que es un mensaje de WhatsApp
        # (Meta también maneja Messenger e Instagram con la misma API)

        "to": numero_destino,
        # El número del destinatario en formato internacional
        # Ejemplo: "573204281555" (Colombia: 57 + número sin 0)

        "type": "text",
        # El tipo de mensaje que enviamos
        # Otros tipos: "image", "audio", "document", "template"

        "text": {"body": texto}
        # El contenido del mensaje
        # "body" es el campo donde va el texto visible
    }

    respuesta = requests.post(url, headers=headers, json=body)
    # Hacemos el POST a la API de Meta
    # requests.post → envía una solicitud HTTP POST
    # json=body     → serializa el diccionario a JSON automáticamente

    print(f"📤 Respuesta de Meta: {respuesta.status_code} - {respuesta.text}")
    # respuesta.status_code → 200 = éxito, 400/401 = error
    # respuesta.text        → detalle de la respuesta de Meta


# ============================================================
# ARRANQUE DEL SERVIDOR
# Solo se ejecuta cuando corres "python app.py" directamente
# Cuando Render usa gunicorn, esta parte se ignora
# ============================================================

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    # os.environ.get("PORT", 5000) →
    #   busca la variable PORT en el entorno
    #   si no existe (local), usa 5000 por defecto
    #   Render asigna PORT automáticamente
    # int() convierte el valor a número entero

    app.run(debug=False, host="0.0.0.0", port=port)
    # debug=False  → no mostrar errores detallados en producción
    # host="0.0.0.0" → acepta conexiones desde cualquier IP
    #                  (necesario para que Render sea accesible)
    # port=port    → usa el puerto que definimos arriba