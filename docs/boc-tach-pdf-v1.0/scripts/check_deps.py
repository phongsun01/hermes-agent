"""
check_deps.py — Kiểm tra dependencies cho skill boc-tach-pdf v2.
Chạy trước mọi thao tác để đảm bảo môi trường sẵn sàng.
"""
import importlib
import sys

CORE_DEPS = [
    ("fitz", "PyMuPDF", "Render PDF, phân tích cấu trúc, trích xuất ảnh"),
    ("PIL", "Pillow", "Preprocessing ảnh, crop ảnh minh họa"),
    ("docx", "python-docx", "Tạo reference.docx template"),
    ("pypandoc", "pypandoc-binary", "Convert Markdown → DOCX (kèm Pandoc binary)"),
]

OPTIONAL_DEPS = [
    ("cv2", "opencv-python", "Preprocessing Tầng 2: deskew, denoise (optional)"),
    ("openpyxl", "openpyxl", "Xuất dữ liệu bảng biểu ra Excel (optional)"),
]


def check_package(import_name):
    try:
        mod = importlib.import_module(import_name)
        version = getattr(mod, "__version__", getattr(mod, "version", "unknown"))
        if import_name == "fitz":
            version = getattr(mod, "VersionBind", version)
        return True, str(version)
    except ImportError:
        return False, None


def main():
    print("=" * 60)
    print("  BÓC TÁCH PDF v2 — Kiểm tra Dependencies")
    print("=" * 60)

    missing_core = []
    missing_optional = []

    # Core dependencies
    print("\n[CORE — Bắt buộc]")
    for import_name, pip_name, description in CORE_DEPS:
        ok, ver = check_package(import_name)
        if ok:
            print(f"  ✅ {pip_name} (v{ver}) — {description}")
        else:
            print(f"  ❌ {pip_name} — THIẾU — {description}")
            missing_core.append(pip_name)

    # Optional dependencies
    print("\n[OPTIONAL — Tùy chọn]")
    for import_name, pip_name, description in OPTIONAL_DEPS:
        ok, ver = check_package(import_name)
        if ok:
            print(f"  ✅ {pip_name} (v{ver}) — {description}")
        else:
            print(f"  ⚡ {pip_name} — chưa cài — {description}")
            missing_optional.append(pip_name)

    # Summary
    print("\n" + "=" * 60)
    if not missing_core and not missing_optional:
        print("✅ TẤT CẢ DEPENDENCIES SẴN SÀNG. Có thể bắt đầu xử lý.")
    elif not missing_core:
        print("✅ Core dependencies đầy đủ. Có thể chạy pipeline chính.")
        print(f"⚡ Optional chưa cài: {', '.join(missing_optional)}")
        print(f"   Cài thêm: pip install {' '.join(missing_optional)}")
    else:
        print("❌ THIẾU CORE DEPENDENCIES. Chạy lệnh sau để cài:")
        install_cmd = f"pip install {' '.join(missing_core)}"
        print(f"   {install_cmd}")
        if missing_optional:
            print(f"\n⚡ Optional (tùy chọn): pip install {' '.join(missing_optional)}")
        print("=" * 60)
        sys.exit(1)

    print("=" * 60)


if __name__ == "__main__":
    main()
