import { useRef } from "react";

export default function UploadButton({ onUpload, disabled }) {
  const inputRef = useRef(null);

  function handleChange(e) {
    const file = e.target.files?.[0];
    if (file) {
      onUpload(file);
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
        className="rounded-full px-3 py-2 text-lg hover:bg-gray-100 disabled:opacity-50"
        title="Upload dokumen atau gambar"
      >
        📎
      </button>
    </>
  );
}
