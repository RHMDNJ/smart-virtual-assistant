"""
Test perutean sapaan.

Latar belakang: llama3.1 refleks memanggil tool begitu tools di-bind. Setelah
knowledge base berisi banyak dokumen, RAG mengembalikan potongan tak nyambung
untuk sapaan, dan model menjawab "tidak ada jawaban yang relevan" untuk sekadar
"selamat pagi" — cacat yang terlihat user, ditemukan saat UAT.
"""

import pathlib

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


# --- pemulihan tool call berbentuk teks ------------------------------------

from agent import _tool_call_dari_teks  # noqa: E402

TOOLS = {"rag_search", "image_ocr", "sql_query"}


def test_tool_call_teks_dipulihkan():
    """
    llama3.1 kadang menulis panggilan tool sebagai JSON biasa alih-alih mengisi
    tool_calls. Tanpa pemulihan ini, JSON mentah tampil sebagai jawaban dan
    tersimpan ke riwayat, lalu meracuni pemilihan tool berikutnya.
    """
    hasil = _tool_call_dari_teks(
        '{"name": "sql_query", "parameters": {"query": "SELECT count(*) FROM documents"}}',
        TOOLS,
    )
    assert hasil == [
        {
            "name": "sql_query",
            "args": {"query": "SELECT count(*) FROM documents"},
            "id": "pulih-dari-teks",
        }
    ]


def test_kunci_arguments_juga_diterima():
    hasil = _tool_call_dari_teks('{"name": "rag_search", "arguments": {"query": "cuti"}}', TOOLS)
    assert hasil[0]["args"] == {"query": "cuti"}


@pytest.mark.parametrize(
    "konten",
    [
        "Selamat pagi! Ada yang bisa dibantu?",
        '{"name": "tool_yang_tidak_ada", "parameters": {}}',
        "{ bukan json",
        '{"parameters": {"query": "x"}}',      # tanpa nama tool
        '{"name": "sql_query", "parameters": "bukan objek"}',
        "",
        None,
    ],
)
def test_bukan_tool_call_dibiarkan(konten):
    assert _tool_call_dari_teks(konten, TOOLS) is None


# --- riwayat bukan sumber fakta ---------------------------------------------

def test_pengingat_disisipkan_pada_hasil_tool_terakhir():
    """
    Regresi: pada sesi berriwayat panjang, model terbukti menyalin angka dari
    jawabannya sendiri di masa lalu — termasuk angka yang keliru — alih-alih
    memakai hasil tool. Pengingat disisipkan ke dalam ToolMessage, BUKAN sebagai
    SystemMessage di akhir, karena pesan sistem di posisi itu membuat llama3.1
    menuliskan penanda peran "assistant" ke dalam jawaban.
    """
    import agent
    from langchain_core.messages import SystemMessage, ToolMessage

    sumber = pathlib.Path(agent.__file__).read_text()
    assert "[Catatan sistem]" in sumber
    # Pastikan pengingat menempel pada ToolMessage, bukan SystemMessage baru.
    potongan = sumber.split("if pesan and isinstance(pesan[-1], ToolMessage):")[1][:400]
    assert "content +=" in potongan
    assert "SystemMessage(" not in potongan


def test_aturan_riwayat_ada_di_system_prompt():
    from agent import SYSTEM_PROMPT

    assert "BUKAN sumber fakta" in SYSTEM_PROMPT
    assert "hasil tool pada giliran ini" in SYSTEM_PROMPT


# --- cadangan RAG ketika SQL tidak menemukan apa pun -------------------------

@pytest.mark.parametrize(
    "isi,kosong",
    [
        ("Query berhasil dijalankan, tetapi tidak ada hasil.", True),
        ("Query ditolak: Hanya query SELECT yang diperbolehkan.", True),
        ("Query gagal dijalankan: relation tidak ada", True),
        ("[{'count': 12}]", False),
        ("[{'filename': 'a.txt'}]", False),
    ],
)
def test_deteksi_hasil_sql_kosong(isi, kosong):
    """
    llama3.1 kerap memilih sql_query untuk pertanyaan yang jawabannya ada di
    dokumen, lalu menyerah. Deteksi ini memicu percobaan ulang lewat RAG.
    """
    from langchain_core.messages import ToolMessage

    from agent import _hasil_sql_kosong

    assert _hasil_sql_kosong([ToolMessage(content=isi, tool_call_id="x")]) is kosong


def test_tanpa_hasil_tool_tidak_dianggap_kosong():
    from agent import _hasil_sql_kosong

    assert _hasil_sql_kosong([]) is False


# --- pertanyaan tentang jati diri SAVIRA ------------------------------------

JATI_DIRI = [
    "Siapa penciptamu?",
    "siapa pembuatmu",
    "kamu buatan siapa",
    "kamu dibuat oleh siapa",
    "siapa yang mengembangkan kamu?",
    "Kamu ini apa?",
    "siapa kamu",
    "apa itu SAVIRA",
    "kamu bisa bantu apa?",
    "apa saja yang bisa kamu lakukan",
]

BUKAN_JATI_DIRI = [
    "Berapa hari cuti tahunan pegawai?",
    "apa isi dokumennya?",
    "Siapa Bupati Hulu Sungai Selatan?",
    "Ada berapa dokumen di knowledge base?",
]


@pytest.mark.parametrize("pesan", JATI_DIRI)
def test_pertanyaan_jati_diri_dikenali(pesan):
    """
    Pertanyaan tentang SAVIRA sendiri tidak butuh tool. Sebelum dirutekan,
    "Kamu ini apa?" memicu pencarian dokumen lalu dijawab "tidak bisa menjawab".
    """
    from agent import tanya_jati_diri

    assert tanya_jati_diri(pesan)


@pytest.mark.parametrize("pesan", BUKAN_JATI_DIRI)
def test_pertanyaan_informasi_bukan_jati_diri(pesan):
    from agent import tanya_jati_diri

    assert not tanya_jati_diri(pesan)


def test_prompt_jati_diri_menyebut_pencipta_dan_sudut_pandang():
    from agent import PROMPT_JATI_DIRI

    assert "Rahmad" in PROMPT_JATI_DIRI
    # Tanpa arahan ini, model menjawab "Rahmad adalah Pencipta Anda" —
    # keliru sudut pandang, seolah lawan bicaranya yang punya pencipta.
    assert "orang pertama" in PROMPT_JATI_DIRI


def test_system_prompt_menyebut_pencipta():
    from agent import SYSTEM_PROMPT

    assert "Rahmad" in SYSTEM_PROMPT
