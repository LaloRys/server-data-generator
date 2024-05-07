# Usa una imagen base de Python
FROM python:3.9

# Establece el directorio de trabajo dentro del contenedor
WORKDIR /app

# Copia los archivos de la aplicación al contenedor
COPY ./app /app

# Instala las dependencias de la aplicación
RUN pip install -r /app/requirements.txt

# Define las variables de entorno HOST y PORT
ENV HOST=0.0.0.0
ENV API_URL=https://location-data-generator.vercel.app

# ENV PORT=8000

# Comando para ejecutar la aplicación cuando se inicie el contenedor
CMD ["python", "/app/main.py"]