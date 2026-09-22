export default function ThinkingDots() {
  return (
    <div className="flex animate-fade-in gap-3" data-thinking>
      <img
        src="/brand/maskot-64.png"
        alt=""
        aria-hidden="true"
        width={32}
        height={32}
        className="h-8 w-8 shrink-0 rounded-full border border-line bg-raised object-contain p-0.5"
      />
      <div className="flex items-center gap-1.5 rounded-2xl rounded-bl-md bg-raised px-4 py-3.5 ring-1 ring-line">
        {[0, 1, 2].map((i) => (
          <span
            key={i}
            className="h-1.5 w-1.5 animate-dot-bounce rounded-full bg-muted"
            style={{ animationDelay: `${i * 0.16}s` }}
          />
        ))}
        <span className="sr-only">Assistant sedang berpikir</span>
      </div>
    </div>
  );
}
