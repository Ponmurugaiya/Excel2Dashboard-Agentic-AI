import React, { useCallback, useState } from "react";
import { UploadCloud, FileSpreadsheet, AlertCircle, Loader2 } from "lucide-react";
import axios from "axios";

/**
 * Upload screen.
 * Supports click-to-browse and drag-and-drop.
 * Calls POST /upload then hands the response to onDashboardReady.
 */
export default function UploadPage({ onDashboardReady }) {
  const [dragging, setDragging] = useState(false);
  const [loading, setLoading]   = useState(false);
  const [error, setError]       = useState(null);
  const [fileName, setFileName] = useState(null);

  const handleFile = useCallback(
    async (file) => {
      if (!file) return;

      const allowed = [".xlsx", ".xls", ".xlsm", ".csv"];
      const ext = "." + file.name.split(".").pop().toLowerCase();
      if (!allowed.includes(ext)) {
        setError(`Unsupported file type "${ext}". Please upload an Excel file (.xlsx, .xls, .xlsm) or a CSV file (.csv).`);
        return;
      }

      setError(null);
      setFileName(file.name);
      setLoading(true);

      try {
        const formData = new FormData();
        formData.append("file", file);

        const response = await axios.post("/upload", formData, {
          headers: { "Content-Type": "multipart/form-data" },
        });

        onDashboardReady(response.data);
      } catch (err) {
        const detail =
          err.response?.data?.detail ||
          err.message ||
          "An unexpected error occurred.";
        setError(detail);
        setFileName(null);
      } finally {
        setLoading(false);
      }
    },
    [onDashboardReady]
  );

  // ── Drag handlers ─────────────────────────────────────────────────────────
  const onDragOver  = (e) => { e.preventDefault(); setDragging(true); };
  const onDragLeave = ()  => setDragging(false);
  const onDrop      = (e) => {
    e.preventDefault();
    setDragging(false);
    handleFile(e.dataTransfer.files[0]);
  };
  const onInputChange = (e) => handleFile(e.target.files[0]);

  return (
    <div className="flex flex-col items-center justify-center min-h-screen px-4">
      {/* Header */}
      <div className="mb-10 text-center">
        <h1 className="text-4xl font-bold text-gray-900 mb-2">
          AI BI Dashboard Builder
        </h1>
        <p className="text-gray-500 text-lg">
          Upload an Excel file and get an interactive dashboard in seconds.
        </p>
      </div>

      {/* Drop zone */}
      <label
        htmlFor="file-input"
        onDragOver={onDragOver}
        onDragLeave={onDragLeave}
        onDrop={onDrop}
        className={`
          flex flex-col items-center justify-center
          w-full max-w-lg h-64 rounded-2xl border-2 border-dashed
          cursor-pointer transition-all duration-200
          ${dragging
            ? "border-brand-500 bg-brand-50 scale-[1.02]"
            : "border-gray-300 bg-white hover:border-brand-500 hover:bg-brand-50"}
          ${loading ? "pointer-events-none opacity-70" : ""}
        `}
      >
        {loading ? (
          <div className="flex flex-col items-center gap-3 text-brand-600">
            <Loader2 className="w-12 h-12 animate-spin" />
            <p className="font-medium">Analysing {fileName}…</p>
            <p className="text-sm text-gray-400">This may take a few seconds.</p>
          </div>
        ) : (
          <div className="flex flex-col items-center gap-3 text-gray-400">
            {fileName ? (
              <>
                <FileSpreadsheet className="w-12 h-12 text-green-500" />
                <p className="font-medium text-gray-700">{fileName}</p>
              </>
            ) : (
              <>
                <UploadCloud className="w-12 h-12" />
                <p className="font-medium text-gray-600">
                  Drag & drop your Excel file here
                </p>
                <p className="text-sm">or click to browse</p>
                <p className="text-xs text-gray-300">.xlsx · .xls · .xlsm · .csv — max 50 MB</p>
              </>
            )}
          </div>
        )}

        <input
          id="file-input"
          type="file"
          accept=".xlsx,.xls,.xlsm,.csv"
          className="hidden"
          onChange={onInputChange}
          disabled={loading}
        />
      </label>

      {/* Error message */}
      {error && (
        <div className="mt-4 flex items-start gap-2 text-red-600 bg-red-50 border border-red-200 rounded-lg px-4 py-3 max-w-lg w-full">
          <AlertCircle className="w-5 h-5 mt-0.5 flex-shrink-0" />
          <p className="text-sm">{error}</p>
        </div>
      )}
    </div>
  );
}
