import cv2
import numpy as np
import sys


def resize_for_processing(img, max_size=900):
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


def process_lip_chin_jawtox(input_path, output_path):
    img = cv2.imread(input_path)

    if img is None:
        print("Image not found")
        sys.exit(1)

    img = resize_for_processing(img)
    h, w = img.shape[:2]
    result = img.copy()

    # ---------------------------------------------------
    # SUBTLE FACE CONTOUR / JAWTOX EFFECT
    # ---------------------------------------------------

    yy, xx = np.indices((h, w), dtype=np.float32)
    center_x = w / 2
    distance = np.abs(xx - center_x)
    strength = 0.055 * np.exp(
        -(distance ** 2) / (2 * (w * 0.26) ** 2)
    )
    lower_face = (yy > h * 0.48) & (yy < h * 0.88)
    direction = np.where(xx < center_x, -1, 1)

    map_x = np.where(lower_face, xx + direction * strength * distance, xx)
    map_x = np.clip(map_x, 0, w - 1).astype(np.float32)
    map_y = yy.astype(np.float32)

    result = cv2.remap(
        result,
        map_x,
        map_y,
        cv2.INTER_LINEAR
    )

    # ---------------------------------------------------
    # CHIN FILLER EFFECT
    # ---------------------------------------------------

    chin_center = (
        int(w * 0.50),
        int(h * 0.80)
    )

    chin_radius = int(w * 0.16)
    dx = xx - chin_center[0]
    dy = yy - chin_center[1]
    distance = np.sqrt(dx * dx + dy * dy)
    chin_area = distance < chin_radius
    factor = np.where(chin_area, 1 - (distance / max(chin_radius, 1)), 0)

    map_x = xx.astype(np.float32)
    map_y = np.clip(yy - dy * factor * 0.045, 0, h - 1).astype(np.float32)

    result = cv2.remap(
        result,
        map_x,
        map_y,
        cv2.INTER_LINEAR
    )

    # ---------------------------------------------------
    # LIP FILLER EFFECT
    # ---------------------------------------------------

    lip_center = (
        int(w * 0.50),
        int(h * 0.68)
    )

    lip_radius = int(w * 0.13)
    dx = xx - lip_center[0]
    dy = yy - lip_center[1]
    distance = np.sqrt(dx * dx + dy * dy)
    lip_area = distance < lip_radius
    factor = np.where(lip_area, 1 - (distance / max(lip_radius, 1)), 0)

    map_x = np.clip(xx - dx * factor * 0.045, 0, w - 1).astype(np.float32)
    map_y = np.clip(yy - dy * factor * 0.070, 0, h - 1).astype(np.float32)

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

    saved = cv2.imwrite(
        output_path,
        result,
        [cv2.IMWRITE_JPEG_QUALITY, 95]
    )

    if not saved:
        print("Failed to save output image")
        sys.exit(1)

    print("Lip Filler, Chin Filler, and Jawtox visualization saved:", output_path)
    sys.exit(0)


if __name__ == "__main__":
    if len(sys.argv) < 3:
        print("Usage: python process_lip_chin_jawtox.py input output")
        sys.exit(1)

    process_lip_chin_jawtox(sys.argv[1], sys.argv[2])
