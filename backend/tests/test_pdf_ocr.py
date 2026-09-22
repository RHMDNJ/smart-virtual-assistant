"""
Test fallback OCR untuk PDF hasil pindai.

PDF pindaian hanyalah gambar yang dibungkus PDF — tanpa fallback ini, dokumen
semacam itu ditolak dengan pesan "tidak memiliki konten teks", padahal isinya
terbaca jelas oleh mata. Dokumen pemerintah kerap berbentuk demikian.
"""

import pytest
from PIL import Image, ImageDraw

from services.document_service import _load_raw_text


def pdf_pindaian(tmp_path, teks="STRUK BELANJA TOTAL Rp 120.000", halaman=1):
    """PDF berisi gambar saja, tanpa lapisan teks — meniru hasil scanner."""
    gambar = []
    for _ in range(halaman):
        im = Image.new("RGB", (600, 200), "white")
        ImageDraw.Draw(im).text((20, 80), teks, fill="black")
        gambar.append(im)
    path = tmp_path / "pindaian.pdf"
    gambar[0].save(path, "PDF", save_all=len(gambar) > 1, append_images=gambar[1:])
    return str(path)


def pdf_berteks(tmp_path):
    """PDF dengan lapisan teks sungguhan (dibuat lewat PyMuPDF)."""
    import pymupdf

    berkas = pymupdf.open()
    hal = berkas.new_page()
    hal.insert_text((72, 100), "Pasal 1. Cuti tahunan 14 hari kerja.")
    path = tmp_path / "berteks.pdf"
    berkas.save(str(path))
    berkas.close()
    return str(path)


def test_pdf_pindaian_dibaca_lewat_ocr(tmp_path, monkeypatch):
    dipanggil = []

    def ocr_palsu(path):
        dipanggil.append(path)
        return "HASIL OCR HALAMAN"

    monkeypatch.setattr("tools.ocr_tool.extract_text_from_image", ocr_palsu)

    hasil = _load_raw_text(pdf_pindaian(tmp_path))
    assert "HASIL OCR HALAMAN" in hasil
    assert len(dipanggil) == 1


def test_pdf_berteks_tidak_perlu_ocr(tmp_path, monkeypatch):
    """OCR itu mahal — halaman yang sudah punya teks tidak boleh ikut di-render."""

    def jangan_dipanggil(path):
        raise AssertionError("OCR tidak boleh dipanggil untuk halaman berteks")

    monkeypatch.setattr("tools.ocr_tool.extract_text_from_image", jangan_dipanggil)

    hasil = _load_raw_text(pdf_berteks(tmp_path))
    assert "Cuti tahunan" in hasil


def test_hanya_halaman_kosong_yang_di_ocr(tmp_path, monkeypatch):
    """PDF campuran: halaman berteks dipakai apa adanya, halaman pindaian di-OCR."""
    import pymupdf

    berkas = pymupdf.open()
    berkas.new_page().insert_text((72, 100), "Halaman satu berisi teks asli.")
    berkas.new_page()  # halaman kosong, mewakili hasil pindaian
    path = tmp_path / "campuran.pdf"
    berkas.save(str(path))
    berkas.close()

    monkeypatch.setattr("tools.ocr_tool.extract_text_from_image", lambda p: "TEKS DARI OCR")

    hasil = _load_raw_text(str(path))
    assert "Halaman satu berisi teks asli." in hasil
    assert "TEKS DARI OCR" in hasil


def test_fallback_bisa_dimatikan(tmp_path, monkeypatch):
    from config import settings

    monkeypatch.setattr(settings, "OCR_PDF_FALLBACK", False)
    monkeypatch.setattr("tools.ocr_tool.extract_text_from_image", lambda p: "TIDAK DIPAKAI")

    assert _load_raw_text(pdf_pindaian(tmp_path)).strip() == ""


