
import time
import os
from collections import defaultdict, deque
from fastapi import Request, HTTPException, status
from dotenv import load_dotenv

# Cargar variables de entorno (si usas .env)
load_dotenv()

# Configuración del límite de tasa
try:
    # Leer desde variables de entorno o usar valores por defecto
    RATE_LIMIT_REQUESTS = int(os.getenv("RATE_LIMIT_REQUESTS", "30"))
    RATE_LIMIT_WINDOW_SECONDS = int(os.getenv("RATE_LIMIT_WINDOW_SECONDS", "3600")) # 1 hora
except ValueError:
    print("Advertencia: Variables de entorno de límite de tasa inválidas. Usando valores por defecto (30 req/hora).")
    RATE_LIMIT_REQUESTS = 30
    RATE_LIMIT_WINDOW_SECONDS = 3600


# Almacenamiento en memoria para las marcas de tiempo (más robusto usar Redis en producción)
request_timestamps: dict[str, deque] = defaultdict(deque)

async def rate_limiter(request: Request):
    """
    Dependencia de FastAPI para aplicar limitación de tasa por IP.
    Considera X-Forwarded-For para proxies inversos.
    """
    # Usar X-Forwarded-For si está presente, si no, la IP directa del cliente
    client_ip = request.headers.get("x-forwarded-for")
    if client_ip:
        # X-Forwarded-For puede contener una lista de IPs (proxy1, proxy2, client), tomar la primera (la del cliente)
        client_ip = client_ip.split(",")[0].strip()
    else:
        # Si no hay proxy, tomar la IP directa
        client_ip = request.client.host if request.client else "unknown_client"
        # Validar si es una IP válida (simple check)
        if not client_ip or client_ip == "127.0.0.1" or client_ip == "::1": # Evitar limitar localhost fácilmente en desarrollo
             client_ip = "local_dev_client" # Usar un identificador genérico para desarrollo local si se quiere

    current_time = time.time()
    timestamps = request_timestamps[client_ip]

    # Eliminar timestamps antiguos (fuera de la ventana)
    while timestamps and timestamps[0] <= current_time - RATE_LIMIT_WINDOW_SECONDS:
        timestamps.popleft()

    # Comprobar si se ha excedido el límite
    if len(timestamps) >= RATE_LIMIT_REQUESTS:
        # Calcular tiempo restante para el reintento
        retry_after_seconds = max(0, int(timestamps[0] + RATE_LIMIT_WINDOW_SECONDS - current_time)) + 1 # +1 para asegurar que pase el segundo
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail=f"Límite de tasa excedido. {len(timestamps)} solicitudes desde tu IP ({client_ip}) en los últimos {RATE_LIMIT_WINDOW_SECONDS // 60} minutos (límite: {RATE_LIMIT_REQUESTS}).",
            headers={"Retry-After": str(retry_after_seconds)}
        )

    # Registrar esta solicitud
    timestamps.append(current_time)

    # Si no se excede el límite, la dependencia no hace nada más
    # La ejecución de la ruta continúa normalmente
