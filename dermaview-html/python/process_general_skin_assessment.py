
import cv2
import numpy as np
import sys
from pathlib import Path

try:
    import mediapipe as mp
    # Some environments have an incomplete mediapipe package where mp.solutions is missing.
    # The script must gracefully fall back to Haar-based regions in that case.
    if not hasattr(mp, "solutions"):
        mp = None
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
    """Fill a polygon exactly from ordered points. No convex hull, no ellipse."""
    mask = np.zeros(shape[:2], np.uint8)
    if points is None or len(points) < 3:
        return mask
    pts = np.array(points, np.int32)
    cv2.fillPoly(mask, [pts], 255)
    return mask

def hull_mask(shape, points):
    """Fallback helper only for feature protection, not for visible region shapes."""
    mask = np.zeros(shape[:2], np.uint8)
    if points is None or len(points) < 3:
        return mask
    pts = np.array(points, np.int32)
    hull = cv2.convexHull(pts)
    cv2.fillConvexPoly(mask, hull, 255)
    return mask

def clip_mask_to_skin(mask, skin):
    skin_bin = (skin > 30).astype(np.uint8) * 255
    return cv2.bitwise_and(mask, skin_bin)


def clip_mask_to_face(mask, face_mask):
    """Keep a region inside the detected face oval."""
    face_bin = (face_mask > 0).astype(np.uint8) * 255
    return cv2.bitwise_and(mask, face_bin)

def subtract_masks(mask, *remove_masks):
    out = mask.copy()
    for r in remove_masks:
        out = cv2.bitwise_and(out, cv2.bitwise_not(r))
    return out

def safe_points(lm, ids):
    try:
        return [lm[i] for i in ids]
    except Exception:
        return []

