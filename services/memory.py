# ============================================================
# services/memory.py
# Responsabilidad: toda la lógica de memoria con Redis.
#
# BENEFICIO: si mañana cambias Redis por una base de datos
# distinta, solo modificas este archivo. El resto del
# código no se entera del cambio.
# ============================================================

import json
import redis
from config import REDIS_URL, MAX_MENSAJES_HISTORIAL

cliente_redis = redis.from_url(REDIS_URL)
# Creamos la conexión una sola vez al importar el módulo
# Todos los que importen memory.py comparten esta conexión


def obtener_historial(numero_usuario: str) -> list:
    """
    Lee el historial de conversación de un usuario.

    numero_usuario: número en formato internacional "573204281555"
    retorna: lista de mensajes [{"role": "user", "content": "..."}]
             o lista vacía si es la primera vez
    """
    clave = f"historial:{numero_usuario}"
    datos = cliente_redis.get(clave)

    if datos:
        return json.loads(datos)
    return []


def guardar_historial(numero_usuario: str, historial: list) -> None:
    """
    Guarda el historial actualizado en Redis.

    Limita automáticamente a MAX_MENSAJES_HISTORIAL para
    controlar costos de OpenAI y espacio en Redis.
    La conversación expira después de 24 horas de inactividad.
    """
    clave = f"historial:{numero_usuario}"

    if len(historial) > MAX_MENSAJES_HISTORIAL:
        historial = historial[-MAX_MENSAJES_HISTORIAL:]

    cliente_redis.setex(
        clave,
        86400,              # 24 horas en segundos
        json.dumps(historial)
    )


def limpiar_historial(numero_usuario: str) -> None:
    """
    Borra el historial de un usuario.
    Útil cuando el usuario escribe "reiniciar" o "reset".
    """
    clave = f"historial:{numero_usuario}"
    cliente_redis.delete(clave)
    # .delete() elimina la clave de Redis completamente