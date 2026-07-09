import React, { useState } from "react";
import UploadPage from "./pages/UploadPage";
import DashboardPage from "./pages/DashboardPage";

/**
 * Root component — two screens: upload or dashboard.
 * No router needed at this stage; simple state-based navigation.
 */
export default function App() {
  const [dashboard, setDashboard] = useState(null);

  const handleReset = () => setDashboard(null);

  return (
    <div className="min-h-screen">
      {dashboard ? (
        <DashboardPage data={dashboard} onReset={handleReset} />
      ) : (
        <UploadPage onDashboardReady={setDashboard} />
      )}
    </div>
  );
}
