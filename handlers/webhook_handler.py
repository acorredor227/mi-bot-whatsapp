# ============================================================
# handlers/webhook_handler.py
# Responsabilidad: decidir qué hacer con cada mensaje.
#
# BENEFICIO: aquí vive SOLO la lógica de negocio.
# No sabe nada de HTTP, Redis o OpenAI directamente —
# delega todo a los servicios correspondientes.
# ============================================================

from data.store import TIENDA
from services.whatsapp import enviar_mensaje, enviar_botones
from services.openai_service import preguntar_a_openai
from services.memory import guardar_historial, obtener_historial, limpiar_historial

# Palabras que disparan el menú principal
SALUDOS = [
    "hola", "hello", "hi", "buenas", "buen dia",
    "buenos dias", "buenas tardes", "buenas noches",
    "inicio", "menu", "menú", "start"
]


def manejar_mensaje(data: dict) -> None:
    """
    Punto de entrada principal para procesar eventos del webhook.
    Recibe el JSON completo de Meta y lo enruta al manejador correcto.
    """
    try:
        entry    = data["entry"][0]
        changes  = entry["changes"][0]
        value    = changes["value"]
        messages = value.get("messages")

        if not messages:
            # Evento sin mensajes (ej: confirmación de entrega)
            # No hacemos nada
            return

        mensaje = messages[0]
        numero  = mensaje["from"]
        tipo    = mensaje.get("type")

        print(f"📨 Tipo: {tipo} | De: {numero}")

        if tipo == "text":
            _manejar_texto(numero, mensaje)

        elif tipo == "interactive":
            _manejar_interactivo(numero, mensaje)

        else:
            print(f"⚠️ Tipo no soportado: {tipo}")

    except (KeyError, IndexError) as e:
        print(f"⚠️ Error procesando webhook: {e}")


def _manejar_texto(numero: str, mensaje: dict) -> None:
    """
    Maneja mensajes de texto.
    El _ al inicio indica que es una función "privada" —
    solo se usa dentro de este archivo, no se importa afuera.
    """
    texto = mensaje["text"]["body"].lower().strip()
    print(f"💬 Texto: {texto}")

    # Comando especial para reiniciar la conversación
    if texto in ["reiniciar", "reset", "restart"]:
        limpiar_historial(numero)
        enviar_mensaje(numero, "Conversación reiniciada. ¡Hola de nuevo! 👋")
        return

    # Si saluda, mostramos el menú
    if any(saludo in texto for saludo in SALUDOS):
        _enviar_menu_principal(numero)
        return

    # Cualquier otra cosa, la IA responde con contexto
    respuesta = preguntar_a_openai(numero, texto)
    enviar_mensaje(numero, respuesta)


def _manejar_interactivo(numero: str, mensaje: dict) -> None:
    """
    Maneja cuando el usuario toca un botón o elige una lista.
    """
    tipo_interactive = mensaje["interactive"]["type"]

    if tipo_interactive == "button_reply":
        boton_id    = mensaje["interactive"]["button_reply"]["id"]
        boton_texto = mensaje["interactive"]["button_reply"]["title"]
        print(f"🔘 Botón: {boton_id}")

        _manejar_boton(numero, boton_id, boton_texto)


def _manejar_boton(numero: str, boton_id: str, boton_texto: str) -> None:
    """
    Ejecuta la acción correspondiente al botón tocado.
    Separamos esto en su propia función para que agregar
    botones nuevos sea tan simple como agregar un elif.
    """
    if boton_id == "ver_productos":
        productos_texto = "\n".join([
            f"• {p['nombre']}: {p['descripcion']}"
            for p in TIENDA["productos"]
        ])
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
            f"Información de contacto:\n\n"
            f"{TIENDA['contacto']}\n\n"
            f"Horario: {TIENDA['horario']}"
        )

    # Guardamos en historial que el usuario eligió esta opción
    # para que la IA tenga contexto en mensajes siguientes
    historial = obtener_historial(numero)
    historial.append({"role": "user",      "content": f"Elegí: {boton_texto}"})
    historial.append({"role": "assistant", "content": f"Respondí sobre: {boton_id}"})
    guardar_historial(numero, historial)


def _enviar_menu_principal(numero: str) -> None:
    """
    Envía el menú de bienvenida con los 3 botones principales.
    Separarlo aquí permite reutilizarlo desde cualquier parte.
    """
    enviar_botones(
        numero,
        f"¡Bienvenido a {TIENDA['nombre']}! 👋\n¿En qué te puedo ayudar hoy?",
        [
            {"id": "ver_productos", "title": "🛍️ Ver productos"},
            {"id": "ver_precios",   "title": "💰 Ver precios"},
            {"id": "contactar",     "title": "📞 Contactar"},
        ]
    )