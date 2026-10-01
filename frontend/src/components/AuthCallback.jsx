import { useEffect, useRef } from "react";
import { useLocation, useNavigate } from "react-router-dom";
import { api, errMsg } from "@/lib/api";
import { useAuth } from "@/context/AuthContext";

export function AuthCallback() {
  const location = useLocation();
  const navigate = useNavigate();
  const { setUser } = useAuth();
  const hasProcessed = useRef(false);

  useEffect(() => {
    if (hasProcessed.current) return;
    hasProcessed.current = true;
    const sessionId = new URLSearchParams(location.hash.replace(/^#/, "")).get("session_id");
    api
      .post("/auth/session", { session_id: sessionId })
      .then(({ data }) => {
        setUser(data);
        window.history.replaceState(null, "", window.location.pathname);
        navigate("/", { replace: true });
      })
      .catch((e) => {
        window.history.replaceState(null, "", "/login");
        navigate("/login", { replace: true, state: { error: errMsg(e, "No se pudo iniciar sesión") } });
      });
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  return (
    <div className="flex min-h-screen items-center justify-center font-mono text-sm text-slate-500" data-testid="auth-callback">
      validando acceso…
    </div>
  );
}
