import { useState } from "react";
import MessageBubble from "./MessageBubble.jsx";
import UploadButton from "./UploadButton.jsx";
import { streamChatMessage, uploadFile } from "../services/api.js";

const SESSION_ID = "session-001";

export default function ChatBox({ user, onLogout }) {
  const [messages, setMessages] = useState([]);
  const [input, setInput] = useState("");
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState(null);
  // Gambar hasil upload yang menunggu dikirim bersama pertanyaan berikutnya.
  const [pendingImage, setPendingImage] = useState(null);

  async function handleSend() {
    const text = input.trim();
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

    // Bubble assistant dibuat kosong lebih dulu, lalu diisi saat token berdatangan.
    setMessages((prev) => [...prev, { role: "assistant", message: "", streaming: true }]);

    const perbaruiTerakhir = (ubah) =>
      setMessages((prev) => {
        const salinan = [...prev];
        salinan[salinan.length - 1] = { ...salinan[salinan.length - 1], ...ubah };
        return salinan;
      });

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
      // Bubble kosong tidak berguna bagi user — buang dan tampilkan error.
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

      if (res.image_id) {
        // Gambar: simpan id-nya, OCR dijalankan saat user mengirim pertanyaan.
        setPendingImage({ imageId: res.image_id, filename: res.filename });
      }

      setMessages((prev) => [
        ...prev,
        {
          role: "assistant",
          message: `📎 **${res.filename}** — ${res.status}\n\n${res.detail || ""}`,
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

  return (
    <div className="flex h-screen flex-col bg-white">
      <header className="flex items-center gap-3 border-b px-4 py-3">
        <span className="text-lg font-semibold">Smart Virtual Assistant</span>
        <span className="ml-auto text-xs text-gray-500">
          {user?.username} · {user?.role}
        </span>
        <button
          type="button"
          onClick={onLogout}
          className="rounded-lg border px-2 py-1 text-xs text-gray-600 hover:bg-gray-50"
        >
          Keluar
        </button>
      </header>

      <div className="flex-1 overflow-y-auto px-4 py-4">
        {messages.length === 0 && (
          <p className="text-sm text-gray-400">
            {user?.role === "READ_ONLY"
              ? "Tulis pertanyaan untuk mulai."
              : "Tulis pertanyaan, atau unggah dokumen/gambar untuk mulai."}
          </p>
        )}
        {messages.map((m, i) => (
          <MessageBubble
            key={i}
            role={m.role}
            message={m.message}
            sources={m.sources}
            toolUsed={m.toolUsed}
            attachment={m.attachment}
            streaming={m.streaming}
          />
        ))}
        {loading && !messages.at(-1)?.message && (
          <p className="text-sm text-gray-400">Assistant sedang berpikir…</p>
        )}
        {error && <p className="text-sm text-red-500">{error}</p>}
      </div>

      {pendingImage && (
        <div className="flex items-center gap-2 border-t bg-amber-50 px-4 py-2 text-xs text-amber-800">
          <span>🖼️ {pendingImage.filename} akan dibaca (OCR) bersama pertanyaan berikutnya.</span>
          <button
            type="button"
            onClick={() => setPendingImage(null)}
            className="ml-auto rounded px-2 py-0.5 hover:bg-amber-100"
          >
            Batal
          </button>
        </div>
      )}

      <div className="flex items-center gap-2 border-t px-3 py-2">
        {user?.role !== "READ_ONLY" && (
          <UploadButton onUpload={handleUpload} disabled={loading} />
        )}
        <textarea
          rows={1}
          value={input}
          onChange={(e) => setInput(e.target.value)}
          onKeyDown={handleKeyDown}
          placeholder={
            pendingImage ? "Tanyakan sesuatu tentang gambar ini…" : "Tulis pertanyaan…"
          }
          className="flex-1 resize-none rounded-full border px-4 py-2 text-sm outline-none"
        />
        <button
          onClick={handleSend}
          disabled={loading}
          className="rounded-full bg-blue-600 px-4 py-2 text-sm font-medium text-white disabled:opacity-50"
        >
          Send
        </button>
      </div>
    </div>
  );
}
