import React, { useEffect, useRef, useState } from "react";
import { Loader2, CheckCircle2, XCircle } from "lucide-react";
import { analyseAPI } from "../lib/api";
import AgentProgressFeed from "../components/AgentProgressFeed";
import AgentQuestionCard from "../components/AgentQuestionCard";

/**
 * Analysis in-progress page.
 * Opens SSE stream, shows agent activity, handles collaborative questions.
 * On completion: calls onDone(sessionId, dashboardSpec).
 */
export default function AnalysisPage({ filePath, mode, onDone, onError }) {
  const [events, setEvents]       = useState([]);
  const [status, setStatus]       = useState("created");
  const [question, setQuestion]   = useState(null);
  const [answering, setAnswering] = useState(false);
  const [sessionId, setSessionId] = useState(null);
  const esRef = useRef(null);

  // Start the analysis session and open SSE stream
  useEffect(() => {
    let mounted = true;

    const start = async () => {
      try {
        const res = await analyseAPI.start(filePath, mode);
        const sid = res.data.session_id;
        setSessionId(sid);

        // Open SSE stream
        const es = new EventSource(`/analyse/${sid}/events`);
        esRef.current = es;

        es.onmessage = (e) => {
          if (!mounted) return;
          try {
            const msg = JSON.parse(e.data);

            // Session done/error
            if (msg.type === "session_status") {
              setStatus(msg.status);
              es.close();
              if (msg.status === "done") {
                // Fetch final spec
                analyseAPI.getStatus(sid).then((r) => {
                  onDone(sid, r.data.dashboard, r.data.downloads || []);
                });
              } else if (msg.status === "error") {
                onError(msg.error || "Analysis failed.");
              }
              return;
            }

            // Pending user question (collaborative mode)
            if (msg.type === "pending_question") {
              setQuestion(msg.question);
              return;
            }

            // Status update
            if (msg.type === "log" && msg.from === "system") {
              const text = msg.payload?.text || "";
              if (text.includes("Cleaning")) setStatus("cleaning");
              else if (text.includes("planning") || text.includes("Planning")) setStatus("planning");
              else if (text.includes("analy")) setStatus("analysing");
              else if (text.includes("insight")) setStatus("insight");
              else if (text.includes("Design")) setStatus("designing");
              else if (text.includes("ready") || text.includes("Done")) setStatus("done");
            }

            setEvents((prev) => [...prev, msg]);
          } catch {}
        };

        es.onerror = () => {
          if (!mounted) return;
          es.close();
          // Poll for final status
          analyseAPI.getStatus(sid).then((r) => {
            if (r.data.status === "done") {
              onDone(sid, r.data.dashboard, r.data.downloads || []);
            } else if (r.data.status === "error") {
              onError(r.data.error || "Analysis failed.");
            }
          }).catch(() => onError("Connection lost."));
        };

      } catch (err) {
        if (mounted) onError(err.response?.data?.detail || err.message);
      }
    };

    start();
    return () => {
      mounted = false;
      esRef.current?.close();
    };
  }, [filePath, mode]);

  // Submit user's answer to waiting agent
  const handleAnswer = async (decisionPointId, answer) => {
    if (!sessionId) return;
    setAnswering(true);
    try {
      await analyseAPI.submitAnswer(sessionId, decisionPointId, answer);
      setQuestion(null);
    } catch (err) {
      console.error("Answer submit failed:", err);
    } finally {
      setAnswering(false);
    }
  };

  return (
    <div className="min-h-screen bg-gray-50 flex flex-col items-center justify-center px-4 py-12">
      <div className="w-full max-w-2xl space-y-5">
        {/* Header */}
        <div className="text-center mb-2">
          <div className="flex items-center justify-center gap-2 mb-1">
            {status === "done" ? (
              <CheckCircle2 className="w-6 h-6 text-green-500" />
            ) : status === "error" ? (
              <XCircle className="w-6 h-6 text-red-500" />
            ) : (
              <Loader2 className="w-6 h-6 text-blue-500 animate-spin" />
            )}
            <h2 className="text-lg font-semibold text-gray-800">
              {status === "done" ? "Analysis Complete" :
               status === "error" ? "Analysis Failed" :
               "Agents are working..."}
            </h2>
          </div>
          {mode === "autonomous" && status !== "done" && status !== "error" && (
            <p className="text-sm text-amber-600 flex items-center justify-center gap-1">
              ⚡ Autonomous mode — no interruptions
            </p>
          )}
        </div>

        {/* Progress feed */}
        <AgentProgressFeed events={events} status={status} />

        {/* Question card (collaborative mode) */}
        {question && mode === "collaborative" && (
          <AgentQuestionCard
            question={question}
            onAnswer={handleAnswer}
            loading={answering}
          />
        )}
      </div>
    </div>
  );
}
