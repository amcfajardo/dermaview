
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

COLORS = {
    'red': (40, 55, 235),
    'orange': (0, 150, 255),
    'blue': (225, 105, 20),
    'purple': (190, 70, 155),
    'green': (70, 165, 65),
    'dark': (35, 35, 35),
    'line': (210, 210, 210),
}


def severity(score):
    if score < 8:
        return 'None'
    if score < 28:
        return 'Mild'
    if score < 55:
        return 'Moderate'
    return 'High'


def pct(mask, area_mask):
    denom = max(1, cv2.countNonZero(area_mask))
    return 100.0 * cv2.countNonZero(cv2.bitwise_and(mask, area_mask)) / denom


def region_masks(img, bbox):
    x, y, w, h = bbox
    return {
        'FOREHEAD AREA': ellipse_mask(img.shape, (x+w*0.50, y+h*0.23), (w*0.29, h*0.105), 0, 0),
        'LEFT CHEEK AREA': ellipse_mask(img.shape, (x+w*0.33, y+h*0.53), (w*0.15, h*0.18), -10, 0),
        'RIGHT CHEEK AREA': ellipse_mask(img.shape, (x+w*0.67, y+h*0.53), (w*0.15, h*0.18), 10, 0),
        'UNDEREYE AREA': cv2.bitwise_or(
            ellipse_mask(img.shape, (x+w*0.34, y+h*0.39), (w*0.13, h*0.045), 0, 0),
            ellipse_mask(img.shape, (x+w*0.66, y+h*0.39), (w*0.13, h*0.045), 0, 0)
        ),
        'NOSE AREA': ellipse_mask(img.shape, (x+w*0.50, y+h*0.50), (w*0.09, h*0.17), 0, 0),
        'CHIN AREA': ellipse_mask(img.shape, (x+w*0.50, y+h*0.78), (w*0.20, h*0.10), 0, 0),
    }



# ------------------------------------------------------------
# Professional area-based visual reporting utilities
# ------------------------------------------------------------
def draw_dashed_ellipse(img, center, axes, color, thickness=1, dash_deg=7, gap_deg=7):
    """Thin dashed ellipse for professional, non-heavy area marking."""
    start = 0
    while start < 360:
        end = min(start + dash_deg, 360)
        cv2.ellipse(img, tuple(map(int, center)), tuple(map(int, axes)), 0, start, end, color, thickness, cv2.LINE_AA)
        start += dash_deg + gap_deg


def draw_soft_area(img, mask, color, alpha=0.10):
    overlay = img.copy()
    overlay[mask > 0] = color
    return cv2.addWeighted(overlay, alpha, img, 1 - alpha, 0)


