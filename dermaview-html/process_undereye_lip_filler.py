import cv2
import numpy as np
import sys


def process_undereye_lip_filler(input_path, output_path):

    img = cv2.imread(input_path)

    if img is None:
        print("Image not found")
        sys.exit(1)

    original = img.copy()

    h, w = img.shape[:2]

    result = original.copy()

    # ---------------------------------------------------
    # UNDEREYE BRIGHTENING
    # ---------------------------------------------------

    overlay = result.copy()

    # approximate undereye regions
    left_eye_center = (int(w * 0.35), int(h * 0.42))
    right_eye_center = (int(w * 0.65), int(h * 0.42))

    eye_axes = (int(w * 0.09), int(h * 0.045))

    cv2.ellipse(
        overlay,
        left_eye_center,
        eye_axes,
        0,
        0,
        360,
        (20, 20, 20),
        -1
    )

    cv2.ellipse(
        overlay,
        right_eye_center,
        eye_axes,
        0,
        0,
        360,
        (20, 20, 20),
        -1
    )

    result = cv2.addWeighted(
        overlay,
        0.08,
        result,
        0.92,
        0
    )

    # smooth undereye area
    smooth = cv2.bilateralFilter(
        result,
        d=11,
        sigmaColor=40,
        sigmaSpace=40
    )

    eye_mask = np.zeros((h, w), dtype=np.uint8)

    cv2.ellipse(
        eye_mask,
        left_eye_center,
        (int(w * 0.11), int(h * 0.06)),
        0,
        0,
        360,
        255,
        -1
    )

    cv2.ellipse(
        eye_mask,
        right_eye_center,
        (int(w * 0.11), int(h * 0.06)),
        0,
        0,
        360,
        255,
        -1
    )

    eye_mask = cv2.GaussianBlur(
        eye_mask,
        (41, 41),
        0
    )

    eye_float = eye_mask.astype(np.float32) / 255.0
    eye_float = np.clip(eye_float * 0.45, 0, 0.45)

    eye_float_3 = cv2.merge([
        eye_float,
        eye_float,
        eye_float
    ])

    result = (
        smooth.astype(np.float32) * eye_float_3 +
        result.astype(np.float32) * (1 - eye_float_3)
    ).astype(np.uint8)

    # ---------------------------------------------------
    # LIP ENHANCEMENT
    # ---------------------------------------------------

    lip_center = (
        int(w * 0.50),
        int(h * 0.72)
    )

    lip_axes = (
        int(w * 0.11),
        int(h * 0.045)
    )

    # subtle lip enlargement warp
    map_x = np.zeros((h, w), np.float32)
    map_y = np.zeros((h, w), np.float32)

    for y in range(h):
        for x in range(w):

            dx = x - lip_center[0]
            dy = y - lip_center[1]

            distance = np.sqrt(dx * dx + dy * dy)

            radius = w * 0.12

            if distance < radius:

                factor = 1 - (distance / radius)

                new_x = x - dx * factor * 0.04
                new_y = y - dy * factor * 0.08

            else:

                new_x = x
                new_y = y

            map_x[y, x] = np.clip(new_x, 0, w - 1)
            map_y[y, x] = np.clip(new_y, 0, h - 1)

    result = cv2.remap(
        result,
        map_x,
        map_y,
        cv2.INTER_LINEAR
    )

    # slight lip color enhancement
    hsv = cv2.cvtColor(result, cv2.COLOR_BGR2HSV)

    lip_mask1 = cv2.inRange(
        hsv,
        np.array([0, 30, 40]),
        np.array([15, 180, 255])
    )

    lip_mask2 = cv2.inRange(
        hsv,
        np.array([160, 30, 40]),
        np.array([180, 180, 255])
    )

    lip_mask = cv2.bitwise_or(
        lip_mask1,
        lip_mask2
    )

    lip_mask = cv2.GaussianBlur(
        lip_mask,
        (31, 31),
        0
    )

    lip_float = lip_mask.astype(np.float32) / 255.0
    lip_float = np.clip(lip_float * 0.25, 0, 0.25)

    hsv = hsv.astype(np.float32)

    hsv[:, :, 1] = hsv[:, :, 1] + (lip_float * 25)
    hsv[:, :, 2] = hsv[:, :, 2] + (lip_float * 8)

    hsv = np.clip(hsv, 0, 255).astype(np.uint8)

    result = cv2.cvtColor(
        hsv,
        cv2.COLOR_HSV2BGR
    )

    cv2.imwrite(
        output_path,
        result,
        [cv2.IMWRITE_JPEG_QUALITY, 95]
    )

    print("Undereye and Lip Filler visualization saved:", output_path)

    sys.exit(0)


if __name__ == "__main__":

    if len(sys.argv) < 3:
        print("Usage: python process_undereye_lip_filler.py input output")
        sys.exit(1)

    process_undereye_lip_filler(
        sys.argv[1],
        sys.argv[2]
    )