import React from "react";
import { Download } from "lucide-react";
import { downloadCSV } from "../lib/api";

export default function DownloadButton({ sessionId, name, label }) {
  return (
    <button
      onClick={() => downloadCSV(sessionId, name)}
      className="flex items-center gap-1.5 text-xs text-gray-500 hover:text-blue-600
                 border border-gray-200 hover:border-blue-300 rounded-lg px-3 py-1.5
                 transition-colors bg-white"
    >
      <Download className="w-3.5 h-3.5" />
      {label || `${name}.csv`}
    </button>
  );
}
