import { useEffect, useRef, useState } from "react";
import MessageBubble from "./MessageBubble.jsx";
import ThinkingDots from "./ThinkingDots.jsx";
import UploadButton from "./UploadButton.jsx";
import { streamChatMessage, uploadFile } from "../services/api.js";

const SESSION_ID = "session-001";

const SARAN = [
  "Berapa hari cuti tahunan pegawai?",
  "Jam berapa mulai kerja?",
  "Ada berapa dokumen di knowledge base?",
];

export default function ChatBox({ user, onLogout }) {
  const [messages, setMessages] = useState([]);
  const [input, setInput] = useState("");
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState(null);
  const [pendingImage, setPendingImage] = useState(null);

  const akhirRef = useRef(null);
  const textareaRef = useRef(null);

  // Gulir otomatis ke pesan terbaru, termasuk saat token streaming berdatangan.
  useEffect(() => {
    akhirRef.current?.scrollIntoView({ behavior: "smooth", block: "end" });
  }, [messages, loading]);

  // Textarea tumbuh mengikuti isi, dibatasi agar tidak menelan layar.
  useEffect(() => {
    const el = textareaRef.current;
    if (!el) return;
    el.style.height = "auto";
    el.style.height = `${Math.min(el.scrollHeight, 160)}px`;
  }, [input]);

  const perbaruiTerakhir = (ubah) =>
    setMessages((prev) => {
      const salinan = [...prev];
      salinan[salinan.length - 1] = { ...salinan[salinan.length - 1], ...ubah };
      return salinan;
    });

  async function handleSend(teksLangsung) {
    const text = (teksLangsung ?? input).trim();
    if (!text || loading) return;

    const attachment = pendingImage;
    setMessages((prev) => [
      ...prev,
      { role: "user", message: text, attachment: attachment?.filename },
    ]);
    setInput("");
    setPendingImage(null);
    setLoading(true);
    setError(null);

    setMessages((prev) => [...prev, { role: "assistant", message: "", streaming: true }]);

    try {
      let terkumpul = "";
      await streamChatMessage(SESSION_ID, text, attachment?.imageId, {
        onTool: (name) => perbaruiTerakhir({ toolUsed: name }),
        onToken: (potongan) => {
          terkumpul += potongan;
          perbaruiTerakhir({ message: terkumpul });
        },
        onDone: (ev) =>
          perbaruiTerakhir({
            message: ev.answer || terkumpul,
            sources: ev.sources,
            toolUsed: ev.tool_used,
            streaming: false,
          }),
        onError: (detail) => {
          perbaruiTerakhir({ streaming: false });
          setError(detail || "Terjadi kesalahan saat memproses jawaban.");
        },
      });
    } catch (err) {
      setMessages((prev) => prev.slice(0, -1));
      setError(err?.message || "Gagal menghubungi server. Pastikan backend berjalan.");
    } finally {
      setLoading(false);
    }
  }

  async function handleUpload(file) {
    setLoading(true);
    setError(null);
    try {
      const res = await uploadFile(file);
      if (res.image_id) setPendingImage({ imageId: res.image_id, filename: res.filename });
      setMessages((prev) => [
        ...prev,
        {
          role: "assistant",
          message: `**${res.filename}** — ${res.status}\n\n${res.detail || ""}`,
          toolUsed: null,
        },
      ]);
    } catch (err) {
      setError(
        err?.response?.status === 403
          ? "Role Anda tidak diizinkan mengunggah file."
          : err?.response?.data?.detail || "Gagal mengunggah file."
      );
    } finally {
      setLoading(false);
    }
  }

  function handleKeyDown(e) {
    if (e.key === "Enter" && !e.shiftKey) {
      e.preventDefault();
      handleSend();
    }
  }

  const menunggu = loading && messages.at(-1)?.role === "assistant" && !messages.at(-1)?.message;

  return (
    <div className="flex h-full flex-col bg-surface">
      <header className="sticky top-0 z-10 border-b border-line bg-surface/85 backdrop-blur">
        <div className="mx-auto flex w-full max-w-3xl items-center gap-3 px-4 py-3">
          <img
            src="/brand/maskot-64.png"
            alt=""
            aria-hidden="true"
            width={36}
            height={36}
            className="h-9 w-9 shrink-0 select-none object-contain"
          />
          <div className="min-w-0">
            <h1 className="truncate text-sm font-bold tracking-tight">
              <span className="text-navy dark:text-ink">SA</span>
              <span className="text-brand">VIRA</span>
              <span className="ml-1.5 font-normal text-muted">
                · Smart Virtual Assistant
              </span>
            </h1>
            <p className="flex items-center gap-1.5 text-[11px] text-muted">
              <span className="relative flex h-1.5 w-1.5">
                <span className="absolute inline-flex h-full w-full animate-pulse-ring rounded-full bg-emerald-500" />
                <span className="relative inline-flex h-1.5 w-1.5 rounded-full bg-emerald-500" />
              </span>
              Lokal · llama3.1
            </p>
          </div>

          <div className="ml-auto flex items-center gap-2">
            <span className="hidden items-center gap-1.5 text-xs text-muted sm:flex">
              {user?.username}
              <span className="rounded-full border border-line px-1.5 py-0.5 text-[10px] font-medium uppercase tracking-wide">
                {user?.role}
              </span>
            </span>
            <button
              type="button"
              onClick={onLogout}
              className="rounded-lg border border-line px-2.5 py-1.5 text-xs text-muted transition hover:bg-line/50 hover:text-ink active:scale-95"
            >
              Keluar
            </button>
          </div>
        </div>
      </header>

      <div className="flex-1 overflow-y-auto">
        <div className="mx-auto flex w-full max-w-3xl flex-col gap-5 px-4 py-6">
          {messages.length === 0 && (
            <div className="animate-fade-up py-10 text-center">
              <img
                src="/brand/maskot-256.png"
                alt=""
                aria-hidden="true"
                width={112}
                height={112}
                className="mx-auto mb-4 h-28 w-28 animate-scale-in select-none object-contain drop-shadow-sm"
              />
              <h2 className="text-base font-medium">Ada yang bisa dibantu?</h2>
              <p className="mx-auto mt-1 max-w-sm text-sm text-muted">
                {user?.role === "READ_ONLY"
                  ? "Tulis pertanyaan untuk mulai."
                  : "Tulis pertanyaan, atau unggah dokumen dan gambar untuk dibaca."}
              </p>
              <div className="mt-5 flex flex-wrap justify-center gap-2">
                {SARAN.map((s) => (
                  <button
                    key={s}
                    type="button"
                    onClick={() => handleSend(s)}
                    className="rounded-full border border-line bg-raised px-3 py-1.5 text-xs text-muted transition hover:border-brand/40 hover:text-ink active:scale-95"
                  >
                    {s}
                  </button>
                ))}
              </div>
            </div>
          )}

          {messages.map((m, i) =>
            // Bubble assistant yang masih kosong tidak dirender; indikator
            // titik-titik di bawah yang mewakilinya sampai token pertama tiba.
            m.role === "assistant" && m.streaming && !m.message ? null : (
            <MessageBubble
              key={i}
              role={m.role}
              message={m.message}
              sources={m.sources}
              toolUsed={m.toolUsed}
              attachment={m.attachment}
              streaming={m.streaming}
            />
            )
          )}

          {menunggu && <ThinkingDots />}

          {error && (
            <p
              role="alert"
              data-error
              className="animate-slide-up self-center rounded-lg bg-red-500/10 px-3 py-2 text-sm text-red-600 dark:text-red-400"
            >
              {error}
            </p>
          )}

          <div ref={akhirRef} />
        </div>
      </div>

      <div className="border-t border-line bg-surface/85 backdrop-blur">
        <div className="mx-auto w-full max-w-3xl px-4 py-3">
          {pendingImage && (
            <div className="mb-2 flex animate-slide-up items-center gap-2 rounded-xl border border-amber-400/40 bg-amber-400/10 px-3 py-2 text-xs text-amber-700 dark:text-amber-300">
              <span aria-hidden="true">🖼️</span>
              <span className="truncate">
                <b>{pendingImage.filename}</b> akan dibaca (OCR) bersama pertanyaan berikutnya.
              </span>
              <button
                type="button"
                onClick={() => setPendingImage(null)}
                className="ml-auto shrink-0 rounded px-1.5 py-0.5 transition hover:bg-amber-400/20"
              >
                Batal
              </button>
            </div>
          )}

          <div className="flex items-end gap-2 rounded-2xl border border-line bg-raised p-1.5 shadow-sm transition focus-within:border-brand/50 focus-within:ring-4 focus-within:ring-brand/10">
            {user?.role !== "READ_ONLY" && (
              <UploadButton onUpload={handleUpload} disabled={loading} />
            )}
            <textarea
              ref={textareaRef}
              rows={1}
              value={input}
              onChange={(e) => setInput(e.target.value)}
              onKeyDown={handleKeyDown}
              placeholder={
                pendingImage ? "Tanyakan sesuatu tentang gambar ini…" : "Tulis pertanyaan…"
              }
              className="max-h-40 flex-1 resize-none bg-transparent px-2 py-2 text-[15px] outline-none placeholder:text-muted/70"
            />
            <button
              onClick={() => handleSend()}
              disabled={loading || !input.trim()}
              aria-label="Kirim"
              className="grid h-9 w-9 shrink-0 place-items-center rounded-xl bg-brand text-brand-ink shadow transition active:scale-95 disabled:opacity-35 disabled:shadow-none"
            >
              {loading ? (
                <span className="h-3.5 w-3.5 animate-spin rounded-full border-2 border-current border-t-transparent" />
              ) : (
                <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
                  <path d="M12 19V5M5 12l7-7 7 7" />
                </svg>
              )}
            </button>
          </div>
          <p className="mt-1.5 text-center text-[11px] text-muted/80">
            Enter untuk kirim · Shift+Enter baris baru
          </p>
        </div>
      </div>
    </div>
  );
}
