
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

def process_undereye_lip_filler(input_path, output_path, intensity=1.0):
    intensity = clamp_intensity(intensity)
    original = resize_for_processing(read_image(input_path), 1000)
    h, w = original.shape[:2]
    result = original.copy()
    yy, xx = np.indices((h, w), dtype=np.float32)
    left_eye = elliptical_mask(original.shape, (int(w * 0.35), int(h * 0.43)), (int(w * 0.13), int(h * 0.060)), blur=41)
    right_eye = elliptical_mask(original.shape, (int(w * 0.65), int(h * 0.43)), (int(w * 0.13), int(h * 0.060)), blur=41)
    eye_mask = cv2.bitwise_or(left_eye, right_eye)
    smooth_eye = cv2.bilateralFilter(result, d=15, sigmaColor=55, sigmaSpace=55)
    smooth_eye = enhance_lab(smooth_eye, l_alpha=1.075, l_beta=6, a_smooth=0.06)
    result = blend(result, smooth_eye, eye_mask, 0.50 * intensity)
    lip_center = (int(w * 0.50), int(h * 0.72))
    dx = (xx - lip_center[0]) / max(w * 0.13, 1)
    dy = (yy - lip_center[1]) / max(h * 0.065, 1)
    dist = np.sqrt(dx * dx + dy * dy)
    factor = np.clip(1 - dist, 0, 1)
    map_x = xx - (xx - lip_center[0]) * factor * 0.035 * intensity
    map_y = yy - (yy - lip_center[1]) * factor * 0.060 * intensity
    result = cv2.remap(result, np.clip(map_x, 0, w - 1).astype(np.float32), np.clip(map_y, 0, h - 1).astype(np.float32), cv2.INTER_LINEAR)
    hsv = cv2.cvtColor(result, cv2.COLOR_BGR2HSV).astype(np.float32)
    hsv_u8 = hsv.astype(np.uint8)
    lip1 = cv2.inRange(hsv_u8, np.array([0, 25, 35]), np.array([18, 195, 255]))
    lip2 = cv2.inRange(hsv_u8, np.array([155, 25, 35]), np.array([180, 195, 255]))
    lip_mask = cv2.morphologyEx(cv2.bitwise_or(lip1, lip2), cv2.MORPH_CLOSE, np.ones((7, 7), np.uint8))
    lip_mask = cv2.GaussianBlur(lip_mask, (31, 31), 0).astype(np.float32) / 255.0
    lip_mask = np.clip(lip_mask * 0.28 * intensity, 0, 0.40)
    hsv[:, :, 1] += lip_mask * 28; hsv[:, :, 2] += lip_mask * 10
    result = cv2.cvtColor(np.clip(hsv, 0, 255).astype(np.uint8), cv2.COLOR_HSV2BGR)
    result = gentle_sharpen(result, 0.05)
    save_image(output_path, result)
    print("Undereye and Lip Filler educational visualization saved:", output_path)
    print(DISCLAIMER)
    sys.exit(0)
if __name__ == "__main__":
    if len(sys.argv) < 3: fail("Usage: python process_undereye_lip_filler_final.py input output [intensity]")
    process_undereye_lip_filler(sys.argv[1], sys.argv[2], sys.argv[3] if len(sys.argv) > 3 else 1.0)
