
import cv2
import numpy as np
import sys
from pathlib import Path

try:
    import mediapipe as mp
except Exception:
    mp = None


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

def get_face_landmarks(img):
    if mp is None:
        return None
    h, w = img.shape[:2]
    rgb = cv2.cvtColor(img, cv2.COLOR_BGR2RGB)
    with mp.solutions.face_mesh.FaceMesh(
        static_image_mode=True,
        max_num_faces=1,
        refine_landmarks=True,
        min_detection_confidence=0.50,
    ) as face_mesh:
        result = face_mesh.process(rgb)
        if not result.multi_face_landmarks:
            return None
        return [(int(p.x * w), int(p.y * h)) for p in result.multi_face_landmarks[0].landmark]

def polygon_mask(shape, points):
    mask = np.zeros(shape[:2], np.uint8)
    if points is None or len(points) < 3:
        return mask
    pts = np.array(points, np.int32)
    cv2.fillPoly(mask, [pts], 255)
    return mask

def safe_points(lm, ids):
    try:
        return [lm[i] for i in ids]
    except Exception:
        return []

def make_face_region_masks(img):
    """Pico Carbon Laser uses FaceMesh zones to localize pigment/pores detection.

    FaceMesh provides the
    'face detection' equivalent for zone restriction.



    Falls back to ellipses if landmarks aren't available.
    """
    h, w = img.shape[:2]
    x, y, fw, fh = detect_face_bbox(img)

    lm = get_face_landmarks(img)
    if lm is not None and len(lm) >= 468:
        def pts(ids):
            return safe_points(lm, ids)

        face_oval_ids = [
            10,338,297,332,284,251,389,356,454,323,361,288,397,365,379,378,400,377,
            152,148,176,149,150,136,172,58,132,93,234,127,162,21,54,103,67,109
        ]
        face_mask = polygon_mask(img.shape, pts(face_oval_ids))

        left_eye_ids  = [33, 246, 161, 160, 159, 158, 157, 173, 133, 155, 154, 153, 145, 144, 163, 7]
        right_eye_ids = [263, 466, 388, 387, 386, 385, 384, 398, 362, 382, 381, 380, 374, 373, 390, 249]
        left_eye = pts(left_eye_ids)
        right_eye = pts(right_eye_ids)
        lcx = int(np.mean([p[0] for p in left_eye])) if left_eye else int(x + fw * 0.4)
        rcx = int(np.mean([p[0] for p in right_eye])) if right_eye else int(x + fw * 0.6)
        mid_x = int((lcx + rcx) / 2)

        brow_y = int(np.mean([p[1] for p in pts([70, 63, 105, 66, 107, 336, 296, 334, 293, 300])]))
        face_top_y = min(p[1] for p in pts([10, 67, 109, 338, 297]))

        eye_gap = max(1, rcx - lcx)
        eye_y = int(np.mean([p[1] for p in (left_eye + right_eye)]) / 2) if (left_eye and right_eye) else int(y + fh * 0.40)
        mouth_bottom_y = int(y + fh * 0.70)

        forehead_pts = [
            (mid_x - int(eye_gap*0.48), int(face_top_y + (brow_y-face_top_y)*0.12)),
            (mid_x, face_top_y),
            (mid_x + int(eye_gap*0.48), int(face_top_y + (brow_y-face_top_y)*0.12)),
            (mid_x + int(eye_gap*0.36), brow_y),
            (mid_x - int(eye_gap*0.36), brow_y),
        ]
        forehead = polygon_mask(img.shape, forehead_pts)

        cheek_y = int(eye_y + (mouth_bottom_y-eye_y)*0.55)
        cheek_low_y = int(mouth_bottom_y + (fh*0.78 - mouth_bottom_y)*0.10)
        left_cheek = polygon_mask(img.shape, [(mid_x - int(eye_gap*0.30), cheek_y), (mid_x - int(eye_gap*0.08), cheek_y), (mid_x - int(eye_gap*0.14), cheek_low_y)])
        right_cheek = polygon_mask(img.shape, [(mid_x + int(eye_gap*0.30), cheek_y), (mid_x + int(eye_gap*0.08), cheek_y), (mid_x + int(eye_gap*0.14), cheek_low_y)])

        # Nose & chin zones
        nose = polygon_mask(img.shape, [(mid_x - int(eye_gap*0.10), brow_y), (mid_x + int(eye_gap*0.10), brow_y), (mid_x, int(brow_y + fh*0.25))])
        chin = polygon_mask(img.shape, [(mid_x - int(eye_gap*0.25), int(y+fh*0.80)), (mid_x + int(eye_gap*0.25), int(y+fh*0.80)), (mid_x, int(y+fh*0.93))])

        # Restrict to face oval
        forehead = cv2.bitwise_and(forehead, face_mask)
        left_cheek = cv2.bitwise_and(left_cheek, face_mask)
        right_cheek = cv2.bitwise_and(right_cheek, face_mask)
        nose = cv2.bitwise_and(nose, face_mask)
        chin = cv2.bitwise_and(chin, face_mask)

        # Undereye as left/right eyelid strips (approx)
        drop = max(5, int(fh*0.030))
        left_lower = pts([33, 7, 163, 144, 145, 153, 154, 155, 133])
        right_lower = pts([362, 382, 381, 380, 374, 373, 390, 249, 263])
        left_under = left_lower + [(px, py + drop) for px, py in reversed(left_lower)]
        right_under = right_lower + [(px, py + drop) for px, py in reversed(right_lower)]
        undereye = cv2.bitwise_or(polygon_mask(img.shape, left_under), polygon_mask(img.shape, right_under))
        undereye = cv2.bitwise_and(undereye, face_mask)

        regions = {
            "forehead": forehead,
            "left_cheek": left_cheek,
            "right_cheek": right_cheek,
            "undereye": undereye,
            "nose": nose,
            "chin": chin,
        }
        return regions, (x, y, fw, fh)

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

