/**
 * DashboardChat — thin wrapper kept for backward-compatibility.
 * DashboardPage imports this and it proxies to ChatPanel in "dashboard" mode.
 */
import React from "react";
import ChatPanel from "./ChatPanel";

export default function DashboardChat({ sessionId, onSpecUpdate }) {
  return (
    <ChatPanel
      mode="dashboard"
      sessionId={sessionId}
      onSpecUpdate={onSpecUpdate}
    />
  );
}
