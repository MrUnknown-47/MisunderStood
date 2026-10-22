import { Link, Navigate, Route, Routes, useLocation } from "react-router-dom";
import { LogOut } from "lucide-react";
import { Logo } from "./components";
import { useSession } from "./session";
import {
  AgreementPage,
  BridgeTestPage,
  CreateSessionPage,
  InterpretationPage,
  JoinSessionPage,
  LandingPage,
  MisunderstandingMapPage,
  NotFoundPage,
  WaitingRoomPage,
} from "./pages";

function AppShell() {
  const { identity, clearIdentity } = useSession();
  const location = useLocation();
  const isLanding = location.pathname === "/";

  return (
    <div className="min-h-screen">
      <header className="relative z-20 border-b border-ink/8 bg-cream/90 backdrop-blur-xl">
        <div className="mx-auto flex h-18 max-w-7xl items-center justify-between px-5 sm:px-8">
          <Link to="/" className="rounded-xl focus:outline-none focus:ring-4 focus:ring-coral/20">
            <Logo />
          </Link>
          <div className="flex items-center gap-2 sm:gap-3">
            {identity.sessionId ? (
              <>
                <Link
                  to={`/sessions/${identity.sessionId}/waiting`}
                  className="hidden rounded-full border border-ink/10 bg-white px-3 py-1.5 text-xs font-bold text-muted sm:block"
                >
                  Session active
                </Link>
                <button
                  onClick={clearIdentity}
                  className="rounded-xl p-2.5 text-muted transition hover:bg-ink/5 hover:text-ink"
                  aria-label="Leave session"
                  title="Leave session on this device"
                >
                  <LogOut className="size-4" />
                </button>
              </>
            ) : !isLanding ? (
              <Link to="/join" className="text-sm font-bold text-ink hover:text-coral">
                Join a session
              </Link>
            ) : null}
          </div>
        </div>
      </header>

      <main>
        <Routes>
          <Route path="/" element={<LandingPage />} />
          <Route path="/create" element={<CreateSessionPage />} />
          <Route path="/join" element={<JoinSessionPage />} />
          <Route path="/sessions/:sessionId/waiting" element={<WaitingRoomPage />} />
          <Route path="/sessions/:sessionId/interpret" element={<InterpretationPage />} />
          <Route path="/sessions/:sessionId/map" element={<MisunderstandingMapPage />} />
          <Route path="/sessions/:sessionId/agreement" element={<AgreementPage />} />
          <Route path="/sessions/:sessionId/bridge-test" element={<BridgeTestPage />} />
          <Route path="/home" element={<Navigate to="/" replace />} />
          <Route path="*" element={<NotFoundPage />} />
        </Routes>
      </main>
    </div>
  );
}

export default AppShell;
