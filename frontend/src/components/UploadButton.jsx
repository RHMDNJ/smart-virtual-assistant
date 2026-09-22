import { useRef } from "react";

export default function UploadButton({ onPilih, disabled }) {
  const inputRef = useRef(null);

  function handleChange(e) {
    const file = e.target.files?.[0];
    if (file) {
      onPilih(file);
      e.target.value = "";
    }
  }

  return (
    <>
      <input
        ref={inputRef}
        type="file"
        accept=".pdf,.txt,.md,.png,.jpg,.jpeg,.webp"
        className="hidden"
        onChange={handleChange}
      />
      <button
        type="button"
        disabled={disabled}
        onClick={() => inputRef.current?.click()}
        title="Lampirkan dokumen (PDF, TXT, MD) atau gambar (OCR)"
        aria-label="Lampirkan dokumen atau gambar"
        className="grid h-9 w-9 shrink-0 place-items-center rounded-xl text-muted/80 transition-all hover:bg-brand/10 hover:text-brand active:scale-95 disabled:opacity-40"
      >
        <svg width="19" height="19" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.8" strokeLinecap="round" strokeLinejoin="round">
          <path d="m21.44 11.05-9.19 9.19a6 6 0 0 1-8.49-8.49l8.57-8.57A4 4 0 1 1 18 8.84l-8.59 8.57a2 2 0 0 1-2.83-2.83l7.88-7.87" />
        </svg>
      </button>
    </>
  );
}
