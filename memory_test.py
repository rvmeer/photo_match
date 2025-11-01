#!/usr/bin/env python3
"""
Test script om memory usage van OpenCV te checken
Run: python memory_test.py
"""

import cv2
import numpy as np
import psutil
import os

def get_memory_mb():
    """Get current process memory in MB"""
    process = psutil.Process(os.getpid())
    return process.memory_info().rss / 1024 / 1024

# Check base memory
print("=" * 60)
print("OpenCV Memory Usage Test")
print("=" * 60)

base_memory = get_memory_mb()
print(f"\n1. Base Python memory: {base_memory:.1f} MB")

# Import OpenCV
import cv2
opencv_memory = get_memory_mb()
print(f"2. After importing OpenCV: {opencv_memory:.1f} MB (+{opencv_memory - base_memory:.1f} MB)")

# Load large image
print("\n3. Loading test image (orgineel.png)...")
img = cv2.imread('orgineel.png')
if img is None:
    print("   Creating test image instead...")
    img = np.random.randint(0, 255, (1920, 1080, 3), dtype=np.uint8)

load_memory = get_memory_mb()
print(f"   After loading image: {load_memory:.1f} MB (+{load_memory - opencv_memory:.1f} MB)")
print(f"   Image shape: {img.shape}")

# Resize
print("\n4. Resizing to 500x500...")
img_resized = cv2.resize(img, (500, 500))
resize_memory = get_memory_mb()
print(f"   After resize: {resize_memory:.1f} MB (+{resize_memory - load_memory:.1f} MB)")

# Grayscale
print("\n5. Converting to grayscale...")
gray = cv2.cvtColor(img_resized, cv2.COLOR_BGR2GRAY)
gray_memory = get_memory_mb()
print(f"   After grayscale: {gray_memory:.1f} MB (+{gray_memory - resize_memory:.1f} MB)")

# Histogram
print("\n6. Calculating histogram...")
hist = cv2.calcHist([img_resized], [0, 1, 2], None, [8, 8, 8], [0, 256, 0, 256, 0, 256])
hist_memory = get_memory_mb()
print(f"   After histogram: {hist_memory:.1f} MB (+{hist_memory - gray_memory:.1f} MB)")

# Simulate comparison
print("\n7. Full comparison simulation...")
img2 = img.copy()
img2_resized = cv2.resize(img2, (500, 500))
gray1 = cv2.cvtColor(img_resized, cv2.COLOR_BGR2GRAY)
gray2 = cv2.cvtColor(img2_resized, cv2.COLOR_BGR2GRAY)
mse = np.mean((gray1.astype(float) - gray2.astype(float)) ** 2)

hist1 = cv2.calcHist([img_resized], [0, 1, 2], None, [8, 8, 8], [0, 256, 0, 256, 0, 256])
hist2 = cv2.calcHist([img2_resized], [0, 1, 2], None, [8, 8, 8], [0, 256, 0, 256, 0, 256])
hist1 = cv2.normalize(hist1, hist1).flatten()
hist2 = cv2.normalize(hist2, hist2).flatten()
similarity = cv2.compareHist(hist1, hist2, cv2.HISTCMP_CORREL)

final_memory = get_memory_mb()
print(f"   After full comparison: {final_memory:.1f} MB")

print("\n" + "=" * 60)
print("SUMMARY")
print("=" * 60)
print(f"Base memory (Python + imports):  {opencv_memory:.1f} MB")
print(f"Peak memory (during comparison): {final_memory:.1f} MB")
print(f"Memory per request:              {final_memory - opencv_memory:.1f} MB")
print("\n" + "=" * 60)
print("LIGHTSAIL RECOMMENDATIONS")
print("=" * 60)
print(f"$3.50/maand (512 MB):  {'⚠️  Krap - mogelijk crashes' if final_memory > 300 else '✅ Voldoende'}")
print(f"$5.00/maand (1 GB):    ✅ Aanbevolen - ruim voldoende")
print(f"$10.00/maand (2 GB):   💰 Overkill voor deze app")
print("=" * 60)
