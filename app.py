# ---- IMPORTACIONES ----
from flask import Flask, request, jsonify  
# Flask: crea el servidor web
# request: nos permite leer los mensajes que llegan
# jsonify: convierte diccionarios Python a formato JSON para responder

import requests  
# Para hacer llamadas HTTP a la API de Meta

import os        
# Para leer las variables del archivo .env

from dotenv import load_dotenv
# Carga el archivo .env automáticamente

# ---- CONFIGURACIÓN ----
load_dotenv()  
# Le dice a Python: "busca el archivo .env y carga las variables"

app = Flask(__name__)  
# Crea la aplicación Flask. __name__ le dice a Flask dónde está el archivo.

# Leemos las credenciales del .env (nunca las escribas directo aquí)
PHONE_NUMBER_ID = os.getenv("PHONE_NUMBER_ID")
ACCESS_TOKEN    = os.getenv("ACCESS_TOKEN")
VERIFY_TOKEN    = os.getenv("VERIFY_TOKEN")

# ---- RUTA DEL WEBHOOK ----
# Un "webhook" es una URL que Meta va a llamar cada vez que alguien te escriba
@app.route("/webhook", methods=["GET", "POST"])
def webhook():

    # --- VERIFICACIÓN (GET) ---
    # Cuando configures el webhook en Meta, Meta primero te "prueba"
    # enviando un GET con un challenge. Tienes que responderlo igual
    # para demostrar que el servidor es tuyo.
    if request.method == "GET":
        mode      = request.args.get("hub.mode")
        token     = request.args.get("hub.verify_token")
        challenge = request.args.get("hub.challenge")

        # Si el token que envía Meta coincide con tu VERIFY_TOKEN, confirmas
        if mode == "subscribe" and token == VERIFY_TOKEN:
            print("✅ Webhook verificado correctamente")
            return challenge, 200  # 200 significa "OK"
        else:
            print("❌ Token incorrecto")
            return "Token inválido", 403  # 403 significa "No autorizado"

    # --- RECIBIR MENSAJES (POST) ---
    # Cada vez que alguien te escriba, Meta envía un POST con los datos
    if request.method == "POST":
        data = request.get_json()  
        # Convierte el JSON que envía Meta a un diccionario Python

        print("📩 Mensaje recibido:", data)  
        # Imprime el mensaje completo (útil para depurar)

        # Navegamos la estructura del JSON para llegar al mensaje
        # Meta envía los datos muy anidados, por eso tantos corchetes
        try:
            entry    = data["entry"][0]
            changes  = entry["changes"][0]
            value    = changes["value"]
            messages = value.get("messages")

            if "hola" in mensaje_recibido.lower():
                respuesta = "¡Hola! ¿En qué te puedo ayudar?"
            elif "precio" in mensaje_recibido.lower():
                respuesta = "Nuestros precios son..."
            else:
                respuesta = "No entendí, escribe 'hola' para empezar"



            if messages:  # Si hay mensajes (a veces Meta envía otros eventos)
                mensaje_recibido = messages[0]["text"]["body"]  
                # El texto que escribió el usuario

                numero_usuario = messages[0]["from"]  
                # El número de WhatsApp de quien te escribió

                if "hola" in mensaje_recibido.lower():
                    # Llamamos a la función que envía la respuesta
                    enviar_mensaje(numero_usuario, f"¡Hola! ¿En qué te puedo ayudar?")
                elif "precio" in mensaje_recibido.lower():
                    # Llamamos a la función que envía la respuesta
                    enviar_mensaje(numero_usuario, f"Nuestros precios son...")
                else:
                    # Llamamos a la función que envía la respuesta
                    enviar_mensaje(numero_usuario, f"No entendí, escribe 'hola' para empezar")

                print(f"👤 De: {numero_usuario} | 💬 Mensaje: {mensaje_recibido}")

        except (KeyError, IndexError) as e:
            # Si la estructura del JSON no es la esperada, no crashea
            print(f"⚠️ Error procesando mensaje: {e}")

        return jsonify({"status": "ok"}), 200  
        # Siempre devuelve 200 a Meta, si no Meta reintenta el envío

# ---- FUNCIÓN PARA ENVIAR MENSAJES ----
def enviar_mensaje(numero_destino, texto):
    url = f"https://graph.facebook.com/v18.0/{PHONE_NUMBER_ID}/messages"
    # Esta es la URL de la API de Meta para enviar mensajes

    headers = {
        "Authorization": f"Bearer {ACCESS_TOKEN}",  
        # Bearer + token = forma estándar de autenticarse en APIs
        "Content-Type": "application/json"
    }

    body = {
        "messaging_product": "whatsapp",  # Le dice a Meta que es WhatsApp
        "to": numero_destino,             # A quién enviar
        "type": "text",                   # Tipo de mensaje: texto
        "text": {"body": texto}           # El contenido del mensaje
    }

    respuesta = requests.post(url, headers=headers, json=body)
    # Hace el POST a la API de Meta

    print(f"📤 Respuesta de Meta: {respuesta.status_code} - {respuesta.text}")
    # Imprime si el envío fue exitoso o falló

# ---- ARRANQUE ----
if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    app.run(debug=False, host="0.0.0.0", port=port)
    # debug=True muestra errores detallados (solo para desarrollo)
    # port=5000 es el puerto local donde corre Flask