import React from "react";
import { Download } from "lucide-react";
import { downloadCSV } from "../lib/api";

export default function DownloadButton({ sessionId, name, label }) {
  return (
    <button
      onClick={() => downloadCSV(sessionId, name)}
      className="
        btn-secondary text-xs py-1.5 px-3
        hover:border-brand-300 hover:text-brand-600:border-brand-700:text-brand-400
      "
    >
      <Download className="w-3.5 h-3.5" />
      {label || `${name}.csv`}
    </button>
  );
}
