from fastapi import FastAPI, Request
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
from routers.api_router import api_router

app = FastAPI()

@app.get("/")
async def render_html_for_permissions(req : Request) : 
    return FileResponse('client/build/index.html')

#api endpoints
app.include_router(router=api_router, prefix="/api")


#render the frontend of the application

app.mount("/",StaticFiles(directory="client/build"),name="frontend")