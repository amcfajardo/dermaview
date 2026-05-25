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


def process_undereye_lip_filler(input_path, output_path):

    img = cv2.imread(input_path)

    if img is None:
        print("Image not found")
        sys.exit(1)

    img = resize_for_processing(img)
    original = img.copy()
    h, w = img.shape[:2]

    result = original.copy()

    # ---------------------------------------------------
    # UNDEREYE AREA MASK
    # ---------------------------------------------------

    eye_mask = np.zeros((h, w), dtype=np.uint8)

    left_eye_center = (int(w * 0.35), int(h * 0.43))
    right_eye_center = (int(w * 0.65), int(h * 0.43))

    cv2.ellipse(
        eye_mask,
        left_eye_center,
        (int(w * 0.12), int(h * 0.055)),
        0,
        0,
        360,
        255,
        -1
    )

    cv2.ellipse(
        eye_mask,
        right_eye_center,
        (int(w * 0.12), int(h * 0.055)),
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
    eye_float = np.clip(eye_float * 0.55, 0, 0.55)

    eye_float_3 = cv2.merge([
        eye_float,
        eye_float,
        eye_float
    ])

    # ---------------------------------------------------
    # BRIGHTEN + FILL UNDEREYES
    # ---------------------------------------------------

    smooth_eye = cv2.bilateralFilter(
        result,
        d=15,
        sigmaColor=55,
        sigmaSpace=55
    )

    lab_eye = cv2.cvtColor(smooth_eye, cv2.COLOR_BGR2LAB)
    l, a, b = cv2.split(lab_eye)

    l = cv2.convertScaleAbs(
        l,
        alpha=1.08,
        beta=7
    )

    a = cv2.addWeighted(
        a,
        0.94,
        cv2.GaussianBlur(a, (0, 0), 3),
        0.06,
        0
    )

    lab_eye = cv2.merge((l, a, b))
    smooth_eye = cv2.cvtColor(lab_eye, cv2.COLOR_LAB2BGR)

    result = (
        smooth_eye.astype(np.float32) * eye_float_3 +
        result.astype(np.float32) * (1 - eye_float_3)
    ).astype(np.uint8)

    # ---------------------------------------------------
    # LIP FILLER: SUBTLE PLUMPING WARP
    # ---------------------------------------------------

    lip_center = (
        int(w * 0.50),
        int(h * 0.72)
    )

    lip_radius_x = int(w * 0.13)
    lip_radius_y = int(h * 0.065)

    map_x = np.zeros((h, w), np.float32)
    map_y = np.zeros((h, w), np.float32)

    for y in range(h):
        for x in range(w):

            dx = (x - lip_center[0]) / max(lip_radius_x, 1)
            dy = (y - lip_center[1]) / max(lip_radius_y, 1)

            distance = np.sqrt(dx * dx + dy * dy)

            if distance < 1.0:
                factor = 1 - distance

                # sample inward to make visible lips look fuller
                new_x = x - (x - lip_center[0]) * factor * 0.035
                new_y = y - (y - lip_center[1]) * factor * 0.060

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
    # LIP COLOR + HYDRATED DEFINITION
    # ---------------------------------------------------

    hsv = cv2.cvtColor(result, cv2.COLOR_BGR2HSV)

    lip_mask1 = cv2.inRange(
        hsv,
        np.array([0, 25, 35]),
        np.array([18, 190, 255])
    )

    lip_mask2 = cv2.inRange(
        hsv,
        np.array([155, 25, 35]),
        np.array([180, 190, 255])
    )

    lip_mask = cv2.bitwise_or(
        lip_mask1,
        lip_mask2
    )

    lip_mask = cv2.morphologyEx(
        lip_mask,
        cv2.MORPH_CLOSE,
        np.ones((7, 7), np.uint8)
    )

    lip_mask = cv2.GaussianBlur(
        lip_mask,
        (31, 31),
        0
    )

    lip_float = lip_mask.astype(np.float32) / 255.0
    lip_float = np.clip(lip_float * 0.30, 0, 0.30)

    hsv_float = hsv.astype(np.float32)

    hsv_float[:, :, 1] = hsv_float[:, :, 1] + (lip_float * 28)
    hsv_float[:, :, 2] = hsv_float[:, :, 2] + (lip_float * 10)

    hsv_float = np.clip(hsv_float, 0, 255).astype(np.uint8)

    lip_enhanced = cv2.cvtColor(
        hsv_float,
        cv2.COLOR_HSV2BGR
    )

    lip_float_3 = cv2.merge([
        lip_float,
        lip_float,
        lip_float
    ])

    result = (
        lip_enhanced.astype(np.float32) * lip_float_3 +
        result.astype(np.float32) * (1 - lip_float_3)
    ).astype(np.uint8)

    # ---------------------------------------------------
    # LIGHT SHARPENING TO KEEP NATURAL DETAILS
    # ---------------------------------------------------

    blur = cv2.GaussianBlur(result, (0, 0), 1)

    result = cv2.addWeighted(
        result,
        1.06,
        blur,
        -0.06,
        0
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
