"""
ocr_tool.py
Tool OCR — membaca teks dari gambar menggunakan PaddleOCR (Bagian 8, Tool 2 & Bagian 10).

Catatan versi: memakai API PaddleOCR 3.x (`predict()`), bukan 2.x (`ocr(cls=True)`).
PaddleOCR 2.7 + paddlepaddle 2.6 tidak dapat dipakai di Apple Silicon M4 — OpenBLAS
yang dibundel paddle 2.6 segfault di kernel sgemm saat konvolusi.
"""

from langchain_core.tools import tool

from config import settings

_ocr_engine = None


def _get_ocr_engine():
    """Lazy-load PaddleOCR engine (inisialisasi berat, hanya sekali)."""
    global _ocr_engine
    if _ocr_engine is None:
        from paddleocr import PaddleOCR

        _ocr_engine = PaddleOCR(
            lang=settings.OCR_LANG,
            use_textline_orientation=settings.OCR_USE_ANGLE_CLS,
        )
    return _ocr_engine


def extract_text_from_image(image_path: str) -> str:
    """Ekstrak teks dari file gambar dan mengembalikan teks gabungan."""
    engine = _get_ocr_engine()
    results = engine.predict(image_path)

    lines: list[str] = []
    for res in results:
        # PaddleOCR 3.x mengembalikan objek mirip-dict berisi rec_texts / rec_scores.
        texts = res["rec_texts"] if "rec_texts" in res else []
        lines.extend(t for t in texts if t and t.strip())

    return "\n".join(lines)


@tool
def image_ocr(image_path: str) -> str:
    """
    Baca teks dari file gambar (struk, dokumen hasil scan, foto, dll) menggunakan PaddleOCR.
    Gunakan tool ini ketika user mengunggah gambar dan bertanya tentang isi teks di dalamnya,
    contoh: "berapa total transaksi pada struk ini?".
    Input berupa path file gambar yang telah diunggah ke server.
    """
    try:
        text = extract_text_from_image(image_path)
    except Exception as exc:  # noqa: BLE001
        return f"Gagal membaca gambar: {exc}"

    if not text.strip():
        return "Tidak ada teks yang terdeteksi pada gambar."

    return text
