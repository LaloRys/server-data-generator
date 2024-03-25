from fastapi import FastAPI, HTTPException, File, UploadFile, Form
from pydantic import BaseModel
from secrets import token_hex
from typing import Text, Optional
from datetime import datetime
from uuid import uuid4 as uuid
from fastapi.middleware.cors import CORSMiddleware
import uvicorn
from fastapi.responses import JSONResponse, FileResponse
import pandas as pd
import requests
import os
from dotenv import load_dotenv

load_dotenv()

app = FastAPI(title="Procesador de datos")

# Obtener el valor de API_URL de las variables de entorno
api_url = os.getenv("API_URL")

# Si API_URL no está definida, usa http://localhost:3000
if api_url is None:
    api_url = "http://localhost:3000"

app.add_middleware(
    CORSMiddleware,
    allow_origins=[api_url],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

posts = [
    {
        "id": "1",
        "title": "Post 1",
        "content": "Content 1",
    }
]

UPLOADS_FOLDER = "uploads"

class Post(BaseModel):
    id: str | None = None
    title: str
    author: str
    content: Text
    create_at: datetime = datetime.now()
    published_at: datetime = None
    published: bool = False

@app.get("/")
async def root():
    return {"message": "Hello World"}


@app.get("/hello/{name}")
async def say_hello(name: str):
    return {"saludo": f'Hola {name}'}


@app.get("/posts")
async def get_posts():
    return {"data": posts}


@app.post("/posts", response_model=Post)
async def create_posts(post: Post):
    try:
        post.id = str(uuid())
        posts.append(post.dict())
        return post
    except Exception as e:
        print(f"Error: {e}")
        raise


@app.get("/posts/{id}")
async def get_post(id: str):
    for post in posts:
        if post["id"] == id:
            return {"data": post}
    # return {"data": "Not found"}
    raise HTTPException(status_code=404, detail="Post not found")


@app.delete("/posts/{id}")
async def delete_post(id: str):
    for post in posts:
        if post["id"] == id:
            posts.remove(post)
            return {"data": "Post deleted"}
    raise HTTPException(status_code=404, detail="Post not found")


@app.put("/posts/{id}")
async def update_post(post_id: str, updatePost: Post):
    for index, post in enumerate(posts):
        if post["id"] == post_id:
            posts[index]["title"] = updatePost.title
            posts[index]["content"] = updatePost.content
            posts[index]["author"] = updatePost.author
            return {"data": "Post updated",
                    "post": posts[index]
                    }             
    raise HTTPException(status_code=404, detail="Post not found")


# Conjunto para almacenar elevaciones ya procesadas

elevaciones_procesadas = {}


@app.post("/elevationapi/")
async def upload(api_key: str = Form(...), file: UploadFile = File(...)):
    api_key_elevacion = api_key
    print(f"Received API Key: {api_key_elevacion}")

    try:
        file_ext = file.filename.split(".").pop()
        file_name = uuid()
        # file_path = os.path.join(UPLOADS_FOLDER, f"{file_name}.{file_ext}")
        file_path = f"{file_name}.{file_ext}"
        
        
        with open(file_path, "wb") as f:
            content = await file.read()
            f.write(content)

        df_procesado = process_excel_file_elevation(file_path, api_key_elevacion)

        # save_data_processing_path = os.path.join(UPLOADS_FOLDER, f"{file_name}_processed_elevation.{file_ext}")
        
        nuevo_nombre = f"{file_name}_processed_elevation.{file_ext}"
        df_procesado.to_excel(nuevo_nombre, index=False)

        return JSONResponse(content={"success": True, "file_path": nuevo_nombre, "message": "File uploaded and processed successfully"})
    
    except Exception as e:
        print(f"Error during file upload and processing: {e}")
        raise HTTPException(status_code=500, detail="Internal Server Error")

def obtener_elevacion(lat, lon, api_key):
    url = f'https://maps.googleapis.com/maps/api/elevation/json?locations={lat},{lon}&key={api_key}'
    response = requests.get(url)
    
    if response.status_code == 200:
        data = response.json()
        if data['status'] == 'OK' and data['results']:
            return data['results'][0]['elevation']
    
    return None

def process_excel_file_elevation(ruta_archivo, api_key_elevacion):
    df = pd.read_excel(ruta_archivo)

    for index, row in df.iterrows():
        latitud = row['latitude']
        longitud = row['longitude']
        print(f"Datos en: {elevaciones_procesadas}")

        if pd.notnull(latitud) and pd.notnull(longitud):
            if (latitud, longitud) in elevaciones_procesadas:
                elevacion = elevaciones_procesadas[(latitud, longitud)]
                df.at[index, 'elevation'] = elevacion
            else:
                elevacion = obtener_elevacion(latitud, longitud, api_key_elevacion)
                if elevacion is not None:
                    df.at[index, 'elevation'] = elevacion
                    elevaciones_procesadas[(latitud, longitud)] = elevacion

    return df

@app.post("/opencage/")
async def opencage(api_key: str = Form(...), file: UploadFile = File(...)):
    print(f"Received API Key: {api_key}")
    
    try:
        file_ext = file.filename.split(".").pop()
        file_name = uuid()
        # file_path = os.path.join(UPLOADS_FOLDER, f"{file_name}.{file_ext}")
        file_path = f"{file_name}.{file_ext}"

        with open(file_path, "wb") as f:
            content = await file.read()
            f.write(content)
        
        df_procesado = process_excel_file_opencage(file_path, api_key)
        
        # save_data_processing_path =os.path.join(UPLOADS_FOLDER, f"{file_name}_processed_OpenCage.{file_ext}")
        
        nuevo_nombre = f"{file_name}_processed_OpenCage.{file_ext}"
        df_procesado.to_excel(nuevo_nombre, index=False)
        
        return JSONResponse(content={"success": True, "file_path": nuevo_nombre, "message": "File uploaded and processed successfully"})
      
    except Exception as e:
        print(f"Error during file upload and processing: {e}")
        raise HTTPException(status_code=500, detail="Internal Server Error")
    
def process_excel_file_opencage(file_path, api_key):
        ubicaciones_oc_consultadas = {}
        claves_ubicacion = ['village', 'town', 'county', 'city', 'province', 'state', 'region', 'district', 'country']

        df = pd.read_excel(file_path)

        for index, row in df.iterrows():
            latitud = row['latitude']
            longitud = row['longitude']

            # Obtener el nombre de la ubicación
            nombre_ubicacion = obtener_nombre_ubicacion_opencage(latitud, longitud, ubicaciones_oc_consultadas, api_key)

            # Inicializar una lista para almacenar las ubicaciones
            ubicaciones = []

            # Iterar sobre las claves y agregar las partes de la ubicación a la lista
            for clave in claves_ubicacion:
                ubicacion_parte = nombre_ubicacion.get(clave, '')
                if ubicacion_parte:
                    ubicaciones.append(ubicacion_parte)

            # Combinar las partes de la ubicación en una sola cadena
            ubicacion_formateada = ', '.join(ubicaciones).rstrip(', ')

            # Verificar si la ubicación está disponible
            if ubicacion_formateada:
                for clave in claves_ubicacion:
                    df.at[index, clave.capitalize()] = nombre_ubicacion[clave]
                df.at[index, 'Ubicacion'] = ubicacion_formateada
                df.at[index, 'Alpha-3'] = nombre_ubicacion['alpha-3']
                df.at[index, 'Url(open street map)'] = nombre_ubicacion['url']
            else:
                print('Ubicación no disponible')

        return df

def obtener_nombre_ubicacion_opencage(lat, lon, ubicaciones_oc_consultadas, api_key):
    
    coordenadas = (lat, lon)
    if coordenadas in ubicaciones_oc_consultadas:
        # Si las coordenadas ya se han consultado, devuelve la información almacenada previamente.
        return ubicaciones_oc_consultadas[coordenadas]
    
    url = f'https://api.opencagedata.com/geocode/v1/json?key={api_key}&q={lat},{lon}&language=en'
    response = requests.get(url)

    if response.status_code == 200:
        data = response.json()
        if data['results']:
            components = data['results'][0].get('components', {})
            
            # Definir las claves de ubicación que deseas extraer
            claves_ubicacion = ['village', 'town', 'county', 'city', 'province', 'state', 'region', 'district', 'country']
            
            info_ubicacion = {}
            for clave in claves_ubicacion:
                info_ubicacion[clave] = components.get(clave, '')

            info_ubicacion['alpha-3'] = components.get('ISO_3166-1_alpha-3', '')
            info_ubicacion['url'] = data['results'][0]['annotations']['OSM']['url']
            ubicaciones_oc_consultadas[coordenadas] = info_ubicacion
            return info_ubicacion
        else:
            print("Alerta: Ubicacion desconocida")
            raise HTTPException(status_code=500, detail="Internal Server Error")
    else:
        print("Error: Error al consultar la API de OpenCage")
        raise HTTPException(status_code=500, detail="Internal Server Error")
    

@app.post("/googlegeocoding/")
async def googlegeocoding(api_key: str = Form(...), file: UploadFile = File(...)):
    print(f"Received API Key: {api_key}")
    
    try:
        file_ext = file.filename.split(".").pop()
        file_name = uuid()
        # file_path = os.path.join(UPLOADS_FOLDER, f"{file_name}.{file_ext}")
        file_path = f"{file_name}.{file_ext}"
        with open(file_path, "wb") as f:
            content = await file.read()
            f.write(content)

        df_procesado = process_excel_file_google(file_path, api_key)

        # save_data_processing_path =os.path.join(UPLOADS_FOLDER, f"{file_name}_processed_GoogleGeocoding.{file_ext}")

        nuevo_nombre = f"{file_name}_processed_GoogleGeocoding.{file_ext}"
        df_procesado.to_excel(nuevo_nombre, index=False)

        return JSONResponse(content={"success": True, "file_path": nuevo_nombre, "message": "File uploaded and processed successfully"})
    
    except Exception as e:
        print(f"Error during file upload and processing: {e}")
        raise HTTPException(status_code=500, detail="Internal Server Error")


def process_excel_file_google(ruta_archivo, api_key):
    df = pd.read_excel(ruta_archivo)
    coordenadas_procesadas_google = {}

    for index, row in df.iterrows():
        latitud = row['latitude']
        longitud = row['longitude']

        if pd.notnull(latitud) and pd.notnull(longitud):
            if (latitud, longitud) in coordenadas_procesadas_google:
                direcciones = coordenadas_procesadas_google[(latitud, longitud)]
                for i, direccion in enumerate(direcciones):
                    df.at[index, f'formatted_address{i+1}'] = direccion
            else:
                nombres_ubicacion = obtener_nombre_ubicacion_google(latitud, longitud, api_key)

                if nombres_ubicacion:
                    for i, direccion in enumerate(nombres_ubicacion[:5]):
                        df.at[index, f'formatted_address{i+1}'] = direccion
                    coordenadas_procesadas_google[(latitud, longitud)] = nombres_ubicacion

    return df
  
def obtener_nombre_ubicacion_google(lat, lon, api_key):
    url = f'https://maps.googleapis.com/maps/api/geocode/json?latlng={lat},{lon}&key={api_key}'

    response = requests.get(url)

    if response.status_code == 200:
        data = response.json()
        direcciones = []
        if data['results']:
            for i in range(5):
                if i < len(data['results']):
                    direcciones.append(data['results'][i].get('formatted_address', ''))
                else:
                    direcciones.append('')  # Agrega un espacio en blanco si no hay dirección disponible
            return direcciones
        else:
            return ['Ubicación desconocida'] * 5
    else:
        # Devolvemos 5 errores
        return ['Error al consultar la API de Google'] * 5


@app.get("/download/{file_name}")
async def download(file_name: str):
    # file_path = os.path.join(UPLOADS_FOLDER, file_name)
    # print(file_path)

    # Asegúrate de que el archivo exista antes de intentar enviarlo
    if not os.path.exists(file_name):
        raise HTTPException(status_code=404, detail="File not found")
    
    # Usa FileResponse para enviar el archivo al cliente
    return FileResponse(file_name, filename=file_name)


    df = pd.read_excel(ruta_archivo)

    for index, row in df.iterrows():
        latitud = row['latitude']
        longitud = row['longitude']

        if pd.notnull(latitud) and pd.notnull(longitud):
            if (latitud, longitud) in coordenadas_procesadas:
                direcciones = coordenadas_procesadas[(latitud, longitud)]
                for i, direccion in enumerate(direcciones):
                    df.at[index, f'formatted_address{i+1}'] = direccion
            else:
                nombres_ubicacion = obtener_nombre_ubicacion(latitud, longitud, api_key)

                if nombres_ubicacion:
                    for i, direccion in enumerate(nombres_ubicacion[:5]):
                        df.at[index, f'formatted_address{i+1}'] = direccion
                    coordenadas_procesadas[(latitud, longitud)] = nombres_ubicacion

    return df


host = os.getenv("HOST", "127.0.0.1")
port = int(os.getenv("PORT", 8000))

if __name__ == "__main__":
    uvicorn.run("main:app", host=host, port=port, reload=True)