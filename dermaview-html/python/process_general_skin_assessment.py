
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


def draw_dashed_ellipse(img, center, axes, color, angle=0, thickness=2, segments=48):
    pts = cv2.ellipse2Poly(tuple(map(int, center)), tuple(map(int, axes)), int(angle), 0, 360, max(5, 360//segments))
    for i in range(0, len(pts)-1, 2):
        cv2.line(img, tuple(pts[i]), tuple(pts[i+1]), color, thickness, cv2.LINE_AA)


def draw_region_outline(img, name, bbox, num, color):
    x, y, w, h = bbox
    settings = {
        'FOREHEAD AREA': ((x+w*0.50, y+h*0.23), (w*0.29, h*0.105), 0),
        'LEFT CHEEK AREA': ((x+w*0.33, y+h*0.53), (w*0.15, h*0.18), -10),
        'RIGHT CHEEK AREA': ((x+w*0.67, y+h*0.53), (w*0.15, h*0.18), 10),
        'NOSE AREA': ((x+w*0.50, y+h*0.50), (w*0.09, h*0.17), 0),
        'CHIN AREA': ((x+w*0.50, y+h*0.78), (w*0.20, h*0.10), 0),
    }
    if name == 'UNDEREYE AREA':
        for c in [(x+w*0.34, y+h*0.39), (x+w*0.66, y+h*0.39)]:
            draw_dashed_ellipse(img, c, (w*0.13, h*0.045), color, 0, 2)
        label = (int(x+w*0.18), int(y+h*0.40))
    else:
        c, a, ang = settings[name]
        draw_dashed_ellipse(img, c, a, color, ang, 2)
        label = (int(c[0]), int(c[1]))
    cv2.circle(img, label, 16, color, -1, cv2.LINE_AA)
    cv2.circle(img, label, 16, (255,255,255), 2, cv2.LINE_AA)
    text(img, str(num), (label[0]-5, label[1]+6), 0.55, (255,255,255), 2)


def analyze_regions(original, bbox):
    hsv = cv2.cvtColor(original, cv2.COLOR_BGR2HSV)
    lab = cv2.cvtColor(original, cv2.COLOR_BGR2LAB)
    gray = cv2.cvtColor(original, cv2.COLOR_BGR2GRAY)
    skin = (skin_mask_bgr(original, bbox) > 30).astype(np.uint8) * 255
    _, a, _ = cv2.split(lab)
    skin_mean_gray = safe_mean(gray, skin)
    skin_mean_a = safe_mean(a, skin)

    red_hsv1 = cv2.inRange(hsv, np.array([0, 35, 45]), np.array([20, 255, 255]))
    red_hsv2 = cv2.inRange(hsv, np.array([155, 35, 45]), np.array([180, 255, 255]))
    red_lab = cv2.inRange(a, int(max(132, skin_mean_a + 8)), 215)
    redness = cv2.bitwise_and(cv2.bitwise_or(cv2.bitwise_or(red_hsv1, red_hsv2), red_lab), skin)
    redness = cv2.morphologyEx(redness, cv2.MORPH_OPEN, np.ones((3,3), np.uint8))

    dark = cv2.inRange(gray, 0, int(max(45, skin_mean_gray - 20)))
    pigmentation = cv2.bitwise_and(dark, skin)
    pigmentation = cv2.morphologyEx(pigmentation, cv2.MORPH_OPEN, np.ones((3,3), np.uint8))

    lap_abs = cv2.convertScaleAbs(cv2.Laplacian(gray, cv2.CV_64F))
    texture = cv2.inRange(lap_abs, 16, 255)
    texture = cv2.bitwise_and(texture, skin)

    regs = region_masks(original, bbox)
    data = []
    for name, m in regs.items():
        area = cv2.bitwise_and(m, skin)
        area_count = cv2.countNonZero(area)
        if area_count < 30:
            area = m
        red_p = pct(redness, area)
        pig_p = pct(pigmentation, area)
        tex_p = pct(texture, area)
        mean_region = safe_mean(gray, area)

        concerns = []
        score = 0
        color = COLORS['green']
        primary = 'Even-looking area'
        if name == 'UNDEREYE AREA':
            # compare undereye to whole skin brightness, not a fixed threshold
            dark_score = max(0, (skin_mean_gray - mean_region) * 2.2)
            if dark_score >= 8 or pig_p >= 1.2:
                concerns.append('dark-circle/shadowing-like signals')
                score = max(score, min(100, dark_score + pig_p*8))
                color = COLORS['purple']; primary = 'Undereye shadowing'
        if red_p >= 0.8:
            concerns.append('redness/acne-like signals')
            score = max(score, min(100, red_p * 14))
            color = COLORS['red']; primary = 'Redness / acne-like'
        if pig_p >= 0.8:
            concerns.append('pigmentation/dark-spot-like signals')
            score = max(score, min(100, pig_p * 12))
            if primary == 'Even-looking area':
                color = COLORS['orange']; primary = 'Pigmentation / dark spots'
        if tex_p >= 14 and name in ['CHIN AREA', 'NOSE AREA', 'LEFT CHEEK AREA', 'RIGHT CHEEK AREA']:
            concerns.append('texture/visible-pore-like signals')
            score = max(score, min(100, tex_p * 1.7))
            if primary == 'Even-looking area':
                color = COLORS['blue']; primary = 'Texture / pores'
        if not concerns:
            concerns.append('no strong visible concern from image processing')
            score = min(7, max(red_p, pig_p, tex_p/5))
        data.append({
            'name': name, 'mask': m, 'red': red_p, 'pig': pig_p, 'tex': tex_p,
            'score': round(score, 1), 'severity': severity(score), 'concerns': concerns[:2],
            'color': color, 'primary': primary
        })
    return data, {'redness': redness, 'pigmentation': pigmentation, 'texture': texture}


def draw_panel(canvas, x0, y0, w, h, title, data):
    cv2.rectangle(canvas, (x0, y0), (x0+w, y0+h), (248,248,248), -1)
    cv2.rectangle(canvas, (x0, y0), (x0+w, y0+48), (70,38,18), -1)
    text(canvas, title, (x0+22, y0+32), 0.78, (255,255,255), 2)
    y = y0 + 78
    text(canvas, 'Area-by-area educational analysis', (x0+22, y), 0.55, COLORS['dark'], 2)
    y += 32
    for i, d in enumerate(data, 1):
        color = d['color']
        cv2.circle(canvas, (x0+35, y-5), 13, color, -1, cv2.LINE_AA)
        text(canvas, str(i), (x0+30, y+1), 0.45, (255,255,255), 2)
        text(canvas, d['name'], (x0+58, y), 0.52, color, 2)
        desc = '; '.join(d['concerns'])
        text(canvas, desc[:64], (x0+58, y+22), 0.43, COLORS['dark'], 1)
        sev_col = color if d['severity'] != 'None' else (80,140,80)
        cv2.rectangle(canvas, (x0+w-108, y-12), (x0+w-22, y+10), sev_col, 1)
        text(canvas, d['severity'], (x0+w-96, y+4), 0.36, sev_col, 1)
        y += 58
    cv2.line(canvas, (x0+22, y-8), (x0+w-22, y-8), COLORS['line'], 1)
    y += 22
    text(canvas, 'Overall summary', (x0+22, y), 0.55, COLORS['dark'], 2)
    y += 26
    avg_red = np.mean([d['red'] for d in data])
    avg_pig = np.mean([d['pig'] for d in data])
    avg_tex = np.mean([d['tex'] for d in data])
    rows = [('Redness / acne-like', avg_red, COLORS['red'], 8), ('Pigmentation / dark spots', avg_pig, COLORS['orange'], 8), ('Texture / pores', avg_tex, COLORS['blue'], 25)]
    for label, val, col, scale in rows:
        pctv = int(np.clip(val*scale, 0, 100))
        text(canvas, label, (x0+22, y), 0.42, COLORS['dark'], 1)
        cv2.rectangle(canvas, (x0+190, y-10), (x0+310, y-2), (230,230,230), -1)
        cv2.rectangle(canvas, (x0+190, y-10), (x0+190+int(1.2*pctv), y-2), col, -1)
        text(canvas, f'{pctv}%', (x0+322, y), 0.38, col, 1)
        y += 24
    y += 16
    text(canvas, 'Recommended visualizations', (x0+22, y), 0.50, (40,120,45), 2)
    y += 25
    recs = []
    if avg_red > 0.8: recs.append('CO2 Laser + Dermapen')
    if avg_pig > 0.8: recs.append('PICO Carbon Laser')
    if avg_tex > 13: recs.append('Diamond Peel Facial')
    if any(d['name']=='UNDEREYE AREA' and d['score']>=8 for d in data): recs.append('Undereye + Lip Filler')
    if not recs: recs.append('General consultation for confirmation')
    for r in recs[:4]:
        text(canvas, '✓ ' + r, (x0+30, y), 0.43, (30,110,40), 1)
        y += 22
    y = y0 + h - 28
    text(canvas, 'Educational visualization only. Not a medical diagnosis.', (x0+22, y), 0.36, COLORS['dark'], 1)


def process_general_skin_assessment(input_path, output_path):
    original = resize_for_processing(read_image(input_path), 1250)
    bbox = detect_face_bbox(original)
    data, signal_masks = analyze_regions(original, bbox)

    # image side: tint only actually detected signal pixels, not the entire region
    vis = original.copy()
    red_overlay = vis.copy(); red_overlay[signal_masks['redness'] > 0] = COLORS['red']
    vis = cv2.addWeighted(red_overlay, 0.18, vis, 0.82, 0)
    pig_overlay = vis.copy(); pig_overlay[signal_masks['pigmentation'] > 0] = COLORS['orange']
    vis = cv2.addWeighted(pig_overlay, 0.13, vis, 0.87, 0)

    for i, d in enumerate(data, 1):
        # Draw every area lightly, but use detected primary color and severity.
        col = d['color'] if d['severity'] != 'None' else (120, 180, 120)
        draw_region_outline(vis, d['name'], bbox, i, col)

    H, W = vis.shape[:2]
    panel_w = max(430, int(W * 0.60))
    canvas = np.full((H, W + panel_w, 3), 255, dtype=np.uint8)
    canvas[:H, :W] = vis
    draw_panel(canvas, W, 0, panel_w, H, 'GENERAL SKIN ASSESSMENT', data)
    save_image(output_path, canvas)
    print('General Skin Assessment area-based educational visualization saved:', output_path)
    print(DISCLAIMER)
    sys.exit(0)

if __name__ == "__main__":
    if len(sys.argv) < 3:
        fail("Usage: python process_general_skin_assessment_final.py input output")
    process_general_skin_assessment(sys.argv[1], sys.argv[2])
