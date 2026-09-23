import { useCallback, useEffect, useState } from "react";
import {
  addDocument,
  deleteDocument,
  getDocument,
  listDocuments,
  reindexDocuments,
  updateDocument,
  uploadFile,
} from "../services/api.js";

const KOSONG = { filename: "", content: "" };

function formatTanggal(iso) {
  try {
    return new Date(iso).toLocaleDateString("id-ID", {
      day: "numeric",
      month: "short",
      year: "numeric",
    });
  } catch {
    return "";
  }
}

export default function KnowledgeBase({ user, onClose }) {
  const [dokumen, setDokumen] = useState([]);
  const [memuat, setMemuat] = useState(true);
  const [error, setError] = useState(null);
  const [info, setInfo] = useState(null);
  const [sunting, setSunting] = useState(null); // {filename, content, baru}
  const [menyimpan, setMenyimpan] = useState(false);
  const [konfirmasiHapus, setKonfirmasiHapus] = useState(null);
  const [sibuk, setSibuk] = useState(false);

  const bolehTulis = user?.role === "USER" || user?.role === "ADMIN";
  const bolehHapus = user?.role === "ADMIN";

  const muat = useCallback(async () => {
    setMemuat(true);
    setError(null);
    try {
      setDokumen(await listDocuments());
    } catch (err) {
      setError(err?.response?.data?.detail || "Gagal memuat daftar dokumen.");
    } finally {
      setMemuat(false);
    }
  }, []);

  useEffect(() => {
    muat();
  }, [muat]);

  // Esc menutup panel — kebiasaan yang diharapkan dari dialog.
  useEffect(() => {
    const onKey = (e) => {
      if (e.key === "Escape" && !sunting && !konfirmasiHapus) onClose();
    };
    window.addEventListener("keydown", onKey);
    return () => window.removeEventListener("keydown", onKey);
  }, [onClose, sunting, konfirmasiHapus]);

  async function bukaSunting(filename) {
    setError(null);
    try {
      const d = await getDocument(filename);
      setSunting({ filename: d.filename, content: d.content, baru: false });
    } catch (err) {
      setError(err?.response?.data?.detail || "Gagal membuka dokumen.");
    }
  }

  async function simpan() {
    if (!sunting.filename.trim() || !sunting.content.trim()) return;
    setMenyimpan(true);
    setError(null);
    try {
      const hasil = sunting.baru
        ? await addDocument(sunting.filename.trim(), sunting.content)
        : await updateDocument(sunting.filename, sunting.content);
      setInfo(`"${hasil.filename}" tersimpan — ${hasil.chunks} bagian terindeks.`);
      setSunting(null);
      muat();
    } catch (err) {
      setError(err?.response?.data?.detail || "Gagal menyimpan dokumen.");
    } finally {
      setMenyimpan(false);
    }
  }

  async function hapus(filename) {
    setSibuk(true);
    setError(null);
    try {
      await deleteDocument(filename);
      setInfo(`"${filename}" dihapus dari knowledge base.`);
      setKonfirmasiHapus(null);
      muat();
    } catch (err) {
      setError(err?.response?.data?.detail || "Gagal menghapus dokumen.");
    } finally {
      setSibuk(false);
    }
  }

  async function unggah(e) {
    const berkas = e.target.files?.[0];
    e.target.value = "";
    if (!berkas) return;
    setSibuk(true);
    setError(null);
    // Umpan balik harus muncul SEKARANG: mengindeks PDF bisa belasan detik, dan
    // PDF hasil pindai lebih dari dua menit karena setiap halaman di-OCR.
    // Tanpa ini panel tampak membeku dan terasa tidak merespons.
    setInfo(
      `Mengunggah ${berkas.name}… ${
        berkas.name.toLowerCase().endsWith(".pdf")
          ? "PDF hasil pindai perlu OCR dan bisa memakan beberapa menit."
          : "Mohon tunggu."
      }`
    );
    try {
      const hasil = await uploadFile(berkas);
      setInfo(`${hasil.filename} — ${hasil.detail || hasil.status}`);
      muat();
    } catch (err) {
      setError(err?.response?.data?.detail || "Gagal mengunggah berkas.");
    } finally {
      setSibuk(false);
    }
  }

  async function indeksUlang() {
    setSibuk(true);
    setError(null);
    setInfo("Menghitung ulang embedding…");
    try {
      const hasil = await reindexDocuments();
      setInfo(`${hasil.reindexed} bagian berhasil diindeks ulang.`);
    } catch (err) {
      setError(err?.response?.data?.detail || "Gagal mengindeks ulang.");
      setInfo(null);
    } finally {
      setSibuk(false);
    }
  }

  const totalChunk = dokumen.reduce((n, d) => n + d.chunks, 0);

  return (
    <div
      className="fixed inset-0 z-30 flex animate-fade-in items-start justify-center bg-navy/40 p-4 backdrop-blur-sm sm:p-8"
      onMouseDown={(e) => e.target === e.currentTarget && onClose()}
    >
      <div
        role="dialog"
        aria-label="Kelola knowledge base"
        data-kb
        className="flex max-h-full w-full max-w-3xl animate-scale-in flex-col overflow-hidden rounded-2xl border border-line bg-raised shadow-2xl"
      >
        <header className="flex items-center gap-3 border-b border-line px-5 py-4">
          <div>
            <h2 className="text-sm font-semibold">Knowledge base</h2>
            <p className="text-[11px] text-muted">
              {memuat ? "memuat…" : `${dokumen.length} dokumen · ${totalChunk} bagian terindeks`}
            </p>
          </div>
          <div className="ml-auto flex items-center gap-2">
            {bolehTulis && (
              <>
                <label
                  className={`flex cursor-pointer items-center gap-1.5 rounded-lg border border-line px-2.5 py-1.5 text-xs text-muted transition hover:bg-line/50 hover:text-ink ${
                    sibuk ? "pointer-events-none opacity-60" : ""
                  }`}
                >
                  {sibuk && (
                    <span className="h-3 w-3 animate-spin rounded-full border-2 border-current border-t-transparent" />
                  )}
                  {sibuk ? "Memproses…" : "Unggah berkas"}
                  <input
                    type="file"
                    accept=".pdf,.txt,.md"
                    className="hidden"
                    onChange={unggah}
                    disabled={sibuk}
                  />
                </label>
                <button
                  type="button"
                  onClick={() => setSunting({ ...KOSONG, baru: true })}
                  className="rounded-lg bg-brand px-2.5 py-1.5 text-xs font-medium text-brand-ink transition active:scale-95"
                >
                  + Tulis dokumen
                </button>
              </>
            )}
            <button
              type="button"
              onClick={onClose}
              aria-label="Tutup"
              className="grid h-8 w-8 place-items-center rounded-lg text-muted transition hover:bg-line/50 hover:text-ink"
            >
              ✕
            </button>
          </div>
        </header>

        {(error || info) && (
          <p
            data-kb-pesan
            className={`flex animate-slide-up items-center gap-2 border-b border-line px-5 py-2 text-xs ${
              error ? "bg-red-500/10 text-red-600 dark:text-red-400" : "bg-brand/10 text-brand"
            }`}
          >
            {sibuk && !error && (
              <span className="h-3 w-3 shrink-0 animate-spin rounded-full border-2 border-current border-t-transparent" />
            )}
            <span>{error || info}</span>
          </p>
        )}

        <div className="flex-1 overflow-y-auto">
          {memuat ? (
            <p className="px-5 py-10 text-center text-sm text-muted">Memuat dokumen…</p>
          ) : dokumen.length === 0 ? (
            <div className="px-5 py-12 text-center">
              <p className="text-sm font-medium">Knowledge base masih kosong</p>
              <p className="mt-1 text-xs text-muted">
                Tambahkan dokumen agar SAVIRA punya bahan untuk menjawab.
              </p>
            </div>
          ) : (
            <ul className="divide-y divide-line">
              {dokumen.map((d) => (
                <li
                  key={d.filename}
                  data-dokumen={d.filename}
                  className="flex items-center gap-3 px-5 py-3 transition hover:bg-surface/60"
                >
                  <span aria-hidden="true" className="text-base">
                    {d.filename.toLowerCase().endsWith(".pdf") ? "📕" : "📄"}
                  </span>
                  <div className="min-w-0 flex-1">
                    <p className="truncate text-sm font-medium">{d.filename}</p>
                    <p className="text-[11px] text-muted">
                      {d.chunks} bagian · {d.characters.toLocaleString("id-ID")} karakter ·{" "}
                      {formatTanggal(d.created_at)}
                    </p>
                  </div>
                  <button
                    type="button"
                    onClick={() => bukaSunting(d.filename)}
                    className="rounded-lg border border-line px-2 py-1 text-xs text-muted transition hover:bg-line/50 hover:text-ink"
                  >
                    {bolehTulis ? "Sunting" : "Lihat"}
                  </button>
                  {bolehHapus && (
                    <button
                      type="button"
                      onClick={() => setKonfirmasiHapus(d.filename)}
                      className="rounded-lg border border-line px-2 py-1 text-xs text-red-600 transition hover:bg-red-500/10 dark:text-red-400"
                    >
                      Hapus
                    </button>
                  )}
                </li>
              ))}
            </ul>
          )}
        </div>

        {user?.role === "ADMIN" && dokumen.length > 0 && (
          <footer className="flex items-center gap-3 border-t border-line px-5 py-3">
            <p className="text-[11px] text-muted">
              Indeks ulang diperlukan setelah mengganti embedding model.
            </p>
            <button
              type="button"
              onClick={indeksUlang}
              disabled={sibuk}
              className="ml-auto rounded-lg border border-line px-2.5 py-1.5 text-xs text-muted transition hover:bg-line/50 hover:text-ink disabled:opacity-50"
            >
              Indeks ulang semua
            </button>
          </footer>
        )}
      </div>

      {sunting && (
        <div className="fixed inset-0 z-40 flex items-center justify-center bg-navy/50 p-4 backdrop-blur-sm">
          <div className="flex max-h-full w-full max-w-2xl animate-scale-in flex-col overflow-hidden rounded-2xl border border-line bg-raised shadow-2xl">
            <header className="border-b border-line px-5 py-4">
              <h3 className="text-sm font-semibold">
                {sunting.baru ? "Tulis dokumen baru" : `Sunting ${sunting.filename}`}
              </h3>
            </header>
            <div className="flex-1 overflow-y-auto px-5 py-4">
              {sunting.baru && (
                <>
                  <label className="mb-1.5 block text-xs font-medium text-muted" htmlFor="kb-nama">
                    Nama dokumen
                  </label>
                  <input
                    id="kb-nama"
                    value={sunting.filename}
                    onChange={(e) => setSunting({ ...sunting, filename: e.target.value })}
                    placeholder="mis. kebijakan-cuti.txt"
                    className="mb-4 w-full rounded-xl border border-line bg-surface px-3.5 py-2.5 text-sm outline-none focus:border-brand focus:ring-4 focus:ring-brand/15"
                  />
                </>
              )}
              <label className="mb-1.5 block text-xs font-medium text-muted" htmlFor="kb-isi">
                Isi
              </label>
              <textarea
                id="kb-isi"
                value={sunting.content}
                onChange={(e) => setSunting({ ...sunting, content: e.target.value })}
                readOnly={!bolehTulis}
                rows={14}
                placeholder="Tulis isi dokumen yang ingin dipelajari SAVIRA…"
                className="w-full resize-y rounded-xl border border-line bg-surface px-3.5 py-2.5 font-mono text-[13px] leading-relaxed outline-none focus:border-brand focus:ring-4 focus:ring-brand/15"
              />
              <p className="mt-1.5 text-[11px] text-muted">
                {sunting.content.length.toLocaleString("id-ID")} karakter. Teks dipecah otomatis
                menjadi beberapa bagian saat disimpan.
              </p>
            </div>
            <footer className="flex items-center gap-2 border-t border-line px-5 py-3">
              <button
                type="button"
                onClick={() => setSunting(null)}
                className="ml-auto rounded-lg border border-line px-3 py-1.5 text-xs text-muted transition hover:bg-line/50 hover:text-ink"
              >
                Batal
              </button>
              {bolehTulis && (
                <button
                  type="button"
                  onClick={simpan}
                  disabled={menyimpan || !sunting.content.trim() || !sunting.filename.trim()}
                  className="rounded-lg bg-brand px-3 py-1.5 text-xs font-medium text-brand-ink transition active:scale-95 disabled:opacity-45"
                >
                  {menyimpan ? "Menyimpan…" : "Simpan & indeks"}
                </button>
              )}
            </footer>
          </div>
        </div>
      )}

      {konfirmasiHapus && (
        <div className="fixed inset-0 z-40 flex items-center justify-center bg-navy/50 p-4 backdrop-blur-sm">
          <div className="w-full max-w-sm animate-scale-in rounded-2xl border border-line bg-raised p-5 shadow-2xl">
            <h3 className="text-sm font-semibold">Hapus dokumen?</h3>
            <p className="mt-1.5 text-sm text-muted">
              <b className="text-ink">{konfirmasiHapus}</b> akan dihapus dari knowledge base dan
              tidak lagi dipakai menjawab. Tindakan ini tidak dapat dibatalkan.
            </p>
            <div className="mt-4 flex justify-end gap-2">
              <button
                type="button"
                onClick={() => setKonfirmasiHapus(null)}
                className="rounded-lg border border-line px-3 py-1.5 text-xs text-muted transition hover:bg-line/50 hover:text-ink"
              >
                Batal
              </button>
              <button
                type="button"
                onClick={() => hapus(konfirmasiHapus)}
                disabled={sibuk}
                className="rounded-lg bg-red-600 px-3 py-1.5 text-xs font-medium text-white transition active:scale-95 disabled:opacity-50"
              >
                {sibuk ? "Menghapus…" : "Ya, hapus"}
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
