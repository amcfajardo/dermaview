
import cv2
import numpy as np
import sys
from pathlib import Path

DISCLAIMER = "Educational visualization only; not a medical diagnosis or guaranteed treatment result."

COLORS = {
    "red": (35, 55, 220),
    "orange": (0, 145, 255),
    "green": (70, 165, 70),
    "blue": (210, 130, 35),
    "purple": (185, 85, 175),
    "cyan": (190, 150, 35),
    "navy": (78, 48, 25),
    "text": (45, 45, 45),
    "muted": (100, 100, 100),
    "panel": (255, 255, 255),
    "line": (220, 224, 230),
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


def detect_face_bbox(img):
    h, w = img.shape[:2]
    gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
    try:
        cascade_path = cv2.data.haarcascades + 'haarcascade_frontalface_default.xml'
        cascade = cv2.CascadeClassifier(cascade_path)
        faces = cascade.detectMultiScale(gray, scaleFactor=1.08, minNeighbors=4, minSize=(max(50, w//8), max(50, h//8)))
    except Exception:
        faces = []
    if len(faces) > 0:
        x, y, fw, fh = max(faces, key=lambda r: r[2] * r[3])
        pad_x, pad_y = int(fw * 0.22), int(fh * 0.34)
        x = max(0, x - pad_x)
        y = max(0, y - pad_y)
        fw = min(w - x, fw + pad_x * 2)
        fh = min(h - y, fh + int(pad_y * 1.65))
        return (x, y, fw, fh)
    # fallback centered head/face estimate
    return (int(w * 0.23), int(h * 0.10), int(w * 0.54), int(h * 0.68))


def skin_mask_bgr(img, bbox=None):
    hsv = cv2.cvtColor(img, cv2.COLOR_BGR2HSV)
    ycrcb = cv2.cvtColor(img, cv2.COLOR_BGR2YCrCb)
    mask_hsv = cv2.inRange(hsv, np.array([0, 14, 32]), np.array([35, 235, 255]))
    mask_ycrcb = cv2.inRange(ycrcb, np.array([0, 126, 68]), np.array([255, 188, 154]))
    mask = cv2.bitwise_and(mask_hsv, mask_ycrcb)
    if bbox is not None:
        face = face_oval_mask(np.zeros(img.shape[:2], np.uint8), bbox, blur=0)
        mask = cv2.bitwise_and(mask, face)
    mask = cv2.morphologyEx(mask, cv2.MORPH_CLOSE, np.ones((9, 9), np.uint8))
    mask = cv2.morphologyEx(mask, cv2.MORPH_OPEN, np.ones((5, 5), np.uint8))
    if cv2.countNonZero(mask) < img.shape[0] * img.shape[1] * 0.015:
        h, w = img.shape[:2]
        if bbox is None:
            bbox = detect_face_bbox(img)
        mask = face_oval_mask(np.zeros((h, w), np.uint8), bbox, blur=0)
    return cv2.GaussianBlur(mask, (35, 35), 0)


def face_oval_mask(mask, bbox, blur=21):
    x, y, w, h = bbox
    center = (int(x + w * 0.50), int(y + h * 0.52))
    axes = (max(1, int(w * 0.43)), max(1, int(h * 0.50)))
    cv2.ellipse(mask, center, axes, 0, 0, 360, 255, -1)
    if blur:
        k = blur if blur % 2 else blur + 1
        mask = cv2.GaussianBlur(mask, (k, k), 0)
    return mask


def ellipse_mask(shape, center, axes, blur=0):
    h, w = shape[:2]
    mask = np.zeros((h, w), np.uint8)
    cv2.ellipse(mask, (int(center[0]), int(center[1])), (max(1, int(axes[0])), max(1, int(axes[1]))), 0, 0, 360, 255, -1)
    if blur:
        k = blur if blur % 2 else blur + 1
        mask = cv2.GaussianBlur(mask, (k, k), 0)
    return mask


def blend(original, processed, mask, strength=1.0):
    f = np.clip((mask.astype(np.float32) / 255.0) * strength, 0, 1)
    f3 = cv2.merge([f, f, f])
    return np.clip(processed.astype(np.float32) * f3 + original.astype(np.float32) * (1 - f3), 0, 255).astype(np.uint8)


def protect_features_mask(img):
    gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
    edges = cv2.Canny(gray, 45, 110)
    dark = cv2.inRange(gray, 0, 70)
    hsv = cv2.cvtColor(img, cv2.COLOR_BGR2HSV)
    lip1 = cv2.inRange(hsv, np.array([0, 25, 35]), np.array([18, 195, 245]))
    lip2 = cv2.inRange(hsv, np.array([155, 25, 35]), np.array([180, 195, 245]))
    mask = cv2.bitwise_or(edges, dark)
    mask = cv2.bitwise_or(mask, cv2.bitwise_or(lip1, lip2))
    mask = cv2.dilate(mask, np.ones((5, 5), np.uint8), iterations=1)
    return cv2.GaussianBlur(mask, (21, 21), 0)


def gentle_sharpen(img, amount=0.06):
    blur = cv2.GaussianBlur(img, (0, 0), 1)
    return cv2.addWeighted(img, 1 + amount, blur, -amount, 0)


def enhance_lab(img, l_alpha=1.04, l_beta=4, a_smooth=0.06):
    lab = cv2.cvtColor(img, cv2.COLOR_BGR2LAB)
    l, a, b = cv2.split(lab)
    l = cv2.convertScaleAbs(l, alpha=l_alpha, beta=l_beta)
    a = cv2.addWeighted(a, 1 - a_smooth, cv2.GaussianBlur(a, (0, 0), 3), a_smooth, 0)
    return cv2.cvtColor(cv2.merge((l, a, b)), cv2.COLOR_LAB2BGR)


def put_text(img, text, pos, scale=0.5, color=(45,45,45), thick=1):
    cv2.putText(img, str(text), pos, cv2.FONT_HERSHEY_SIMPLEX, scale, color, thick, cv2.LINE_AA)


def wrap_lines(text, max_chars=45):
    words = str(text).split()
    lines, cur = [], ''
    for word in words:
        if len(cur) + len(word) + 1 <= max_chars:
            cur = (cur + ' ' + word).strip()
        else:
            if cur: lines.append(cur)
            cur = word
    if cur: lines.append(cur)
    return lines


def put_wrapped(img, text, x, y, max_chars=45, scale=0.42, color=(45,45,45), line_h=18, max_lines=3):
    for line in wrap_lines(text, max_chars)[:max_lines]:
        put_text(img, line, (x, y), scale, color, 1)
        y += line_h
    return y


def rounded_rect(img, pt1, pt2, color, border=None, radius=14, thickness=-1):
    # Simple rectangle fallback with antialiased borders; OpenCV lacks native rounded rect.
    cv2.rectangle(img, pt1, pt2, color, thickness, cv2.LINE_AA)
    if border is not None:
        cv2.rectangle(img, pt1, pt2, border, 1, cv2.LINE_AA)


def draw_dashed_ellipse(img, center, axes, color, thickness=1, dash_deg=5, gap_deg=8):
    start = 0
    while start < 360:
        end = min(start + dash_deg, 360)
        cv2.ellipse(img, (int(center[0]), int(center[1])), (max(1, int(axes[0])), max(1, int(axes[1]))), 0, start, end, color, thickness, cv2.LINE_AA)
        start += dash_deg + gap_deg


def draw_soft_area(img, mask, color, alpha=0.045):
    overlay = img.copy()
    overlay[mask > 0] = color
    return cv2.addWeighted(overlay, alpha, img, 1-alpha, 0)


def draw_badge(img, center, text, color, r=13):
    x, y = int(center[0]), int(center[1])
    cv2.circle(img, (x, y), r, color, -1, cv2.LINE_AA)
    cv2.circle(img, (x, y), r, (255,255,255), 2, cv2.LINE_AA)
    tw = cv2.getTextSize(str(text), cv2.FONT_HERSHEY_SIMPLEX, 0.45, 2)[0][0]
    put_text(img, text, (x - tw//2, y + 5), 0.45, (255,255,255), 2)


def severity_label(score):
    if score < 18: return 'Low'
    if score < 40: return 'Mild'
    if score < 65: return 'Moderate'
    return 'High'


def create_before_after_report(original, processed, title, findings, recommendations=None):
    original = resize_for_processing(original, 900)
    processed = cv2.resize(processed, (original.shape[1], original.shape[0]), interpolation=cv2.INTER_AREA)
    h, w = original.shape[:2]
    panel_h = 250
    gap = 18
    top_h = 58
    out_w = w*2 + gap + 48
    out_h = top_h + h + panel_h + 38
    canvas = np.full((out_h, out_w, 3), 248, dtype=np.uint8)
    cv2.rectangle(canvas, (0,0), (out_w, top_h), COLORS['navy'], -1)
    tw = cv2.getTextSize(title, cv2.FONT_HERSHEY_SIMPLEX, 0.85, 2)[0][0]
    put_text(canvas, title, ((out_w-tw)//2, 38), 0.85, (255,255,255), 2)
    x1, y1 = 24, top_h + 16
    x2 = x1 + w + gap
    canvas[y1:y1+h, x1:x1+w] = original
    canvas[y1:y1+h, x2:x2+w] = processed
    cv2.rectangle(canvas, (x1,y1), (x1+w,y1+h), (225,225,225), 1)
    cv2.rectangle(canvas, (x2,y1), (x2+w,y1+h), (225,225,225), 1)
    # labels below image, not blocking face
    for label, xx in [('BEFORE', x1), ('AFTER', x2)]:
        cv2.rectangle(canvas, (xx+14, y1+h-42), (xx+120, y1+h-12), (20,20,20), -1, cv2.LINE_AA)
        put_text(canvas, label, (xx+31, y1+h-20), 0.55, (255,255,255), 2)
    py = y1 + h + 24
    rounded_rect(canvas, (24, py), (out_w-24, out_h-20), (255,255,255), (220,225,232))
    put_text(canvas, 'EDUCATIONAL VISUALIZATION FINDINGS', (48, py+32), 0.58, COLORS['navy'], 2)
    col_w = (out_w-96)//2
    fx = 48
    fy = py + 64
    for i, line in enumerate(findings[:4]):
        yy = fy + i*36
        cv2.circle(canvas, (fx+8, yy-2), 8, COLORS['green'], -1, cv2.LINE_AA)
        put_text(canvas, '✓', (fx+3, yy+3), 0.35, (255,255,255), 1)
        put_wrapped(canvas, line, fx+24, yy+3, 58, 0.42, COLORS['text'], 16, 2)
    rx = 48 + col_w + 28
    put_text(canvas, 'RECOMMENDED USE', (rx, py+32), 0.58, (40,100,45), 2)
    if recommendations is None:
        recommendations = ['Use as visual guide only', 'Consult a licensed professional for actual evaluation', 'Compare before and after output with original image']
    for i, line in enumerate(recommendations[:4]):
        yy = fy + i*36
        cv2.circle(canvas, (rx+8, yy-2), 8, COLORS['orange'], -1, cv2.LINE_AA)
        put_wrapped(canvas, line, rx+24, yy+3, 48, 0.42, COLORS['text'], 16, 2)
    put_text(canvas, 'Disclaimer: ' + DISCLAIMER, (48, out_h-34), 0.38, COLORS['muted'], 1)
    return canvas

def process_diamond_peel(input_path, output_path, intensity=1.0):
    intensity = clamp_intensity(intensity)
    original = resize_for_processing(read_image(input_path), 1100)
    bbox = detect_face_bbox(original); skin = skin_mask_bgr(original, bbox); protect = protect_features_mask(original)
    usable_skin = (skin.astype(np.float32) * (1 - 0.45 * protect.astype(np.float32)/255.0)).astype(np.uint8)
    smooth = cv2.bilateralFilter(original, 17, 65, 65)
    smooth = cv2.bilateralFilter(smooth, 11, 38, 38)
    bright = enhance_lab(smooth, 1.065, 7, 0.06)
    glow = cv2.addWeighted(bright, 0.90, cv2.GaussianBlur(bright, (0,0), 2.0), 0.10, 0)
    result = blend(original, glow, usable_skin, 0.66*intensity)
    result = gentle_sharpen(result, 0.055)
    report = create_before_after_report(original, result, 'DIAMOND PEEL FACIAL', [
        'Complexion appears brighter and more refreshed through controlled luminance enhancement.',
        'Skin-area smoothing simulates gentle exfoliation without fully removing natural facial texture.',
        'Soft glow is applied only on detected face/skin areas to avoid affecting the background.',
        'Final sharpening is added so the output does not look overly blurred or plastic.'
    ], ['For dullness and exfoliation visualization', 'For smoother skin appearance demonstration', 'Educational result only'])
    save_image(output_path, report)
    print('Diamond Peel Facial professional report saved:', output_path); print(DISCLAIMER); sys.exit(0)

if __name__ == '__main__':
    if len(sys.argv) < 3: fail('Usage: python process_diamond_peel.py input output [intensity]')
    process_diamond_peel(sys.argv[1], sys.argv[2], sys.argv[3] if len(sys.argv)>3 else 1.0)
