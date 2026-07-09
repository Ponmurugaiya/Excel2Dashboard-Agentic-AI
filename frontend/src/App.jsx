import React, { useState } from "react";
import LoginPage     from "./pages/LoginPage";
import UploadPage    from "./pages/UploadPage";
import AnalysisPage  from "./pages/AnalysisPage";
import DashboardPage from "./pages/DashboardPage";
import { isLoggedIn } from "./lib/auth";

/**
 * Root component — state-based navigation.
 *
 * Screens:
 *   login      → UploadPage (if not logged in, login is optional — can skip)
 *   upload     → AnalysisPage (file uploaded, mode chosen)
 *   analysis   → DashboardPage (agents running)
 *   dashboard  → show result
 */

const SCREEN = {
  LOGIN:     "login",
  UPLOAD:    "upload",
  ANALYSIS:  "analysis",
  DASHBOARD: "dashboard",
};

export default function App() {
  const [screen, setScreen]     = useState(isLoggedIn() ? SCREEN.UPLOAD : SCREEN.LOGIN);
  const [filePath, setFilePath] = useState(null);
  const [runMode, setRunMode]   = useState("collaborative");
  const [sessionId, setSessionId] = useState(null);
  const [spec, setSpec]         = useState(null);
  const [downloads, setDownloads] = useState([]);
  const [events, setEvents]     = useState([]);
  const [error, setError]       = useState(null);

  // Login → Upload
  const handleAuth = () => setScreen(SCREEN.UPLOAD);

  // UploadPage calls this when file is saved + mode chosen
  const handleReady = (path, mode) => {
    setFilePath(path);
    setRunMode(mode);
    setError(null);
    setScreen(SCREEN.ANALYSIS);
  };

  // AnalysisPage calls this when pipeline completes
  const handleDone = (sid, dashSpec, dlList, evtList) => {
    setSessionId(sid);
    setSpec(dashSpec);
    setDownloads(dlList || []);
    setEvents(evtList || []);
    setScreen(SCREEN.DASHBOARD);
  };

  // AnalysisPage calls this on error
  const handleError = (msg) => {
    setError(msg);
    setScreen(SCREEN.UPLOAD);
  };

  // Reset to upload screen
  const handleReset = () => {
    setFilePath(null);
    setSpec(null);
    setSessionId(null);
    setDownloads([]);
    setEvents([]);
    setError(null);
    setScreen(SCREEN.UPLOAD);
  };

  // Load a saved dashboard directly
  const handleLoadSaved = (savedSpec) => {
    setSpec(savedSpec);
    setSessionId(savedSpec?.session_id || null);
    setScreen(SCREEN.DASHBOARD);
  };

  return (
    <div className="min-h-screen bg-gray-50">
      {screen === SCREEN.LOGIN && (
        <LoginPage
          onAuth={handleAuth}
          onSkip={() => setScreen(SCREEN.UPLOAD)}
        />
      )}

      {screen === SCREEN.UPLOAD && (
        <UploadPage
          onReady={handleReady}
          error={error}
        />
      )}

      {screen === SCREEN.ANALYSIS && (
        <AnalysisPage
          filePath={filePath}
          mode={runMode}
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
    </div>
  );
}
