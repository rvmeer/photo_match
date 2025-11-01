from fastapi import FastAPI, File, UploadFile, HTTPException
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse, JSONResponse
from fastapi.middleware.cors import CORSMiddleware
import os
import shutil
from pathlib import Path
import cv2
import numpy as np

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

# Referentie foto voor vergelijking
REFERENCE_IMAGE = Path(".") / "orgineel.png"

def compare_images(image_path1: Path, image_path2: Path, threshold: float = 0.85) -> bool:
    """
    Vergelijk twee afbeeldingen met behulp van verschillende OpenCV technieken.
    Retourneert True als de afbeeldingen overeenkomen.
    """
    try:
        # Lees beide afbeeldingen
        img1 = cv2.imread(str(image_path1))
        img2 = cv2.imread(str(image_path2))

        if img1 is None or img2 is None:
            return False

        # Resize beide images naar dezelfde grootte voor vergelijking
        height, width = 500, 500
        img1_resized = cv2.resize(img1, (width, height))
        img2_resized = cv2.resize(img2, (width, height))

        # Methode 1: Structural Similarity Index (SSIM)
        # Convert naar grayscale
        gray1 = cv2.cvtColor(img1_resized, cv2.COLOR_BGR2GRAY)
        gray2 = cv2.cvtColor(img2_resized, cv2.COLOR_BGR2GRAY)

        # Bereken Mean Squared Error
        mse = np.mean((gray1.astype(float) - gray2.astype(float)) ** 2)

        # Als MSE laag is, zijn de afbeeldingen vergelijkbaar
        # Normaliseer MSE naar similarity score (0-1)
        similarity = 1 / (1 + mse / 1000)

        # Methode 2: Histogram vergelijking
        hist1 = cv2.calcHist([img1_resized], [0, 1, 2], None, [8, 8, 8], [0, 256, 0, 256, 0, 256])
        hist2 = cv2.calcHist([img2_resized], [0, 1, 2], None, [8, 8, 8], [0, 256, 0, 256, 0, 256])

        hist1 = cv2.normalize(hist1, hist1).flatten()
        hist2 = cv2.normalize(hist2, hist2).flatten()

        hist_similarity = cv2.compareHist(hist1, hist2, cv2.HISTCMP_CORREL)

        # Combineer beide scores
        combined_score = (similarity * 0.5) + (hist_similarity * 0.5)

        print(f"Similarity score: {similarity:.3f}, Histogram similarity: {hist_similarity:.3f}, Combined: {combined_score:.3f}")

        return combined_score >= threshold

    except Exception as e:
        print(f"Error comparing images: {e}")
        return False

@app.post("/api/upload")
async def upload_photo(file: UploadFile = File(...)):
    """Upload een foto met de originele bestandsnaam en vergelijk met orgineel.png"""
    try:
        # Valideer dat het een image is
        if not file.content_type.startswith("image/"):
            raise HTTPException(status_code=400, detail="File must be an image")

        # Sla op met de originele bestandsnaam in de uploads folder
        file_path = UPLOAD_DIR / file.filename

        with open(file_path, "wb") as buffer:
            shutil.copyfileobj(file.file, buffer)

        # Vergelijk de geüploade foto met orgineel.png
        is_match = False
        result_message = ""

        if REFERENCE_IMAGE.exists():
            is_match = compare_images(file_path, REFERENCE_IMAGE)

            if is_match:
                result_message = "Gefeliciteerd, je hebt de puzzel opgelost, de code is: 196"
            else:
                result_message = "Helaas, de puzzel is nog niet goed opgelost, probeer het nogmaals en upload een nieuwe foto"
        else:
            result_message = "Referentie afbeelding niet gevonden"

        return JSONResponse(content={
            "message": "File uploaded successfully",
            "filename": file.filename,
            "match": bool(is_match),
            "result": result_message
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
    import os

    # Port kan worden ingesteld via environment variabele (standaard 8080)
    port = int(os.getenv("PORT", "8080"))
    uvicorn.run(app, host="0.0.0.0", port=port)
