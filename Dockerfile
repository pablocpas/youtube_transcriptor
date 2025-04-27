
# Usar una imagen base oficial de Python
FROM python:3.10-slim

# Establecer variables de entorno (previene que Python escriba archivos pyc y asegura salida inmediata)
ENV PYTHONDONTWRITEBYTECODE 1
ENV PYTHONUNBUFFERED 1

# Establecer el directorio de trabajo dentro del contenedor
WORKDIR /app

# Instalar dependencias
# Copiar primero requirements.txt para aprovechar el caché de capas de Docker
COPY requirements.txt .
RUN pip install --no-cache-dir --upgrade pip && \
    pip install --no-cache-dir -r requirements.txt

# Copiar el resto del código de la aplicación
COPY . .

# Exponer el puerto en el que correrá la aplicación (uvicorn por defecto usa 8000)
EXPOSE 8000

# Comando para ejecutar la aplicación usando uvicorn
# Escucha en 0.0.0.0 para ser accesible desde fuera del contenedor
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
