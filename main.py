from fastapi import FastAPI, File, UploadFile, HTTPException
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse, JSONResponse
from fastapi.middleware.cors import CORSMiddleware
import os
import shutil
from pathlib import Path

app = FastAPI()

# CORS configuratie voor development
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Huidige directory voor foto opslag
UPLOAD_DIR = Path(".") / "uploads"
UPLOAD_DIR.mkdir(parents=True, exist_ok=True)

@app.post("/api/upload")
async def upload_photo(file: UploadFile = File(...)):
    """Upload een foto met de originele bestandsnaam"""
    try:
        # Valideer dat het een image is
        if not file.content_type.startswith("image/"):
            raise HTTPException(status_code=400, detail="File must be an image")

        # Sla op met de originele bestandsnaam in de uploads folder
        file_path = UPLOAD_DIR / file.filename

        with open(file_path, "wb") as buffer:
            shutil.copyfileobj(file.file, buffer)

        return JSONResponse(content={
            "message": "File uploaded successfully",
            "filename": file.filename
        })

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/photo")
async def get_photo():
    """Haal de laatst geüploade foto op uit uploads folder"""
    # Vind alle image files in de uploads directory
    image_extensions = {'.jpg', '.jpeg', '.png', '.gif', '.bmp', '.webp'}
    image_files = [
        f for f in UPLOAD_DIR.iterdir()
        if f.is_file() and f.suffix.lower() in image_extensions
    ]

    if not image_files:
        raise HTTPException(status_code=404, detail="No photos found")

    # Sorteer op modification time en pak de meest recente
    latest_file = max(image_files, key=lambda f: f.stat().st_mtime)

    return FileResponse(latest_file)

# Serveer de React build directory
app.mount("/", StaticFiles(directory="build", html=True), name="static")

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8080)