def make_face_region_masks_adaptive(img):
    """Adaptive facial region segmentation using detected MediaPipe landmarks.

    This version is intentionally VISIBLY different from the old one:
    - no ellipse regions when FaceMesh is detected
    - no convex-hull blob for visible areas
    - cheeks, chin, forehead, nose, and under-eye are built from detected
      anatomy-derived points, so they scale with each face shape and size
    """
    h, w = img.shape[:2]
    x, y, fw, fh = detect_face_bbox(img)
    lm = get_face_landmarks(img)
    regions = {}

    def _bbox_stats(points):
        xs = [p[0] for p in points]
        ys = [p[1] for p in points]
        minx, maxx = min(xs), max(xs)
        miny, maxy = min(ys), max(ys)
        bw, bh = maxx - minx, maxy - miny
        cx, cy = (minx + maxx) / 2.0, (miny + maxy) / 2.0
        return minx, miny, bw, bh, cx, cy

    def _plausible_landmarks(points):
        # Reject obviously wrong/partial landmarks.
        if points is None or len(points) < 468:
            return False

        minx, miny, bw, bh, cx, cy = _bbox_stats(points)

        # Landmarks should cover a reasonable portion of the image.
        if bw < w * 0.18 or bh < h * 0.22:
            return False
        if bw > w * 0.92 or bh > h * 0.95:
            return False

        # Face center should not be wildly off.
        if abs(cx - w / 2.0) > w * 0.35:
            return False
        if abs(cy - h / 2.0) > h * 0.30:
            return False

        # Avoid degenerate/clustered landmark sets.
        xs = np.array([p[0] for p in points], dtype=np.float32)
        ys = np.array([p[1] for p in points], dtype=np.float32)
        if float(xs.std()) < w * 0.05 or float(ys.std()) < h * 0.05:
            return False

        return True

    if lm is not None and len(lm) >= 468 and _plausible_landmarks(lm):
        print("Using REGION_V4 anatomical landmark polygons")


        def P(i):
            return lm[i]

        def pts(ids):
            return safe_points(lm, ids)

        def avg(ids):
            arr = pts(ids)
            return (int(np.mean([p[0] for p in arr])), int(np.mean([p[1] for p in arr])))

        def clamp_pt(pt):
            return (int(np.clip(pt[0], 0, w - 1)), int(np.clip(pt[1], 0, h - 1)))

        def make_poly(points):
            return polygon_mask(img.shape, [clamp_pt(p) for p in points])

        # Core detected anchors
        left_eye_ids  = [33, 246, 161, 160, 159, 158, 157, 173, 133, 155, 154, 153, 145, 144, 163, 7]
        right_eye_ids = [263, 466, 388, 387, 386, 385, 384, 398, 362, 382, 381, 380, 374, 373, 390, 249]
        left_eye = pts(left_eye_ids)
        right_eye = pts(right_eye_ids)
        lcx, lcy = avg(left_eye_ids)
        rcx, rcy = avg(right_eye_ids)
        mid_x = int((lcx + rcx) / 2)
        eye_y = int((lcy + rcy) / 2)
        eye_gap = max(1, rcx - lcx)

        brow_y = int(np.mean([p[1] for p in pts([70, 63, 105, 66, 107, 336, 296, 334, 293, 300])]))
        face_top_y = min(p[1] for p in pts([10, 67, 109, 338, 297]))
        chin_y = P(152)[1]
        mouth_top_y = min(P(13)[1], P(0)[1], P(267)[1], P(37)[1])
        mouth_bottom_y = max(P(14)[1], P(17)[1], P(18)[1])
        nose_tip = P(1)
        nose_bottom = P(2)

        face_oval_ids = [
            10,338,297,332,284,251,389,356,454,323,361,288,397,365,379,378,400,377,
            152,148,176,149,150,136,172,58,132,93,234,127,162,21,54,103,67,109
        ]
        face_mask = polygon_mask(img.shape, pts(face_oval_ids))
        eye_mask = cv2.bitwise_or(polygon_mask(img.shape, left_eye), polygon_mask(img.shape, right_eye))
        lip_mask = polygon_mask(img.shape, pts([61,185,40,39,37,0,267,269,270,409,291,375,321,405,314,17,84,181,91,146]))
        lip_protect = cv2.dilate(lip_mask, np.ones((max(5, fw // 45), max(5, fw // 45)), np.uint8), iterations=2)

        # 1) FOREHEAD — broad trapezoid between upper face and brows.
        # This avoids the tiny oval template look.
        forehead_top = int(face_top_y + (brow_y - face_top_y) * 0.12)
        forehead_bottom = int(brow_y - (brow_y - face_top_y) * 0.10)
        top_half = int(eye_gap * 0.48)
        bottom_half = int(eye_gap * 0.76)
        forehead_pts = [
            (mid_x - top_half, forehead_top),
            (mid_x - int(top_half * 0.45), face_top_y + int((brow_y - face_top_y) * 0.05)),
            (mid_x, face_top_y),
            (mid_x + int(top_half * 0.45), face_top_y + int((brow_y - face_top_y) * 0.05)),
            (mid_x + top_half, forehead_top),
            (mid_x + bottom_half, forehead_bottom),
            (mid_x + int(eye_gap * 0.28), forehead_bottom + int(fh * 0.012)),
            (mid_x, forehead_bottom + int(fh * 0.018)),
            (mid_x - int(eye_gap * 0.28), forehead_bottom + int(fh * 0.012)),
            (mid_x - bottom_half, forehead_bottom),
        ]
        regions["forehead"] = make_poly(forehead_pts)

        # 2) UNDEREYE — thin strips following lower eyelids, not circles.
        drop = max(5, int(fh * 0.030))
        left_lower = pts([33, 7, 163, 144, 145, 153, 154, 155, 133])
        right_lower = pts([362, 382, 381, 380, 374, 373, 390, 249, 263])
        left_under = left_lower + [(px, py + drop) for px, py in reversed(left_lower)]
        right_under = right_lower + [(px, py + drop) for px, py in reversed(right_lower)]
        regions["undereye"] = cv2.bitwise_or(make_poly(left_under), make_poly(right_under))
        regions["undereye"] = subtract_masks(regions["undereye"], eye_mask)

        # 3) NOSE — narrow bridge + nose wings + tip from landmarks.
        nose_top_y = int(brow_y + (nose_tip[1] - brow_y) * 0.06)
        nose_bridge_half = max(8, int(eye_gap * 0.105))
        nose_mid_half = max(12, int(eye_gap * 0.145))
        nose_wing_half = max(18, int(eye_gap * 0.215))
        nose_pts = [
            (mid_x - nose_bridge_half, nose_top_y),
            (mid_x + nose_bridge_half, nose_top_y),
            (mid_x + nose_mid_half, int((eye_y + nose_tip[1]) * 0.52)),
            (mid_x + nose_wing_half, int(nose_bottom[1] - fh * 0.015)),
            (mid_x + int(nose_wing_half * 0.55), int(nose_bottom[1] + fh * 0.030)),
            (mid_x, int(nose_bottom[1] + fh * 0.055)),
            (mid_x - int(nose_wing_half * 0.55), int(nose_bottom[1] + fh * 0.030)),
            (mid_x - nose_wing_half, int(nose_bottom[1] - fh * 0.015)),
            (mid_x - nose_mid_half, int((eye_y + nose_tip[1]) * 0.52)),
        ]
        regions["nose"] = make_poly(nose_pts)

        nose_protect = cv2.dilate(regions["nose"], np.ones((max(5, fw // 60), max(5, fw // 60)), np.uint8), iterations=1)
        under_protect = cv2.dilate(regions["undereye"], np.ones((max(5, fw // 60), max(5, fw // 60)), np.uint8), iterations=1)

        # 4) CHEEKS — larger cheekbone-to-lower-cheek polygons.
        # Uses landmark anchors and proportional points; visible shape changes per face.
        cheek_top_y = int(eye_y + fh * 0.065)
        cheek_mid_y = int(eye_y + (mouth_bottom_y - eye_y) * 0.50)
        cheek_low_y = int(mouth_bottom_y + (chin_y - mouth_bottom_y) * 0.18)

        left_outer_x = min(P(234)[0], P(93)[0], P(132)[0])
        right_outer_x = max(P(454)[0], P(323)[0], P(361)[0])
        left_inner_x = int(mid_x - eye_gap * 0.22)
        right_inner_x = int(mid_x + eye_gap * 0.22)
        left_mouth_x = P(61)[0]
        right_mouth_x = P(291)[0]

        left_cheek = [
            (left_outer_x + int(eye_gap * 0.12), cheek_top_y),
            (left_inner_x, cheek_top_y + int(fh * 0.015)),
            (left_inner_x - int(eye_gap * 0.04), cheek_mid_y),
            (left_mouth_x - int(eye_gap * 0.10), cheek_low_y),
            (left_outer_x + int(eye_gap * 0.18), cheek_low_y + int(fh * 0.040)),
            (left_outer_x, cheek_mid_y),
        ]
        right_cheek = [
            (right_outer_x - int(eye_gap * 0.12), cheek_top_y),
            (right_inner_x, cheek_top_y + int(fh * 0.015)),
            (right_inner_x + int(eye_gap * 0.04), cheek_mid_y),
            (right_mouth_x + int(eye_gap * 0.10), cheek_low_y),
            (right_outer_x - int(eye_gap * 0.18), cheek_low_y + int(fh * 0.040)),
            (right_outer_x, cheek_mid_y),
        ]
        regions["left_cheek"] = make_poly(left_cheek)
        regions["right_cheek"] = make_poly(right_cheek)

        remove_from_cheeks = cv2.bitwise_or(nose_protect, under_protect)
        remove_from_cheeks = cv2.bitwise_or(remove_from_cheeks, lip_protect)
        remove_from_cheeks = cv2.bitwise_or(remove_from_cheeks, eye_mask)
        regions["left_cheek"] = subtract_masks(regions["left_cheek"], remove_from_cheeks)
        regions["right_cheek"] = subtract_masks(regions["right_cheek"], remove_from_cheeks)

        # 5) CHIN — below lower lip and down toward real chin landmark.
        chin_top_y = int(mouth_bottom_y + fh * 0.035)
        chin_mid_y = int(mouth_bottom_y + (chin_y - mouth_bottom_y) * 0.46)
        chin_bottom_y = int(mouth_bottom_y + (chin_y - mouth_bottom_y) * 0.78)
        chin_half_top = int(eye_gap * 0.34)
        chin_half_mid = int(eye_gap * 0.50)
        chin_half_bottom = int(eye_gap * 0.30)
        chin_pts = [
            (mid_x - chin_half_top, chin_top_y),
            (mid_x + chin_half_top, chin_top_y),
            (mid_x + chin_half_mid, chin_mid_y),
            (mid_x + chin_half_bottom, chin_bottom_y),
            (mid_x, chin_bottom_y + int(fh * 0.020)),
            (mid_x - chin_half_bottom, chin_bottom_y),
            (mid_x - chin_half_mid, chin_mid_y),
        ]
        regions["chin"] = make_poly(chin_pts)
        regions["chin"] = subtract_masks(regions["chin"], lip_protect)

        # Keep visible zones inside the detected face oval only. Do NOT clip to skin here,
        # because skin-threshold clipping was hiding shape changes on bright images.
        for key in list(regions.keys()):
            regions[key] = clip_mask_to_face(regions[key], face_mask)
            regions[key] = cv2.morphologyEx(regions[key], cv2.MORPH_CLOSE, np.ones((3, 3), np.uint8))

        return regions, (x, y, fw, fh)

    print("Using fallback ellipse regions because MediaPipe landmarks were not detected")
    return make_face_region_masks_fallback(img)

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

def make_face_region_masks_fallback(img):
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

    # Undereye fallback: use detected-eye centers only when MediaPipe landmarks are unavailable.
    # Do NOT use MediaPipe landmark ids here because lm does not exist in the fallback path.
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



def make_face_region_masks(img):
    """Adaptive region segmentation. Uses MediaPipe FaceMesh landmarks when available,
    and only falls back to Haar/proportional placement if landmarks cannot be detected.
    This makes the areas adjust to different face sizes and positions instead of using
    a fixed template.
    """
    return make_face_region_masks_adaptive(img)

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

    # Report canvas: larger face image, with only area findings below.
    W = 1300
    H = 1350
    canvas = np.full((H, W, 3), 255, dtype=np.uint8)

    # Header
    cv2.rectangle(canvas, (0,0), (W,80), (45, 24, 5), -1)
    cv2.putText(canvas, "GENERAL SKIN ASSESSMENT", (315, 48), cv2.FONT_HERSHEY_SIMPLEX, 1.25, (255,255,255), 2, cv2.LINE_AA)
    cv2.putText(canvas, "AREA-BY-AREA EDUCATIONAL ANALYSIS", (440, 74), cv2.FONT_HERSHEY_SIMPLEX, 0.48, (220,230,245), 1, cv2.LINE_AA)

    # Image area bigger and centered
    max_img_w, max_img_h = 980, 720
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

    # Overall summary, severity guide, and recommended visualization blocks were removed
    # so the output focuses on the enlarged detected face and area-by-area findings.

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