def process_pico_carbon_laser(input_path, output_path, intensity=1.0):
    intensity = clamp_intensity(intensity)
    original = resize_for_processing(read_image(input_path), 1300)
    skin = skin_mask_bgr(original)
    protect = protect_features_mask(original)
    usable_skin = (skin.astype(np.float32) * (1 - 0.40 * protect.astype(np.float32) / 255.0)).astype(np.uint8)

    smooth = cv2.bilateralFilter(original, d=19, sigmaColor=70, sigmaSpace=70)
    smooth = cv2.bilateralFilter(smooth, d=11, sigmaColor=45, sigmaSpace=45)
    bright = enhance_lab(smooth, l_alpha=1.07, l_beta=7, a_smooth=0.08)
    radiant = cv2.addWeighted(bright, 0.84, cv2.GaussianBlur(bright, (0, 0), 2.5), 0.16, 0)

    gray = cv2.cvtColor(original, cv2.COLOR_BGR2GRAY)
    mean = cv2.mean(gray, mask=skin)[0]
    pigment = cv2.inRange(gray, 0, int(max(55, mean - 18)))
    pigment = cv2.bitwise_and(pigment, skin)
    pigment = cv2.GaussianBlur(cv2.dilate(pigment, np.ones((5, 5), np.uint8), 1), (31, 31), 0)

    result = blend(original, radiant, usable_skin, 0.62 * intensity)
    result = blend(result, radiant, pigment, 0.42 * intensity)
    result = gentle_sharpen(result, 0.05)
    save_image(output_path, result)
    print("PICO Carbon Laser educational visualization saved:", output_path)
    print(DISCLAIMER)
    sys.exit(0)

if __name__ == "__main__":
    if len(sys.argv) < 3:
        fail("Usage: python process_pico_carbon_laser.py input output [intensity]")
    process_pico_carbon_laser(sys.argv[1], sys.argv[2], sys.argv[3] if len(sys.argv) > 3 else 1.0)
