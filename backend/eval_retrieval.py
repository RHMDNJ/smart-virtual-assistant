"""Ukur recall@k: seberapa sering dokumen yang benar masuk hasil teratas."""
from config import settings
from database import SessionLocal
from tools.rag_tool import cari_dokumen

# (pertanyaan, dokumen yang seharusnya terambil, jenis)
KASUS = [
    ("Peraturan Bupati Nomor 12 Tahun 2024 mengatur apa?", "sk-tunjangan-kinerja", "literal"),
    ("Apa isi PP Nomor 94 Tahun 2021?", "disiplin-pegawai", "literal"),
    ("Berapa batas nilai Rp 50.000.000 dalam pengadaan?", "sop-pengadaan", "literal"),
    ("Apa itu HPS dan berita acara serah terima?", "sop-pengadaan", "literal"),
    ("Apa itu Kartu Inventaris Barang?", "pengelolaan-aset", "literal"),
    ("Apa fungsi TAPD dan SPJ?", "keuangan-daerah", "literal"),
    ("Berapa lama libur tahunan yang bisa diambil pegawai?", "kebijakan-cuti", "parafrase"),
    ("Kapan pegawai harus mulai bekerja setiap hari?", "jam-kerja", "parafrase"),
    ("Berapa lama berkas keuangan harus disimpan?", "retensi-arsip", "parafrase"),
    ("Aturan sandi komputer dan cadangan data", "panduan-keamanan-ti", "parafrase"),
    ("Uang saku untuk tugas ke luar kota", "perjalanan-dinas", "parafrase"),
    ("Sanksi bagi pegawai yang melanggar aturan", "disiplin-pegawai", "parafrase"),
    ("Kesempatan pegawai mengikuti pelatihan", "pengembangan-kompetensi", "parafrase"),
    ("Berapa lama pengaduan warga dijawab?", "layanan-publik", "parafrase"),
]

TOP_K = 3
db = SessionLocal()
try:
    hasil = {}
    for mode, hybrid in (("vektor saja", False), ("hybrid", True)):
        settings.RAG_HYBRID = hybrid
        skor = {"literal": [0, 0], "parafrase": [0, 0]}
        meleset = []
        for pertanyaan, benar, jenis in KASUS:
            nama = [h["filename"].replace(".txt", "") for h in cari_dokumen(db, pertanyaan, TOP_K)]
            kena = benar in nama
            skor[jenis][0] += int(kena)
            skor[jenis][1] += 1
            if not kena:
                meleset.append((jenis, pertanyaan[:44], benar, nama[:2]))
        hasil[mode] = (skor, meleset)

    print(f"\n  recall@{TOP_K} dari {len(KASUS)} pertanyaan\n")
    print(f"  {'mode':<12} {'literal':<12} {'parafrase':<12} total")
    for mode, (skor, _) in hasil.items():
        lit = skor["literal"]; par = skor["parafrase"]
        tot_b = lit[0] + par[0]; tot_n = lit[1] + par[1]
        print(f"  {mode:<12} {lit[0]}/{lit[1]:<10} {par[0]}/{par[1]:<10} {tot_b}/{tot_n} ({100*tot_b/tot_n:.0f}%)")

    for mode, (_, meleset) in hasil.items():
        if meleset:
            print(f"\n  meleset pada {mode}:")
            for jenis, q, benar, dapat in meleset:
                print(f"    [{jenis}] {q!r} -> harusnya {benar}, dapat {dapat}")
finally:
    db.close()