def pill(img, x, y, w, h, text_value, color):
    cv2.rectangle(img, (x, y), (x+w, y+h), (245, 248, 252), -1, cv2.LINE_AA)
    cv2.rectangle(img, (x, y), (x+w, y+h), color, 1, cv2.LINE_AA)
    tw = cv2.getTextSize(text_value, cv2.FONT_HERSHEY_SIMPLEX, 0.42, 1)[0][0]
    cv2.putText(img, text_value, (x + max(6, (w-tw)//2), y + h - 8), cv2.FONT_HERSHEY_SIMPLEX, 0.42, color, 1, cv2.LINE_AA)


def put_wrapped(img, s, x, y, max_chars, scale=0.46, color=(45,45,45), thick=1, line_h=18):
    words = str(s).split()
    lines, cur = [], ''
    for word in words:
        if len(cur) + len(word) + 1 <= max_chars:
            cur = (cur + ' ' + word).strip()
        else:
            if cur:
                lines.append(cur)
            cur = word
    if cur:
        lines.append(cur)
    for line in lines[:3]:
        cv2.putText(img, line, (x, y), cv2.FONT_HERSHEY_SIMPLEX, scale, color, thick, cv2.LINE_AA)
        y += line_h
    return y


def face_regions(shape, bbox):
    x, y, w, h = bbox
    # region colors are BGR for OpenCV
    data = [
        ('Forehead Area', 'redness / acne-like', (0, 70, 235), (x+w*0.50, y+h*0.19), (w*0.34, h*0.105)),
        ('Left Cheek Area', 'pigmentation / dark-spot-like', (0, 135, 255), (x+w*0.30, y+h*0.50), (w*0.17, h*0.22)),
        ('Right Cheek Area', 'pigmentation / dark-spot-like', (55, 170, 55), (x+w*0.70, y+h*0.50), (w*0.17, h*0.22)),
        ('Undereye Area', 'dark-circle / shadowing-like', (190, 80, 190), (x+w*0.50, y+h*0.335), (w*0.31, h*0.055)),
        ('Nose Area', 'pores / blackhead-like', (220, 130, 20), (x+w*0.50, y+h*0.45), (w*0.095, h*0.205)),
        ('Chin Area', 'texture unevenness', (190, 145, 30), (x+w*0.50, y+h*0.76), (w*0.24, h*0.105)),
    ]
    out = []
    face = face_oval_mask(np.zeros(shape, dtype=np.uint8), bbox, blur=0)
    for idx, (name, concern, color, center, axes) in enumerate(data, 1):
        mask = ellipse_mask(shape, center, axes, 0, 0)
        mask = cv2.bitwise_and(mask, face)
        out.append({'id':idx, 'name':name, 'concern':concern, 'color':color, 'center':center, 'axes':axes, 'mask':mask})
    return out


def severity_label(score):
    if score < 18:
        return 'Low'
    if score < 40:
        return 'Mild'
    if score < 65:
        return 'Moderate'
    return 'High'


def assess_region(region, hsv, lab, gray, skin_mask):
    mask = cv2.bitwise_and(region['mask'], skin_mask)
    pixels = max(1, cv2.countNonZero(mask))
    if pixels < 40:
        mask = region['mask']
        pixels = max(1, cv2.countNonZero(mask))

    _, a, _ = cv2.split(lab)
    h_channel, s_channel, v_channel = cv2.split(hsv)

    # Redness: LAB a-channel + HSV red ranges; normalized to region skin area.
    a_mean = cv2.mean(a, mask=skin_mask)[0] if cv2.countNonZero(skin_mask) else np.mean(a)
    red_lab = cv2.inRange(a, int(max(132, a_mean + 8)), 210)
    red_hsv1 = cv2.inRange(hsv, np.array([0, 35, 45]), np.array([18, 255, 255]))
    red_hsv2 = cv2.inRange(hsv, np.array([155, 35, 45]), np.array([180, 255, 255]))
    red = cv2.bitwise_or(red_lab, cv2.bitwise_or(red_hsv1, red_hsv2))
    red = cv2.bitwise_and(red, mask)
    red_pct = cv2.countNonZero(red) / pixels * 100.0

    # Dark / pigmentation-like: darker than surrounding skin, not hair/background.
    skin_mean = cv2.mean(gray, mask=skin_mask)[0] if cv2.countNonZero(skin_mask) else float(np.mean(gray))
    dark = cv2.inRange(gray, 0, int(max(40, skin_mean - 20)))
    dark = cv2.bitwise_and(dark, mask)
    dark_pct = cv2.countNonZero(dark) / pixels * 100.0

    # Texture and pores: edge / local contrast inside the region.
    lap = cv2.Laplacian(gray, cv2.CV_64F)
    vals = lap[mask > 0]
    texture = float(np.var(vals)) if vals.size else 0.0
    texture_norm = min(100.0, texture / 3.2)

    # Undereye shadowing: region brightness compared with face average.
    region_lum = cv2.mean(gray, mask=mask)[0]
    shadow = max(0.0, skin_mean - region_lum)
    shadow_norm = min(100.0, shadow * 2.8)

    name = region['name'].lower()
    if 'forehead' in name:
        score = min(100, red_pct * 3.0 + dark_pct * 1.5 + texture_norm * 0.15)
        primary = 'redness/acne-like signals'
    elif 'cheek' in name:
        score = min(100, dark_pct * 2.4 + red_pct * 1.8 + texture_norm * 0.12)
        primary = 'pigmentation/dark-spot-like signals'
    elif 'undereye' in name:
        score = min(100, shadow_norm + dark_pct * 1.7 + red_pct * 0.7)
        primary = 'dark-circle/shadowing-like signals'
    elif 'nose' in name:
        score = min(100, texture_norm * 0.50 + dark_pct * 1.5 + red_pct * 0.7)
        primary = 'pores/blackhead-like signals'
    elif 'chin' in name:
        score = min(100, texture_norm * 0.42 + red_pct * 1.5 + dark_pct * 1.0)
        primary = 'texture unevenness / blemish-like signals'
    else:
        score = min(100, red_pct + dark_pct + texture_norm * 0.2)
        primary = region['concern']

    # Avoid every area looking extreme for bright red portraits; keep educational scaling moderate.
    score = float(np.clip(score, 0, 100))
    return {
        'score': score,
        'severity': severity_label(score),
        'red_pct': red_pct,
        'dark_pct': dark_pct,
        'texture': texture_norm,
        'shadow': shadow_norm,
        'primary': primary,
    }


def build_professional_canvas(original, regions, assessments):
    h, w = original.shape[:2]
    # top image plus lower findings panel; no right-side findings.
    panel_h = max(300, int(h * 0.55))
    canvas = np.full((h + panel_h, w, 3), 248, dtype=np.uint8)
    canvas[:h, :] = original

    # subtle white fade at bottom for readability
    cv2.rectangle(canvas, (0, h), (w, h+panel_h), (255,255,255), -1)

    # Title bar
    title_h = max(42, int(h * 0.07))
    cv2.rectangle(canvas, (0, 0), (w, title_h), (32, 58, 92), -1)
    title = 'GENERAL SKIN ASSESSMENT'
    tw = cv2.getTextSize(title, cv2.FONT_HERSHEY_SIMPLEX, 0.88, 2)[0][0]
    cv2.putText(canvas, title, ((w - tw)//2, int(title_h*0.68)), cv2.FONT_HERSHEY_SIMPLEX, 0.88, (255,255,255), 2, cv2.LINE_AA)

    # Draw thin, color-coded area overlays on photo.
    annotated = canvas[:h, :]
    for r in regions:
        a = assessments[r['id']]
        color = r['color']
        annotated[:] = draw_soft_area(annotated, r['mask'], color, alpha=0.055)
        draw_dashed_ellipse(annotated, r['center'], r['axes'], color, thickness=1, dash_deg=6, gap_deg=8)
        cx, cy = int(r['center'][0]), int(r['center'][1])
        cv2.circle(annotated, (cx, cy), 15, color, -1, cv2.LINE_AA)
        cv2.circle(annotated, (cx, cy), 15, (255,255,255), 2, cv2.LINE_AA)
        id_txt = str(r['id'])
        idw = cv2.getTextSize(id_txt, cv2.FONT_HERSHEY_SIMPLEX, 0.52, 2)[0][0]
        cv2.putText(annotated, id_txt, (cx-idw//2, cy+6), cv2.FONT_HERSHEY_SIMPLEX, 0.52, (255,255,255), 2, cv2.LINE_AA)

    # Bottom panel background cards
    y0 = h + 18
    margin = 22
    cv2.rectangle(canvas, (margin, y0), (w-margin, h+panel_h-18), (255,255,255), -1, cv2.LINE_AA)
    cv2.rectangle(canvas, (margin, y0), (w-margin, h+panel_h-18), (215,225,235), 1, cv2.LINE_AA)

    cv2.putText(canvas, 'AREA-BY-AREA EDUCATIONAL FINDINGS', (margin+18, y0+34), cv2.FONT_HERSHEY_SIMPLEX, 0.62, (32,58,92), 2, cv2.LINE_AA)

    left_x = margin + 18
    right_x = w//2 + 8
    row_h = 72
    start_y = y0 + 60
    for i, r in enumerate(regions):
        col_x = left_x if i < 3 else right_x
        row_y = start_y + (i % 3) * row_h
        a = assessments[r['id']]
        color = r['color']
        cv2.circle(canvas, (col_x+15, row_y+12), 11, color, -1, cv2.LINE_AA)
        cv2.putText(canvas, str(r['id']), (col_x+10, row_y+17), cv2.FONT_HERSHEY_SIMPLEX, 0.38, (255,255,255), 1, cv2.LINE_AA)
        cv2.putText(canvas, r['name'].upper(), (col_x+34, row_y+10), cv2.FONT_HERSHEY_SIMPLEX, 0.48, color, 2, cv2.LINE_AA)
        desc = f"{a['severity']} {a['primary']} observed in this area."
        put_wrapped(canvas, desc, col_x+34, row_y+32, 42, 0.42, (45,45,45), 1, 16)
        pill(canvas, col_x+360 if w > 850 else col_x+300, row_y-4, 92, 24, a['severity'], color)

    # Summary bars and recommendations
    sum_y = start_y + 3*row_h + 18
    cv2.line(canvas, (margin+18, sum_y-18), (w-margin-18, sum_y-18), (220,225,230), 1, cv2.LINE_AA)
    cv2.putText(canvas, 'OVERALL SUMMARY', (margin+18, sum_y+8), cv2.FONT_HERSHEY_SIMPLEX, 0.55, (32,58,92), 2, cv2.LINE_AA)
    labels = [
        ('Redness / Acne-like', np.mean([assessments[1]['red_pct'], assessments[2]['red_pct'], assessments[3]['red_pct']]) * 3.0, (0,70,235)),
        ('Pigmentation / Dark Spots', np.mean([assessments[2]['dark_pct'], assessments[3]['dark_pct']]) * 2.3, (0,135,255)),
        ('Texture / Pores', np.mean([assessments[5]['texture'], assessments[6]['texture']]), (220,130,20)),
        ('Undereye Shadowing', assessments[4]['shadow'], (190,80,190)),
    ]
    bar_x = margin + 260
    bar_w = max(150, w//4)
    for j, (labtxt, score, color) in enumerate(labels):
        yy = sum_y + 36 + j*24
        score = float(np.clip(score, 0, 100))
        cv2.putText(canvas, labtxt, (margin+34, yy+5), cv2.FONT_HERSHEY_SIMPLEX, 0.43, (45,45,45), 1, cv2.LINE_AA)
        cv2.rectangle(canvas, (bar_x, yy-6), (bar_x+bar_w, yy+4), (235,238,242), -1, cv2.LINE_AA)
        cv2.rectangle(canvas, (bar_x, yy-6), (bar_x+int(bar_w*score/100), yy+4), color, -1, cv2.LINE_AA)
        cv2.putText(canvas, f'{int(round(score))}%', (bar_x+bar_w+12, yy+5), cv2.FONT_HERSHEY_SIMPLEX, 0.42, (80,80,80), 1, cv2.LINE_AA)

    rec_x = w//2 + 10
    cv2.putText(canvas, 'RECOMMENDED VISUALIZATIONS', (rec_x, sum_y+8), cv2.FONT_HERSHEY_SIMPLEX, 0.55, (32,92,46), 2, cv2.LINE_AA)
    recs = ['CO2 Laser + Dermapen', 'PICO Carbon Laser', 'Diamond Peel Facial', 'Undereye + Lip Filler']
    for j, rec in enumerate(recs):
        yy = sum_y + 36 + j*24
        cv2.circle(canvas, (rec_x+8, yy), 8, (62,165,65), -1, cv2.LINE_AA)
        cv2.putText(canvas, '✓', (rec_x+3, yy+5), cv2.FONT_HERSHEY_SIMPLEX, 0.40, (255,255,255), 1, cv2.LINE_AA)
        cv2.putText(canvas, rec, (rec_x+24, yy+5), cv2.FONT_HERSHEY_SIMPLEX, 0.44, (45,45,45), 1, cv2.LINE_AA)

    foot_y = h + panel_h - 28
    cv2.putText(canvas, 'Disclaimer: Educational visualization only. Not a medical diagnosis or guaranteed treatment result.', (margin+18, foot_y), cv2.FONT_HERSHEY_SIMPLEX, 0.42, (90,90,90), 1, cv2.LINE_AA)
    return canvas


def process_general_skin_assessment(input_path, output_path):
    original = resize_for_processing(read_image(input_path), 1200)
    bbox = detect_face_bbox(original)
    hsv = cv2.cvtColor(original, cv2.COLOR_BGR2HSV)
    lab = cv2.cvtColor(original, cv2.COLOR_BGR2LAB)
    gray = cv2.cvtColor(original, cv2.COLOR_BGR2GRAY)
    skin = skin_mask_bgr(original, bbox)
    regions = face_regions(original.shape, bbox)
    assessments = {r['id']: assess_region(r, hsv, lab, gray, skin) for r in regions}
    canvas = build_professional_canvas(original, regions, assessments)
    save_image(output_path, canvas)
    print('General Skin Assessment area-based educational visualization saved:', output_path)
    print(DISCLAIMER)
    sys.exit(0)


if __name__ == '__main__':
    if len(sys.argv) < 3:
        fail('Usage: python process_general_skin_assessment.py input output')
    process_general_skin_assessment(sys.argv[1], sys.argv[2])
