import cv2
import numpy as np
import sys


def process_pico_carbon_laser(input_path, output_path):
    img = cv2.imread(input_path)

    if img is None:
        print("Image not found")
        sys.exit(1)

    original = img.copy()

    hsv = cv2.cvtColor(original, cv2.COLOR_BGR2HSV)
    ycrcb = cv2.cvtColor(original, cv2.COLOR_BGR2YCrCb)

    # Skin mask only
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

    skin_mask = cv2.GaussianBlur(
        skin_mask,
        (35, 35),
        0
    )

    skin_float = skin_mask.astype(np.float32) / 255.0
    skin_float = np.clip(skin_float * 0.65, 0, 0.65)
    skin_float_3 = cv2.merge([skin_float, skin_float, skin_float])

    # Refine pores / smooth texture
    smooth = cv2.bilateralFilter(
        original,
        d=17,
        sigmaColor=60,
        sigmaSpace=60
    )

    smooth = cv2.bilateralFilter(
        smooth,
        d=11,
        sigmaColor=40,
        sigmaSpace=40
    )

    # Brighten and reduce dullness
    lab = cv2.cvtColor(smooth, cv2.COLOR_BGR2LAB)
    l, a, b = cv2.split(lab)

    l = cv2.convertScaleAbs(
        l,
        alpha=1.04,
        beta=4
    )

    a = cv2.addWeighted(
        a,
        0.94,
        cv2.GaussianBlur(a, (0, 0), 3),
        0.06,
        0
    )

    lab = cv2.merge((l, a, b))
    smooth = cv2.cvtColor(lab, cv2.COLOR_LAB2BGR)

    # Mild carbon laser glow
    glow = cv2.GaussianBlur(
        smooth,
        (0, 0),
        2
    )

    smooth = cv2.addWeighted(
        smooth,
        0.90,
        glow,
        0.10,
        0
    )

    # Blend only on skin
    result = (
        smooth.astype(np.float32) * skin_float_3 +
        original.astype(np.float32) * (1 - skin_float_3)
    ).astype(np.uint8)

    cv2.imwrite(output_path, result, [cv2.IMWRITE_JPEG_QUALITY, 95])

    print("PICO Carbon Laser visualization saved:", output_path)
    sys.exit(0)


if __name__ == "__main__":
    if len(sys.argv) < 3:
        print("Usage: python process_pico_carbon_laser.py input output")
        sys.exit(1)

    process_pico_carbon_laser(sys.argv[1], sys.argv[2])