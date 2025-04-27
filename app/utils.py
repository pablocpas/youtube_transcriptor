
import re
from urllib.parse import urlparse, parse_qs

def extract_video_id(url_or_id: str) -> str | None:
    """Extrae el Video ID de una URL de YouTube o devuelve el ID si ya es uno."""
    if not isinstance(url_or_id, str):
        return None

    url_or_id = url_or_id.strip()

    # Regex para un ID de YouTube estándar (11 caracteres alfanuméricos más - y _)
    youtube_id_pattern = r"^[a-zA-Z0-9_-]{11}$"
    if re.match(youtube_id_pattern, url_or_id):
        return url_or_id

    # Intenta parsear como URL
    try:
        parsed_url = urlparse(url_or_id)
        if 'youtube.com' in parsed_url.netloc:
            query_params = parse_qs(parsed_url.query)
            if 'v' in query_params and re.match(youtube_id_pattern, query_params['v'][0]):
                return query_params['v'][0]
            # Manejar URLs como youtube.com/embed/VIDEO_ID o youtube.com/shorts/VIDEO_ID
            path_parts = [part for part in parsed_url.path.split('/') if part]
            if len(path_parts) > 0 and re.match(youtube_id_pattern, path_parts[-1]):
                 if len(path_parts) == 1 and re.match(youtube_id_pattern, path_parts[0]): # Ej: youtube.com/VIDEOID
                      return path_parts[0]
                 if len(path_parts) > 1 and path_parts[-2] in ['watch', 'embed', 'shorts']: # Ej: youtube.com/[watch|embed|shorts]/VIDEOID
                      return path_parts[-1]


        elif 'youtu.be' in parsed_url.netloc:
            video_id_part = parsed_url.path.lstrip('/')
            if re.match(youtube_id_pattern, video_id_part):
                return video_id_part
    except Exception:
        return None

    return None
