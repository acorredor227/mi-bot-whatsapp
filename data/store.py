# ============================================================
# data/store.py
# Responsabilidad: contener los datos del negocio.
#
# BENEFICIO: cuando quieras actualizar productos o precios
# sabes exactamente dónde ir — sin tocar lógica del bot.
# ============================================================

TIENDA = {
    "nombre": "Mi Tienda",
    "productos": [
        {"nombre": "Producto A", "descripcion": "Descripción del producto A", "precio": "$10.000"},
        {"nombre": "Producto B", "descripcion": "Descripción del producto B", "precio": "$25.000"},
        {"nombre": "Producto C", "descripcion": "Descripción del producto C", "precio": "$50.000"},
    ],
    "contacto": "Escríbenos a tienda@ejemplo.com o llámanos al 300 123 4567",
    "horario": "Lunes a viernes 8am - 6pm"
}

# El system prompt vive aquí porque es parte de la
# "personalidad" del negocio, no lógica técnica
import json

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