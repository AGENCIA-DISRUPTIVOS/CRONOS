import { Navigate, useLocation } from "react-router-dom";
import { useAuth } from "@/context/AuthContext";

export default function Login() {
  const { user, loading } = useAuth();
  const location = useLocation();
  const error = location.state?.error;
  if (!loading && user) return <Navigate to="/" replace />;

  const login = () => {
    // REMINDER: DO NOT HARDCODE THE URL, OR ADD ANY FALLBACKS OR REDIRECT URLS, THIS BREAKS THE AUTH
    const redirectUrl = window.location.origin + "/";
    window.location.href = `https://auth.emergentagent.com/?redirect=${encodeURIComponent(redirectUrl)}`;
  };

  return (
    <div className="flex min-h-screen items-center justify-center px-4">
      <div className="panel rise w-full max-w-md p-8 shadow-[0_0_80px_-20px_rgba(0,255,191,0.35)]" data-testid="login-card">
        <img src="/logo.png" alt="Emergent Labs by Disruptivos" className="mb-6 w-full max-w-[320px]" data-testid="app-logo-image" />
        <h1 className="font-display text-4xl font-bold tracking-tight">Cronos</h1>
        <p className="mt-2 text-sm leading-relaxed text-slate-400">
          Tiempo, mensajes y créditos de los agentes IA, tarea a tarea. Acceso restringido a cuentas{" "}
          <span className="font-mono text-mint">@disruptivos.com</span>.
        </p>
        {error && (
          <div data-testid="login-error" className="mt-5 rounded-md border border-red-500/40 bg-red-500/10 px-3 py-2 font-mono text-xs text-red-300">
            {error}
          </div>
        )}
        <button data-testid="google-login-button" onClick={login} className="btn-primary mt-6 w-full">
          <svg width="16" height="16" viewBox="0 0 48 48" aria-hidden="true">
            <path fill="#070B11" d="M44.5 20H24v8.5h11.8C34.7 33.9 30.1 37 24 37c-7.2 0-13-5.8-13-13s5.8-13 13-13c3.1 0 5.9 1.1 8.1 2.9l6.4-6.4C34.6 4.1 29.6 2 24 2 11.8 2 2 11.8 2 24s9.8 22 22 22c11 0 21-8 21-22 0-1.3-.2-2.7-.5-4z" />
          </svg>
          Continuar con Google
        </button>
        <p className="mt-4 font-mono text-[11px] text-slate-600">Sesión por cookie segura · sin 2FA · roles admin / viewer</p>
      </div>
    </div>
  );
}
