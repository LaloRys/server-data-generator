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

origins = ["http://localhost:3000"]  # Agrega aquí la URL de tu frontend
app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
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

# Post Model


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


@app.post("/uploadfile/")
async def upload(api_key: str = Form(...), file: UploadFile = File(...)):
    api_key_elevacion = api_key
    print(f"Received API Key: {api_key_elevacion}")

    try:
        file_ext = file.filename.split(".").pop()
        file_name = uuid()
        file_path = f"{file_name}.{file_ext}"
        
        with open(file_path, "wb") as f:
            content = await file.read()
            f.write(content)

        df_procesado = procesar_archivo_excel(file_path, api_key_elevacion)

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

def procesar_archivo_excel(ruta_archivo, api_key_elevacion):
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

@app.get("/download/{file_path}")
async def download(file_path: str):
    # Asegúrate de que el archivo exista antes de intentar enviarlo
    if not os.path.exists(file_path):
        raise HTTPException(status_code=404, detail="File not found")
    
    # Usa FileResponse para enviar el archivo al cliente
    return FileResponse(file_path, filename=file_path)

host = os.getenv("HOST", "127.0.0.1")
port = int(os.getenv("PORT", 8000))

if __name__ == "__main__":
    uvicorn.run("main:app", host=host, port=port, reload=True)