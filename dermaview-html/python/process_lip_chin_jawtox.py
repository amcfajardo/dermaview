import cv2
import numpy as np
import sys


def process_lip_chin_jawtox(input_path, output_path):
    img = cv2.imread(input_path)

    if img is None:
        print("Image not found")
        sys.exit(1)

    h, w = img.shape[:2]
    result = img.copy()

    # ---------------------------------------------------
    # SUBTLE FACE CONTOUR / JAWTOX EFFECT
    # ---------------------------------------------------

    map_x = np.zeros((h, w), np.float32)
    map_y = np.zeros((h, w), np.float32)

    center_x = w // 2

    for y in range(h):
        for x in range(w):
            new_x = x
            new_y = y

            # lower face only
            if h * 0.48 < y < h * 0.88:
                distance = abs(x - center_x)

                strength = 0.055 * np.exp(
                    -(distance ** 2) / (2 * (w * 0.26) ** 2)
                )

                # slim jaw naturally
                if x < center_x:
                    new_x = x - strength * distance
                else:
                    new_x = x + strength * distance

            map_x[y, x] = np.clip(new_x, 0, w - 1)
            map_y[y, x] = np.clip(new_y, 0, h - 1)

    result = cv2.remap(
        result,
        map_x,
        map_y,
        cv2.INTER_LINEAR
    )

    # ---------------------------------------------------
    # CHIN FILLER EFFECT
    # ---------------------------------------------------

    map_x = np.zeros((h, w), np.float32)
    map_y = np.zeros((h, w), np.float32)

    chin_center = (
        int(w * 0.50),
        int(h * 0.80)
    )

    chin_radius = int(w * 0.16)

    for y in range(h):
        for x in range(w):
            dx = x - chin_center[0]
            dy = y - chin_center[1]

            distance = np.sqrt(dx * dx + dy * dy)

            if distance < chin_radius:
                factor = 1 - (distance / chin_radius)

                new_x = x
                new_y = y - dy * factor * 0.045

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

    # ---------------------------------------------------
    # LIP FILLER EFFECT
    # ---------------------------------------------------

    map_x = np.zeros((h, w), np.float32)
    map_y = np.zeros((h, w), np.float32)

    lip_center = (
        int(w * 0.50),
        int(h * 0.68)
    )

    lip_radius = int(w * 0.13)

    for y in range(h):
        for x in range(w):
            dx = x - lip_center[0]
            dy = y - lip_center[1]

            distance = np.sqrt(dx * dx + dy * dy)

            if distance < lip_radius:
                factor = 1 - (distance / lip_radius)

                new_x = x - dx * factor * 0.045
                new_y = y - dy * factor * 0.070

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

    # ---------------------------------------------------
    # SUBTLE LIP COLOR ENHANCEMENT
    # ---------------------------------------------------

    hsv = cv2.cvtColor(result, cv2.COLOR_BGR2HSV)

    lip_mask1 = cv2.inRange(
        hsv,
        np.array([0, 25, 40]),
        np.array([15, 190, 255])
    )

    lip_mask2 = cv2.inRange(
        hsv,
        np.array([160, 25, 40]),
        np.array([180, 190, 255])
    )

    lip_mask = cv2.bitwise_or(lip_mask1, lip_mask2)

    lip_mask = cv2.GaussianBlur(
        lip_mask,
        (31, 31),
        0
    )

    lip_float = lip_mask.astype(np.float32) / 255.0
    lip_float = np.clip(lip_float * 0.20, 0, 0.20)

    hsv = hsv.astype(np.float32)

    hsv[:, :, 1] = hsv[:, :, 1] + lip_float * 20
    hsv[:, :, 2] = hsv[:, :, 2] + lip_float * 5

    hsv = np.clip(hsv, 0, 255).astype(np.uint8)

    result = cv2.cvtColor(
        hsv,
        cv2.COLOR_HSV2BGR
    )

    # ---------------------------------------------------
    # LIGHT SHARPENING TO AVOID BLUR
    # ---------------------------------------------------

    blur = cv2.GaussianBlur(result, (0, 0), 1)

    result = cv2.addWeighted(
        result,
        1.08,
        blur,
        -0.08,
        0
    )

    cv2.imwrite(
        output_path,
        result,
        [cv2.IMWRITE_JPEG_QUALITY, 95]
    )

    print("Lip Filler, Chin Filler, and Jawtox visualization saved:", output_path)
    sys.exit(0)


if __name__ == "__main__":
    if len(sys.argv) < 3:
        print("Usage: python process_lip_chin_jawtox.py input output")
        sys.exit(1)

    process_lip_chin_jawtox(sys.argv[1], sys.argv[2])