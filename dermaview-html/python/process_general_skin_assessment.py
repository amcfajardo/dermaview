
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

    # Best option: MediaPipe FaceMesh if installed.
    if mp is not None:
        rgb = cv2.cvtColor(img, cv2.COLOR_BGR2RGB)
        with mp.solutions.face_mesh.FaceMesh(
            static_image_mode=True,
            max_num_faces=1,
            refine_landmarks=True,
            min_detection_confidence=0.50
        ) as face_mesh:
            result = face_mesh.process(rgb)
            if result.multi_face_landmarks:
                lm = result.multi_face_landmarks[0].landmark
                xs = [int(p.x * w) for p in lm]
                ys = [int(p.y * h) for p in lm]
                x1, y1 = max(0, min(xs)), max(0, min(ys))
                x2, y2 = min(w - 1, max(xs)), min(h - 1, max(ys))
                pad_x = int((x2 - x1) * 0.08)
                pad_y = int((y2 - y1) * 0.10)
                x1 = max(0, x1 - pad_x)
                y1 = max(0, y1 - pad_y)
                x2 = min(w - 1, x2 + pad_x)
                y2 = min(h - 1, y2 + pad_y)
                return x1, y1, max(1, x2 - x1), max(1, y2 - y1)

    # Fallback: Haar cascade.
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

    # Last fallback: proportional center face estimate.
    fw = int(w * 0.56)
    fh = int(h * 0.70)
    x = (w - fw) // 2
    y = int(h * 0.12)
    return x, y, fw, fh

def get_face_landmarks(img):
    if mp is None:
        return None
    h, w = img.shape[:2]
    rgb = cv2.cvtColor(img, cv2.COLOR_BGR2RGB)
    with mp.solutions.face_mesh.FaceMesh(
        static_image_mode=True,
        max_num_faces=1,
        refine_landmarks=True,
        min_detection_confidence=0.50
    ) as face_mesh:
        result = face_mesh.process(rgb)
        if not result.multi_face_landmarks:
            return None
        return [(int(p.x * w), int(p.y * h)) for p in result.multi_face_landmarks[0].landmark]

def polygon_mask(shape, points):
    mask = np.zeros(shape[:2], np.uint8)
    pts = np.array(points, np.int32)
    if len(pts) >= 3:
        cv2.fillPoly(mask, [pts], 255)
    return mask

def safe_points(lm, ids):
    try:
        return [lm[i] for i in ids]
    except Exception:
        return []

