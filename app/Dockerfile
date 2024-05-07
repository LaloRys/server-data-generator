# Usa una imagen base de Python
FROM python:3.8-slim

# Establece el directorio de trabajo dentro del contenedor
WORKDIR /app

# Copia los archivos de la aplicación al contenedor
COPY ./app /app

# Instala las dependencias de la aplicación
RUN pip install -r /app/requirements.txt

# Comando para ejecutar la aplicación cuando se inicie el contenedor
CMD ["python", "/app/main.py"]

# Expone el puerto en el que la aplicación se ejecuta
EXPOSE 8000
