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
}

# ---------------- BASIC UTILS ----------------

def fail(msg):
    print(msg)
    sys.exit(1)

def read_image(p):
    img = cv2.imread(str(p))
    if img is None:
        fail("Invalid image")
    return img

def save_image(p, img):
    Path(p).parent.mkdir(parents=True, exist_ok=True)
    cv2.imwrite(str(p), img, [cv2.IMWRITE_JPEG_QUALITY, 95])

# ---------------- FACE + REGIONS ----------------

def detect_face(img):
    h, w = img.shape[:2]
    gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
    cascade = cv2.CascadeClassifier(cv2.data.haarcascades + "haarcascade_frontalface_default.xml")
    faces = cascade.detectMultiScale(gray, 1.1, 4)
    if len(faces) > 0:
        return faces[0]
    return (int(w*0.2), int(h*0.2), int(w*0.6), int(h*0.6))


def ellipse_mask(shape, center, axes):
    mask = np.zeros(shape[:2], np.uint8)
    cv2.ellipse(mask, center, axes, 0, 0, 360, 255, -1)
    return cv2.GaussianBlur(mask, (21,21), 0)


def make_regions(img):
    h, w = img.shape[:2]
    x,y,fw,fh = detect_face(img)

    cx = x + fw//2
    eye_y = y + int(fh*0.35)

    regions = {}
    regions["forehead"] = ellipse_mask(img.shape, (cx, y+int(fh*0.2)), (int(fw*0.25), int(fh*0.08)))
    regions["undereye"] = ellipse_mask(img.shape, (cx, eye_y+20), (int(fw*0.18), int(fh*0.06)))
    regions["nose"] = ellipse_mask(img.shape, (cx, y+int(fh*0.5)), (int(fw*0.1), int(fh*0.18)))
    regions["left_cheek"] = ellipse_mask(img.shape, (x+int(fw*0.3), y+int(fh*0.55)), (int(fw*0.15), int(fh*0.18)))
    regions["right_cheek"] = ellipse_mask(img.shape, (x+int(fw*0.7), y+int(fh*0.55)), (int(fw*0.15), int(fh*0.18)))
    regions["chin"] = ellipse_mask(img.shape, (cx, y+int(fh*0.8)), (int(fw*0.2), int(fh*0.1)))

    return regions

# ---------------- ISSUE DETECTION ----------------

def detect_issues(img):
    hsv = cv2.cvtColor(img, cv2.COLOR_BGR2HSV)
    gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)

    redness = cv2.inRange(hsv, (0,40,40), (20,255,255))
    dark = cv2.inRange(gray, 0, 60)

    lap = cv2.Laplacian(gray, cv2.CV_64F)
    texture = cv2.convertScaleAbs(lap)

    return redness, dark, texture


def score(mask, region):
    total = max(1, cv2.countNonZero(region))
    return (cv2.countNonZero(cv2.bitwise_and(mask, region)) / total) * 100


def severity(v):
    if v < 8: return "Low"
    if v < 20: return "Mild"
    if v < 35: return "Moderate"
    return "High"

# ---------------- SMART OBSERVATIONS ----------------

def generate_observations(results):
    obs = []

    if results["forehead"][0] > 25:
        obs.append("Elevated erythema detected in frontal zone")

    if results["left_cheek"][0] > 20 or results["right_cheek"][0] > 20:
        obs.append("Pigmentation signals across malar regions")

    if results["undereye"][0] > 15:
        obs.append("Infraorbital shadowing present")

    if results["nose"][0] > 20:
        obs.append("Pore activity concentrated in nasal (T-zone)")

    if results["chin"][0] > 20:
        obs.append("Texture irregularities observed in mental region")

    if len(obs) == 0:
        obs.append("Skin appears generally balanced with minimal concerns")

    return obs

# ---------------- DRAW ----------------

def draw_overlay(img, regions):
    keys = list(regions.keys())
    palette = ["red","orange","green","purple","blue","teal"]

    for i, k in enumerate(keys):
        m = regions[k]
        color = COLORS[palette[i]]
        overlay = img.copy()
        overlay[m>0] = color
        img[:] = cv2.addWeighted(img, 0.85, overlay, 0.15, 0)


def label_map():
    return {
        "forehead": "FRONTAL ZONE",
        "left_cheek": "LEFT MALAR REGION",
        "right_cheek": "RIGHT MALAR REGION",
        "undereye": "INFRAORBITAL REGION",
        "nose": "NASAL (T-ZONE)",
        "chin": "MENTAL REGION"
    }

# ---------------- MAIN ----------------

def process(input_path, output_path):
    img = read_image(input_path)
    regions = make_regions(img)

    red, dark, tex = detect_issues(img)

    results = {}
    for k, r in regions.items():
        s = max(score(red,r), score(dark,r), score(tex,r))
        results[k] = (s, severity(s))

    canvas = img.copy()
    draw_overlay(canvas, regions)

    labels = label_map()

    # Title
    cv2.putText(canvas, "GENERAL SKIN ASSESSMENT", (20,30), cv2.FONT_HERSHEY_SIMPLEX, 0.8, COLORS["navy"], 2)

    y = 70
    for k in labels:
        text = f"{labels[k]}: {results[k][1]} ({int(results[k][0])}%)"
        cv2.putText(canvas, text, (20,y), cv2.FONT_HERSHEY_SIMPLEX, 0.55, COLORS["navy"], 1)
        y += 28

    # Key Observations (dynamic)
    y += 20
    cv2.putText(canvas, "KEY OBSERVATIONS", (20, y), cv2.FONT_HERSHEY_SIMPLEX, 0.7, COLORS["navy"], 2)
    y += 40

    observations = generate_observations(results)
    for o in observations:
        cv2.putText(canvas, "- "+o, (20,y), cv2.FONT_HERSHEY_SIMPLEX, 0.5, COLORS["gray"], 1)
        y += 25

    # Disclaimer
    cv2.putText(canvas, DISCLAIMER, (20, canvas.shape[0]-20), cv2.FONT_HERSHEY_SIMPLEX, 0.4, COLORS["gray"], 1)

    save_image(output_path, canvas)
    print("Done:", output_path)


if __name__ == "__main__":
    if len(sys.argv) < 3:
        fail("Usage: python script.py input output")
    process(sys.argv[1], sys.argv[2])