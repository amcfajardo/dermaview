
import cv2
import numpy as np
import sys
from pathlib import Path

DISCLAIMER = "Educational visualization only. Not a medical diagnosis or guaranteed treatment result."

COLORS = {
    "red": (45, 45, 220),
    "orange": (0, 135, 255),
    "green": (70, 160, 60),
    "purple": (180, 70, 155),
    "blue": (215, 120, 30),
    "teal": (165, 150, 20),
    "navy": (55, 30, 10),
    "gray": (95, 95, 95),
    "light": (248, 248, 248),
}

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
    return float(np.clip(value, 0.30, 1.60))

def detect_face_bbox(img):
    h, w = img.shape[:2]
    gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
    cascade_path = cv2.data.haarcascades + "haarcascade_frontalface_default.xml"
    cascade = cv2.CascadeClassifier(cascade_path)
    faces = cascade.detectMultiScale(gray, scaleFactor=1.08, minNeighbors=4, minSize=(max(40, w//8), max(40, h//8)))
    if len(faces) > 0:
        faces = sorted(faces, key=lambda r: r[2] * r[3], reverse=True)
        x, y, fw, fh = [int(v) for v in faces[0]]
        pad_x, pad_y = int(fw * 0.08), int(fh * 0.16)
        x = max(0, x - pad_x)
        y = max(0, y - pad_y)
        fw = min(w - x, fw + 2 * pad_x)
        fh = min(h - y, fh + int(pad_y * 1.6))
        return x, y, fw, fh
    # Fallback: center face estimate. This keeps the script usable for different image sizes even when detection fails.
    fw = int(w * 0.56)
    fh = int(h * 0.70)
    x = (w - fw) // 2
    y = int(h * 0.12)
    return x, y, fw, fh

def skin_mask_bgr(img):
    hsv = cv2.cvtColor(img, cv2.COLOR_BGR2HSV)
    ycrcb = cv2.cvtColor(img, cv2.COLOR_BGR2YCrCb)
    mask_hsv = cv2.inRange(hsv, np.array([0, 14, 32]), np.array([35, 235, 255]))
    mask_ycrcb = cv2.inRange(ycrcb, np.array([0, 126, 68]), np.array([255, 188, 155]))
    mask = cv2.bitwise_and(mask_hsv, mask_ycrcb)
    mask = cv2.morphologyEx(mask, cv2.MORPH_CLOSE, np.ones((7, 7), np.uint8))
    mask = cv2.morphologyEx(mask, cv2.MORPH_OPEN, np.ones((3, 3), np.uint8))
    if cv2.countNonZero(mask) < img.shape[0] * img.shape[1] * 0.025:
        h, w = img.shape[:2]
        mask = np.zeros((h, w), np.uint8)
        x, y, fw, fh = detect_face_bbox(img)
        cv2.ellipse(mask, (x + fw//2, y + int(fh*0.53)), (int(fw*0.46), int(fh*0.50)), 0, 0, 360, 255, -1)
    mask = cv2.GaussianBlur(mask, (31, 31), 0)
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
    edges = cv2.Canny(gray, 45, 115)
    dark = cv2.inRange(gray, 0, 70)
    hsv = cv2.cvtColor(img, cv2.COLOR_BGR2HSV)
    lip1 = cv2.inRange(hsv, np.array([0, 25, 35]), np.array([18, 200, 245]))
    lip2 = cv2.inRange(hsv, np.array([155, 25, 35]), np.array([180, 200, 245]))
    mask = cv2.bitwise_or(edges, dark)
    mask = cv2.bitwise_or(mask, cv2.bitwise_or(lip1, lip2))
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

def elliptical_mask(shape, center, axes, blur=31):
    h, w = shape[:2]
    mask = np.zeros((h, w), np.uint8)
    cv2.ellipse(mask, center, axes, 0, 0, 360, 255, -1)
    if blur:
        blur = blur if blur % 2 == 1 else blur + 1
        mask = cv2.GaussianBlur(mask, (blur, blur), 0)
    return mask

def rounded_rect(img, p1, p2, color, radius=16, thickness=-1):
    x1, y1 = p1; x2, y2 = p2
    if thickness < 0:
        cv2.rectangle(img, (x1+radius, y1), (x2-radius, y2), color, -1)
        cv2.rectangle(img, (x1, y1+radius), (x2, y2-radius), color, -1)
        cv2.circle(img, (x1+radius, y1+radius), radius, color, -1)
        cv2.circle(img, (x2-radius, y1+radius), radius, color, -1)
        cv2.circle(img, (x1+radius, y2-radius), radius, color, -1)
        cv2.circle(img, (x2-radius, y2-radius), radius, color, -1)
    else:
        cv2.rectangle(img, p1, p2, color, thickness)

def draw_text(img, text, org, scale=0.55, color=(20,20,20), thickness=1, max_width=None, line_gap=22):
    x, y = org
    if max_width is None:
        cv2.putText(img, text, (x, y), cv2.FONT_HERSHEY_SIMPLEX, scale, color, thickness, cv2.LINE_AA)
        return y + line_gap
    words = str(text).split()
    line = ""
    for word in words:
        test = (line + " " + word).strip()
        tw = cv2.getTextSize(test, cv2.FONT_HERSHEY_SIMPLEX, scale, thickness)[0][0]
        if tw > max_width and line:
            cv2.putText(img, line, (x, y), cv2.FONT_HERSHEY_SIMPLEX, scale, color, thickness, cv2.LINE_AA)
            y += line_gap
            line = word
        else:
            line = test
    if line:
        cv2.putText(img, line, (x, y), cv2.FONT_HERSHEY_SIMPLEX, scale, color, thickness, cv2.LINE_AA)
        y += line_gap
    return y

def color_tint(original, mask, color, alpha=0.15):
    overlay = original.copy()
    overlay[mask > 0] = color
    return cv2.addWeighted(overlay, alpha, original, 1-alpha, 0)

def make_face_region_masks(img):
    h, w = img.shape[:2]
    x, y, fw, fh = detect_face_bbox(img)
    # Conservative segmented regions to avoid covering the whole face.
    regions = {}
    regions["forehead"] = elliptical_mask(img.shape, (x + int(fw*0.50), y + int(fh*0.24)), (int(fw*0.24), int(fh*0.060)), blur=0)
    regions["left_cheek"] = elliptical_mask(img.shape, (x + int(fw*0.31), y + int(fh*0.55)), (int(fw*0.105), int(fh*0.150)), blur=0)
    regions["right_cheek"] = elliptical_mask(img.shape, (x + int(fw*0.69), y + int(fh*0.55)), (int(fw*0.105), int(fh*0.150)), blur=0)
    under = np.zeros((h, w), np.uint8)
    cv2.ellipse(under, (x + int(fw*0.36), y + int(fh*0.405)), (int(fw*0.105), int(fh*0.035)), 0, 0, 360, 255, -1)
    cv2.ellipse(under, (x + int(fw*0.64), y + int(fh*0.405)), (int(fw*0.105), int(fh*0.035)), 0, 0, 360, 255, -1)
    regions["undereye"] = under
    regions["nose"] = elliptical_mask(img.shape, (x + int(fw*0.50), y + int(fh*0.51)), (int(fw*0.080), int(fh*0.150)), blur=0)
    regions["chin"] = elliptical_mask(img.shape, (x + int(fw*0.50), y + int(fh*0.78)), (int(fw*0.150), int(fh*0.075)), blur=0)
    return regions, (x, y, fw, fh)

def score_region(issue_mask, region_mask):
    denom = max(1, cv2.countNonZero(region_mask))
    return min(100.0, (cv2.countNonZero(cv2.bitwise_and(issue_mask, region_mask)) / denom) * 100.0)

def severity_from_score(score):
    if score < 8:
        return "Low"
    if score < 18:
        return "Mild"
    if score < 35:
        return "Moderate"
    return "High"

def process_face_slimming(input_path, output_path, intensity=1.0):
    intensity = clamp_intensity(intensity)
    img = resize_for_processing(read_image(input_path), 1000)
    h, w = img.shape[:2]
    x, y, fw, fh = detect_face_bbox(img)
    yy, xx = np.indices((h, w), dtype=np.float32)
    center_x = x + fw / 2.0

    lower_face_mask = elliptical_mask(img.shape, (int(center_x), y + int(fh * 0.63)), (int(fw * 0.36), int(fh * 0.27)), blur=41)
    lower = lower_face_mask.astype(np.float32) / 255.0
    distance = np.abs(xx - center_x)
    falloff = np.exp(-(distance ** 2) / (2 * (fw * 0.25) ** 2))
    direction = np.where(xx < center_x, -1.0, 1.0)
    strength = 0.060 * intensity
    map_x = xx + direction * strength * distance * falloff * lower
    slimmed = cv2.remap(img, np.clip(map_x, 0, w - 1).astype(np.float32), yy.astype(np.float32), cv2.INTER_LINEAR)
    slimmed = cv2.bilateralFilter(slimmed, 5, 28, 28)
    slimmed = cv2.convertScaleAbs(slimmed, alpha=1.015, beta=2)
    slimmed = gentle_sharpen(slimmed, 0.035)
    save_image(output_path, slimmed)
    print("Face Slimming educational visualization saved:", output_path)
    print(DISCLAIMER)
    sys.exit(0)

if __name__ == "__main__":
    if len(sys.argv) < 3:
        fail("Usage: python process_face_slimming.py input output [intensity]")
    process_face_slimming(sys.argv[1], sys.argv[2], sys.argv[3] if len(sys.argv) > 3 else 1.0)
