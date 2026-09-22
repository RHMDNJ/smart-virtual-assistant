export default function ThinkingDots({ label = "Sedang berpikir..." }) {
  return (
    <div className="flex animate-fade-in gap-3 items-start" data-thinking>
      <div className="relative shrink-0">
        <div className="absolute -inset-0.5 rounded-full bg-brand/20 blur-sm animate-pulse" />
        <img
          src="/brand/maskot-64.png"
          alt=""
          aria-hidden="true"
          width={34}
          height={34}
          className="relative h-8 w-8 select-none rounded-full border border-line/80 bg-raised object-contain p-0.5 shadow-sm"
        />
      </div>
      <div className="flex items-center gap-2 rounded-2xl rounded-bl-md border border-line/80 bg-raised px-4 py-3 shadow-sm">
        <div className="flex items-center gap-1.5">
          {[0, 1, 2].map((i) => (
            <span
              key={i}
              className="h-2 w-2 animate-dot-bounce rounded-full bg-brand/80"
              style={{ animationDelay: `${i * 0.18}s` }}
            />
          ))}
        </div>
        <span className="text-xs text-muted font-normal pl-1">
          {label}
        </span>
        <span className="sr-only">{label}</span>
      </div>
    </div>
  );
}
