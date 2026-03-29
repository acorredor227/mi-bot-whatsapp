# ============================================================
# IMPORTACIONES
# ============================================================

from flask import Flask, request, jsonify
import requests
import os
import json
from dotenv import load_dotenv
from openai import OpenAI
import redis

load_dotenv()

app = Flask(__name__)

PHONE_NUMBER_ID = os.getenv("PHONE_NUMBER_ID")
ACCESS_TOKEN    = os.getenv("ACCESS_TOKEN")
VERIFY_TOKEN    = os.getenv("VERIFY_TOKEN")
OPENAI_API_KEY  = os.getenv("OPENAI_API_KEY")
REDIS_URL       = os.getenv("REDIS_URL")

cliente_openai = OpenAI(api_key=OPENAI_API_KEY)
cliente_redis  = redis.from_url(REDIS_URL)

MAX_MENSAJES_HISTORIAL = 10


# ============================================================
# DATOS DE TU TIENDA
# Cambia estos datos por los de tu tienda real
# ============================================================

TIENDA = {
    "nombre": "Mi Tienda",
    "productos": [
        {"nombre": "Producto A", "descripcion": "Descripción del producto A", "precio": "$10.000"},
        {"nombre": "Producto B", "descripcion": "Descripción del producto B", "precio": "$25.000"},
        {"nombre": "Producto C", "descripcion": "Descripción del producto C", "precio": "$50.000"},
    ],
    "contacto": "Para más información escríbenos al correo tienda@ejemplo.com o llámanos al 300 123 4567",
    "horario": "Lunes a viernes 8am - 6pm"
}

SYSTEM_PROMPT = f"""
Eres el asistente virtual de {TIENDA['nombre']}.
Responde siempre en español, de forma concisa y amable.
No uses markdown como asteriscos o corchetes porque WhatsApp no los renderiza.

Información de la tienda:
- Productos: {json.dumps(TIENDA['productos'], ensure_ascii=False)}
- Contacto: {TIENDA['contacto']}
- Horario: {TIENDA['horario']}

Cuando el usuario pregunte por productos, precios o contacto,
responde usando únicamente la información de la tienda de arriba.
Si preguntan algo que no está en la información, di que no tienes
esa información y sugiere contactar directamente.
"""
# Inyectamos los datos de la tienda directamente en el system prompt
# Así ChatGPT solo responde con información real de tu tienda
# y no inventa datos


# ============================================================
# FUNCIONES DE MEMORIA (sin cambios)
# ============================================================

def obtener_historial(numero_usuario):
    clave = f"historial:{numero_usuario}"
    datos = cliente_redis.get(clave)
    if datos:
        return json.loads(datos)
    return []

def guardar_historial(numero_usuario, historial):
    clave = f"historial:{numero_usuario}"
    if len(historial) > MAX_MENSAJES_HISTORIAL:
        historial = historial[-MAX_MENSAJES_HISTORIAL:]
    cliente_redis.setex(clave, 86400, json.dumps(historial))


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
        return "Token inválido", 403

    if request.method == "POST":
        data = request.get_json()
        print("📩 Evento recibido:", data)

        try:
            entry    = data["entry"][0]
            changes  = entry["changes"][0]
            value    = changes["value"]
            messages = value.get("messages")

            if messages:
                mensaje    = messages[0]
                numero     = mensaje["from"]
                tipo       = mensaje.get("type")

                # --------------------------------------------------
                # CASO 1: El usuario escribió texto
                # --------------------------------------------------
                if tipo == "text":
                    texto = mensaje["text"]["body"].lower().strip()
                    print(f"👤 Texto de {numero}: {texto}")

                    # Detectamos saludos para mostrar el menú
                    saludos = ["hola", "hello", "hi", "buenas", "buen dia",
                               "buenos dias", "buenas tardes", "buenas noches",
                               "inicio", "menu", "menú", "start"]

                    if any(saludo in texto for saludo in saludos):
                        # Si saluda, mostramos el menú de botones
                        enviar_botones(
                            numero,
                            f"¡Bienvenido a {TIENDA['nombre']}! 👋\n¿En qué te puedo ayudar hoy?",
                            [
                                {"id": "ver_productos", "title": "🛍️ Ver productos"},
                                {"id": "ver_precios",   "title": "💰 Ver precios"},
                                {"id": "contactar",     "title": "📞 Contactar"},
                            ]
                        )
                    else:
                        # Si escribe algo distinto a un saludo,
                        # la IA responde con contexto de la tienda
                        respuesta = preguntar_a_openai(numero, texto)
                        enviar_mensaje(numero, respuesta)

                # --------------------------------------------------
                # CASO 2: El usuario tocó un botón
                # --------------------------------------------------
                elif tipo == "interactive":
                    tipo_interactive = mensaje["interactive"]["type"]
                    # WhatsApp envía "button_reply" cuando tocan un botón
                    # y "list_reply" cuando eligen una opción de lista

                    if tipo_interactive == "button_reply":
                        boton_id    = mensaje["interactive"]["button_reply"]["id"]
                        boton_texto = mensaje["interactive"]["button_reply"]["title"]
                        print(f"🔘 Botón tocado: {boton_id} por {numero}")

                        # Según qué botón tocó, respondemos diferente
                        if boton_id == "ver_productos":
                            productos_texto = "\n".join([
                                f"• {p['nombre']}: {p['descripcion']}"
                                for p in TIENDA["productos"]
                            ])
                            # Construimos la lista de productos como texto
                            # porque WhatsApp no soporta HTML ni formato especial
                            enviar_mensaje(
                                numero,
                                f"Estos son nuestros productos:\n\n{productos_texto}\n\n"
                                f"¿Te interesa alguno? Escríbeme y te doy más detalles 😊"
                            )

                        elif boton_id == "ver_precios":
                            precios_texto = "\n".join([
                                f"• {p['nombre']}: {p['precio']}"
                                for p in TIENDA["productos"]
                            ])
                            enviar_mensaje(
                                numero,
                                f"Lista de precios:\n\n{precios_texto}\n\n"
                                f"¿Quieres hacer un pedido? Escríbeme 🛒"
                            )

                        elif boton_id == "contactar":
                            enviar_mensaje(
                                numero,
                                f"📞 Información de contacto:\n\n"
                                f"{TIENDA['contacto']}\n\n"
                                f"⏰ Horario: {TIENDA['horario']}"
                            )

                        # Después de responder al botón, guardamos
                        # en el historial que el usuario eligió esa opción
                        historial = obtener_historial(numero)
                        historial.append({"role": "user",      "content": f"Elegí la opción: {boton_texto}"})
                        historial.append({"role": "assistant", "content": f"Respondí sobre: {boton_id}"})
                        guardar_historial(numero, historial)

                else:
                    print(f"⚠️ Tipo no soportado: {tipo}")

        except (KeyError, IndexError) as e:
            print(f"⚠️ Error: {e}")

        return jsonify({"status": "ok"}), 200


