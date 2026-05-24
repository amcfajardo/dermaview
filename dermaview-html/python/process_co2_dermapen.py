import cv2
import numpy as np
import sys


def process_co2_dermapen(input_path, output_path):
    img = cv2.imread(input_path)

    if img is None:
        print("Image not found")
        sys.exit(1)

    original = img.copy()

    hsv = cv2.cvtColor(img, cv2.COLOR_BGR2HSV)
    ycrcb = cv2.cvtColor(img, cv2.COLOR_BGR2YCrCb)

    # SKIN MASK ONLY
    skin_hsv = cv2.inRange(
        hsv,
        np.array([0, 18, 45]),
        np.array([35, 210, 255])
    )

    skin_ycrcb = cv2.inRange(
        ycrcb,
        np.array([0, 133, 77]),
        np.array([255, 180, 140])
    )

    skin_mask = cv2.bitwise_and(skin_hsv, skin_ycrcb)

    skin_mask = cv2.morphologyEx(
        skin_mask,
        cv2.MORPH_CLOSE,
        np.ones((9, 9), np.uint8)
    )

    skin_mask = cv2.morphologyEx(
        skin_mask,
        cv2.MORPH_OPEN,
        np.ones((5, 5), np.uint8)
    )

    skin_mask = cv2.GaussianBlur(skin_mask, (35, 35), 0)

        # Protect eyes, eyebrows, nose edges, lips, and hair
    gray = cv2.cvtColor(original, cv2.COLOR_BGR2GRAY)

    edges = cv2.Canny(gray, 40, 100)

    dark_features = cv2.inRange(
        gray,
        0,
        85
    )

    hsv_original = cv2.cvtColor(original, cv2.COLOR_BGR2HSV)

    lip_mask1 = cv2.inRange(
        hsv_original,
        np.array([0, 25, 40]),
        np.array([15, 180, 230])
    )

    lip_mask2 = cv2.inRange(
        hsv_original,
        np.array([160, 25, 40]),
        np.array([180, 180, 230])
    )

    lip_mask = cv2.bitwise_or(lip_mask1, lip_mask2)

    protect_mask = cv2.bitwise_or(edges, dark_features)
    protect_mask = cv2.bitwise_or(protect_mask, lip_mask)

    protect_mask = cv2.dilate(
        protect_mask,
        np.ones((5, 5), np.uint8),
        iterations=1
    )

    protect_mask = cv2.GaussianBlur(
        protect_mask,
        (21, 21),
        0
    )

    protect_float = protect_mask.astype(np.float32) / 255.0

    skin_float = skin_mask.astype(np.float32) / 255.0
    skin_float = np.clip(skin_float * 0.55, 0, 0.55)

    # Remove protected details from smoothing area
    skin_float = skin_float * (1 - protect_float)

    skin_float_3 = cv2.merge([
        skin_float,
        skin_float,
        skin_float
    ])

    # STRONGER CLEAR SKIN VERSION
    # CREATE CLEARER SKIN VERSION
    smooth = cv2.bilateralFilter(
        original,
        d=15,
        sigmaColor=45,
        sigmaSpace=45
    )

    smooth = cv2.bilateralFilter(
        smooth,
        d=9,
        sigmaColor=30,
        sigmaSpace=30
    )

    # SOFTEN TEXTURE
    blur = cv2.GaussianBlur(smooth, (0, 0), 1.3)
    smooth = cv2.addWeighted(smooth, 0.75, blur, 0.25, 0)

    # SKIN TONE CORRECTION
        # SKIN TONE CORRECTION
        # CORRECT SKIN TONE ONLY
    smooth_lab = cv2.cvtColor(smooth, cv2.COLOR_BGR2LAB)
    l, a, b = cv2.split(smooth_lab)

    l = cv2.convertScaleAbs(l, alpha=1.02, beta=2)

    a = cv2.addWeighted(
        a,
        0.92,
        cv2.GaussianBlur(a, (0, 0), 3),
        0.08,
        0
    )

    smooth_lab = cv2.merge((l, a, b))
    smooth = cv2.cvtColor(smooth_lab, cv2.COLOR_LAB2BGR)

    # BLEND ONLY SKIN
        # Detect remaining red marks
    lab_original = cv2.cvtColor(original, cv2.COLOR_BGR2LAB)
    _, red_channel, _ = cv2.split(lab_original)

    red_marks = cv2.inRange(red_channel, 128, 200)

    red_marks = cv2.bitwise_and(red_marks, skin_mask)

    red_marks = cv2.morphologyEx(
        red_marks,
        cv2.MORPH_CLOSE,
        np.ones((7, 7), np.uint8)
    )

    red_marks = cv2.dilate(
        red_marks,
        np.ones((5, 5), np.uint8),
        iterations=2
    )

    # Detect dark spots on skin
    gray_original = cv2.cvtColor(original, cv2.COLOR_BGR2GRAY)

    dark_spots = cv2.inRange(
        gray_original,
        35,
        115
    )

    # only dark spots inside skin
    dark_spots = cv2.bitwise_and(dark_spots, skin_mask)

    dark_spots = cv2.morphologyEx(
        dark_spots,
        cv2.MORPH_OPEN,
        np.ones((3, 3), np.uint8)
    )

    dark_spots = cv2.morphologyEx(
        dark_spots,
        cv2.MORPH_CLOSE,
        np.ones((5, 5), np.uint8)
    )

    dark_spots = cv2.dilate(
        dark_spots,
        np.ones((5, 5), np.uint8),
        iterations=1
    )

    # combine red acne marks + dark spots
    red_marks = cv2.bitwise_or(red_marks, dark_spots)

    red_soft = cv2.GaussianBlur(red_marks, (31, 31), 0)
    red_soft = red_soft.astype(np.float32) / 255.0
    red_soft = np.clip(red_soft * 2.2, 0, 1)
    red_soft_3 = cv2.merge([red_soft, red_soft, red_soft])

    # First: normal skin smoothing
    result = (
        smooth.astype(np.float32) * skin_float_3 +
        original.astype(np.float32) * (1 - skin_float_3)
    ).astype(np.uint8)

    # Second: stronger replacement only on red marks
    result = (
        smooth.astype(np.float32) * red_soft_3 +
        result.astype(np.float32) * (1 - red_soft_3)
    ).astype(np.uint8)

    cv2.imwrite(output_path, result, [cv2.IMWRITE_JPEG_QUALITY, 95])

    print("Skin only processed:", output_path)
    sys.exit(0)


if __name__ == "__main__":
    if len(sys.argv) < 3:
        print("Usage: python process_co2_dermapen.py input output")
        sys.exit(1)

    process_co2_dermapen(sys.argv[1], sys.argv[2])