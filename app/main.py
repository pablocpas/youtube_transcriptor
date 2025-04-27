
from fastapi import FastAPI, Request, HTTPException, Depends, status
from fastapi.responses import HTMLResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from youtube_transcript_api import YouTubeTranscriptApi, NoTranscriptFound, TranscriptsDisabled, VideoUnavailable

# Importar componentes locales
from .models import VideoRequest, TranscriptResponse, ErrorResponse
from .utils import extract_video_id
from .rate_limiter import rate_limiter

# Inicializar FastAPI
app = FastAPI(
    title="YouTube Transcript API Service",
    description="Obtiene transcripciones de videos de YouTube.",
    version="1.1.1" # Increment version
)

# Montar directorio estático (para JS)
app.mount("/static", StaticFiles(directory="static"), name="static")

# Configurar plantillas Jinja2 (para HTML)
templates = Jinja2Templates(directory="templates")

# --- Rutas ---

@app.get("/", response_class=HTMLResponse, summary="Muestra la interfaz principal")
async def read_root(request: Request):
    """
    Sirve el archivo index.html.
    """
    return templates.TemplateResponse("index.html", {"request": request})

@app.post(
    "/get_transcript",
    response_model=TranscriptResponse,
    responses={
        status.HTTP_400_BAD_REQUEST: {"model": ErrorResponse, "description": "Entrada inválida"},
        status.HTTP_404_NOT_FOUND: {"model": ErrorResponse, "description": "Video o transcripción no encontrada/deshabilitada"},
        status.HTTP_429_TOO_MANY_REQUESTS: {"model": ErrorResponse, "description": "Límite de tasa excedido"},
        status.HTTP_500_INTERNAL_SERVER_ERROR: {"model": ErrorResponse, "description": "Error interno del servidor"}
    },
    summary="Obtiene la transcripción de un video",
    dependencies=[Depends(rate_limiter)] # Aplicar el limitador de tasa a esta ruta
)
async def get_transcript(payload: VideoRequest):
    """
    Recibe una URL o ID de video, extrae la transcripción (priorizando es/en)
    y la devuelve junto con metadatos.
    """
    # -- Inicio de la lógica de la ruta --
    video_id = extract_video_id(payload.video_id)

    if not video_id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="ID o URL de video inválida proporcionada."
        )

    try:
        # Obtener la lista de transcripciones
        transcript_list = YouTubeTranscriptApi.list_transcripts(video_id)

        transcript = None
        preferred_langs = ['es', 'en'] # Prioridad de idiomas

        # Lógica mejorada para seleccionar la mejor transcripción
        found = False
        # 1. Buscar manual en idiomas preferidos
        try:
            transcript = transcript_list.find_manually_created_transcript(preferred_langs)
            found = True
        except NoTranscriptFound:
            pass # Continuar buscando

        # 2. Si no, buscar generada en idiomas preferidos
        if not found:
            try:
                transcript = transcript_list.find_generated_transcript(preferred_langs)
                found = True
            except NoTranscriptFound:
                pass # Continuar buscando

        # 3. Si no, buscar CUALQUIER manual (priorizando 'en' si existe entre ellas)
        if not found:
            try:
                manual_transcripts = [t for t in transcript_list if not t.is_generated]
                if manual_transcripts:
                    # Intentar encontrar 'en' dentro de las manuales si hay varias
                    en_manual = next((t for t in manual_transcripts if t.language_code == 'en'), None)
                    transcript = en_manual if en_manual else manual_transcripts[0] # Tomar 'en' o la primera manual
                    found = True
            except Exception:
                 pass # Error filtrando, continuar

        # 4. Si no, buscar CUALQUIER generada (priorizando 'en' si existe)
        if not found:
             try:
                generated_transcripts = [t for t in transcript_list if t.is_generated]
                if generated_transcripts:
                    en_generated = next((t for t in generated_transcripts if t.language_code == 'en'), None)
                    transcript = en_generated if en_generated else generated_transcripts[0] # Tomar 'en' o la primera generada
                    found = True
             except Exception:
                  pass # Error filtrando

        # Si después de todo no se encontró ninguna transcripción válida
        if not transcript:
             # Lanzar error específico para que el bloque except lo capture
             raise NoTranscriptFound(video_id=video_id, languages=preferred_langs, transcript_list=transcript_list)

        # Obtener el contenido de la transcripción seleccionada
        fetched_transcript = transcript.fetch()

        # Unir el texto (considerar reemplazar saltos de línea dobles por simples a veces)
        full_text = " ".join(item.text for item in fetched_transcript)

        return TranscriptResponse(
            transcript=full_text,
            language=transcript.language,
            language_code=transcript.language_code,
            is_generated=transcript.is_generated
        )

    # Manejo específico de excepciones de la API
    except TranscriptsDisabled:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Las transcripciones están deshabilitadas para el video ID: {video_id}"
        )
    except NoTranscriptFound:
         # Este error ahora captura todos los casos donde no se encontró transcripción
         raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"No se encontraron transcripciones adecuadas para el video ID: {video_id}"
        )
    except VideoUnavailable:
         raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"El video ID: {video_id} no está disponible, es privado o ha sido eliminado."
        )
    # Manejo de excepciones HTTP (como rate limit)
    except HTTPException as http_exc:
        raise http_exc # Re-lanzar para que FastAPI la maneje
    # Captura genérica para otros errores (problemas de red, etc.)
    except Exception as e:
        error_type = type(e).__name__
        print(f"Error inesperado procesando video ID {video_id}: {error_type} - {e}") # Loguear el error completo
        # Devolver un mensaje más útil al usuario sin exponer detalles internos sensibles
        error_detail = f"Ocurrió un error interno ({error_type}) al intentar obtener la transcripción. Por favor, inténtalo de nuevo más tarde."
        # Podrías añadir lógica aquí para diferenciar errores (ej. si es un error de red específico de youtube-transcript-api)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=error_detail
        )
    # -- Fin de la lógica de la ruta --


@app.get("/health", status_code=status.HTTP_200_OK, summary="Verifica el estado del servicio")
async def health_check():
    """Endpoint simple para verificar que el servicio está en línea."""
    return {"status": "ok"}

# --- Fin de Rutas ---
