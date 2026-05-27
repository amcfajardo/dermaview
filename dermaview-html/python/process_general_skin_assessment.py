
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

RED = (45, 45, 235)
ORANGE = (0, 150, 255)
GREEN = (70, 170, 70)
BLUE = (210, 110, 25)
PURPLE = (170, 70, 170)
TEAL = (170, 170, 20)
DARK = (25, 35, 55)
GRAY = (110, 110, 110)

def severity_label(score):
    if score < 8:
        return "Very Low"
    if score < 20:
        return "Mild"
    if score < 40:
        return "Mild-Moderate"
    return "Moderate"

def add_text(img, text, org, scale=0.48, color=(35,35,35), thickness=1):
    cv2.putText(img, text, org, cv2.FONT_HERSHEY_SIMPLEX, scale, color, thickness, cv2.LINE_AA)

def wrap_text(text, max_chars=44):
    words, lines, line = text.split(), [], ""
    for word in words:
        if len(line) + len(word) + 1 <= max_chars:
            line = (line + " " + word).strip()
        else:
            if line: lines.append(line)
            line = word
    if line: lines.append(line)
    return lines

def region_mask(shape, center_rel, axes_rel):
    h, w = shape[:2]
    mask = np.zeros((h, w), np.uint8)
    center = (int(w * center_rel[0]), int(h * center_rel[1]))
    axes = (max(4, int(w * axes_rel[0])), max(4, int(h * axes_rel[1])))
    cv2.ellipse(mask, center, axes, 0, 0, 360, 255, -1)
    return mask, center, axes

def analyze_region(name, mask, redness, dark_spots, pore_like, texture_map):
    pixels = max(1, cv2.countNonZero(mask))
    red_pct = cv2.countNonZero(cv2.bitwise_and(redness, mask)) / pixels * 100
    dark_pct = cv2.countNonZero(cv2.bitwise_and(dark_spots, mask)) / pixels * 100
    pore_pct = cv2.countNonZero(cv2.bitwise_and(pore_like, mask)) / pixels * 100
    tex_vals = texture_map[mask > 0]
    tex_score = float(np.mean(tex_vals)) if tex_vals.size else 0
    concerns = []
    score = 0
    if red_pct > 0.75:
        concerns.append(("Redness / acne-like signals", RED, red_pct * 7.0))
        score += red_pct * 7.0
    if dark_pct > 0.55:
        concerns.append(("Pigmentation / dark-spot-like signals", ORANGE, dark_pct * 7.5))
        score += dark_pct * 7.5
    if pore_pct > 0.70:
        concerns.append(("Visible pores / blackhead-like signals", GREEN, pore_pct * 5.5))
        score += pore_pct * 5.5
    if tex_score > 6.0:
        concerns.append(("Uneven texture signals", PURPLE, min(tex_score * 2.0, 45)))
        score += min(tex_score * 2.0, 45)
    return {
        "name": name, "red_pct": red_pct, "dark_pct": dark_pct,
        "pore_pct": pore_pct, "tex_score": tex_score, "concerns": concerns,
        "score": min(score, 100)
    }

def draw_transparent_overlay(base, mask, color, alpha=0.20):
    overlay = base.copy()
    overlay[mask > 0] = color
    return cv2.addWeighted(overlay, alpha, base, 1 - alpha, 0)

def draw_region_outline(img, center, axes, color, number):
    cv2.ellipse(img, center, axes, 0, 0, 360, color, 2, cv2.LINE_AA)
    # inner soft outline
    cv2.ellipse(img, center, (max(1, axes[0]-4), max(1, axes[1]-4)), 0, 0, 360, color, 1, cv2.LINE_AA)
    bx = min(max(center[0] + axes[0] - 16, 18), img.shape[1]-18)
    by = min(max(center[1] - axes[1] + 18, 18), img.shape[0]-18)
    cv2.circle(img, (bx, by), 14, color, -1, cv2.LINE_AA)
    cv2.circle(img, (bx, by), 14, (255,255,255), 2, cv2.LINE_AA)
    add_text(img, str(number), (bx-5, by+5), 0.48, (255,255,255), 2)

