import { useState } from "react";
import { login } from "../services/api.js";

export default function LoginForm({ onLoggedIn }) {
  const [username, setUsername] = useState("");
  const [password, setPassword] = useState("");
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

  const field =
    "w-full rounded-xl border border-line bg-surface px-3.5 py-2.5 text-sm outline-none transition " +
    "placeholder:text-muted/70 focus:border-brand focus:ring-4 focus:ring-brand/15";

  return (
    <div className="relative grid min-h-full place-items-center overflow-hidden px-4 py-10">
      {/* Banner brand sebagai latar; versi terang dan gelap dipilih lewat media query. */}
      <img
        src="/brand/banner-terang.webp"
        alt=""
        aria-hidden="true"
        className="pointer-events-none absolute inset-0 h-full w-full select-none object-cover opacity-90 dark:hidden"
      />
      <img
        src="/brand/banner-gelap.webp"
        alt=""
        aria-hidden="true"
        className="pointer-events-none absolute inset-0 hidden h-full w-full select-none object-cover dark:block"
      />

      <form
        onSubmit={handleSubmit}
        className="relative w-full max-w-sm animate-scale-in rounded-2xl border border-line bg-raised/95 p-7 shadow-2xl shadow-navy/20 backdrop-blur"
      >
        <div className="mb-6 flex flex-col items-center text-center">
          {/* Wordmark ditulis sebagai teks, bukan gambar: logo raster harus di-invert
              di mode gelap, dan filter itu mengubah maskot jadi siluet tanpa wajah. */}
          <img
            src="/brand/maskot-256.png"
            alt=""
            aria-hidden="true"
            width={96}
            height={96}
            className="mb-4 h-24 w-24 select-none object-contain drop-shadow-md"
          />
          <h1 className="text-2xl font-extrabold tracking-tight">
            <span className="text-navy dark:text-ink">HELP</span>
            <span className="text-brand">DESK</span>
          </h1>
          <p className="mt-0.5 text-[13px] font-semibold text-navy/80 dark:text-ink/70">
            Pusat Bantuan Layanan Digital
          </p>
          <p className="text-[11px] text-muted">
            Pemerintah Kabupaten Hulu Sungai Selatan
          </p>
          <p className="mt-4 text-sm text-muted">Masuk untuk melanjutkan.</p>
        </div>

        <label className="mb-1.5 block text-xs font-medium text-muted" htmlFor="username">
          Username
        </label>
        <input
          id="username"
          value={username}
          onChange={(e) => setUsername(e.target.value)}
          autoComplete="username"
          autoFocus
          className={`${field} mb-4`}
        />

        <label className="mb-1.5 block text-xs font-medium text-muted" htmlFor="password">
          Password
        </label>
        <input
          id="password"
          type="password"
          value={password}
          onChange={(e) => setPassword(e.target.value)}
          autoComplete="current-password"
          className={`${field} mb-5`}
        />

        {error && (
          <p
            key={error}
            role="alert"
            data-error
            className="mb-4 animate-shake rounded-lg bg-red-500/10 px-3 py-2 text-sm text-red-600 dark:text-red-400"
          >
            {error}
          </p>
        )}

        <button
          type="submit"
          disabled={loading || !username || !password}
          className="flex w-full items-center justify-center gap-2 rounded-xl bg-brand py-2.5 text-sm font-medium text-brand-ink shadow-lg shadow-brand/25 transition active:scale-[.98] disabled:opacity-45 disabled:shadow-none"
        >
          {loading && (
            <span className="h-3.5 w-3.5 animate-spin rounded-full border-2 border-current border-t-transparent" />
          )}
          {loading ? "Memeriksa…" : "Masuk"}
        </button>
      </form>
    </div>
  );
}
