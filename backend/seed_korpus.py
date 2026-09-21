"""Isi knowledge base dengan korpus sintetis untuk mengukur mutu retrieval."""
import sys
from database import SessionLocal
from models import Document
from services.document_service import index_text

TOPIK = [
    ("sk-tunjangan-kinerja", "SURAT KEPUTUSAN TUNJANGAN KINERJA. Tunjangan kinerja dibayarkan paling lambat tanggal 10 setiap bulan. Besaran mengacu kelas jabatan sesuai Peraturan Bupati Nomor 12 Tahun 2024. Kehadiran di bawah 80 persen dikenakan pemotongan."),
    ("sop-pengadaan", "SOP PENGADAAN BARANG DAN JASA. Pengadaan di bawah Rp 50.000.000 dapat melalui pengadaan langsung. Di atas nilai itu wajib tender terbuka. Setiap pengadaan melampirkan HPS, spesifikasi teknis, dan berita acara serah terima."),
    ("panduan-keamanan-ti", "PANDUAN KEAMANAN TI. Kata sandi minimal 12 karakter, diganti tiap 90 hari. Akses VPN hanya untuk pegawai yang menandatangani pakta integritas. Backup basis data harian pukul 23.00 WITA, disimpan 30 hari."),
    ("kebijakan-cuti", "KEBIJAKAN CUTI. Karyawan tetap berhak cuti tahunan 14 hari kerja per tahun, diajukan minimal 7 hari sebelumnya. Cuti melahirkan 3 bulan. Cuti besar diberikan setelah 6 tahun masa kerja."),
    ("retensi-arsip", "KEBIJAKAN RETENSI ARSIP. Dokumen keuangan disimpan 10 tahun sejak penerbitan. Dokumen kepegawaian disimpan 5 tahun setelah pegawai berhenti. Arsip rapat disimpan 3 tahun."),
    ("jam-kerja", "KETENTUAN JAM KERJA. Jam kerja standar 08.00 sampai 17.00 WITA, Senin hingga Jumat. Keterlambatan lebih dari 30 menit dicatat sebagai pelanggaran ringan. Lembur wajib disetujui atasan langsung."),
    ("perjalanan-dinas", "PEDOMAN PERJALANAN DINAS. Uang harian perjalanan dinas dalam daerah Rp 350.000 per hari. Luar daerah mengikuti Standar Biaya Masukan. Bukti perjalanan diserahkan maksimal 5 hari kerja setelah kembali."),
    ("pengelolaan-aset", "PENGELOLAAN ASET DAERAH. Setiap aset dicatat dalam Kartu Inventaris Barang. Penghapusan aset memerlukan persetujuan Sekretaris Daerah. Inventarisasi fisik dilakukan setahun sekali."),
    ("layanan-publik", "STANDAR LAYANAN PUBLIK. Pengaduan masyarakat dijawab maksimal 3 hari kerja. Survei kepuasan dilakukan tiap semester. Loket layanan buka pukul 08.00 sampai 15.00 WITA."),
    ("disiplin-pegawai", "DISIPLIN PEGAWAI. Pelanggaran ringan berupa teguran lisan. Pelanggaran sedang berupa penundaan kenaikan gaji berkala. Pelanggaran berat dapat berupa pemberhentian, mengacu PP Nomor 94 Tahun 2021."),
    ("pengembangan-kompetensi", "PENGEMBANGAN KOMPETENSI. Setiap pegawai berhak minimal 20 jam pelajaran per tahun. Diklat teknis diusulkan melalui atasan. Beasiswa tugas belajar mensyaratkan masa kerja minimal 4 tahun."),
    ("keuangan-daerah", "PENGELOLAAN KEUANGAN DAERAH. Pergeseran anggaran antar objek belanja memerlukan persetujuan TAPD. Laporan realisasi disusun bulanan. SPJ diserahkan maksimal tanggal 5 bulan berikutnya."),
]

db = SessionLocal()
try:
    db.query(Document).delete()
    db.commit()
    total = 0
    for nama, isi in TOPIK:
        total += index_text(db, isi, f"{nama}.txt")
    print(f"  {len(TOPIK)} dokumen, {total} chunk diindeks")
finally:
    db.close()
