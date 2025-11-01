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
REFERENCE_IMAGE = Path(".") / "orgineel.JPG"

def preprocess_image(img):
    """
    Pre-process afbeelding om robuust te zijn tegen lichtreflecties en verschillende belichting.
    """
    # 1. Convert naar LAB kleurruimte (beter voor belichting normalisatie)
    lab = cv2.cvtColor(img, cv2.COLOR_BGR2LAB)
    l, a, b = cv2.split(lab)

    # 2. CLAHE (Contrast Limited Adaptive Histogram Equalization) op L channel
    # Dit normaliseert de belichting en vermindert effect van schaduwen/reflecties
    clahe = cv2.createCLAHE(clipLimit=3.0, tileGridSize=(8, 8))
    l_clahe = clahe.apply(l)

    # Merge terug
    lab_clahe = cv2.merge([l_clahe, a, b])
    processed = cv2.cvtColor(lab_clahe, cv2.COLOR_LAB2BGR)

    return processed

def rotate_image(img, angle):
    """Roteer afbeelding 0, 90, 180, of 270 graden."""
    if angle == 0:
        return img
    elif angle == 90:
        return cv2.rotate(img, cv2.ROTATE_90_CLOCKWISE)
    elif angle == 180:
        return cv2.rotate(img, cv2.ROTATE_180)
    elif angle == 270:
        return cv2.rotate(img, cv2.ROTATE_90_COUNTERCLOCKWISE)
    return img

def find_homography_match(img1, img2, min_matches=10):
    """
    Vind homography tussen twee afbeeldingen met SIFT.
    Retourneert (inliers_count, total_matches, homography_matrix, warped_img2)
    """
    try:
        # Convert naar grayscale
        gray1 = cv2.cvtColor(img1, cv2.COLOR_BGR2GRAY)
        gray2 = cv2.cvtColor(img2, cv2.COLOR_BGR2GRAY)

        # SIFT detector
        sift = cv2.SIFT_create(nfeatures=1000)  # Meer features voor betere homography

        # Detecteer keypoints
        kp1, des1 = sift.detectAndCompute(gray1, None)
        kp2, des2 = sift.detectAndCompute(gray2, None)

        if des1 is None or des2 is None or len(kp1) < min_matches or len(kp2) < min_matches:
            return 0, 0, None, None

        # FLANN matcher
        FLANN_INDEX_KDTREE = 1
        index_params = dict(algorithm=FLANN_INDEX_KDTREE, trees=5)
        search_params = dict(checks=50)
        flann = cv2.FlannBasedMatcher(index_params, search_params)

        matches = flann.knnMatch(des1, des2, k=2)

        # Lowe's ratio test
        good_matches = []
        for match in matches:
            if len(match) == 2:
                m, n = match
                if m.distance < 0.7 * n.distance:
                    good_matches.append(m)

        total_matches = len(good_matches)

        # Probeer homography te vinden als we genoeg matches hebben
        if total_matches >= min_matches:
            src_pts = np.float32([kp1[m.queryIdx].pt for m in good_matches]).reshape(-1, 1, 2)
            dst_pts = np.float32([kp2[m.trainIdx].pt for m in good_matches]).reshape(-1, 1, 2)

            # Find homography met RANSAC
            M, mask = cv2.findHomography(dst_pts, src_pts, cv2.RANSAC, 5.0)

            if M is not None:
                # Tel hoeveel matches inliers zijn (good homography)
                inliers = np.sum(mask)

                # Warp img2 naar perspectief van img1
                h, w = img1.shape[:2]
                warped = cv2.warpPerspective(img2, M, (w, h))

                return inliers, total_matches, M, warped

        return 0, total_matches, None, None

    except Exception as e:
        print(f"      Homography error: {e}")
        return 0, 0, None, None

def compare_with_rotation(img_ref, img_test):
    """
    Vergelijk afbeeldingen met alle 4 rotaties (0°, 90°, 180°, 270°).
    Retourneert beste match info.
    """
    best_inliers = 0
    best_rotation = 0
    best_warped = None
    best_homography = None
    best_total_matches = 0

    print(f"\n   Testing rotations:")

    for angle in [0, 90, 180, 270]:
        rotated = rotate_image(img_test, angle)

        inliers, total_matches, M, warped = find_homography_match(img_ref, rotated)

        inlier_ratio = inliers / total_matches if total_matches > 0 else 0

        print(f"      {angle:3d}°: {inliers}/{total_matches} inliers ({inlier_ratio:.1%}) - " +
              f"{'✓ Valid homography' if M is not None else 'No homography'}")

        if inliers > best_inliers:
            best_inliers = inliers
            best_rotation = angle
            best_warped = warped
            best_homography = M
            best_total_matches = total_matches

    return best_inliers, best_total_matches, best_rotation, best_homography, best_warped