def make_dashboard(original, analyses, regions, overall, recommendations):
    h, w = original.shape[:2]
    target_h = 820
    scale = target_h / h
    face = cv2.resize(original, (int(w*scale), target_h), interpolation=cv2.INTER_AREA)
    fh, fw = face.shape[:2]
    panel_w = 650
    canvas = np.full((fh, fw + panel_w, 3), 248, dtype=np.uint8)
    canvas[:, :fw] = face
    # Header on right
    x0 = fw + 20
    cv2.rectangle(canvas, (fw, 0), (fw+panel_w, 62), (18, 44, 80), -1)
    add_text(canvas, "GENERAL SKIN ASSESSMENT", (fw+28, 39), 0.82, (255,255,255), 2)
    add_text(canvas, "Area-by-area educational analysis", (x0, 92), 0.62, DARK, 2)
    y = 128
    # draw scaled outlines on face
    for idx, (key, info) in enumerate(regions.items(), start=1):
        a = analyses[key]
        if a["concerns"]:
            color = a["concerns"][0][1]
        else:
            color = GREEN
        c = (int(info["center"][0]*scale), int(info["center"][1]*scale))
        ax = (int(info["axes"][0]*scale), int(info["axes"][1]*scale))
        draw_region_outline(canvas[:, :fw], c, ax, color, idx)
    # right region cards
    for idx, key in enumerate(regions.keys(), start=1):
        a = analyses[key]
        primary = a["concerns"][0] if a["concerns"] else ("No strong visible concern", GREEN, 0)
        color = primary[1]
        cv2.circle(canvas, (x0+16, y-4), 13, color, -1, cv2.LINE_AA)
        add_text(canvas, str(idx), (x0+11, y+1), 0.42, (255,255,255), 2)
        add_text(canvas, a["name"].upper(), (x0+42, y), 0.54, color, 2)
        sev = severity_label(a["score"])
        cv2.rectangle(canvas, (fw+panel_w-155, y-22), (fw+panel_w-35, y+6), (245,245,245), -1)
        cv2.rectangle(canvas, (fw+panel_w-155, y-22), (fw+panel_w-35, y+6), color, 1)
        add_text(canvas, sev, (fw+panel_w-142, y-3), 0.37, color, 1)
        desc = []
        if a["concerns"]:
            for label, _, _ in a["concerns"][:2]:
                desc.append(label)
        else:
            desc.append("No strong visible issue detected")
        detail = f"{'; '.join(desc)} observed in this area."
        yy = y + 24
        for line in wrap_text(detail, 54)[:2]:
            add_text(canvas, line, (x0+42, yy), 0.43, (35,35,35), 1)
            yy += 22
        cv2.line(canvas, (x0, y+62), (fw+panel_w-25, y+62), (215,215,215), 1)
        y += 82
    # summary block
    y += 10
    cv2.rectangle(canvas, (x0, y), (fw+panel_w-25, y+168), (255,255,255), -1)
    cv2.rectangle(canvas, (x0, y), (fw+panel_w-25, y+168), (220,225,235), 1)
    add_text(canvas, "OVERALL SUMMARY", (x0+18, y+30), 0.56, DARK, 2)
    metrics = [
        ("Redness / acne-like", overall["red"], RED),
        ("Pigmentation / dark spots", overall["dark"], ORANGE),
        ("Pores / blackhead-like", overall["pore"], GREEN),
        ("Texture unevenness", overall["texture"], PURPLE),
    ]
    yy = y + 62
    for label, val, color in metrics:
        add_text(canvas, label, (x0+18, yy), 0.42, (35,35,35), 1)
        bar_x = x0 + 255
        cv2.rectangle(canvas, (bar_x, yy-11), (bar_x+170, yy-3), (230,230,230), -1)
        cv2.rectangle(canvas, (bar_x, yy-11), (bar_x+int(min(val,100)/100*170), yy-3), color, -1)
        add_text(canvas, f"{val:.0f}%", (bar_x+188, yy-4), 0.39, color, 1)
        yy += 26
    # recs
    y = y + 186
    cv2.rectangle(canvas, (x0, y), (fw+panel_w-25, y+125), (250,255,250), -1)
    cv2.rectangle(canvas, (x0, y), (fw+panel_w-25, y+125), (210,230,210), 1)
    add_text(canvas, "RECOMMENDED VISUALIZATIONS", (x0+18, y+30), 0.53, (40,120,50), 2)
    yy = y + 62
    for rec in recommendations[:3]:
        cv2.circle(canvas, (x0+25, yy-6), 8, (70,170,70), -1, cv2.LINE_AA)
        add_text(canvas, "✓", (x0+19, yy-1), 0.42, (255,255,255), 2)
        add_text(canvas, rec, (x0+45, yy), 0.43, (25,25,25), 1)
        yy += 25
    # footer
    y = fh - 45
    add_text(canvas, "Educational visualization only. Not a medical diagnosis.", (x0, y), 0.42, (65,65,65), 1)
    add_text(canvas, "Consult a licensed professional for proper evaluation.", (x0, y+22), 0.42, (65,65,65), 1)
    return canvas

