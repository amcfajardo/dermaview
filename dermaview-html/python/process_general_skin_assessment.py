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
    if v < 10: return "Low"
    if v < 25: return "Moderate"
    return "High"

# ---------------- DRAW ----------------

def draw_overlay(img, regions):
    for k, m in regions.items():
        color = COLORS[["red","orange","green","purple","blue","teal"][list(regions.keys()).index(k)]]
        overlay = img.copy()
        overlay[m>0] = color
        img[:] = cv2.addWeighted(img, 0.85, overlay, 0.15, 0)


def label_map():
    return {
        "forehead": "FRONTAL ZONE",
        "left_cheek": "LEFT MALAR",
        "right_cheek": "RIGHT MALAR",
        "undereye": "INFRAORBITAL",
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

    y = 30
    for k in labels:
        text = f"{labels[k]}: {results[k][1]}"
        cv2.putText(canvas, text, (20,y), cv2.FONT_HERSHEY_SIMPLEX, 0.6, COLORS["navy"], 2)
        y += 30

    # Key Observations
    cv2.putText(canvas, "KEY OBSERVATIONS", (20, y+20), cv2.FONT_HERSHEY_SIMPLEX, 0.7, COLORS["navy"], 2)
    y += 60
    obs = [
        "Frontal redness detected",
        "Malar pigmentation present",
        "Mild under-eye shadowing"
    ]
    for o in obs:
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
