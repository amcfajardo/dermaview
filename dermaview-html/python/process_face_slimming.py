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


def process_face_slimming(input_path, output_path):
    img = cv2.imread(input_path)

    if img is None:
        print("Image not found.")
        sys.exit(1)

    img = resize_for_processing(img)
    h, w = img.shape[:2]

    yy, xx = np.indices((h, w), dtype=np.float32)
    center_x = w / 2
    distance = np.abs(xx - center_x)
    strength = 0.075 * np.exp(-(distance ** 2) / (2 * (w * 0.23) ** 2))
    face_area = (yy > h * 0.38) & (yy < h * 0.82)
    direction = np.where(xx < center_x, -1, 1)

    map_x = np.where(face_area, xx + direction * strength * distance, xx)
    map_x = np.clip(map_x, 0, w - 1).astype(np.float32)
    map_y = yy.astype(np.float32)

    slimmed = cv2.remap(img, map_x, map_y, cv2.INTER_LINEAR)

    # Slight smoothing
    slimmed = cv2.bilateralFilter(slimmed, 7, 35, 35)

    # Slight brightness enhancement
    slimmed = cv2.convertScaleAbs(slimmed, alpha=1.02, beta=3)

    saved = cv2.imwrite(output_path, slimmed)

    if not saved:
        print("Failed to save output image")
        sys.exit(1)

    print("Face slimming visualization saved:", output_path)
    sys.exit(0)

if __name__ == "__main__":
    if len(sys.argv) == 3:
        process_face_slimming(sys.argv[1], sys.argv[2])
    else:
        print("Usage: python process_face_slimming.py input output")
        sys.exit(1)