def process_general_skin_assessment(input_path, output_path):
    original = resize_for_processing(read_image(input_path), 1100)
    h, w = original.shape[:2]
    hsv = cv2.cvtColor(original, cv2.COLOR_BGR2HSV)
    lab = cv2.cvtColor(original, cv2.COLOR_BGR2LAB)
    gray = cv2.cvtColor(original, cv2.COLOR_BGR2GRAY)
    skin = skin_mask_bgr(original)
    skin_binary = (skin > 35).astype(np.uint8) * 255
    skin_pixels = max(1, cv2.countNonZero(skin_binary))
    _, a_channel, _ = cv2.split(lab)
    red1 = cv2.inRange(hsv, np.array([0, 34, 40]), np.array([22, 255, 255]))
    red2 = cv2.inRange(hsv, np.array([155, 34, 40]), np.array([180, 255, 255]))
    redness = cv2.bitwise_and(cv2.bitwise_or(red1, red2), skin_binary)
    redness = cv2.morphologyEx(redness, cv2.MORPH_OPEN, np.ones((3, 3), np.uint8))
    skin_mean = cv2.mean(gray, mask=skin_binary)[0]
    dark_spots = cv2.inRange(gray, 0, int(max(40, skin_mean - 24)))
    dark_spots = cv2.bitwise_and(dark_spots, skin_binary)
    dark_spots = cv2.morphologyEx(dark_spots, cv2.MORPH_OPEN, np.ones((3, 3), np.uint8))
    edges = cv2.Laplacian(gray, cv2.CV_64F)
    texture_abs = np.uint8(np.clip(np.abs(edges), 0, 255))
    texture_map = cv2.GaussianBlur(texture_abs, (9, 9), 0)
    pore_like = cv2.inRange(gray, 0, int(max(55, skin_mean - 14)))
    pore_like = cv2.bitwise_and(pore_like, skin_binary)
    pore_like = cv2.morphologyEx(pore_like, cv2.MORPH_OPEN, np.ones((2, 2), np.uint8))
    # face regions using relative positions: usable for centered portrait uploads
    region_defs = {
        "forehead": ("Forehead Area", (0.50, 0.285), (0.23, 0.075)),
        "left_cheek": ("Left Cheek Area", (0.34, 0.535), (0.135, 0.145)),
        "right_cheek": ("Right Cheek Area", (0.66, 0.535), (0.135, 0.145)),
        "undereye": ("Undereye Area", (0.50, 0.435), (0.29, 0.055)),
        "nose": ("Nose Area", (0.50, 0.515), (0.070, 0.120)),
        "chin": ("Chin Area", (0.50, 0.760), (0.19, 0.080)),
    }
    regions = {}
    analyses = {}
    for key, (name, c_rel, a_rel) in region_defs.items():
        mask, center, axes = region_mask(original.shape, c_rel, a_rel)
        mask = cv2.bitwise_and(mask, skin_binary)
        regions[key] = {"name": name, "center": center, "axes": axes, "mask": mask}
        analyses[key] = analyze_region(name, mask, redness, dark_spots, pore_like, texture_map)
    # build highlighted face image
    highlighted = original.copy()
    highlighted = draw_transparent_overlay(highlighted, cv2.GaussianBlur(redness, (17,17), 0), RED, 0.18)
    highlighted = draw_transparent_overlay(highlighted, cv2.GaussianBlur(dark_spots, (17,17), 0), ORANGE, 0.14)
    highlighted = draw_transparent_overlay(highlighted, cv2.GaussianBlur(pore_like, (13,13), 0), GREEN, 0.10)
    overall = {
        "red": min(100, cv2.countNonZero(redness) / skin_pixels * 850),
        "dark": min(100, cv2.countNonZero(dark_spots) / skin_pixels * 850),
        "pore": min(100, cv2.countNonZero(pore_like) / skin_pixels * 650),
        "texture": min(100, float(np.mean(texture_map[skin_binary > 0])) * 3.2 if cv2.countNonZero(skin_binary) else 0),
    }
    recommendations = []
    if overall["red"] >= 8 or overall["texture"] >= 18:
        recommendations.append("CO2 Laser + Dermapen for redness/texture visualization")
    if overall["dark"] >= 8 or overall["pore"] >= 10:
        recommendations.append("PICO Carbon Laser for pigmentation/pore visualization")
    if overall["texture"] >= 12 or overall["pore"] >= 10:
        recommendations.append("Diamond Peel Facial for exfoliation/glow visualization")
    if analyses["undereye"]["score"] >= 8:
        recommendations.append("Undereye + Lip Filler for dark-circle visualization")
    if not recommendations:
        recommendations = ["General consultation for professional confirmation"]
    dashboard = make_dashboard(highlighted, analyses, regions, overall, recommendations)
    save_image(output_path, dashboard)
    print("Detailed region-based General Skin Assessment saved:", output_path)
    print(DISCLAIMER)
    sys.exit(0)
if __name__ == "__main__":
    if len(sys.argv) < 3: fail("Usage: python process_general_skin_assessment_final.py input output")
    process_general_skin_assessment(sys.argv[1], sys.argv[2])
