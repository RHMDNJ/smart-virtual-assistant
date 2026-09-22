const EKSTENSI_GAMBAR = /\.(png|jpe?g|webp)$/i;

export function isGambar(nama) {
  return EKSTENSI_GAMBAR.test(nama || "");
}

function ukuranTerbaca(byte) {
  if (byte < 1024) return `${byte} B`;
  if (byte < 1024 * 1024) return `${Math.round(byte / 1024)} KB`;
  return `${(byte / (1024 * 1024)).toFixed(1)} MB`;
}

/** Kartu lampiran di atas kolom tulis, sebelum berkas dikirim. */
export default function AttachmentPreview({ berkas, previewUrl, onBatal, disabled }) {
  const gambar = isGambar(berkas.name);

  return (
    <div className="mb-2 flex animate-slide-up items-center gap-3 rounded-xl border border-line bg-surface px-3 py-2">
      {gambar && previewUrl ? (
        <img
          src={previewUrl}
          alt=""
          className="h-11 w-11 shrink-0 rounded-lg border border-line object-cover"
        />
      ) : (
        <div className="grid h-11 w-11 shrink-0 place-items-center rounded-lg border border-line bg-raised text-lg">
          {berkas.name.toLowerCase().endsWith(".pdf") ? "📕" : "📄"}
        </div>
      )}

      <div className="min-w-0 flex-1">
        <p className="truncate text-sm font-medium">{berkas.name}</p>
        <p className="text-[11px] text-muted">
          {ukuranTerbaca(berkas.size)} ·{" "}
          {gambar
            ? "akan dibaca dengan OCR"
            : "akan ditambahkan ke knowledge base"}
        </p>
      </div>

      <button
        type="button"
        onClick={onBatal}
        disabled={disabled}
        aria-label="Batalkan lampiran"
        className="grid h-7 w-7 shrink-0 place-items-center rounded-lg text-muted transition hover:bg-line/60 hover:text-ink disabled:opacity-40"
      >
        ✕
      </button>
    </div>
  );
}
