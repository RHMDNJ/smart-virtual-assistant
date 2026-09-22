import { useState } from "react";
import { login } from "../services/api.js";

export default function LoginForm({ onLoggedIn }) {
  const [username, setUsername] = useState("");
  const [password, setPassword] = useState("");
  const [showPassword, setShowPassword] = useState(false);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState(null);

  async function handleSubmit(e) {
    e.preventDefault();
    if (loading) return;
    setLoading(true);
    setError(null);
    try {
      onLoggedIn(await login(username, password));
    } catch (err) {
      setError(
        err?.response?.status === 401
          ? "Username atau password salah."
          : "Gagal menghubungi server. Pastikan backend berjalan."
      );
    } finally {
      setLoading(false);
    }
  }

  function handleDemoFill() {
    setUsername("admin");
    setPassword("admin12345");
  }

  return (
    <div className="relative grid min-h-full place-items-center overflow-hidden px-4 py-8">
      {/* Banner brand sebagai latar belakang atmosferik */}
      <img
        src="/brand/banner-terang.webp"
        alt=""
        aria-hidden="true"
        className="pointer-events-none absolute inset-0 h-full w-full select-none object-cover opacity-85 dark:hidden"
      />
      <img
        src="/brand/banner-gelap.webp"
        alt=""
        aria-hidden="true"
        className="pointer-events-none absolute inset-0 hidden h-full w-full select-none object-cover opacity-90 dark:block"
      />

      <div className="relative w-full max-w-[400px]">
        {/* Decorative backdrop glow */}
        <div className="absolute -inset-1 rounded-3xl bg-gradient-to-r from-brand/30 via-cyan/20 to-brand/30 opacity-70 blur-xl filter" />

        <form
          onSubmit={handleSubmit}
          className="relative w-full animate-scale-in rounded-3xl border border-line/80 bg-raised/90 p-8 shadow-2xl shadow-navy/20 backdrop-blur-xl transition-all"
        >
          <div className="mb-6 flex flex-col items-center text-center">
            <div className="relative mb-3 flex items-center justify-center">
              <div className="absolute -inset-2 rounded-full bg-brand/15 blur-md" />
              <img
                src="/brand/maskot-256.png"
                alt=""
                aria-hidden="true"
                width={92}
                height={92}
                className="relative h-20 w-20 select-none object-contain drop-shadow-md transition-transform duration-300 hover:scale-105"
              />
            </div>
            
            <div className="inline-flex items-center gap-1.5 rounded-full border border-line bg-surface/60 px-3 py-1 text-[11px] font-medium text-muted mb-2">
              <span className="h-1.5 w-1.5 rounded-full bg-emerald-500 animate-pulse" />
              Pemkab Hulu Sungai Selatan
            </div>

            <h1 className="text-3xl font-black tracking-tight">
              <span className="text-navy dark:text-ink">SA</span>
              <span className="text-brand">VIRA</span>
            </h1>
            <p className="mt-0.5 text-xs font-semibold tracking-wide text-navy/80 dark:text-ink/70">
              SMART VIRTUAL ASSISTANT
            </p>
            <p className="mt-2 text-xs text-muted">
              Masuk untuk berinteraksi dengan asisten cerdas lokal
            </p>
          </div>

          <div className="space-y-4">
            <div>
              <label className="mb-1.5 block text-xs font-medium text-ink/80" htmlFor="username">
                Username
              </label>
              <div className="relative flex items-center">
                <span className="pointer-events-none absolute left-3.5 text-muted/60">
                  <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
                    <path d="M19 21v-2a4 4 0 0 0-4-4H9a4 4 0 0 0-4 4v2" />
                    <circle cx="12" cy="7" r="4" />
                  </svg>
                </span>
                <input
                  id="username"
                  value={username}
                  onChange={(e) => setUsername(e.target.value)}
                  autoComplete="username"
                  autoFocus
                  placeholder="Masukkan username"
                  className="w-full rounded-xl border border-line bg-surface/70 pl-10 pr-3.5 py-2.5 text-sm outline-none transition placeholder:text-muted/60 focus:border-brand focus:bg-raised focus:ring-4 focus:ring-brand/15"
                />
              </div>
            </div>

            <div>
              <label className="mb-1.5 block text-xs font-medium text-ink/80" htmlFor="password">
                Password
              </label>
              <div className="relative flex items-center">
                <span className="pointer-events-none absolute left-3.5 text-muted/60">
                  <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
                    <rect width="18" height="11" x="3" y="11" rx="2" ry="2" />
                    <path d="M7 11V7a5 5 0 0 1 10 0v4" />
                  </svg>
                </span>
                <input
                  id="password"
                  type={showPassword ? "text" : "password"}
                  value={password}
                  onChange={(e) => setPassword(e.target.value)}
                  autoComplete="current-password"
                  placeholder="Masukkan password"
                  className="w-full rounded-xl border border-line bg-surface/70 pl-10 pr-10 py-2.5 text-sm outline-none transition placeholder:text-muted/60 focus:border-brand focus:bg-raised focus:ring-4 focus:ring-brand/15"
                />
                <button
                  type="button"
                  onClick={() => setShowPassword(!showPassword)}
                  aria-label={showPassword ? "Sembunyikan password" : "Tampilkan password"}
                  className="absolute right-3 text-muted/60 hover:text-ink transition p-1"
                >
                  {showPassword ? (
                    <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
                      <path d="M9.88 9.88a3 3 0 1 0 4.24 4.24" />
                      <path d="M10.73 5.08A10.43 10.43 0 0 1 12 5c7 0 10 7 10 7a13.16 13.16 0 0 1-1.67 2.68" />
                      <path d="M6.61 6.61A13.526 13.526 0 0 0 2 12s3 7 10 7a9.74 9.74 0 0 0 5.39-1.61" />
                      <line x1="2" x2="22" y1="2" y2="22" />
                    </svg>
                  ) : (
                    <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
                      <path d="M2 12s3-7 10-7 10 7 10 7-3 7-10 7-10-7-10-7Z" />
                      <circle cx="12" cy="12" r="3" />
                    </svg>
                  )}
                </button>
              </div>
            </div>
          </div>

          {error && (
            <p
              key={error}
              role="alert"
              data-error
              className="mt-4 animate-shake rounded-xl border border-red-500/20 bg-red-500/10 px-3.5 py-2.5 text-xs font-medium text-red-600 dark:text-red-400 flex items-center gap-2"
            >
              <svg width="15" height="15" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" className="shrink-0">
                <circle cx="12" cy="12" r="10" />
                <line x1="12" y1="8" x2="12" y2="12" />
                <line x1="12" y1="16" x2="12.01" y2="16" />
              </svg>
              <span>{error}</span>
            </p>
          )}

          <button
            type="submit"
            disabled={loading || !username || !password}
            className="mt-6 flex w-full items-center justify-center gap-2 rounded-xl bg-brand py-2.5 text-sm font-semibold text-brand-ink shadow-lg shadow-brand/25 transition duration-150 hover:opacity-95 active:scale-[0.99] disabled:opacity-45 disabled:shadow-none"
          >
            {loading && (
              <span className="h-4 w-4 animate-spin rounded-full border-2 border-current border-t-transparent" />
            )}
            {loading ? "Memeriksa kredensial…" : "Masuk"}
          </button>

          {/* Quick demo helper */}
          <div className="mt-5 pt-4 border-t border-line/60 flex items-center justify-between text-[11px] text-muted">
            <span>Akun demo pengujian:</span>
            <button
              type="button"
              onClick={handleDemoFill}
              className="rounded-md border border-line bg-surface/80 px-2 py-0.5 font-mono text-muted hover:border-brand/50 hover:text-brand transition"
            >
              admin / admin12345
            </button>
          </div>
        </form>
      </div>
    </div>
  );
}
