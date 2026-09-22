"""
Test perutean sapaan.

Latar belakang: llama3.1 refleks memanggil tool begitu tools di-bind. Setelah
knowledge base berisi banyak dokumen, RAG mengembalikan potongan tak nyambung
untuk sapaan, dan model menjawab "tidak ada jawaban yang relevan" untuk sekadar
"selamat pagi" — cacat yang terlihat user, ditemukan saat UAT.
"""

import pytest

from agent import sapaan_saja

SAPAAN = [
    "halo", "Halo!", "hai", "Selamat pagi!", "selamat sore",
    "assalamualaikum", "Terima kasih", "makasih", "thanks",
    "apa kabar", "ok", "oke", "sip", "bye", "sampai jumpa",
    # Partikel penutup yang lazim dalam percakapan Indonesia
    "Terima kasih ya", "makasih banyak", "halo kak", "pagi pak", "ok deh",
]

BUKAN_SAPAAN = [
    "Berapa hari cuti tahunan?",
    "Halo, berapa cuti tahunan pegawai?",   # sapaan + pertanyaan → tetap butuh tool
    "jelaskan aturan cuti",
    "apa itu HPS?",
    "Selamat pagi, tolong carikan kebijakan retensi dokumen keuangan",
    "Ada berapa dokumen di knowledge base?",
    "terima kasih atas penjelasan kebijakan cuti tahunan",   # ada permintaan konteks
]


@pytest.mark.parametrize("pesan", SAPAAN)
def test_sapaan_dikenali(pesan):
    assert sapaan_saja(pesan)


@pytest.mark.parametrize("pesan", BUKAN_SAPAAN)
def test_pertanyaan_tidak_dianggap_sapaan(pesan):
    assert not sapaan_saja(pesan)


def test_pesan_panjang_bukan_sapaan():
    """Batas panjang mencegah paragraf yang kebetulan diawali sapaan ikut terlewat."""
    assert not sapaan_saja("halo " + "a" * 50)
