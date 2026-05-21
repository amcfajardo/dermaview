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

    skin_float = skin_mask.astype(np.float32) / 255.0
    skin_float = np.clip(skin_float * 0.95, 0, 0.95)
    skin_float_3 = cv2.merge([skin_float, skin_float, skin_float])

    # STRONGER CLEAR SKIN VERSION
    smooth = cv2.bilateralFilter(
    original,
    d=35,
    sigmaColor=120,
    sigmaSpace=120
    )

    smooth = cv2.bilateralFilter(
    smooth,
    d=25,
    sigmaColor=95,
    sigmaSpace=95
    )

    # SOFTEN TEXTURE
    blur = cv2.GaussianBlur(smooth, (0, 0), 1.3)
    smooth = cv2.addWeighted(smooth, 0.75, blur, 0.25, 0)

    # SKIN TONE CORRECTION
    # SKIN TONE CORRECTION
    smooth_lab = cv2.cvtColor(smooth, cv2.COLOR_BGR2LAB)
    l, a, b = cv2.split(smooth_lab)

    # Slight brightness
    l = cv2.convertScaleAbs(
        l,
        alpha=1.02,
        beta=2
    )

    # VERY LIGHT redness reduction
    a = cv2.addWeighted(
        a,
        0.96,
        cv2.GaussianBlur(a, (0, 0), 3),
        0.04,
        0
    )

    smooth_lab = cv2.merge((l, a, b))
    smooth = cv2.cvtColor(smooth_lab, cv2.COLOR_LAB2BGR)

    # BLEND ONLY SKIN
    result = (
        smooth.astype(np.float32) * skin_float_3 +
        original.astype(np.float32) * (1 - skin_float_3)
    ).astype(np.uint8)

    cv2.imwrite(output_path, result, [cv2.IMWRITE_JPEG_QUALITY, 95])

    print("Skin only processed:", output_path)
    sys.exit(0)


if __name__ == "__main__":
    if len(sys.argv) < 3:
        print("Usage: python process_co2_dermapen.py input output")
        sys.exit(1)

    process_co2_dermapen(sys.argv[1], sys.argv[2])