def test_batas_jumlah_halaman_dihormati(tmp_path, monkeypatch):
    """Dokumen tebal tidak boleh menggantung request hanya karena OCR."""
    from config import settings

    monkeypatch.setattr(settings, "OCR_PDF_MAX_PAGES", 2)
    dipanggil = []
    monkeypatch.setattr(
        "tools.ocr_tool.extract_text_from_image",
        lambda p: dipanggil.append(p) or "OCR",
    )

    _load_raw_text(pdf_pindaian(tmp_path, halaman=5))
    assert len(dipanggil) == 2


def test_satu_halaman_gagal_ocr_tidak_membuang_sisanya(tmp_path, monkeypatch):
    """Pada dokumen pindaian tebal, satu halaman bermasalah tidak boleh
    membatalkan halaman lain yang berhasil dibaca."""
    urutan = []

    def kadang_gagal(path):
        urutan.append(path)
        if len(urutan) == 1:
            raise RuntimeError("engine OCR mati pada halaman pertama")
        return f"TEKS HALAMAN {len(urutan)}"

    monkeypatch.setattr("tools.ocr_tool.extract_text_from_image", kadang_gagal)

    hasil = _load_raw_text(pdf_pindaian(tmp_path, halaman=3))
    assert "TEKS HALAMAN 2" in hasil
    assert "TEKS HALAMAN 3" in hasil
    assert len(urutan) == 3, "seluruh halaman tetap dicoba"


# --- teks kacau (font tanpa peta Unicode) -----------------------------------

from services.document_service import _teks_kacau  # noqa: E402


@pytest.mark.parametrize(
    "teks,kacau",
    [
        ("BAHAN RAPAT DISKOMINFO Pembahasan Ranperda Perubahan Kedua atas Perda", False),
        ("Pasal 1 - Cuti tahunan 14 hari kerja per tahun bagi pegawai tetap.", False),
        ("Jalan Kalimantan No. 12, Kandangan — telp (0517) 21234, 70614", False),
        ("ʽ˔˞˔˥˧˔\x03ˆˠ˔˥˧\x03ʶ˜˧ˬ\x03˯\x03ʥʣʥʩ\x03·ëŜƠëŜĮëŜȥfŦŎëőȰȥ«ŦőƨƔĺȥ", True),
        ("EŦƿĕƌŜŚĕŜƠȥƔĕĆëĮëĺȥëƔëőȥĮëĮëƔëŜȥƠĕƌĆĕŜƠƨŎ$ĺƔƌƨƉƔĺ", True),
        ("abc", False),  # terlalu pendek untuk dinilai
    ],
)
def test_deteksi_teks_kacau(teks, kacau):
    """
    Sebagian PDF memakai font subset tanpa peta ToUnicode, sehingga ekstraksi
    menghasilkan simbol alih-alih huruf. Teks itu lolos pemeriksaan "tidak
    kosong" tetapi tidak bermakna — halamannya harus ikut di-OCR.
    """
    assert _teks_kacau(teks) is kacau


def test_halaman_berteks_kacau_ikut_di_ocr(tmp_path, monkeypatch):
    """Regresi: halaman dengan teks kacau sebelumnya lolos dan tersimpan apa adanya."""
    import pymupdf

    berkas = pymupdf.open()
    hal = berkas.new_page()
    # Simulasi hasil ekstraksi yang rusak — disisipkan sebagai teks sungguhan.
    hal.insert_text((72, 100), "EŦƿĕƌŜŚĕŜƠȥƔĕĆëĮëĺȥëƔëőȥĮëĮëƔëŜȥƠĕƌĆĕŜƠƨŎ$ĺƔƌƨƉƔĺ")
    path = tmp_path / "kacau.pdf"
    berkas.save(str(path))
    berkas.close()

    monkeypatch.setattr("tools.ocr_tool.extract_text_from_image", lambda p: "TEKS HASIL OCR")

    hasil = _load_raw_text(str(path))
    assert "TEKS HASIL OCR" in hasil