def make_face_region_masks(img):
    h, w = img.shape[:2]
    x, y, fw, fh = detect_face_bbox(img)
    lm = get_face_landmarks(img)

    regions = {}

    if lm is not None and len(lm) >= 468:
        # MediaPipe landmark-based regions.
        # These follow the actual detected face, so they adjust better to different face sizes.
        left_eye_pts = safe_points(lm, [33, 246, 161, 160, 159, 158, 157, 173, 133, 155, 154, 153, 145, 144, 163, 7])
        right_eye_pts = safe_points(lm, [263, 466, 388, 387, 386, 385, 384, 398, 362, 382, 381, 380, 374, 373, 390, 249])

        lcx = int(np.mean([p[0] for p in left_eye_pts]))
        lcy = int(np.mean([p[1] for p in left_eye_pts]))
        rcx = int(np.mean([p[0] for p in right_eye_pts]))
        rcy = int(np.mean([p[1] for p in right_eye_pts]))
        eye_y = int((lcy + rcy) / 2)
        eye_gap = max(1, rcx - lcx)
        nose_cx = int((lcx + rcx) / 2)

        face_top = min(p[1] for p in safe_points(lm, [10, 67, 109, 338, 297]))
        chin_y = lm[152][1]
        mouth_bottom_y = max(lm[14][1], lm[17][1], lm[18][1])
        nose_bottom_y = lm[2][1]

        # Forehead: above eyebrows, inside the upper face.
        forehead_y = int(face_top + (eye_y - face_top) * 0.55)
        regions["forehead"] = elliptical_mask(
            img.shape,
            (nose_cx, forehead_y),
            (int(eye_gap * 0.48), int(fh * 0.055)),
            blur=0
        )

        # Undereye: directly below the actual eye landmarks, but not on the eye.
        under_y = int(eye_y + max(10, fh * 0.050))
        under_axes = (max(14, int(eye_gap * 0.18)), max(7, int(fh * 0.026)))
        under = np.zeros((h, w), np.uint8)
        cv2.ellipse(under, (lcx, under_y), under_axes, 0, 0, 360, 255, -1)
        cv2.ellipse(under, (rcx, under_y), under_axes, 0, 0, 360, 255, -1)
        regions["undereye"] = under

        # Nose based on real nose bridge and tip landmarks.
        nose_pts = safe_points(lm, [168, 6, 197, 195, 5, 4, 1, 19, 94, 2, 98, 327, 358, 129])
        regions["nose"] = polygon_mask(img.shape, nose_pts)
        if cv2.countNonZero(regions["nose"]) < 40:
            regions["nose"] = elliptical_mask(img.shape, (nose_cx, int((eye_y + nose_bottom_y) / 2)), (int(eye_gap * 0.18), int(fh * 0.145)), blur=0)

        # Cheeks are lower than undereye and outward from the nose.
        cheek_y = int(eye_y + (mouth_bottom_y - eye_y) * 0.45)
        left_cheek_cx = int(lcx - eye_gap * 0.10)
        right_cheek_cx = int(rcx + eye_gap * 0.10)
        cheek_axes = (int(eye_gap * 0.23), int(fh * 0.120))
        regions["left_cheek"] = elliptical_mask(img.shape, (left_cheek_cx, cheek_y), cheek_axes, blur=0)
        regions["right_cheek"] = elliptical_mask(img.shape, (right_cheek_cx, cheek_y), cheek_axes, blur=0)

        # Chin below lower lip, between mouth and actual chin landmark.
        chin_center_y = int(mouth_bottom_y + (chin_y - mouth_bottom_y) * 0.50)
        regions["chin"] = elliptical_mask(
            img.shape,
            (nose_cx, chin_center_y),
            (int(eye_gap * 0.34), int(max(10, (chin_y - mouth_bottom_y) * 0.28))),
            blur=0
        )

        # Prevent overlaps between neighboring regions.
        eye_protection = cv2.dilate(regions["undereye"], np.ones((max(7, int(fw * 0.030)), max(7, int(fw * 0.030))), np.uint8), iterations=2)
        nose_protection = cv2.dilate(regions["nose"], np.ones((max(5, int(fw * 0.018)), max(5, int(fw * 0.018))), np.uint8), iterations=1)
        mouth_protection = elliptical_mask(img.shape, (nose_cx, int(mouth_bottom_y - fh * 0.015)), (int(eye_gap * 0.38), int(fh * 0.055)), blur=0)

        protection_for_cheeks = cv2.bitwise_or(eye_protection, nose_protection)
        regions["left_cheek"] = cv2.bitwise_and(regions["left_cheek"], cv2.bitwise_not(protection_for_cheeks))
        regions["right_cheek"] = cv2.bitwise_and(regions["right_cheek"], cv2.bitwise_not(protection_for_cheeks))
        regions["chin"] = cv2.bitwise_and(regions["chin"], cv2.bitwise_not(mouth_protection))

        return regions, (x, y, fw, fh)

    # Fallback if MediaPipe is unavailable: eye-cascade proportional placement.
    left_eye, right_eye = detect_eyes_in_face(img, (x, y, fw, fh))
    lx, ly, lew, leh, lcx, lcy = left_eye
    rx, ry, rew, reh, rcx, rcy = right_eye

    eye_y = int((lcy + rcy) / 2)
    eye_gap = max(1, rcx - lcx)
    nose_cx = int((lcx + rcx) / 2)

    regions["forehead"] = elliptical_mask(img.shape, (nose_cx, int(y + fh * 0.22)), (int(fw * 0.22), int(fh * 0.055)), blur=0)

    under_y = int(eye_y + max(fh * 0.065, max(leh, reh) * 0.80))
    under_axes = (max(14, int(eye_gap * 0.16)), max(7, int(fh * 0.028)))
    under = np.zeros((h, w), np.uint8)
    cv2.ellipse(under, (lcx, under_y), under_axes, 0, 0, 360, 255, -1)
    cv2.ellipse(under, (rcx, under_y), under_axes, 0, 0, 360, 255, -1)
    regions["undereye"] = under

    regions["nose"] = elliptical_mask(img.shape, (nose_cx, int(eye_y + fh * 0.18)), (int(fw * 0.070), int(fh * 0.135)), blur=0)

    cheek_y = int(eye_y + fh * 0.260)
    regions["left_cheek"] = elliptical_mask(img.shape, (int(x + fw * 0.285), cheek_y), (int(fw * 0.090), int(fh * 0.120)), blur=0)
    regions["right_cheek"] = elliptical_mask(img.shape, (int(x + fw * 0.715), cheek_y), (int(fw * 0.090), int(fh * 0.120)), blur=0)

    protection = cv2.bitwise_or(
        cv2.dilate(regions["undereye"], np.ones((max(7, int(fw * 0.030)), max(7, int(fw * 0.030))), np.uint8), iterations=2),
        cv2.dilate(regions["nose"], np.ones((max(5, int(fw * 0.018)), max(5, int(fw * 0.018))), np.uint8), iterations=1)
    )
    regions["left_cheek"] = cv2.bitwise_and(regions["left_cheek"], cv2.bitwise_not(protection))
    regions["right_cheek"] = cv2.bitwise_and(regions["right_cheek"], cv2.bitwise_not(protection))

    # Chin lower than lip estimate.
    regions["chin"] = elliptical_mask(img.shape, (nose_cx, int(y + fh * 0.850)), (int(fw * 0.145), int(fh * 0.060)), blur=0)

    return regions, (x, y, fw, fh)


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

