import { useState } from "react";
import ReactMarkdown from "react-markdown";

const TOOL_META = {
  rag_search: {
    label: "Dokumen",
    icon: "📚",
    badgeClass: "bg-blue-500/10 text-blue-600 dark:text-blue-400 border-blue-500/20",
  },
  image_ocr: {
    label: "OCR gambar",
    icon: "🖼️",
    badgeClass: "bg-amber-500/10 text-amber-600 dark:text-amber-400 border-amber-500/20",
  },
  sql_query: {
    label: "Database",
    icon: "🗄️",
    badgeClass: "bg-purple-500/10 text-purple-600 dark:text-purple-400 border-purple-500/20",
  },
  llm_direct: {
    label: "Jawaban langsung",
    icon: "💬",
    badgeClass: "bg-emerald-500/10 text-emerald-600 dark:text-emerald-400 border-emerald-500/20",
  },
};

function Avatar({ isUser }) {
  if (isUser) {
    return (
      <div
        className="grid h-8 w-8 shrink-0 select-none place-items-center rounded-xl bg-gradient-to-tr from-brand to-cyan text-xs font-bold text-white shadow-sm"
        aria-hidden="true"
      >
        <svg width="15" height="15" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.2" strokeLinecap="round" strokeLinejoin="round">
          <path d="M19 21v-2a4 4 0 0 0-4-4H9a4 4 0 0 0-4 4v2" />
          <circle cx="12" cy="7" r="4" />
        </svg>
      </div>
    );
  }
  return (
    <div className="relative shrink-0">
      <img
        src="/brand/maskot-64.png"
        alt=""
        aria-hidden="true"
        width={34}
        height={34}
        className="h-8 w-8 select-none rounded-xl border border-line/80 bg-raised object-contain p-0.5 shadow-sm transition hover:scale-105"
      />
    </div>
  );
}

export default function MessageBubble({
  role,
  message,
  sources = [],
  toolUsed,
  attachment,
  streaming = false,
}) {
  const [copied, setCopied] = useState(false);
  const isUser = role === "user";
  const tool = TOOL_META[toolUsed];

  function handleCopy() {
    if (!message) return;
    navigator.clipboard?.writeText(message);
    setCopied(true);
    setTimeout(() => setCopied(false), 2000);
  }

  return (
    <div
      data-msg={role}
      data-streaming={streaming ? "1" : undefined}
      className={`group flex animate-fade-up gap-3 ${isUser ? "flex-row-reverse" : ""}`}
    >
      <Avatar isUser={isUser} />

      <div className={`flex min-w-0 max-w-[min(44rem,82%)] flex-col gap-1.5 ${isUser ? "items-end" : "items-start"}`}>
        {attachment && (
          <span className="inline-flex items-center gap-1.5 rounded-xl border border-line bg-raised px-3 py-1 text-xs text-muted shadow-sm">
            <span aria-hidden="true">🖼️</span>
            <span className="font-medium">{attachment}</span>
          </span>
        )}

        <div
          className={`relative rounded-2xl px-4 py-3 text-[15px] shadow-sm transition-all ${
            isUser
              ? "rounded-tr-xs bg-brand text-brand-ink shadow-brand/15"
              : "rounded-tl-xs border border-line/80 bg-raised text-ink"
          }`}
        >
          <div className="markdown" data-bubble>
            <ReactMarkdown>{message}</ReactMarkdown>
          </div>
          {streaming && (
            <span
              className="ml-1 inline-block h-[1.1em] w-[2px] translate-y-[2px] animate-caret-blink bg-brand align-baseline"
              aria-hidden="true"
            />
          )}
        </div>

        {/* Action bar for assistant messages */}
        {!isUser && !streaming && message && (
          <div className="flex items-center gap-2 px-1 text-xs text-muted">
            <button
              type="button"
              onClick={handleCopy}
              title="Salin jawaban ke clipboard"
              className="inline-flex items-center gap-1 rounded-md px-1.5 py-0.5 text-[11px] text-muted transition hover:bg-surface hover:text-ink active:scale-95"
            >
              {copied ? (
                <>
                  <svg width="13" height="13" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.5" className="text-emerald-500">
                    <polyline points="20 6 9 17 4 12" />
                  </svg>
                  <span className="text-emerald-600 dark:text-emerald-400 font-medium">Tersalin!</span>
                </>
              ) : (
                <>
                  <svg width="13" height="13" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
                    <rect width="14" height="14" x="8" y="8" rx="2" ry="2" />
                    <path d="M4 16c-1.1 0-2-.9-2-2V4c0-1.1.9-2 2-2h10c1.1 0 2 .9 2 2" />
                  </svg>
                  <span>Salin</span>
                </>
              )}
            </button>
          </div>
        )}

        {/* Metadata: Tool and Sources */}
        {!isUser && !streaming && (tool || sources.length > 0) && (
          <div className="flex flex-wrap items-center gap-1.5 px-0.5 mt-0.5" data-meta>
            {tool && (
              <span
                className={`inline-flex items-center gap-1.5 rounded-full border px-2.5 py-0.5 text-[11px] font-medium shadow-sm ${
                  tool.badgeClass || "border-line bg-raised text-muted"
                }`}
              >
                <span aria-hidden="true">{tool.icon}</span>
                {tool.label}
              </span>
            )}
            {sources.length > 0 && (
              <span className="text-[11px] font-medium text-muted/75 pl-1">Sumber:</span>
            )}
            {sources.map((s, i) => (
              <span
                key={i}
                title={s.filename}
                className="inline-flex max-w-[15rem] items-center gap-1.5 truncate rounded-full border border-line/80 bg-raised px-2.5 py-0.5 text-[11px] text-muted transition hover:border-brand/40"
              >
                <span aria-hidden="true" className="text-xs">📄</span>
                <span className="truncate">{s.filename}</span>
              </span>
            ))}
          </div>
        )}
      </div>
    </div>
  );
}
