import ReactMarkdown from "react-markdown";

const TOOL_META = {
  rag_search: { label: "Dokumen", icon: "📚" },
  image_ocr: { label: "OCR gambar", icon: "🖼️" },
  sql_query: { label: "Database", icon: "🗄️" },
  llm_direct: { label: "Jawaban langsung", icon: "💬" },
};

function Avatar({ isUser }) {
  if (isUser) {
    return (
      <div
        className="grid h-8 w-8 shrink-0 select-none place-items-center rounded-full bg-brand text-[13px] font-semibold text-brand-ink"
        aria-hidden="true"
      >
        A
      </div>
    );
  }
  return (
    <img
      src="/brand/maskot-64.png"
      alt=""
      aria-hidden="true"
      width={32}
      height={32}
      className="h-8 w-8 shrink-0 select-none rounded-full border border-line bg-raised object-contain p-0.5"
    />
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
  const isUser = role === "user";
  const tool = TOOL_META[toolUsed];

  return (
    <div
      data-msg={role}
      data-streaming={streaming ? "1" : undefined}
      className={`flex animate-fade-up gap-3 ${isUser ? "flex-row-reverse" : ""}`}
    >
      <Avatar isUser={isUser} />

      <div className={`flex min-w-0 max-w-[min(42rem,78%)] flex-col gap-1.5 ${isUser ? "items-end" : "items-start"}`}>
        {attachment && (
          <span className="inline-flex items-center gap-1.5 rounded-full border border-line bg-raised px-2.5 py-1 text-xs text-muted">
            <span aria-hidden="true">🖼️</span>
            {attachment}
          </span>
        )}

        <div
          className={`rounded-2xl px-4 py-2.5 text-[15px] shadow-sm ring-1 transition-colors ${
            isUser
              ? "rounded-br-md bg-brand text-brand-ink ring-black/5"
              : "rounded-bl-md bg-raised text-ink ring-line"
          }`}
        >
          <div className="markdown" data-bubble>
            <ReactMarkdown>{message}</ReactMarkdown>
          </div>
          {streaming && (
            <span
              className="ml-0.5 inline-block h-[1.05em] w-[2px] translate-y-[3px] animate-caret-blink bg-current align-baseline"
              aria-hidden="true"
            />
          )}
        </div>

        {!isUser && !streaming && (tool || sources.length > 0) && (
          <div className="flex flex-wrap items-center gap-1.5 px-0.5" data-meta>
            {tool && (
              <span className="inline-flex items-center gap-1 rounded-full border border-line bg-raised px-2 py-0.5 text-[11px] font-medium text-muted">
                <span aria-hidden="true">{tool.icon}</span>
                {tool.label}
              </span>
            )}
            {sources.length > 0 && (
              <span className="text-[11px] text-muted/80">Sumber:</span>
            )}
            {sources.map((s, i) => (
              <span
                key={i}
                title={s.filename}
                className="inline-flex max-w-[14rem] items-center gap-1 truncate rounded-full border border-line px-2 py-0.5 text-[11px] text-muted"
              >
                <span aria-hidden="true">📄</span>
                <span className="truncate">{s.filename}</span>
              </span>
            ))}
          </div>
        )}
      </div>
    </div>
  );
}
