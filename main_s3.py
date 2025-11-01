"""
Alternative main.py met S3 support voor AWS deployment
Gebruik dit voor production op AWS
"""
from fastapi import FastAPI, File, UploadFile, HTTPException
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse, JSONResponse, StreamingResponse
from fastapi.middleware.cors import CORSMiddleware
import os
import shutil
from pathlib import Path
import cv2
import numpy as np
import boto3
from io import BytesIO
import tempfile

app = FastAPI()

# CORS configuratie
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# S3 Configuration
USE_S3 = os.getenv("USE_S3", "false").lower() == "true"
S3_BUCKET = os.getenv("S3_BUCKET", "photo-match-uploads")
AWS_REGION = os.getenv("AWS_REGION", "eu-west-1")

# Local directory voor foto opslag (fallback)
UPLOAD_DIR = Path(".") / "uploads"
UPLOAD_DIR.mkdir(parents=True, exist_ok=True)

# Referentie foto voor vergelijking
REFERENCE_IMAGE = Path(".") / "orgineel.JPG"

# S3 client (alleen als S3 enabled)
s3_client = None
if USE_S3:
    s3_client = boto3.client('s3', region_name=AWS_REGION)

def save_file(file_content: bytes, filename: str) -> str:
    """Save file to S3 or local filesystem"""
    if USE_S3 and s3_client:
        # Upload to S3
        s3_client.put_object(
            Bucket=S3_BUCKET,
            Key=f"uploads/{filename}",
            Body=file_content,
            ContentType='image/jpeg'
        )
        return f"s3://{S3_BUCKET}/uploads/{filename}"
    else:
        # Save locally
        file_path = UPLOAD_DIR / filename
        with open(file_path, 'wb') as f:
            f.write(file_content)
        return str(file_path)

def get_file(filename: str) -> bytes:
    """Get file from S3 or local filesystem"""
    if USE_S3 and s3_client:
        # Download from S3
        response = s3_client.get_object(
            Bucket=S3_BUCKET,
            Key=f"uploads/{filename}"
        )
        return response['Body'].read()
    else:
        # Read locally
        file_path = UPLOAD_DIR / filename
        with open(file_path, 'rb') as f:
            return f.read()

def list_uploaded_files():
    """List all uploaded files"""
    if USE_S3 and s3_client:
        # List from S3
        response = s3_client.list_objects_v2(
            Bucket=S3_BUCKET,
            Prefix='uploads/'
        )
        if 'Contents' not in response:
            return []
        return [obj['Key'].replace('uploads/', '') for obj in response['Contents']]
    else:
        # List locally
        image_extensions = {'.jpg', '.jpeg', '.png', '.gif', '.bmp', '.webp'}
        return [f.name for f in UPLOAD_DIR.iterdir()
                if f.is_file() and f.suffix.lower() in image_extensions]

def compare_images(image_bytes1: bytes, image_bytes2: bytes, threshold: float = 0.85) -> bool:
    """
    Vergelijk twee afbeeldingen met behulp van verschillende OpenCV technieken.
    Retourneert True als de afbeeldingen overeenkomen.
    """
    try:
        # Convert bytes to numpy arrays
        nparr1 = np.frombuffer(image_bytes1, np.uint8)
        nparr2 = np.frombuffer(image_bytes2, np.uint8)

        img1 = cv2.imdecode(nparr1, cv2.IMREAD_COLOR)
        img2 = cv2.imdecode(nparr2, cv2.IMREAD_COLOR)

        if img1 is None or img2 is None:
            return False

        # Resize beide images naar dezelfde grootte voor vergelijking
        height, width = 500, 500
        img1_resized = cv2.resize(img1, (width, height))
        img2_resized = cv2.resize(img2, (width, height))

        # Methode 1: Convert naar grayscale en bereken MSE
        gray1 = cv2.cvtColor(img1_resized, cv2.COLOR_BGR2GRAY)
        gray2 = cv2.cvtColor(img2_resized, cv2.COLOR_BGR2GRAY)

        mse = np.mean((gray1.astype(float) - gray2.astype(float)) ** 2)
        similarity = 1 / (1 + mse / 1000)

        # Methode 2: Histogram vergelijking
        hist1 = cv2.calcHist([img1_resized], [0, 1, 2], None, [8, 8, 8], [0, 256, 0, 256, 0, 256])
        hist2 = cv2.calcHist([img2_resized], [0, 1, 2], None, [8, 8, 8], [0, 256, 0, 256, 0, 256])

        hist1 = cv2.normalize(hist1, hist1).flatten()
        hist2 = cv2.normalize(hist2, hist2).flatten()

        hist_similarity = cv2.compareHist(hist1, hist2, cv2.HISTCMP_CORREL)

        # Combineer beide scores
        combined_score = (similarity * 0.5) + (hist_similarity * 0.5)

        print(f"Similarity: {similarity:.3f}, Histogram: {hist_similarity:.3f}, Combined: {combined_score:.3f}")

        return combined_score >= threshold

    except Exception as e:
        print(f"Error comparing images: {e}")
        return False

@app.post("/api/upload")
async def upload_photo(file: UploadFile = File(...)):
    """Upload een foto met de originele bestandsnaam en vergelijk met orgineel.JPG"""
    try:
        # Valideer dat het een image is
        if not file.content_type.startswith("image/"):
            raise HTTPException(status_code=400, detail="File must be an image")

        # Read file content
        file_content = await file.read()

        # Sla op met de originele bestandsnaam
        save_file(file_content, file.filename)

        # Vergelijk de geüploade foto met orgineel.JPG
        is_match = False
        result_message = ""

        if REFERENCE_IMAGE.exists():
            with open(REFERENCE_IMAGE, 'rb') as ref_file:
                ref_content = ref_file.read()

            is_match = compare_images(file_content, ref_content)

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
            "result": result_message,
            "storage": "s3" if USE_S3 else "local"
        })

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/photo")
async def get_photo():
    """Haal de laatst geüploade foto op"""
    try:
        files = list_uploaded_files()

        if not files:
            raise HTTPException(status_code=404, detail="No photos found")

        # Get laatste file (voor S3 moet je LastModified gebruiken)
        latest_file = files[-1]  # Simpele implementatie

        file_content = get_file(latest_file)

        return StreamingResponse(
            BytesIO(file_content),
            media_type="image/jpeg"
        )

    except Exception as e:
        raise HTTPException(status_code=404, detail=str(e))

# Serveer de React build directory
app.mount("/", StaticFiles(directory="build", html=True), name="static")

if __name__ == "__main__":
    import uvicorn
    port = int(os.getenv("PORT", "8080"))
    uvicorn.run(app, host="0.0.0.0", port=port)
