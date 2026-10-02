import "@/App.css";
import { BrowserRouter, Routes, Route, Navigate, Outlet, useLocation } from "react-router-dom";
import { Toaster } from "@/components/ui/sonner";
import { AuthProvider, useAuth } from "@/context/AuthContext";
import { AuthCallback } from "@/components/AuthCallback";
import { Layout } from "@/components/Layout";
import Login from "@/pages/Login";
import Dashboard from "@/pages/Dashboard";
import Registro from "@/pages/Registro";
import Cuadrar from "@/pages/Cuadrar";
import Ajustes from "@/pages/Ajustes";
import Equipo from "@/pages/Equipo";
import Wiki from "@/pages/Wiki";
import Instrucciones from "@/pages/Instrucciones";

function ProtectedRoute() {
  const { user, loading } = useAuth();
  if (loading) {
    return (
      <div className="flex min-h-screen items-center justify-center font-mono text-sm text-slate-500" data-testid="auth-loading">
        comprobando sesión…
      </div>
    );
  }
  if (!user) return <Navigate to="/login" replace />;
  return (
    <Layout>
      <Outlet />
    </Layout>
  );
}

function AppRouter() {
  const location = useLocation();
  if (location.hash?.includes("session_id=")) return <AuthCallback />;
  return (
    <Routes>
      <Route path="/login" element={<Login />} />
      <Route element={<ProtectedRoute />}>
        <Route path="/" element={<Dashboard />} />
        <Route path="/registro" element={<Registro />} />
        <Route path="/cuadrar" element={<Cuadrar />} />
        <Route path="/equipo" element={<Equipo />} />
        <Route path="/wiki" element={<Wiki />} />
        <Route path="/instrucciones" element={<Instrucciones />} />
        <Route path="/ajustes" element={<Ajustes />} />
      </Route>
      <Route path="*" element={<Navigate to="/" replace />} />
    </Routes>
  );
}

export default function App() {
  return (
    <div className="App">
      <BrowserRouter>
        <AuthProvider>
          <AppRouter />
          <Toaster theme="dark" position="bottom-right" toastOptions={{ className: "font-sans" }} />
        </AuthProvider>
      </BrowserRouter>
    </div>
  );
}