def detect_eyes_in_face(img, bbox):
    x, y, fw, fh = bbox
    gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
    face_gray = gray[y:y+fh, x:x+fw]
    eye_path = cv2.data.haarcascades + "haarcascade_eye.xml"
    eye_cascade = cv2.CascadeClassifier(eye_path)

    search_top = int(fh * 0.20)
    search_bottom = int(fh * 0.58)
    roi = face_gray[search_top:search_bottom, :]
    eyes = eye_cascade.detectMultiScale(
        roi,
        scaleFactor=1.08,
        minNeighbors=5,
        minSize=(max(14, fw // 14), max(10, fh // 20))
    )

    candidates = []
    for ex, ey, ew, eh in eyes:
        gx = x + int(ex)
        gy = y + search_top + int(ey)
        cx = gx + int(ew / 2)
        cy = gy + int(eh / 2)
        relx = (cx - x) / max(1, fw)
        rely = (cy - y) / max(1, fh)
        if 0.16 <= relx <= 0.84 and 0.24 <= rely <= 0.52:
            candidates.append((gx, gy, int(ew), int(eh), cx, cy))

    if len(candidates) >= 2:
        lefts = [e for e in candidates if e[4] < x + fw * 0.50]
        rights = [e for e in candidates if e[4] >= x + fw * 0.50]
        if lefts and rights:
            expected_y = y + fh * 0.38
            left = sorted(lefts, key=lambda e: abs(e[5] - expected_y))[0]
            right = sorted(rights, key=lambda e: abs(e[5] - expected_y))[0]
            return left, right

    # fallback if eye cascade fails
    left = (
        x + int(fw * 0.29), y + int(fh * 0.36),
        int(fw * 0.15), int(fh * 0.075),
        x + int(fw * 0.365), y + int(fh * 0.397)
    )
    right = (
        x + int(fw * 0.56), y + int(fh * 0.36),
        int(fw * 0.15), int(fh * 0.075),
        x + int(fw * 0.635), y + int(fh * 0.397)
    )
    return left, right

def make_face_region_masks(img):
    h, w = img.shape[:2]
    x, y, fw, fh = detect_face_bbox(img)

    left_eye, right_eye = detect_eyes_in_face(img, (x, y, fw, fh))
    lx, ly, lew, leh, lcx, lcy = left_eye
    rx, ry, rew, reh, rcx, rcy = right_eye

    eye_y = int((lcy + rcy) / 2)
    eye_gap = max(1, rcx - lcx)
    nose_cx = int((lcx + rcx) / 2)

    regions = {}

    # Forehead above eyes
    regions["forehead"] = elliptical_mask(
        img.shape,
        (nose_cx, int(y + fh * 0.22)),
        (int(fw * 0.22), int(fh * 0.055)),
        blur=0
    )

    # Undereye placed below detected eyes
    under_y = int(eye_y + max(fh * 0.065, max(leh, reh) * 0.80))
    under_axes = (max(14, int(eye_gap * 0.16)), max(7, int(fh * 0.028)))
    under = np.zeros((h, w), np.uint8)
    cv2.ellipse(under, (lcx, under_y), under_axes, 0, 0, 360, 255, -1)
    cv2.ellipse(under, (rcx, under_y), under_axes, 0, 0, 360, 255, -1)
    regions["undereye"] = under

    # Nose centered between eyes
    nose_cy = int(eye_y + fh * 0.18)
    regions["nose"] = elliptical_mask(
        img.shape,
        (nose_cx, nose_cy),
        (int(fw * 0.070), int(fh * 0.135)),
        blur=0
    )

    # Cheeks lower and outward, with protection so they do not overlap the undereye
    cheek_y = int(eye_y + fh * 0.245)
    left_cheek_cx = int(x + fw * 0.285)
    right_cheek_cx = int(x + fw * 0.715)
    cheek_axes = (int(fw * 0.095), int(fh * 0.130))
    regions["left_cheek"] = elliptical_mask(img.shape, (left_cheek_cx, cheek_y), cheek_axes, blur=0)
    regions["right_cheek"] = elliptical_mask(img.shape, (right_cheek_cx, cheek_y), cheek_axes, blur=0)

    eye_protection = cv2.dilate(
        regions["undereye"],
        np.ones((max(5, int(fw * 0.025)), max(5, int(fw * 0.025))), np.uint8),
        iterations=2
    )
    nose_protection = cv2.dilate(
        regions["nose"],
        np.ones((max(5, int(fw * 0.018)), max(5, int(fw * 0.018))), np.uint8),
        iterations=1
    )
    protection = cv2.bitwise_or(eye_protection, nose_protection)
    regions["left_cheek"] = cv2.bitwise_and(regions["left_cheek"], cv2.bitwise_not(protection))
    regions["right_cheek"] = cv2.bitwise_and(regions["right_cheek"], cv2.bitwise_not(protection))

    # Chin below the lips, not on the lips
    chin_cy = int(y + fh * 0.835)
    regions["chin"] = elliptical_mask(
        img.shape,
        (nose_cx, chin_cy),
        (int(fw * 0.145), int(fh * 0.065)),
        blur=0
    )

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

def issue_masks(img):
    hsv = cv2.cvtColor(img, cv2.COLOR_BGR2HSV)
    lab = cv2.cvtColor(img, cv2.COLOR_BGR2LAB)
    gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
    skin = (skin_mask_bgr(img) > 35).astype(np.uint8) * 255

    red1 = cv2.inRange(hsv, np.array([0, 40, 45]), np.array([18, 255, 255]))
    red2 = cv2.inRange(hsv, np.array([158, 40, 45]), np.array([180, 255, 255]))
    redness = cv2.bitwise_and(cv2.bitwise_or(red1, red2), skin)
    redness = cv2.morphologyEx(redness, cv2.MORPH_OPEN, np.ones((3, 3), np.uint8))

    mean = cv2.mean(gray, mask=skin)[0]
    dark = cv2.inRange(gray, 0, int(max(45, mean - 22)))
    dark = cv2.bitwise_and(dark, skin)
    dark = cv2.morphologyEx(dark, cv2.MORPH_OPEN, np.ones((3, 3), np.uint8))

    lap = cv2.convertScaleAbs(cv2.Laplacian(gray, cv2.CV_64F))
    texture = cv2.inRange(lap, 18, 255)
    texture = cv2.bitwise_and(texture, skin)
    texture = cv2.morphologyEx(texture, cv2.MORPH_OPEN, np.ones((2, 2), np.uint8))

    # Pore-like signal: small dark points on skin, not whole shadows.
    blur = cv2.GaussianBlur(gray, (0, 0), 2)
    local_dark = cv2.subtract(blur, gray)
    pores = cv2.inRange(local_dark, 10, 255)
    pores = cv2.bitwise_and(pores, skin)
    pores = cv2.morphologyEx(pores, cv2.MORPH_OPEN, np.ones((2, 2), np.uint8))
    return {"redness": redness, "dark": dark, "texture": texture, "pores": pores}

def draw_segment_overlay(face_img, regions, issue_scores, offset=(0,0)):
    ox, oy = offset
    overlay = face_img.copy()
    mapping = [
        ("forehead", "red", "1"),
        ("left_cheek", "orange", "2"),
        ("right_cheek", "green", "3"),
        ("undereye", "purple", "4"),
        ("nose", "blue", "5"),
        ("chin", "teal", "6"),
    ]
    for key, cname, num in mapping:
        mask = regions[key]
        color = COLORS[cname]
        # Soft tint only inside the exact small segmented region.
        colored = overlay.copy()
        colored[mask > 0] = color
        overlay = cv2.addWeighted(colored, 0.08, overlay, 0.92, 0)

        contours, _ = cv2.findContours(mask, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
        for c in contours:
            if cv2.contourArea(c) < 20:
                continue
            c = c + np.array([[[ox, oy]]])
            cv2.drawContours(face_img, [c], -1, color, 3, cv2.LINE_AA)

    # blend tinted exact regions
    face_img[:] = cv2.addWeighted(overlay, 0.55, face_img, 0.45, 0)

def _put_label_box(canvas, text, x, y, color, side="right"):
    """Draws readable callout text with a tiny white backing so labels stay clean."""
    scale = 0.42
    thickness = 1
    (tw, th), _ = cv2.getTextSize(text, cv2.FONT_HERSHEY_SIMPLEX, scale, thickness)
    pad_x, pad_y = 7, 5
    H, W = canvas.shape[:2]
    if side == "left":
        x = max(8, min(x, W - tw - 2 * pad_x - 8))
    else:
        x = max(8, min(x, W - tw - 2 * pad_x - 8))
    y = max(20, min(y, H - 20))
    cv2.rectangle(canvas, (x - pad_x, y - th - pad_y), (x + tw + pad_x, y + pad_y), (255,255,255), -1)
    cv2.rectangle(canvas, (x - pad_x, y - th - pad_y), (x + tw + pad_x, y + pad_y), color, 1)
    cv2.putText(canvas, text, (x, y), cv2.FONT_HERSHEY_SIMPLEX, scale, color, thickness, cv2.LINE_AA)

def draw_callouts(canvas, img_area, regions, x0, y0, scale_x, scale_y):
    # Fixed text lanes. These avoid the previous overlap where NOSE AREA and
    # RIGHT CHEEK AREA were placed on almost the same line.
    # Values are relative to the displayed image height so the layout still
    # works with different face sizes and image dimensions.
    labels = [
        ("forehead",    "1", "FOREHEAD AREA",    "red",    "right", 0.26),
        ("nose",        "5", "NOSE AREA",        "blue",   "right", 0.43),
        ("right_cheek", "3", "RIGHT CHEEK AREA", "green",  "right", 0.48),
        ("chin",        "6", "CHIN AREA",        "teal",   "right", 0.63),
        ("undereye",    "4", "UNDEREYE AREA",    "purple", "left",  0.38),
        ("left_cheek",  "2", "LEFT CHEEK AREA",  "orange", "left",  0.49),
    ]
    H, W = canvas.shape[:2]
    _, _, iw, ih = img_area
    left_badge_x = max(38, x0 - 72)
    right_badge_x = min(W - 92, x0 + iw + 58)

    for key, num, name, cname, side, lane_ratio in labels:
        mask = regions[key]
        ys, xs = np.where(mask > 0)
        if len(xs) == 0:
            continue
        cx = int(x0 + np.mean(xs) * scale_x)
        cy = int(y0 + np.mean(ys) * scale_y)
        color = COLORS[cname]
        by = int(y0 + ih * lane_ratio)
        by = int(np.clip(by, y0 + 22, y0 + ih - 22))

        if side == "left":
            bx = left_badge_x
            label_x = bx - 178
            label_x = max(12, label_x)
            cv2.line(canvas, (cx, cy), (bx, by), color, 2, cv2.LINE_AA)
            cv2.circle(canvas, (bx, by), 14, color, -1, cv2.LINE_AA)
            cv2.putText(canvas, num, (bx-5, by+5), cv2.FONT_HERSHEY_SIMPLEX, 0.48, (255,255,255), 2, cv2.LINE_AA)
            _put_label_box(canvas, name, label_x, by+5, color, "left")
        else:
            bx = right_badge_x
            label_x = bx + 22
            # Keep right labels fully inside the report canvas.
            label_x = min(label_x, W - 205)
            cv2.line(canvas, (cx, cy), (bx, by), color, 2, cv2.LINE_AA)
            cv2.circle(canvas, (bx, by), 14, color, -1, cv2.LINE_AA)
            cv2.putText(canvas, num, (bx-5, by+5), cv2.FONT_HERSHEY_SIMPLEX, 0.48, (255,255,255), 2, cv2.LINE_AA)
            _put_label_box(canvas, name, label_x, by+5, color, "right")

def compute_findings(img, regions):
    masks = issue_masks(img)
    data = {}
    for key in regions:
        r = regions[key]
        red = score_region(masks["redness"], r)
        dark = score_region(masks["dark"], r)
        texture = score_region(masks["texture"], r)
        pores = score_region(masks["pores"], r)
        if key == "forehead":
            main = max(red, texture)
            finding = "Redness/acne-like signals and uneven texture."
        elif key in ("left_cheek", "right_cheek"):
            main = max(dark, red)
            finding = "Pigmentation/dark-spot-like signals and uneven tone."
        elif key == "undereye":
            main = max(dark, 10)
            finding = "Dark-circle/shadowing-like signal."
        elif key == "nose":
            main = max(pores, texture)
            finding = "Pore/blackhead-like signal on T-zone."
        else:
            main = max(texture, red)
            finding = "Texture unevenness/blemish-like signal."
        data[key] = {
            "red": red, "dark": dark, "texture": texture, "pores": pores,
            "score": min(100.0, main), "severity": severity_from_score(main), "finding": finding
        }
    return data

def bar(canvas, x, y, w, pct, color, label):
    cv2.putText(canvas, label, (x, y+4), cv2.FONT_HERSHEY_SIMPLEX, 0.42, COLORS["navy"], 1, cv2.LINE_AA)
    bx = x + 168
    cv2.line(canvas, (bx, y), (bx+w, y), (225,225,225), 7, cv2.LINE_AA)
    cv2.line(canvas, (bx, y), (bx+int(w*pct/100.0), y), color, 7, cv2.LINE_AA)
    cv2.putText(canvas, f"{int(round(pct))}%", (bx+w+14, y+4), cv2.FONT_HERSHEY_SIMPLEX, 0.40, COLORS["navy"], 1, cv2.LINE_AA)

def draw_finding_card(canvas, x, y, w, h, num, title, color, zone, finding, severity):
    rounded_rect(canvas, (x, y), (x+w, y+h), (255,255,255), radius=12, thickness=-1)
    cv2.rectangle(canvas, (x, y), (x+w, y+h), (225,225,225), 1)
    cv2.circle(canvas, (x+24, y+28), 14, color, -1, cv2.LINE_AA)
    cv2.putText(canvas, str(num), (x+19, y+34), cv2.FONT_HERSHEY_SIMPLEX, 0.45, (255,255,255), 2, cv2.LINE_AA)
    # Keep long titles from colliding with the severity badge.
    draw_text(canvas, title, (x+48, y+26), scale=0.43, color=color, thickness=2, max_width=w-150, line_gap=16)
    # severity small badge
    sev_col = (60,170,60) if severity in ("Low","Mild") else ((0,135,255) if severity=="Moderate" else (45,45,220))
    cv2.rectangle(canvas, (x+w-92, y+13), (x+w-14, y+36), sev_col, 1)
    cv2.putText(canvas, severity, (x+w-84, y+29), cv2.FONT_HERSHEY_SIMPLEX, 0.32, sev_col, 1, cv2.LINE_AA)
    draw_text(canvas, "Zone: " + zone, (x+48, y+52), scale=0.34, color=(45,45,45), thickness=1, max_width=w-68, line_gap=15)
    draw_text(canvas, "Finding: " + finding, (x+48, y+72), scale=0.34, color=(45,45,45), thickness=1, max_width=w-68, line_gap=15)

def process_general_skin_assessment(input_path, output_path):
    src = resize_for_processing(read_image(input_path), 1200)
    h, w = src.shape[:2]
    regions, bbox = make_face_region_masks(src)
    findings = compute_findings(src, regions)

    # Report canvas: wide enough for different images, with findings at the lower part.
    W = 1300
    H = 1500
    canvas = np.full((H, W, 3), 255, dtype=np.uint8)

    # Header
    cv2.rectangle(canvas, (0,0), (W,80), (45, 24, 5), -1)
    cv2.putText(canvas, "GENERAL SKIN ASSESSMENT", (315, 48), cv2.FONT_HERSHEY_SIMPLEX, 1.25, (255,255,255), 2, cv2.LINE_AA)
    cv2.putText(canvas, "AREA-BY-AREA EDUCATIONAL ANALYSIS", (440, 74), cv2.FONT_HERSHEY_SIMPLEX, 0.48, (220,230,245), 1, cv2.LINE_AA)

    # Image area bigger and centered
    max_img_w, max_img_h = 820, 590
    scale = min(max_img_w / w, max_img_h / h)
    nw, nh = int(w * scale), int(h * scale)
    resized = cv2.resize(src, (nw, nh), interpolation=cv2.INTER_AREA)
    x0 = (W - nw) // 2
    y0 = 98
    canvas[y0:y0+nh, x0:x0+nw] = resized

    # Draw segmented overlays on a transparent layer based on scaled masks
    scaled_regions = {}
    for k, m in regions.items():
        scaled_regions[k] = cv2.resize(m, (nw, nh), interpolation=cv2.INTER_NEAREST)
    local = canvas[y0:y0+nh, x0:x0+nw].copy()
    draw_segment_overlay(local, scaled_regions, findings)
    canvas[y0:y0+nh, x0:x0+nw] = local
    draw_callouts(canvas, (x0, y0, nw, nh), scaled_regions, x0, y0, 1.0, 1.0)

    # Lower findings section
    panel_y = y0 + nh + 28
    rounded_rect(canvas, (28, panel_y), (W-28, H-78), (252,252,252), radius=16, thickness=-1)
    cv2.rectangle(canvas, (28, panel_y), (W-28, H-78), (225,225,225), 1)
    cv2.putText(canvas, "AREA-BY-AREA EDUCATIONAL FINDINGS", (400, panel_y+42), cv2.FONT_HERSHEY_SIMPLEX, 0.72, COLORS["navy"], 2, cv2.LINE_AA)

    card_w, card_h = 375, 130
    cols = [65, 470, 875]
    rows = [panel_y+65, panel_y+205]
    cards = [
        ("forehead", 1, "FOREHEAD AREA", "red", "Forehead/upper face"),
        ("left_cheek", 2, "LEFT CHEEK AREA", "orange", "Left mid-to-lower cheek"),
        ("right_cheek", 3, "RIGHT CHEEK AREA", "green", "Right mid-to-lower cheek"),
        ("undereye", 4, "UNDEREYE AREA", "purple", "Both left and right under-eye areas"),
        ("nose", 5, "NOSE AREA (T-ZONE)", "blue", "Nose bridge, sides, and tip"),
        ("chin", 6, "CHIN AREA", "teal", "Central chin and lower jawline"),
    ]
    for idx, (key, num, title, cname, zone) in enumerate(cards):
        draw_finding_card(canvas, cols[idx % 3], rows[idx // 3], card_w, card_h, num, title, COLORS[cname], zone, findings[key]["finding"], findings[key]["severity"])

    # Summary panels
    sy = panel_y + 360
    summary_x = 55
    cv2.putText(canvas, "OVERALL SUMMARY", (summary_x, sy), cv2.FONT_HERSHEY_SIMPLEX, 0.58, COLORS["navy"], 2, cv2.LINE_AA)
    red_pct = (findings["forehead"]["score"] + findings["left_cheek"]["red"] + findings["right_cheek"]["red"]) / 3
    pigment_pct = (findings["left_cheek"]["dark"] + findings["right_cheek"]["dark"]) / 2
    texture_pct = (findings["chin"]["texture"] + findings["forehead"]["texture"]) / 2
    pores_pct = findings["nose"]["pores"]
    under_pct = findings["undereye"]["score"]
    bar(canvas, summary_x, sy+45, 155, red_pct, COLORS["red"], "Redness / acne-like")
    bar(canvas, summary_x, sy+82, 155, pigment_pct, COLORS["orange"], "Pigmentation / spots")
    bar(canvas, summary_x, sy+119, 155, texture_pct, COLORS["blue"], "Texture / pores")
    bar(canvas, summary_x, sy+156, 155, under_pct, COLORS["purple"], "Undereye shadowing")

    guide_x = 485
    cv2.putText(canvas, "SEVERITY GUIDE", (guide_x, sy), cv2.FONT_HERSHEY_SIMPLEX, 0.58, COLORS["navy"], 2, cv2.LINE_AA)
    sev = [("Low/Mild", "0-17%", COLORS["green"]), ("Moderate", "18-34%", COLORS["orange"]), ("High", "35%+", COLORS["red"])]
    gy = sy+45
    for name, rng, col in sev:
        cv2.circle(canvas, (guide_x, gy-4), 6, col, -1)
        cv2.putText(canvas, name, (guide_x+18, gy), cv2.FONT_HERSHEY_SIMPLEX, 0.45, col, 1, cv2.LINE_AA)
        cv2.putText(canvas, rng, (guide_x+150, gy), cv2.FONT_HERSHEY_SIMPLEX, 0.45, COLORS["navy"], 1, cv2.LINE_AA)
        gy += 37

    rec_x = 760
    cv2.putText(canvas, "RECOMMENDED VISUALIZATIONS", (rec_x, sy), cv2.FONT_HERSHEY_SIMPLEX, 0.58, COLORS["navy"], 2, cv2.LINE_AA)
    recs = [("CO2 Laser + Dermapen", "for redness & texture", COLORS["red"]),
            ("PICO Carbon Laser", "for pigmentation & pores", COLORS["blue"]),
            ("Diamond Peel Facial", "for glow & exfoliation", COLORS["orange"]),
            ("Undereye + Lip Filler", "for dark circles & lip hydration", COLORS["purple"])]
    for i, (name, sub, col) in enumerate(recs):
        rx = rec_x + (i % 2) * 245
        ry = sy + 28 + (i // 2) * 82
        rounded_rect(canvas, (rx, ry), (rx+225, ry+65), (255,255,255), radius=10, thickness=-1)
        cv2.rectangle(canvas, (rx, ry), (rx+225, ry+65), col, 1)
        cv2.circle(canvas, (rx+24, ry+32), 18, col, -1)
        cv2.putText(canvas, "✓", (rx+16, ry+40), cv2.FONT_HERSHEY_SIMPLEX, 0.55, (255,255,255), 2, cv2.LINE_AA)
        cv2.putText(canvas, name, (rx+52, ry+27), cv2.FONT_HERSHEY_SIMPLEX, 0.38, COLORS["navy"], 1, cv2.LINE_AA)
        cv2.putText(canvas, sub, (rx+52, ry+47), cv2.FONT_HERSHEY_SIMPLEX, 0.32, COLORS["gray"], 1, cv2.LINE_AA)

    # Disclaimer strip
    cv2.rectangle(canvas, (28, H-62), (W-28, H-20), (245,249,255), -1)
    cv2.rectangle(canvas, (28, H-62), (W-28, H-20), (220,230,245), 1)
    cv2.putText(canvas, "DISCLAIMER:", (55, H-36), cv2.FONT_HERSHEY_SIMPLEX, 0.45, COLORS["navy"], 2, cv2.LINE_AA)
    cv2.putText(canvas, DISCLAIMER, (170, H-36), cv2.FONT_HERSHEY_SIMPLEX, 0.42, COLORS["gray"], 1, cv2.LINE_AA)

    save_image(output_path, canvas)
    print("General Skin Assessment segmented educational report saved:", output_path)
    print(DISCLAIMER)
    sys.exit(0)

if __name__ == "__main__":
    if len(sys.argv) < 3:
        fail("Usage: python process_general_skin_assessment.py input output")
    process_general_skin_assessment(sys.argv[1], sys.argv[2])