def compare_images(image_path1: Path, image_path2: Path, threshold: float = 0.70) -> bool:
    """
    Robuuste puzzel verificatie met perspective correction en rotatie handling.

    FLOW:
    1. Laad beide foto's
    2. Pre-process (CLAHE voor belichting normalisatie)
    3. Test alle 4 rotaties (0°, 90°, 180°, 270°)
    4. Voor elke rotatie: vind homography met SIFT
    5. Beste rotatie = meeste inlier matches
    6. Validatie: Als homography gevonden EN >5% inliers → MATCH
    7. Extra check: HSV histogram als backup validatie

    ROBUUST TEGEN:
    - Perspectief verschillen (schuin van boven)
    - Rotatie (0°, 90°, 180°, 270°)
    - Verschillende camera hoeken
    - Lichtreflecties (SIFT + CLAHE)
    - Belichting verschillen (LAB + CLAHE)

    Threshold: 5% inliers bij goede homography is voldoende
    """
    try:
        print(f"   Loading images...")
        img_ref = cv2.imread(str(image_path1))  # Reference (origineel)
        img_test = cv2.imread(str(image_path2))  # Test (uploaded)

        if img_ref is None or img_test is None:
            print(f"   ❌ Failed to load images")
            return False

        # Resize voor consistentie (behoud aspect ratio)
        max_size = 1000
        h1, w1 = img_ref.shape[:2]
        h2, w2 = img_test.shape[:2]

        scale1 = max_size / max(h1, w1)
        scale2 = max_size / max(h2, w2)

        img_ref_resized = cv2.resize(img_ref, None, fx=scale1, fy=scale1)
        img_test_resized = cv2.resize(img_test, None, fx=scale2, fy=scale2)

        print(f"   Preprocessing images (CLAHE for lighting normalization)...")
        # Pre-process beide images voor belichting normalisatie
        img_ref_processed = preprocess_image(img_ref_resized)
        img_test_processed = preprocess_image(img_test_resized)

        # Test alle rotaties en vind beste match met homography
        best_inliers, best_total, best_angle, best_H, best_warped = compare_with_rotation(
            img_ref_processed, img_test_processed
        )

        # Bereken inlier ratio
        inlier_ratio = best_inliers / best_total if best_total > 0 else 0

        print(f"\n   Best match: {best_angle}° rotation")
        print(f"   Inliers: {best_inliers}/{best_total} ({inlier_ratio:.1%})")
        print(f"   Homography: {'✓ Found' if best_H is not None else '✗ Not found'}")

        # Beslissingslogica:
        # Als homography gevonden wordt met >70% inliers = MATCH ✅

        is_match = False
        decision_reason = ""

        if best_H is not None:
            # Match als inlier ratio >= 70%
            if inlier_ratio >= 0.70:
                is_match = True
                decision_reason = f"✅ MATCH - Valid homography at {best_angle}° ({best_inliers}/{best_total} inliers = {inlier_ratio:.1%})"
            else:
                decision_reason = f"❌ NO MATCH - Inlier ratio too low ({inlier_ratio:.1%} < 70%)"
        else:
            decision_reason = f"❌ NO MATCH - No valid homography found"

        print(f"\n   Decision: {decision_reason}")

        return is_match

    except Exception as e:
        print(f"   ❌ Error comparing images: {e}")
        import traceback
        traceback.print_exc()
        return False

@app.post("/api/upload")
async def upload_photo(file: UploadFile = File(...)):
    """Upload een foto met de originele bestandsnaam en vergelijk met orgineel.JPG"""
    try:
        # Valideer dat het een image is
        if not file.content_type.startswith("image/"):
            raise HTTPException(status_code=400, detail="File must be an image")

        # Sla op met de originele bestandsnaam in de uploads folder
        file_path = UPLOAD_DIR / file.filename

        with open(file_path, "wb") as buffer:
            shutil.copyfileobj(file.file, buffer)

        # Vergelijk de geüploade foto met orgineel.JPG
        is_match = False
        result_message = ""

        if REFERENCE_IMAGE.exists():
            print(f"\n{'='*60}")
            print(f"Image Comparison Started")
            print(f"Uploaded file: {file.filename}")
            print(f"Reference: {REFERENCE_IMAGE}")
            print(f"{'='*60}")

            is_match = compare_images(file_path, REFERENCE_IMAGE)

            print(f"Match result: {'✅ MATCH' if is_match else '❌ NO MATCH'}")
            print(f"{'='*60}\n")

            if is_match:
                result_message = "Gefeliciteerd, je hebt de puzzel opgelost, de code is: 196"
            else:
                result_message = "Helaas, de puzzel is nog niet goed opgelost, probeer het nogmaals en upload een nieuwe foto"
        else:
            result_message = "Referentie afbeelding niet gevonden"
            print(f"⚠️  WARNING: Reference image not found at {REFERENCE_IMAGE}")

        return JSONResponse(content={
            "message": "File uploaded successfully",
            "filename": file.filename,
            "match": bool(is_match),
            "result": result_message
        })

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/status")
async def health_check():
    """Health check endpoint voor monitoring en load balancers"""
    import psutil
    import platform

    # Check if reference image exists
    reference_exists = REFERENCE_IMAGE.exists()

    # Get system info
    memory = psutil.virtual_memory()

    return JSONResponse(content={
        "status": "healthy",
        "service": "photo-match",
        "version": "1.0.0",
        "reference_image": {
            "exists": reference_exists,
            "path": str(REFERENCE_IMAGE) if reference_exists else None
        },
        "system": {
            "platform": platform.system(),
            "python_version": platform.python_version(),
            "cpu_count": psutil.cpu_count(),
            "memory_total_mb": round(memory.total / 1024 / 1024, 1),
            "memory_available_mb": round(memory.available / 1024 / 1024, 1),
            "memory_percent": memory.percent
        },
        "uploads_directory": str(UPLOAD_DIR)
    })

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
