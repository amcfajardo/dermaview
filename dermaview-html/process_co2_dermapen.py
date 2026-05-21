import cv2
import numpy as np
import sys


def process_co2_dermapen(input_path, output_path):
    img = cv2.imread(input_path)

    if img is None:
        print("Image not found")
        sys.exit(1)

    original = img.copy()

    # Convert colors
    hsv = cv2.cvtColor(img, cv2.COLOR_BGR2HSV)
    lab = cv2.cvtColor(img, cv2.COLOR_BGR2LAB)

    h, s, v = cv2.split(hsv)
    l, a, b = cv2.split(lab)

    # 1. Detect skin area only
    skin_mask = cv2.inRange(
        hsv,
        np.array([0, 20, 50]),
        np.array([35, 180, 255])
    )

    # 2. Detect red acne/scars
    red_mask1 = cv2.inRange(
        hsv,
        np.array([0, 45, 50]),
        np.array([15, 255, 255])
    )

    red_mask2 = cv2.inRange(
        hsv,
        np.array([160, 45, 50]),
        np.array([180, 255, 255])
    )

    red_mask = cv2.bitwise_or(red_mask1, red_mask2)

    lab_red = cv2.inRange(a, 140, 180)

    acne_mask = cv2.bitwise_or(red_mask, lab_red)

    # 3. Only acne inside skin
    mask = cv2.bitwise_and(acne_mask, skin_mask)

    kernel = np.ones((5, 5), np.uint8)

    mask = cv2.morphologyEx(mask, cv2.MORPH_OPEN, kernel)
    mask = cv2.morphologyEx(mask, cv2.MORPH_CLOSE, kernel)
    mask = cv2.dilate(mask, kernel, iterations=1)

    hard_mask = cv2.threshold(mask, 50, 255, cv2.THRESH_BINARY)[1]

    # 4. Inpaint acne marks
    inpainted = cv2.inpaint(
        img,
        hard_mask,
        5,
        cv2.INPAINT_TELEA
    )

    # 5. Smooth repaired areas
    smooth = cv2.bilateralFilter(
        inpainted,
        d=25,
        sigmaColor=90,
        sigmaSpace=90
    )

    # 6. Soft blend only acne areas
    soft_mask = cv2.GaussianBlur(hard_mask, (25, 25), 0)
    soft_mask = soft_mask.astype(np.float32) / 255.0
    soft_mask = cv2.merge([soft_mask, soft_mask, soft_mask])

    result = (
        smooth.astype(np.float32) * soft_mask +
        original.astype(np.float32) * (1 - soft_mask)
    ).astype(np.uint8)

    cv2.imwrite(output_path, result)

    print("Processed image saved:", output_path)
    sys.exit(0)


if __name__ == "__main__":
    if len(sys.argv) < 3:
        print("Usage: python process_co2_dermapen.py input output")
        sys.exit(1)

    process_co2_dermapen(sys.argv[1], sys.argv[2])