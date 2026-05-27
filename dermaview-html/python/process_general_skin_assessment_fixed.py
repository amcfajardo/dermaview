
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

    # Region positions are relative to the detected face box so the script still works
    # for different face sizes. The under-eye zone is intentionally BELOW the eye line,
    # not on top of the eyes.
    regions = {}
    regions["forehead"] = elliptical_mask(img.shape, (x + int(fw*0.50), y + int(fh*0.235)), (int(fw*0.24), int(fh*0.055)), blur=0)
    regions["left_cheek"] = elliptical_mask(img.shape, (x + int(fw*0.31), y + int(fh*0.565)), (int(fw*0.105), int(fh*0.145)), blur=0)
    regions["right_cheek"] = elliptical_mask(img.shape, (x + int(fw*0.69), y + int(fh*0.565)), (int(fw*0.105), int(fh*0.145)), blur=0)

    # Fixed: old value was fh*0.405, which places the purple mask over the eyes
    # on many front-facing portraits. Use a lower, flatter ellipse for the actual
    # lower eyelid / under-eye shadow area.
    under = np.zeros((h, w), np.uint8)
    under_y = y + int(fh * 0.465)
    under_axes = (max(8, int(fw * 0.095)), max(3, int(fh * 0.020)))
    cv2.ellipse(under, (x + int(fw*0.365), under_y), under_axes, 0, 0, 360, 255, -1)
    cv2.ellipse(under, (x + int(fw*0.635), under_y), under_axes, 0, 0, 360, 255, -1)
    regions["undereye"] = under

    regions["nose"] = elliptical_mask(img.shape, (x + int(fw*0.50), y + int(fh*0.525)), (int(fw*0.075), int(fh*0.145)), blur=0)
    regions["chin"] = elliptical_mask(img.shape, (x + int(fw*0.50), y + int(fh*0.790)), (int(fw*0.150), int(fh*0.070)), blur=0)
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
            cv2.drawContours(face_img, [c], -1, color, 1, cv2.LINE_AA)

    # blend tinted exact regions
    face_img[:] = cv2.addWeighted(overlay, 0.55, face_img, 0.45, 0)

def draw_callouts(canvas, img_area, regions, x0, y0, scale_x, scale_y):
    # Fixed label lanes: prevents label text from overlapping on the right side
    # and keeps the under-eye label aligned with the actual under-eye area.
    labels = [
        ("forehead", "1", "FOREHEAD AREA", "red", "right", 0.00),
        ("left_cheek", "2", "LEFT CHEEK AREA", "orange", "left", 0.00),
        ("right_cheek", "3", "RIGHT CHEEK AREA", "green", "right", -18),
        ("undereye", "4", "UNDEREYE AREA", "purple", "left", -10),
        ("nose", "5", "NOSE AREA", "blue", "right", 18),
        ("chin", "6", "CHIN AREA", "teal", "right", 0.00),
    ]
    H, W = canvas.shape[:2]
    for key, num, name, cname, side, lane_offset in labels:
        mask = regions[key]
        ys, xs = np.where(mask > 0)
        if len(xs) == 0:
            continue
        cx = int(x0 + np.mean(xs) * scale_x)
        cy = int(y0 + np.mean(ys) * scale_y)
        color = COLORS[cname]
        if side == "left":
            bx = max(30, x0 - 70)
        else:
            bx = min(W - 40, x0 + img_area[2] + 48)
        by = int(np.clip(cy + lane_offset, y0 + 16, y0 + img_area[3] - 16))
        cv2.line(canvas, (cx, cy), (bx, by), color, 1, cv2.LINE_AA)
        cv2.circle(canvas, (bx, by), 14, color, -1, cv2.LINE_AA)
        cv2.putText(canvas, num, (bx-5, by+5), cv2.FONT_HERSHEY_SIMPLEX, 0.48, (255,255,255), 2, cv2.LINE_AA)
        tx = bx + 20 if side == "right" else bx - 165
        tx = max(12, min(W-190, tx))
        cv2.putText(canvas, name, (tx, by+5), cv2.FONT_HERSHEY_SIMPLEX, 0.45, color, 1, cv2.LINE_AA)

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
    cv2.putText(canvas, title, (x+48, y+26), cv2.FONT_HERSHEY_SIMPLEX, 0.48, color, 2, cv2.LINE_AA)
    # severity small badge
    sev_col = (60,170,60) if severity in ("Low","Mild") else ((0,135,255) if severity=="Moderate" else (45,45,220))
    cv2.rectangle(canvas, (x+w-84, y+13), (x+w-14, y+36), sev_col, 1)
    cv2.putText(canvas, severity, (x+w-76, y+29), cv2.FONT_HERSHEY_SIMPLEX, 0.34, sev_col, 1, cv2.LINE_AA)
    draw_text(canvas, "Zone: " + zone, (x+48, y+50), scale=0.36, color=(45,45,45), thickness=1, max_width=w-70, line_gap=15)
    draw_text(canvas, "Finding: " + finding, (x+48, y+68), scale=0.36, color=(45,45,45), thickness=1, max_width=w-70, line_gap=15)

