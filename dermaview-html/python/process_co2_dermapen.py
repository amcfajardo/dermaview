
import cv2
import numpy as np
import sys
from pathlib import Path

DISCLAIMER = "Educational visualization only; not a medical diagnosis or guaranteed treatment result."

def fail(message, code=1):
    print(message)
    sys.exit(code)

def read_image(input_path):
    img = cv2.imread(str(input_path), cv2.IMREAD_COLOR)
    if img is None:
        fail("Image not found or unsupported image format")
    return img

def save_image(output_path, img):
    output_path = Path(output_path)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    ok = cv2.imwrite(str(output_path), img, [cv2.IMWRITE_JPEG_QUALITY, 95])
    if not ok:
        fail("Failed to save output image")

def resize_for_processing(img, max_size=1200):
    h, w = img.shape[:2]
    longest = max(h, w)
    if longest <= max_size:
        return img
    scale = max_size / float(longest)
    return cv2.resize(img, (int(w * scale), int(h * scale)), interpolation=cv2.INTER_AREA)

def clamp_intensity(value, default=1.0):
    try:
        value = float(value)
    except Exception:
        value = default
    return float(np.clip(value, 0.35, 1.50))

def skin_mask_bgr(img):
    hsv = cv2.cvtColor(img, cv2.COLOR_BGR2HSV)
    ycrcb = cv2.cvtColor(img, cv2.COLOR_BGR2YCrCb)
    mask_hsv = cv2.inRange(hsv, np.array([0, 16, 35]), np.array([35, 230, 255]))
    mask_ycrcb = cv2.inRange(ycrcb, np.array([0, 128, 70]), np.array([255, 185, 150]))
    mask = cv2.bitwise_and(mask_hsv, mask_ycrcb)
    mask = cv2.morphologyEx(mask, cv2.MORPH_CLOSE, np.ones((9, 9), np.uint8))
    mask = cv2.morphologyEx(mask, cv2.MORPH_OPEN, np.ones((5, 5), np.uint8))
    if cv2.countNonZero(mask) < img.shape[0] * img.shape[1] * 0.03:
        h, w = img.shape[:2]
        mask = np.zeros((h, w), np.uint8)
        cv2.ellipse(mask, (w // 2, int(h * 0.52)), (int(w * 0.36), int(h * 0.42)), 0, 0, 360, 255, -1)
    mask = cv2.GaussianBlur(mask, (35, 35), 0)
    return mask

def mask3(mask, strength=1.0):
    f = mask.astype(np.float32) / 255.0
    f = np.clip(f * strength, 0, 1)
    return cv2.merge([f, f, f])

def blend(original, processed, mask, strength=1.0):
    alpha = mask3(mask, strength)
    out = processed.astype(np.float32) * alpha + original.astype(np.float32) * (1 - alpha)
    return np.clip(out, 0, 255).astype(np.uint8)

def protect_features_mask(img):
    gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
    edges = cv2.Canny(gray, 45, 110)
    dark = cv2.inRange(gray, 0, 70)
    hsv = cv2.cvtColor(img, cv2.COLOR_BGR2HSV)
    lip1 = cv2.inRange(hsv, np.array([0, 25, 35]), np.array([16, 190, 245]))
    lip2 = cv2.inRange(hsv, np.array([155, 25, 35]), np.array([180, 190, 245]))
    mask = cv2.bitwise_or(edges, dark)
    mask = cv2.bitwise_or(mask, cv2.bitwise_or(lip1, lip2))
    mask = cv2.dilate(mask, np.ones((5, 5), np.uint8), iterations=1)
    return cv2.GaussianBlur(mask, (21, 21), 0)

def gentle_sharpen(img, amount=0.07):
    blur = cv2.GaussianBlur(img, (0, 0), 1)
    return cv2.addWeighted(img, 1 + amount, blur, -amount, 0)

def enhance_lab(img, l_alpha=1.04, l_beta=4, a_smooth=0.06):
    lab = cv2.cvtColor(img, cv2.COLOR_BGR2LAB)
    l, a, b = cv2.split(lab)
    l = cv2.convertScaleAbs(l, alpha=l_alpha, beta=l_beta)
    a = cv2.addWeighted(a, 1 - a_smooth, cv2.GaussianBlur(a, (0, 0), 3), a_smooth, 0)
    return cv2.cvtColor(cv2.merge((l, a, b)), cv2.COLOR_LAB2BGR)

def elliptical_mask(shape, center, axes, blur=31):
    h, w = shape[:2]
    mask = np.zeros((h, w), np.uint8)
    cv2.ellipse(mask, center, axes, 0, 0, 360, 255, -1)
    if blur:
        blur = blur if blur % 2 == 1 else blur + 1
        mask = cv2.GaussianBlur(mask, (blur, blur), 0)
    return mask

def process_co2_dermapen(input_path, output_path, intensity=1.0):
    intensity = clamp_intensity(intensity)
    original = resize_for_processing(read_image(input_path), 1300)
    skin = skin_mask_bgr(original)
    protect = protect_features_mask(original)
    usable_skin = (skin.astype(np.float32) * (1 - protect.astype(np.float32) / 255.0)).astype(np.uint8)
    smooth = cv2.bilateralFilter(original, d=15, sigmaColor=45, sigmaSpace=45)
    smooth = cv2.bilateralFilter(smooth, d=9, sigmaColor=30, sigmaSpace=30)
    smooth = cv2.addWeighted(smooth, 0.78, cv2.GaussianBlur(smooth, (0, 0), 1.25), 0.22, 0)
    smooth = enhance_lab(smooth, l_alpha=1.02, l_beta=2, a_smooth=0.08)
    lab = cv2.cvtColor(original, cv2.COLOR_BGR2LAB)
    gray = cv2.cvtColor(original, cv2.COLOR_BGR2GRAY)
    _, a, _ = cv2.split(lab)
    red_marks = cv2.inRange(a, 130, 205)
    dark_spots = cv2.inRange(gray, 0, int(max(60, cv2.mean(gray, mask=skin)[0] - 20)))
    marks = cv2.bitwise_or(cv2.bitwise_and(red_marks, skin), cv2.bitwise_and(dark_spots, skin))
    marks = cv2.morphologyEx(marks, cv2.MORPH_CLOSE, np.ones((7, 7), np.uint8))
    marks = cv2.dilate(marks, np.ones((5, 5), np.uint8), iterations=1)
    marks = cv2.GaussianBlur(marks, (31, 31), 0)
    result = blend(original, smooth, usable_skin, 0.50 * intensity)
    result = blend(result, smooth, marks, 0.78 * intensity)
    result = gentle_sharpen(result, 0.045)
    save_image(output_path, result)
    print("CO2 Laser + Dermapen educational visualization saved:", output_path)
    print(DISCLAIMER)
    sys.exit(0)
if __name__ == "__main__":
    if len(sys.argv) < 3: fail("Usage: python process_co2_dermapen_final.py input output [intensity]")
    process_co2_dermapen(sys.argv[1], sys.argv[2], sys.argv[3] if len(sys.argv) > 3 else 1.0)
