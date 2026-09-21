import ReactMarkdown from "react-markdown";

const TOOL_LABEL = {
  rag_search: "📚 RAG",
  image_ocr: "🖼️ OCR",
  sql_query: "🗄️ SQL",
  llm_direct: "💬 LLM",
};

export default function MessageBubble({
  role,
  message,
  sources = [],
  toolUsed,
  attachment,
  streaming = false,
}) {
  const isUser = role === "user";

  return (
    <div className={`flex ${isUser ? "justify-end" : "justify-start"} mb-3`}>
      <div
        className={`max-w-[75%] rounded-2xl px-4 py-2 text-sm ${
          isUser ? "bg-blue-600 text-white" : "bg-gray-100 text-gray-900"
        }`}
      >
        {attachment && (
          <div className="mb-1 text-xs opacity-80">🖼️ {attachment}</div>
        )}

        <div className="prose prose-sm max-w-none">
          <ReactMarkdown>{message}</ReactMarkdown>
          {streaming && (
            <span className="ml-0.5 inline-block h-4 w-1.5 animate-pulse bg-gray-400 align-middle" />
          )}
        </div>

        {!isUser && toolUsed && !streaming && (
          <div className="mt-1 text-xs opacity-60">
            {TOOL_LABEL[toolUsed] || `🔧 ${toolUsed}`}
          </div>
        )}

        {sources.length > 0 && (
          <div className="mt-2 border-t border-gray-300 pt-1 text-xs opacity-70">
            {sources.map((s, i) => (
              <div key={i}>📄 Sumber: {s.filename}</div>
            ))}
          </div>
        )}
      </div>
    </div>
  );
}
