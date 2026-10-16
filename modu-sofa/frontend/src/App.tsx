import { useEffect, type ReactNode } from 'react';
import { BrowserRouter, Navigate, Route, Routes, useLocation } from 'react-router-dom';
import { Toasts } from './components/common/Toasts';
import { useAuth } from './hooks/useAuth';
import { DashboardPage } from './pages/DashboardPage';
import { EditorPage } from './pages/EditorPage';
import { LoginPage } from './pages/LoginPage';
import { ProcessingPage } from './pages/ProcessingPage';
import { SpeakersPage } from './pages/SpeakersPage';
import { UploadPage } from './pages/UploadPage';

function RequireAuth({ children }: { children: ReactNode }) {
  const token = useAuth((s) => s.token);
  const location = useLocation();
  if (!token) return <Navigate to="/login" replace state={{ from: location.pathname }} />;
  return <>{children}</>;
}

export default function App() {
  const ready = useAuth((s) => s.ready);
  const init = useAuth((s) => s.init);

  useEffect(() => {
    void init();
  }, [init]);

  if (!ready) return null;

  return (
    <BrowserRouter>
      <Routes>
        <Route path="/login" element={<LoginPage />} />
        <Route path="/" element={<RequireAuth><DashboardPage /></RequireAuth>} />
        <Route path="/upload" element={<RequireAuth><UploadPage /></RequireAuth>} />
        <Route path="/episodes/:id" element={<RequireAuth><EditorPage /></RequireAuth>} />
        <Route path="/episodes/:id/processing" element={<RequireAuth><ProcessingPage /></RequireAuth>} />
        <Route path="/episodes/:id/speakers" element={<RequireAuth><SpeakersPage /></RequireAuth>} />
        <Route path="*" element={<Navigate to="/" replace />} />
      </Routes>
      <Toasts />
    </BrowserRouter>
  );
}
