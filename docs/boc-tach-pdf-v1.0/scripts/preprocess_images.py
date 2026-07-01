"""
preprocess_images.py — Tiền xử lý ảnh scan để tăng chất lượng OCR.
2 tầng: Pillow (mặc định, nhẹ) và OpenCV (optional, nặng).

Usage:
    python preprocess_images.py <thư_mục_processing>
    python preprocess_images.py <thư_mục_processing> --enhance   # Kích hoạt Tầng 2
"""
import os
import sys
import argparse
from pathlib import Path


def preprocess_tier1(image_path):
    """Tầng 1 — Preprocessing nhẹ bằng Pillow (chạy mặc định).
    An toàn, không gây hại cho ảnh chất lượng tốt.
    Giữ nguyên màu sắc gốc.
    """
    from PIL import Image, ImageEnhance, ImageOps

    try:
        img = Image.open(image_path)

        # Autocontrast — cân bằng histogram tự động
        img = ImageOps.autocontrast(img, cutoff=1)

        # Tăng nhẹ contrast
        img = ImageEnhance.Contrast(img).enhance(1.2)

        # Làm nét nhẹ
        img = ImageEnhance.Sharpness(img).enhance(1.5)

        img.save(image_path, quality=95)
        return True
    except Exception as e:
        print(f"  [WARN] Tầng 1 lỗi cho {Path(image_path).name}: {e}")
        return False


def preprocess_tier2(image_path):
    """Tầng 2 — Preprocessing nặng bằng OpenCV (chỉ khi cần).
    Bao gồm deskew và denoise. Cần cài opencv-python.
    """
    try:
        import cv2
        import numpy as np
    except ImportError:
        print(f"  [WARN] OpenCV chưa cài. Bỏ qua Tầng 2.")
        print(f"         Cài thêm: pip install opencv-python")
        return False

    try:
        img = cv2.imread(str(image_path))
        if img is None:
            return False

        gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)

        # --- Deskew ---
        # Tìm góc nghiêng từ text pixels
        coords = np.column_stack(np.where(gray < 128))
        if len(coords) > 500:
            rect = cv2.minAreaRect(coords)
            angle = rect[-1]

            # Chuẩn hóa góc
            if angle < -45:
                angle = -(90 + angle)
            else:
                angle = -angle

            # Chỉ xoay nếu nghiêng đáng kể (> 0.5°)
            if abs(angle) > 0.5:
                h, w = img.shape[:2]
                M = cv2.getRotationMatrix2D((w // 2, h // 2), angle, 1.0)
                img = cv2.warpAffine(
                    img, M, (w, h),
                    flags=cv2.INTER_LINEAR,
                    borderMode=cv2.BORDER_REPLICATE
                )
                print(f"    Deskew: xoay {angle:.1f}°")

        # --- Denoise ---
        if len(img.shape) == 3:
            img = cv2.fastNlMeansDenoisingColored(
                img, None, h=8, hForColorComponents=8,
                templateWindowSize=7, searchWindowSize=21
            )
        else:
            img = cv2.fastNlMeansDenoising(
                img, None, h=8,
                templateWindowSize=7, searchWindowSize=21
            )

        cv2.imwrite(str(image_path), img)
        return True
    except Exception as e:
        print(f"  [WARN] Tầng 2 lỗi cho {Path(image_path).name}: {e}")
        return False


def process_all(processing_dir, enhance=False):
    input_dir = Path(processing_dir) / "01.input"

    if not input_dir.exists():
        print(f"[FAIL] Không tìm thấy thư mục 01.input: {input_dir}")
        return

    images = sorted(input_dir.glob("page_*.png"))
    if not images:
        print("[FAIL] Không tìm thấy ảnh nào trong 01.input/")
        return

    total = len(images)
    print(f"[INFO] Tìm thấy {total} ảnh. Bắt đầu preprocessing...")

    # Tầng 1 — Luôn chạy
    print(f"\n[Tầng 1 — Pillow] Autocontrast + Sharpen...")
    t1_ok = 0
    for i, img_path in enumerate(images, 1):
        if preprocess_tier1(str(img_path)):
            t1_ok += 1
        if i % 10 == 0:
            print(f"  ... {i}/{total}")
    print(f"  Hoàn tất: {t1_ok}/{total} ảnh")

    # Tầng 2 — Chỉ khi --enhance
    if enhance:
        print(f"\n[Tầng 2 — OpenCV] Deskew + Denoise...")
        t2_ok = 0
        for i, img_path in enumerate(images, 1):
            if preprocess_tier2(str(img_path)):
                t2_ok += 1
            if i % 10 == 0:
                print(f"  ... {i}/{total}")
        print(f"  Hoàn tất: {t2_ok}/{total} ảnh")

    print(f"\n[OK] Preprocessing xong {total} ảnh.")


def main():
    parser = argparse.ArgumentParser(
        description="Tiền xử lý ảnh scan — 2 tầng"
    )
    parser.add_argument("processing_dir", help="Thư mục *_processing")
    parser.add_argument("--enhance", action="store_true",
                        help="Kích hoạt Tầng 2 (OpenCV: deskew + denoise)")
    args = parser.parse_args()

    process_all(args.processing_dir, enhance=args.enhance)


if __name__ == "__main__":
    main()
