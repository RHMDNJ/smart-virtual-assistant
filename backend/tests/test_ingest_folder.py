"""Test alat ingest massal (memasukkan bahan resmi dalam jumlah banyak)."""

import pytest

from ingest_folder import EKSTENSI, baca, teks_dari_html


def test_html_membuang_navigasi_dan_footer(tmp_path):
    """
    Menu dan footer situs bukan isi dokumen. Bila ikut terindeks, potongan
    navigasi akan bersaing dengan isi sebenarnya saat pencarian.
    """
    p = tmp_path / "halaman.html"
    p.write_text(
        "<html><head><title>Judul</title><style>.a{}</style></head>"
        "<body><nav>Beranda Kontak Profil</nav>"
        "<h1>Peraturan Daerah</h1><p>Isi yang sebenarnya.</p>"
        "<script>lacak()</script><footer>Hak cipta 2026</footer></body></html>",
        encoding="utf-8",
    )
    hasil = teks_dari_html(str(p))
    assert "Isi yang sebenarnya." in hasil
    assert "Peraturan Daerah" in hasil
    assert "Beranda Kontak" not in hasil
    assert "Hak cipta" not in hasil
    assert "lacak()" not in hasil


def test_html_tanpa_baris_kosong_berlebihan(tmp_path):
    p = tmp_path / "a.html"
    p.write_text("<body><p>satu</p>\n\n\n<p>dua</p></body>", encoding="utf-8")
    assert teks_dari_html(str(p)) == "satu\ndua"


def test_baca_memilih_pembaca_sesuai_ekstensi(tmp_path):
    txt = tmp_path / "catatan.txt"
    txt.write_text("Isi berkas teks biasa.", encoding="utf-8")
    assert "Isi berkas teks biasa." in baca(str(txt))


@pytest.mark.parametrize("ext", [".pdf", ".txt", ".md", ".html", ".htm"])
def test_ekstensi_yang_didukung(ext):
    assert ext in EKSTENSI


@pytest.mark.parametrize("ext", [".docx", ".xlsx", ".zip", ".exe"])
def test_ekstensi_yang_diabaikan(ext):
    assert ext not in EKSTENSI
