import React, { useState } from "react";
import LoginPage     from "./pages/LoginPage";
import UploadPage    from "./pages/UploadPage";
import AnalysisPage  from "./pages/AnalysisPage";
import DashboardPage from "./pages/DashboardPage";
import AppShell      from "./components/AppShell";
import { ToastProvider } from "./components/Toast";
import { isLoggedIn, clearToken } from "./lib/auth";

const SCREEN = {
  LOGIN:     "login",
  UPLOAD:    "upload",
  ANALYSIS:  "analysis",
  DASHBOARD: "dashboard",
};

export default function App() {
  const [screen, setScreen]       = useState(isLoggedIn() ? SCREEN.UPLOAD : SCREEN.LOGIN);
  const [filePath, setFilePath]   = useState(null);
  const [runMode, setRunMode]     = useState("collaborative");
  const [sessionId, setSessionId] = useState(null);
  const [spec, setSpec]           = useState(null);
  const [downloads, setDownloads] = useState([]);
  const [events, setEvents]       = useState([]);
  const [error, setError]         = useState(null);

  const handleAuth = () => setScreen(SCREEN.UPLOAD);

  const handleReady = (path, mode) => {
    setFilePath(path);
    setRunMode(mode);
    setError(null);
    setSessionId(null);   // reset — AnalysisPage will set it via onSessionStart
    setScreen(SCREEN.ANALYSIS);
  };

  // Called by AnalysisPage as soon as the backend session is created
  const handleSessionStart = (sid) => {
    setSessionId(sid);
  };

  const handleDone = (sid, dashSpec, dlList, evtList) => {
    setSessionId(sid);
    setSpec(dashSpec);
    setDownloads(dlList || []);
    setEvents(evtList || []);
    setScreen(SCREEN.DASHBOARD);
  };

  const handleError = (msg) => {
    setError(msg);
    setScreen(SCREEN.UPLOAD);
  };

  const handleReset = () => {
    setFilePath(null);
    setSpec(null);
    setSessionId(null);
    setDownloads([]);
    setEvents([]);
    setError(null);
    setScreen(SCREEN.UPLOAD);
  };

  const handleLoadSaved = (savedSpec) => {
    setSpec(savedSpec);
    setSessionId(savedSpec?.session_id || null);
    setScreen(SCREEN.DASHBOARD);
  };

  const handleLogout = () => {
    clearToken();
    handleReset();
    setScreen(SCREEN.LOGIN);
  };

  const handleNavigate = (target) => {
    if (target === "upload") handleReset();
    else if (target === "dashboard" && spec) setScreen(SCREEN.DASHBOARD);
    else if (target === "login") setScreen(SCREEN.LOGIN);
  };

  /* Login page gets its own full-screen layout (no sidebar) */
  if (screen === SCREEN.LOGIN) {
    return (
      <ToastProvider>
        <LoginPage
          onAuth={handleAuth}
          onSkip={() => setScreen(SCREEN.UPLOAD)}
        />
      </ToastProvider>
    );
  }

  return (
    <ToastProvider>
      <AppShell
        screen={screen}
        onNavigate={handleNavigate}
        onLogout={handleLogout}
      >
        {screen === SCREEN.UPLOAD && (
          <UploadPage onReady={handleReady} error={error} />
        )}

        {screen === SCREEN.ANALYSIS && (
          <AnalysisPage
            filePath={filePath}
            mode={runMode}
            onSessionStart={handleSessionStart}
            onDone={handleDone}
            onError={handleError}
          />
        )}

        {screen === SCREEN.DASHBOARD && (
          <DashboardPage
            sessionId={sessionId}
            spec={spec}
            downloads={downloads}
            mode={runMode}
            events={events}
            onReset={handleReset}
            onLoadSaved={handleLoadSaved}
          />
        )}
      </AppShell>
    </ToastProvider>
  );
}
