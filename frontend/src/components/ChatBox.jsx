import { useEffect, useRef, useState } from "react";
import MessageBubble from "./MessageBubble.jsx";
import ThinkingDots from "./ThinkingDots.jsx";
import AttachmentPreview, { isGambar } from "./AttachmentPreview.jsx";
import KnowledgeBase from "./KnowledgeBase.jsx";
import UploadButton from "./UploadButton.jsx";
import { streamChatMessage, uploadFile } from "../services/api.js";

const SESSION_ID = "session-001";

const FITUR = [
  {
    icon: "📋",
    title: "Regulasi Kepegawaian",
    desc: "Cuti tahunan, aturan jam kerja, kode etik, dan SK bupati.",
  },
  {
    icon: "🗄️",
    title: "Statistik & Database",
    desc: "Jumlah berkas tersimpan, rekapitulasi data layanan daerah.",
  },
  {
    icon: "🖼️",
    title: "Ekstraksi OCR",
    desc: "Unggah foto formulir atau pindaian berkas untuk dibaca otomatis.",
  },
  {
    icon: "⚡",
    title: "Tanya Jawab Cepat",
    desc: "Sapaan dan konsultasi informasi umum pemerintahan HSS.",
  },
];

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
  // Berkas ditahan di klien sampai user menekan Kirim, supaya caption dan
  // lampiran berangkat bersamaan seperti pada aplikasi pesan.
  const [lampiran, setLampiran] = useState(null);       // { berkas, previewUrl }
  const [fase, setFase] = useState(null);               // "mengunggah" | "menjawab"
  const [bukaKB, setBukaKB] = useState(false);
  const [isDragging, setIsDragging] = useState(false);
  const [theme, setTheme] = useState(() => {
    try {
      return localStorage.getItem("sva_theme") || "system";
    } catch {
      return "system";
    }
  });

  const akhirRef = useRef(null);
  const textareaRef = useRef(null);

  // Sinkronisasi tema manual (light / dark / system)
  useEffect(() => {
    const root = document.documentElement;
    try {
      localStorage.setItem("sva_theme", theme);
    } catch {}

    const applyTheme = () => {
      if (theme === "dark") {
        root.classList.add("dark");
        root.classList.remove("light");
      } else if (theme === "light") {
        root.classList.add("light");
        root.classList.remove("dark");
      } else {
        root.classList.remove("light");
        if (window.matchMedia("(prefers-color-scheme: dark)").matches) {
          root.classList.add("dark");
        } else {
          root.classList.remove("dark");
        }
      }
    };

    applyTheme();

    if (theme === "system") {
      const mql = window.matchMedia("(prefers-color-scheme: dark)");
      const listener = () => applyTheme();
      mql.addEventListener("change", listener);
      return () => mql.removeEventListener("change", listener);
    }
  }, [theme]);

  const toggleTheme = () => {
    setTheme((prev) => {
      if (prev === "system") return "dark";
      if (prev === "dark") return "light";
      return "system";
    });
  };

  // Gulir otomatis ke pesan terbaru, termasuk saat token streaming berdatangan.
  useEffect(() => {
    akhirRef.current?.scrollIntoView({ behavior: "smooth", block: "end" });
  }, [messages, loading]);

  // Object URL pratinjau harus dilepas agar tidak membocorkan memori.
  useEffect(() => {
    return () => {
      if (lampiran?.previewUrl) URL.revokeObjectURL(lampiran.previewUrl);
    };
  }, [lampiran]);

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

  function handleNewChat() {
    setMessages([]);
    setInput("");
    setError(null);
    setPendingImage(null);
  }

  function pilihBerkas(berkas) {
    if (lampiran?.previewUrl) URL.revokeObjectURL(lampiran.previewUrl);
    setError(null);
    setLampiran({
      berkas,
      previewUrl: isGambar(berkas.name) ? URL.createObjectURL(berkas) : null,
    });
  }

  function batalkanLampiran() {
    if (lampiran?.previewUrl) URL.revokeObjectURL(lampiran.previewUrl);
    setLampiran(null);
  }

  async function handleSend(teksLangsung) {
    const text = (teksLangsung ?? input).trim();
    const berkas = lampiran?.berkas ?? null;
    if ((!text && !berkas) || loading) return;

    // Gambar tanpa caption tetap perlu pertanyaan agar agent tahu harus apa.
    const pesanTampil = text || (berkas ? `Lampiran: ${berkas.name}` : "");
    const pesanDikirim =
      text || (berkas && isGambar(berkas.name) ? "Tolong baca dan jelaskan isi gambar ini." : "");

    setMessages((prev) => [
      ...prev,
      {
        role: "user",
        message: pesanTampil,
        attachment: berkas
          ? { nama: berkas.name, previewUrl: lampiran.previewUrl, gambar: isGambar(berkas.name) }
          : undefined,
      },
    ]);
    setInput("");
    setLampiran(null);
    setLoading(true);
    setError(null);

    // --- unggah lebih dulu bila ada lampiran ---
    let imageId = null;
    if (berkas) {
      setFase("mengunggah");
      try {
        const hasil = await uploadFile(berkas);
        imageId = hasil.image_id || null;
        if (!imageId) {
          // Dokumen: beri tahu hasil indexing sebelum menjawab.
          setMessages((prev) => [
            ...prev,
            { role: "assistant", message: `**${hasil.filename}** — ${hasil.detail || hasil.status}` },
          ]);
        }
      } catch (err) {
        setMessages((prev) => prev.slice(0, -1));
        setError(
          err?.response?.status === 403
            ? "Role Anda tidak diizinkan mengunggah berkas."
            : err?.response?.data?.detail || "Gagal mengunggah berkas."
        );
        setLoading(false);
        setFase(null);
        return;
      }
    }

    if (!pesanDikirim) {
      // Dokumen diunggah tanpa caption: cukup laporkan hasil indexing.
      setLoading(false);
      setFase(null);
      return;
    }

    setFase("menjawab");
    setMessages((prev) => [...prev, { role: "assistant", message: "", streaming: true }]);

    try {
      let terkumpul = "";
      await streamChatMessage(SESSION_ID, pesanDikirim, imageId, {
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

  function handleKeyDown(e) {
    if (e.key === "Enter" && !e.shiftKey) {
      e.preventDefault();
      handleSend();
    }
  }

  // Drag and Drop handlers
  function handleDragOver(e) {
    e.preventDefault();
    if (user?.role !== "READ_ONLY") {
      setIsDragging(true);
    }
  }

  function handleDragLeave(e) {
    e.preventDefault();
    setIsDragging(false);
  }

  function handleDrop(e) {
    e.preventDefault();
    setIsDragging(false);
    if (user?.role === "READ_ONLY") return;
    const files = e.dataTransfer?.files;
    if (files && files.length > 0) {
      pilihBerkas(files[0]);
    }
  }

  const menunggu = loading && messages.at(-1)?.role === "assistant" && !messages.at(-1)?.message;

  return (
    <div
      onDragOver={handleDragOver}
      onDragLeave={handleDragLeave}
      onDrop={handleDrop}
      className="relative flex h-full flex-col bg-surface transition-colors duration-200"
    >
      {/* Drag and Drop Overlay */}
      {isDragging && (
        <div className="pointer-events-none absolute inset-0 z-50 flex items-center justify-center bg-surface/90 p-6 backdrop-blur-md">
          <div className="flex w-full max-w-md flex-col items-center justify-center rounded-3xl border-2 border-dashed border-brand bg-brand/5 p-8 text-center animate-scale-in">
            <div className="mb-3 grid h-14 w-14 place-items-center rounded-2xl bg-brand/10 text-brand">
              <svg width="28" height="28" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
                <path d="M21 15v4a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2v-4" />
                <polyline points="17 8 12 3 7 8" />
                <line x1="12" x2="12" y1="3" y2="15" />
              </svg>
            </div>
            <p className="text-base font-semibold text-ink">Lepaskan berkas untuk mengunggah</p>
            <p className="mt-1 text-xs text-muted">Mendukung dokumen (PDF, TXT, MD) & pindaian berkas (PNG, JPG, WEBP)</p>
          </div>
        </div>
      )}

      {/* Header */}
      <header className="sticky top-0 z-20 border-b border-line/80 bg-surface/85 backdrop-blur-md">
        <div className="mx-auto flex w-full max-w-4xl items-center gap-3 px-4 py-2.5">
          <div className="relative shrink-0">
            <img
              src="/brand/maskot-64.png"
              alt="SAVIRA"
              aria-hidden="true"
              width={36}
              height={36}
              className="h-9 w-9 select-none rounded-xl border border-line/80 bg-raised object-contain p-0.5 shadow-sm"
            />
          </div>

          <div className="min-w-0">
            <div className="flex items-center gap-2">
              <h1 className="truncate text-sm font-extrabold tracking-tight">
                <span className="text-navy dark:text-ink">SA</span>
                <span className="text-brand">VIRA</span>
              </h1>
              <span className="hidden text-xs text-muted/70 sm:inline">
                · Smart Virtual Assistant HSS
              </span>
            </div>
            <p className="flex items-center gap-1.5 text-[11px] text-muted">
              <span className="relative flex h-2 w-2">
                <span className="absolute inline-flex h-full w-full animate-pulse-ring rounded-full bg-emerald-500" />
                <span className="relative inline-flex h-2 w-2 rounded-full bg-emerald-500" />
              </span>
              <span className="font-medium">Sistem Lokal</span> · <span className="opacity-80">llama3.1</span>
            </p>
          </div>

          <div className="ml-auto flex items-center gap-2">
            {/* New Chat Button */}
            {messages.length > 0 && (
              <button
                type="button"
                onClick={handleNewChat}
                title="Mulai percakapan baru"
                className="inline-flex items-center gap-1.5 rounded-xl border border-line/80 bg-raised px-2.5 py-1.5 text-xs font-medium text-muted transition hover:border-brand/40 hover:text-ink active:scale-95 shadow-sm"
              >
                <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
                  <path d="M12 5v14M5 12h14" />
                </svg>
                <span className="hidden sm:inline">Obrolan Baru</span>
              </button>
            )}

            {/* Theme Toggle Button */}
            <button
              type="button"
              onClick={toggleTheme}
              title={`Tema: ${theme === "system" ? "Sistem" : theme === "dark" ? "Gelap" : "Terang"} (Klik untuk beralih)`}
              className="grid h-8 w-8 place-items-center rounded-xl border border-line/80 bg-raised text-muted transition hover:border-brand/40 hover:text-ink active:scale-95 shadow-sm"
            >
              {theme === "dark" ? (
                <svg width="15" height="15" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" className="text-amber-400">
                  <circle cx="12" cy="12" r="4" />
                  <path d="M12 2v2M12 20v2M4.93 4.93l1.41 1.41M17.66 17.66l1.41 1.41M2 12h2M20 12h2M6.34 17.66l-1.41 1.41M19.07 4.93l-1.41 1.41" />
                </svg>
              ) : theme === "light" ? (
                <svg width="15" height="15" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" className="text-blue-500">
                  <path d="M12 3a6 6 0 0 0 9 9 9 9 0 1 1-9-9Z" />
                </svg>
              ) : (
                <svg width="15" height="15" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
                  <rect width="20" height="14" x="2" y="3" rx="2" />
                  <line x1="8" x2="16" y1="21" y2="21" />
                  <line x1="12" x2="12" y1="17" y2="21" />
                </svg>
              )}
            </button>

            {/* User Role Badge */}
            <div className="hidden sm:flex items-center gap-1.5 pl-1">
              <span className="text-xs font-semibold text-ink/80">{user?.username}</span>
              <span className="rounded-full border border-line/80 bg-raised px-2 py-0.5 text-[10px] font-bold uppercase tracking-wider text-muted">
                {user?.role}
              </span>
            </div>

            {/* Logout Button */}
            <button
              type="button"
              onClick={() => setBukaKB(true)}
              data-buka-kb
              title="Kelola dokumen yang dipelajari SAVIRA"
              className="rounded-lg border border-line px-2.5 py-1.5 text-xs text-muted transition hover:bg-line/50 hover:text-ink active:scale-95"
            >
              Knowledge base
            </button>
            <button
              type="button"
              onClick={onLogout}
              className="rounded-xl border border-line/80 bg-raised px-3 py-1.5 text-xs font-medium text-muted transition hover:border-red-500/30 hover:bg-red-500/10 hover:text-red-600 dark:hover:text-red-400 active:scale-95 shadow-sm"
            >
              Keluar
            </button>
          </div>
        </div>
      </header>

      {/* Main Chat Container */}
      <div className="flex-1 overflow-y-auto">
        <div className="mx-auto flex w-full max-w-4xl flex-col gap-6 px-4 py-6">
          {messages.length === 0 && (
            <div className="animate-fade-up py-6 text-center">
              {/* Animated Mascot */}
              <div className="relative mx-auto mb-4 inline-flex items-center justify-center">
                <div className="absolute -inset-4 rounded-full bg-gradient-to-tr from-brand/20 via-cyan/15 to-transparent blur-xl" />
                <img
                  src="/brand/maskot-256.png"
                  alt="SAVIRA"
                  aria-hidden="true"
                  width={112}
                  height={112}
                  className="relative h-28 w-28 animate-scale-in select-none object-contain drop-shadow-md transition duration-300 hover:scale-105"
                />
              </div>

              <h2 className="text-xl font-bold tracking-tight text-ink">
                Halo, {user?.username || "Rekan"}! 👋
              </h2>
              <p className="mx-auto mt-1 max-w-md text-sm text-muted">
                {user?.role === "READ_ONLY"
                  ? "Asisten cerdas Kabupaten Hulu Sungai Selatan siap membantu Anda mencari informasi regulasi dan data daerah."
                  : "Asisten cerdas Kabupaten Hulu Sungai Selatan siap menjawab regulasi, membaca pindaian dokumen/OCR, dan menganalisis data."}
              </p>

              {/* Capability feature cards */}
              <div className="mt-8 grid grid-cols-1 gap-3 sm:grid-cols-2 text-left max-w-2xl mx-auto">
                {FITUR.map((f, idx) => (
                  <div
                    key={idx}
                    className="flex items-start gap-3 rounded-2xl border border-line/70 bg-raised/70 p-3.5 shadow-sm backdrop-blur-sm transition hover:border-brand/30 hover:shadow"
                  >
                    <span className="text-2xl select-none" aria-hidden="true">{f.icon}</span>
                    <div>
                      <h3 className="text-xs font-bold text-ink">{f.title}</h3>
                      <p className="mt-0.5 text-[11px] text-muted leading-relaxed">{f.desc}</p>
                    </div>
                  </div>
                ))}
              </div>

              {/* Prompt Suggestions */}
              <div className="mt-8">
                <p className="text-xs font-semibold text-muted/80 mb-3 uppercase tracking-wider">
                  Coba tanyakan contoh ini:
                </p>
                <div className="flex flex-wrap justify-center gap-2 max-w-2xl mx-auto">
                  {SARAN.map((s) => (
                    <button
                      key={s}
                      type="button"
                      onClick={() => handleSend(s)}
                      className="rounded-full border border-line bg-raised px-3.5 py-1.5 text-xs font-medium text-muted transition hover:border-brand/50 hover:bg-brand/5 hover:text-brand shadow-sm active:scale-95"
                    >
                      {s}
                    </button>
                  ))}
                </div>
              </div>
            </div>
          )}

          {/* Messages Stream */}
          {messages.map((m, i) =>
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
              className="animate-slide-up self-center rounded-xl border border-red-500/20 bg-red-500/10 px-4 py-2.5 text-xs font-medium text-red-600 dark:text-red-400 shadow-sm flex items-center gap-2"
            >
              <svg width="15" height="15" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
                <circle cx="12" cy="12" r="10" />
                <line x1="12" y1="8" x2="12" y2="12" />
                <line x1="12" y1="16" x2="12.01" y2="16" />
              </svg>
              <span>{error}</span>
            </p>
          )}

          <div ref={akhirRef} />
        </div>
      </div>

      {/* Input Area */}
      <div className="border-t border-line/80 bg-surface/85 backdrop-blur-md">
        <div className="mx-auto w-full max-w-4xl px-4 py-3">
          {lampiran && (
            <AttachmentPreview
              berkas={lampiran.berkas}
              previewUrl={lampiran.previewUrl}
              onBatal={batalkanLampiran}
              disabled={loading}
            />
          )}

          <div className="flex items-end gap-2 rounded-2xl border border-line/80 bg-raised p-2 shadow-sm transition focus-within:border-brand/60 focus-within:ring-4 focus-within:ring-brand/10">
            {user?.role !== "READ_ONLY" && (
              <UploadButton onPilih={pilihBerkas} disabled={loading} />
            )}
            <textarea
              ref={textareaRef}
              rows={1}
              value={input}
              onChange={(e) => setInput(e.target.value)}
              onKeyDown={handleKeyDown}
              placeholder={
                lampiran
                  ? "Tulis keterangan atau pertanyaan tentang lampiran ini…"
                  : "Tulis pertanyaan tentang kepegawaian, regulasi, atau data daerah…"
              }
              className="max-h-40 flex-1 resize-none bg-transparent px-2 py-1.5 text-[15px] outline-none placeholder:text-muted/60 leading-normal"
            />
            <button
              onClick={() => handleSend()}
              disabled={loading || (!input.trim() && !lampiran)}
              aria-label="Kirim"
              className={`grid h-9 w-9 shrink-0 place-items-center rounded-xl transition-all duration-150 active:scale-95 ${
                input.trim() || lampiran
                  ? "bg-brand text-brand-ink shadow-md shadow-brand/25"
                  : "bg-muted/15 text-muted/50 cursor-not-allowed"
              } disabled:opacity-40 disabled:shadow-none`}
            >
              {loading ? (
                <span className="h-4 w-4 animate-spin rounded-full border-2 border-current border-t-transparent" />
              ) : (
                <svg width="17" height="17" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.2" strokeLinecap="round" strokeLinejoin="round">
                  <path d="M12 19V5M5 12l7-7 7 7" />
                </svg>
              )}
            </button>
          </div>
          <div className="mt-2 flex items-center justify-between px-1 text-[11px] text-muted/70">
            <span>Tekan <kbd className="rounded border border-line bg-raised px-1 py-0.5 font-mono text-[10px]">Enter ↵</kbd> untuk kirim, <kbd className="rounded border border-line bg-raised px-1 py-0.5 font-mono text-[10px]">Shift+Enter</kbd> baris baru</span>
            <span className="hidden sm:inline">Dapat menyeret file langsung ke jendela chat</span>
          </div>
        </div>
      </div>

      {bukaKB && <KnowledgeBase user={user} onClose={() => setBukaKB(false)} />}
    </div>
  );
}