# ============================================================
# FUNCIÓN: enviar_botones
# Envía un mensaje con hasta 3 botones tocables
# ============================================================

def enviar_botones(numero_destino, texto_mensaje, botones):
    """
    numero_destino  → número del usuario
    texto_mensaje   → el texto que aparece arriba de los botones
    botones         → lista de dicts con "id" y "title"
                      máximo 3 botones por mensaje
    """
    url = f"https://graph.facebook.com/v18.0/{PHONE_NUMBER_ID}/messages"

    headers = {
        "Authorization": f"Bearer {ACCESS_TOKEN}",
        "Content-Type": "application/json"
    }

    # Construimos la lista de botones en el formato que espera Meta
    botones_formateados = [
        {
            "type": "reply",
            # "reply" significa que al tocarlo envía una respuesta
            "reply": {
                "id": boton["id"],
                # ID interno — lo usamos en el código para saber
                # qué botón tocó el usuario (no lo ve el usuario)
                "title": boton["title"]
                # Texto visible del botón (máximo 20 caracteres)
            }
        }
        for boton in botones
        # Convertimos cada dict simple a formato Meta
    ]

    body = {
        "messaging_product": "whatsapp",
        "to": numero_destino,
        "type": "interactive",
        # "interactive" es el tipo para mensajes con botones o listas
        "interactive": {
            "type": "button",
            # "button" para botones, "list" para listas desplegables
            "body": {
                "text": texto_mensaje
                # El texto que aparece arriba de los botones
            },
            "action": {
                "buttons": botones_formateados
                # La lista de botones que construimos arriba
            }
        }
    }

    respuesta = requests.post(url, headers=headers, json=body)
    print(f"📤 Botones enviados: {respuesta.status_code} - {respuesta.text}")


# ============================================================
# FUNCIÓN: preguntar_a_openai (con memoria, sin cambios)
# ============================================================

def preguntar_a_openai(numero_usuario, mensaje_usuario):
    historial = obtener_historial(numero_usuario)
    historial.append({"role": "user", "content": mensaje_usuario})

    try:
        respuesta = cliente_openai.chat.completions.create(
            model="gpt-4o-mini",
            messages=[
                {"role": "system", "content": SYSTEM_PROMPT},
                *historial
            ],
            max_tokens=500,
            temperature=0.7
        )
        texto = respuesta.choices[0].message.content
        print(f"🤖 IA: {texto}")

        historial.append({"role": "assistant", "content": texto})
        guardar_historial(numero_usuario, historial)
        return texto

    except Exception as e:
        print(f"❌ Error OpenAI: {e}")
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
    print(f"📤 Mensaje: {respuesta.status_code} - {respuesta.text}")


# ============================================================
# ARRANQUE
# ============================================================

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    app.run(debug=False, host="0.0.0.0", port=port)