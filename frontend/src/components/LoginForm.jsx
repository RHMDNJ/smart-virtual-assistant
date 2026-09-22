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
    <div className="grid min-h-full place-items-center px-4 py-10">
      <form
        onSubmit={handleSubmit}
        className="w-full max-w-sm animate-scale-in rounded-2xl border border-line bg-raised p-7 shadow-xl shadow-black/[.04]"
      >
        <div className="mb-6 flex flex-col items-center text-center">
          <div className="mb-3 grid h-12 w-12 place-items-center rounded-2xl bg-brand text-xl text-brand-ink shadow-lg shadow-brand/25">
            ✦
          </div>
          <h1 className="text-lg font-semibold tracking-tight">Smart Virtual Assistant</h1>
          <p className="mt-1 text-sm text-muted">Masuk untuk melanjutkan.</p>
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
