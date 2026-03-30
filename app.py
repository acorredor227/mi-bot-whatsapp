# ============================================================
# app.py
# Responsabilidad: arrancar el servidor y definir las rutas.
# NADA más. Toda la lógica vive en handlers/ y services/
# ============================================================

from flask import Flask, request, jsonify
from config import VERIFY_TOKEN
from handlers.webhook_handler import manejar_mensaje
import os

app = Flask(__name__)


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
        print("📩 Evento recibido")
        manejar_mensaje(data)
        # app.py no sabe nada de WhatsApp, OpenAI ni Redis
        # Solo recibe el evento y lo delega al handler
        return jsonify({"status": "ok"}), 200


if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    app.run(debug=False, host="0.0.0.0", port=port)