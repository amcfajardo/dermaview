import cv2
import numpy as np
import sys


def resize_for_processing(img, max_size=1400):
    h, w = img.shape[:2]
    longest_side = max(h, w)

    if longest_side <= max_size:
        return img

    scale = max_size / longest_side
    return cv2.resize(
        img,
        (int(w * scale), int(h * scale)),
        interpolation=cv2.INTER_AREA
    )


def process_general_skin_assessment(input_path, output_path):
    img = cv2.imread(input_path)

    if img is None:
        print("Image not found")
        sys.exit(1)

    img = resize_for_processing(img)
    original = img.copy()

    hsv = cv2.cvtColor(original, cv2.COLOR_BGR2HSV)
    lab = cv2.cvtColor(original, cv2.COLOR_BGR2LAB)
    gray = cv2.cvtColor(original, cv2.COLOR_BGR2GRAY)

    h, w = img.shape[:2]

    result = original.copy()

    # Skin mask
    skin_mask = cv2.inRange(
        hsv,
        np.array([0, 18, 45]),
        np.array([35, 220, 255])
    )

    skin_mask = cv2.morphologyEx(
        skin_mask,
        cv2.MORPH_CLOSE,
        np.ones((7, 7), np.uint8)
    )

    skin_pixels = cv2.countNonZero(skin_mask)

    if skin_pixels == 0:
        skin_mask = np.zeros((h, w), np.uint8)
        cv2.ellipse(
            skin_mask,
            (w // 2, h // 2),
            (max(1, int(w * 0.38)), max(1, int(h * 0.42))),
            0,
            0,
            360,
            255,
            -1
        )
        skin_pixels = cv2.countNonZero(skin_mask)

    # Redness / acne-like signals
    _, a, _ = cv2.split(lab)

    red1 = cv2.inRange(
        hsv,
        np.array([0, 35, 40]),
        np.array([20, 255, 255])
    )

    red2 = cv2.inRange(
        hsv,
        np.array([155, 35, 40]),
        np.array([180, 255, 255])
    )

    redness = cv2.bitwise_or(red1, red2)
    redness = cv2.bitwise_and(redness, skin_mask)

    redness_score = cv2.countNonZero(redness)

    # Dark spots / pigmentation-like signals
    skin_mean = cv2.mean(gray, mask=skin_mask)[0]

    dark_spots = cv2.inRange(
        gray,
        0,
        max(0, int(skin_mean - 25))
    )

    dark_spots = cv2.bitwise_and(dark_spots, skin_mask)

    dark_score = cv2.countNonZero(dark_spots)

    # Texture / unevenness signal
    laplacian = cv2.Laplacian(gray, cv2.CV_64F)
    texture_pixels = laplacian[skin_mask > 0]
    texture_score = np.var(texture_pixels) if texture_pixels.size else 0

    # Draw soft overlays
    red_overlay = result.copy()
    red_overlay[redness > 0] = [80, 80, 255]

    result = cv2.addWeighted(
        red_overlay,
        0.18,
        result,
        0.82,
        0
    )

    dark_overlay = result.copy()
    dark_overlay[dark_spots > 0] = [255, 180, 80]

    result = cv2.addWeighted(
        dark_overlay,
        0.16,
        result,
        0.84,
        0
    )

    # Add educational label panel
    panel_height = int(h * 0.22)

    canvas = np.full(
        (h + panel_height, w, 3),
        255,
        dtype=np.uint8
    )

    canvas[:h, :] = result

    suggestions = []

    if redness_score > 500:
        suggestions.append("Visible redness/acne-like areas detected")
        suggestions.append("Suggested: CO2 Laser + Dermapen or PICO Carbon Laser")

    if dark_score > 500:
        suggestions.append("Visible dark spots/pigmentation-like areas detected")
        suggestions.append("Suggested: PICO Carbon Laser or Diamond Peel Facial")

    if texture_score > 80:
        suggestions.append("Uneven texture signals detected")
        suggestions.append("Suggested: Diamond Peel or Skin Rejuvenation")

    if not suggestions:
        suggestions.append("No strong visible issue detected")
        suggestions.append("Suggested: General consultation for confirmation")

    y = h + 28

    cv2.putText(
        canvas,
        "General Skin Assessment",
        (20, y),
        cv2.FONT_HERSHEY_SIMPLEX,
        0.75,
        (30, 30, 30),
        2,
        cv2.LINE_AA
    )

    y += 35

    for text in suggestions[:4]:
        cv2.putText(
            canvas,
            "- " + text,
            (20, y),
            cv2.FONT_HERSHEY_SIMPLEX,
            0.55,
            (60, 60, 60),
            1,
            cv2.LINE_AA
        )

        y += 28

    saved = cv2.imwrite(
        output_path,
        canvas,
        [cv2.IMWRITE_JPEG_QUALITY, 95]
    )

    if not saved:
        print("Failed to save output image")
        sys.exit(1)

    print("General Skin Assessment saved:", output_path)
    sys.exit(0)


if __name__ == "__main__":
    if len(sys.argv) < 3:
        print("Usage: python process_general_skin_assessment.py input output")
        sys.exit(1)

    process_general_skin_assessment(sys.argv[1], sys.argv[2])
