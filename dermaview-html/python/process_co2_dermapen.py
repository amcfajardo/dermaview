
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


def resize_for_processing(img, max_size=1300):
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


def detect_face_bbox(img):
    """Return a face bounding box (x, y, w, h). Uses Haar detection, then a centered fallback."""
    gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
    gray = cv2.equalizeHist(gray)
    cascades = [
        cv2.data.haarcascades + 'haarcascade_frontalface_alt2.xml',
        cv2.data.haarcascades + 'haarcascade_frontalface_default.xml',
    ]
    faces = []
    for c in cascades:
        clf = cv2.CascadeClassifier(c)
        if not clf.empty():
            found = clf.detectMultiScale(gray, scaleFactor=1.08, minNeighbors=4, minSize=(80, 80))
            if len(found):
                faces = found
                break
    H, W = img.shape[:2]
    if len(faces):
        x, y, w, h = max(faces, key=lambda r: r[2] * r[3])
        pad_x, pad_y = int(w * 0.16), int(h * 0.22)
        x1 = max(0, x - pad_x)
        y1 = max(0, y - int(pad_y * 0.65))
        x2 = min(W, x + w + pad_x)
        y2 = min(H, y + h + pad_y)
        return (x1, y1, x2 - x1, y2 - y1)
    # fallback for very bright, stylized, or side-cropped images
    fw, fh = int(W * 0.62), int(H * 0.72)
    fx, fy = (W - fw) // 2, int(H * 0.12)
    return (fx, fy, fw, fh)


def ellipse_mask(shape, center, axes, angle=0, blur=0):
    mask = np.zeros(shape[:2], dtype=np.uint8)
    cv2.ellipse(mask, tuple(map(int, center)), tuple(map(int, axes)), angle, 0, 360, 255, -1)
    if blur:
        k = int(blur)
        k = k if k % 2 == 1 else k + 1
        mask = cv2.GaussianBlur(mask, (k, k), 0)
    return mask


def face_oval_mask(img, bbox=None, blur=41):
    if bbox is None:
        bbox = detect_face_bbox(img)
    x, y, w, h = bbox
    return ellipse_mask(img.shape, (x + w * 0.50, y + h * 0.52), (w * 0.46, h * 0.52), 0, blur)


def skin_mask_bgr(img, bbox=None):
    hsv = cv2.cvtColor(img, cv2.COLOR_BGR2HSV)
    ycrcb = cv2.cvtColor(img, cv2.COLOR_BGR2YCrCb)
    mask_hsv = cv2.inRange(hsv, np.array([0, 14, 35]), np.array([38, 235, 255]))
    mask_ycrcb = cv2.inRange(ycrcb, np.array([0, 124, 68]), np.array([255, 190, 155]))
    mask = cv2.bitwise_and(mask_hsv, mask_ycrcb)
    if bbox is not None:
        mask = cv2.bitwise_and(mask, face_oval_mask(img, bbox, blur=0))
    mask = cv2.morphologyEx(mask, cv2.MORPH_CLOSE, np.ones((9, 9), np.uint8))
    mask = cv2.morphologyEx(mask, cv2.MORPH_OPEN, np.ones((5, 5), np.uint8))
    if cv2.countNonZero(mask) < img.shape[0] * img.shape[1] * 0.025:
        mask = face_oval_mask(img, bbox, blur=0)
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


def protect_features_mask(img, bbox=None):
    gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
    edges = cv2.Canny(gray, 45, 110)
    dark = cv2.inRange(gray, 0, 65)
    hsv = cv2.cvtColor(img, cv2.COLOR_BGR2HSV)
    lip1 = cv2.inRange(hsv, np.array([0, 24, 35]), np.array([18, 195, 245]))
    lip2 = cv2.inRange(hsv, np.array([155, 24, 35]), np.array([180, 195, 245]))
    mask = cv2.bitwise_or(edges, dark)
    mask = cv2.bitwise_or(mask, cv2.bitwise_or(lip1, lip2))
    if bbox is not None:
        mask = cv2.bitwise_and(mask, face_oval_mask(img, bbox, blur=0))
    mask = cv2.dilate(mask, np.ones((5, 5), np.uint8), iterations=1)
    mask = cv2.GaussianBlur(mask, (21, 21), 0)
    return mask


def gentle_sharpen(img, amount=0.06):
    blur = cv2.GaussianBlur(img, (0, 0), 1)
    return cv2.addWeighted(img, 1 + amount, blur, -amount, 0)


def enhance_lab(img, l_alpha=1.04, l_beta=4, a_smooth=0.06):
    lab = cv2.cvtColor(img, cv2.COLOR_BGR2LAB)
    l, a, b = cv2.split(lab)
    l = cv2.convertScaleAbs(l, alpha=l_alpha, beta=l_beta)
    a = cv2.addWeighted(a, 1 - a_smooth, cv2.GaussianBlur(a, (0, 0), 3), a_smooth, 0)
    return cv2.cvtColor(cv2.merge((l, a, b)), cv2.COLOR_LAB2BGR)


def text(img, s, org, scale=0.55, color=(40,40,40), thick=1):
    cv2.putText(img, str(s), org, cv2.FONT_HERSHEY_SIMPLEX, scale, color, thick, cv2.LINE_AA)


def safe_mean(gray, mask):
    if cv2.countNonZero(mask) == 0:
        return float(np.mean(gray))
    return cv2.mean(gray, mask=mask)[0]

def process_co2_dermapen(input_path, output_path, intensity=1.0):
    intensity = clamp_intensity(intensity)
    original = resize_for_processing(read_image(input_path), 1300)
    bbox = detect_face_bbox(original)
    skin = skin_mask_bgr(original, bbox)
    protect = protect_features_mask(original, bbox)
    usable_skin = (skin.astype(np.float32) * (1 - protect.astype(np.float32) / 255.0)).astype(np.uint8)

    smooth = cv2.bilateralFilter(original, 15, 45, 45)
    smooth = cv2.bilateralFilter(smooth, 9, 30, 30)
    smooth = cv2.addWeighted(smooth, 0.78, cv2.GaussianBlur(smooth, (0, 0), 1.25), 0.22, 0)
    smooth = enhance_lab(smooth, l_alpha=1.02, l_beta=2, a_smooth=0.08)

    lab = cv2.cvtColor(original, cv2.COLOR_BGR2LAB)
    gray = cv2.cvtColor(original, cv2.COLOR_BGR2GRAY)
    _, a, _ = cv2.split(lab)
    red_marks = cv2.inRange(a, int(max(132, cv2.mean(a, mask=skin)[0] + 7)), 210)
    dark_spots = cv2.inRange(gray, 0, int(max(55, safe_mean(gray, skin) - 18)))
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
    if len(sys.argv) < 3:
        fail("Usage: python process_co2_dermapen_final.py input output [intensity]")
    process_co2_dermapen(sys.argv[1], sys.argv[2], sys.argv[3] if len(sys.argv) > 3 else 1.0)
