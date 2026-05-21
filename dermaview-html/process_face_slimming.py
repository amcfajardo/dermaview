import cv2
import numpy as np
import sys

def process_face_slimming(input_path, output_path):
    img = cv2.imread(input_path)

    if img is None:
        print("Image not found.")
        return

    h, w = img.shape[:2]

    # Create slimming mesh distortion
    map_x = np.zeros((h, w), np.float32)
    map_y = np.zeros((h, w), np.float32)

    center_x = w // 2

    for y in range(h):
        for x in range(w):

            offset_x = x - center_x
            distance = abs(offset_x)

            # Only affect middle face area
            strength = 0

            if h * 0.20 < y < h * 0.85:
              strength = 0.16 * np.exp(-(distance ** 2) / (2 * (w * 0.30) ** 2))

            # Pull cheeks inward
            if x < center_x:
                new_x = x - strength * distance
            else:
                new_x = x + strength * distance

            map_x[y, x] = np.clip(new_x, 0, w - 1)
            map_y[y, x] = y

    slimmed = cv2.remap(img, map_x, map_y, cv2.INTER_LINEAR)

    # Slight smoothing
    slimmed = cv2.bilateralFilter(slimmed, 7, 35, 35)

    # Slight brightness enhancement
    slimmed = cv2.convertScaleAbs(slimmed, alpha=1.02, beta=3)

    cv2.imwrite(output_path, slimmed)

    print("Face slimming visualization saved:", output_path)

if len(sys.argv) == 3:
    process_face_slimming(sys.argv[1], sys.argv[2])
else:
    print("Usage: python process_face_slimming.py input output")