def process_general_skin_assessment(input_path, output_path):
    src = resize_for_processing(read_image(input_path), 1200)
    h, w = src.shape[:2]
    regions, bbox = make_face_region_masks(src)
    findings = compute_findings(src, regions)

    # Report canvas: wide enough for different images, with findings at the lower part.
    W = 1200
    H = 1500
    canvas = np.full((H, W, 3), 255, dtype=np.uint8)

    # Header
    cv2.rectangle(canvas, (0,0), (W,80), (45, 24, 5), -1)
    cv2.putText(canvas, "GENERAL SKIN ASSESSMENT", (265, 48), cv2.FONT_HERSHEY_SIMPLEX, 1.25, (255,255,255), 2, cv2.LINE_AA)
    cv2.putText(canvas, "AREA-BY-AREA EDUCATIONAL ANALYSIS", (390, 74), cv2.FONT_HERSHEY_SIMPLEX, 0.48, (220,230,245), 1, cv2.LINE_AA)

    # Image area bigger and centered
    max_img_w, max_img_h = 860, 590
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
    cv2.putText(canvas, "AREA-BY-AREA EDUCATIONAL FINDINGS", (350, panel_y+42), cv2.FONT_HERSHEY_SIMPLEX, 0.72, COLORS["navy"], 2, cv2.LINE_AA)

    card_w, card_h = 360, 130
    cols = [55, 420, 785]
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

    guide_x = 445
    cv2.putText(canvas, "SEVERITY GUIDE", (guide_x, sy), cv2.FONT_HERSHEY_SIMPLEX, 0.58, COLORS["navy"], 2, cv2.LINE_AA)
    sev = [("Low/Mild", "0-17%", COLORS["green"]), ("Moderate", "18-34%", COLORS["orange"]), ("High", "35%+", COLORS["red"])]
    gy = sy+45
    for name, rng, col in sev:
        cv2.circle(canvas, (guide_x, gy-4), 6, col, -1)
        cv2.putText(canvas, name, (guide_x+18, gy), cv2.FONT_HERSHEY_SIMPLEX, 0.45, col, 1, cv2.LINE_AA)
        cv2.putText(canvas, rng, (guide_x+150, gy), cv2.FONT_HERSHEY_SIMPLEX, 0.45, COLORS["navy"], 1, cv2.LINE_AA)
        gy += 37

    rec_x = 690
    cv2.putText(canvas, "RECOMMENDED VISUALIZATIONS", (rec_x, sy), cv2.FONT_HERSHEY_SIMPLEX, 0.58, COLORS["navy"], 2, cv2.LINE_AA)
    recs = [("CO2 Laser + Dermapen", "for redness & texture", COLORS["red"]),
            ("PICO Carbon Laser", "for pigmentation & pores", COLORS["blue"]),
            ("Diamond Peel Facial", "for glow & exfoliation", COLORS["orange"]),
            ("Undereye + Lip Filler", "for dark circles & lip hydration", COLORS["purple"])]
    for i, (name, sub, col) in enumerate(recs):
        rx = rec_x + (i % 2) * 230
        ry = sy + 28 + (i // 2) * 82
        rounded_rect(canvas, (rx, ry), (rx+210, ry+65), (255,255,255), radius=10, thickness=-1)
        cv2.rectangle(canvas, (rx, ry), (rx+210, ry+65), col, 1)
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
