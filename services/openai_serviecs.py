# ============================================================
# services/openai_service.py
# Responsabilidad: toda la comunicación con OpenAI.
#
# BENEFICIO: si cambias de GPT-4o-mini a Claude o Gemini,
# solo modificas este archivo.
# ============================================================

from openai import OpenAI
from config import OPENAI_API_KEY
from data.store import SYSTEM_PROMPT
from services.memory import obtener_historial, guardar_historial

cliente_openai = OpenAI(api_key=OPENAI_API_KEY)


def preguntar_a_openai(numero_usuario: str, mensaje_usuario: str) -> str:
    """
    Envía el mensaje a OpenAI con el historial completo
    y devuelve la respuesta en texto.

    numero_usuario:  para leer y guardar su historial
    mensaje_usuario: el texto que escribió el usuario
    retorna:         la respuesta de ChatGPT como string
    """
    # 1. Leemos el historial previo
    historial = obtener_historial(numero_usuario)

    # 2. Agregamos el mensaje nuevo
    historial.append({
        "role": "user",
        "content": mensaje_usuario
    })

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

        # 3. Guardamos la respuesta en el historial
        historial.append({
            "role": "assistant",
            "content": texto
        })

        # 4. Persistimos el historial actualizado
        guardar_historial(numero_usuario, historial)

        return texto

    except Exception as e:
        print(f"❌ Error OpenAI: {e}")
        return "Lo siento, tuve un problema procesando tu mensaje. Intenta de nuevo."