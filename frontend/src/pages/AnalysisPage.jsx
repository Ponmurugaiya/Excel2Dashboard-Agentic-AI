import React, { useEffect, useRef, useState } from "react";
import {
  Loader2, CheckCircle2, XCircle, FileSearch,
  Wand2, BarChart3, Lightbulb, Layers, Sparkles,
} from "lucide-react";
import { analyseAPI } from "../lib/api";
import AgentProgressFeed from "../components/AgentProgressFeed";
import AgentQuestionCard from "../components/AgentQuestionCard";

/* ── Pipeline stages ─────────────────────────────────────────────────────── */
const STAGES = [
  { id: "parsing",   label: "Parsing",   desc: "Reading file structure",       icon: FileSearch  },
  { id: "cleaning",  label: "Cleaning",  desc: "Fixing missing & invalid data", icon: Wand2       },
  { id: "planning",  label: "Planning",  desc: "Designing analysis strategy",   icon: Layers      },
  { id: "analysing", label: "Analysing", desc: "Running statistical analyses",  icon: BarChart3   },
  { id: "insight",   label: "Insights",  desc: "Extracting key findings",       icon: Lightbulb   },
  { id: "designing", label: "Building",  desc: "Constructing your dashboard",   icon: Sparkles    },
];

const STAGE_ORDER = STAGES.map((s) => s.id);

function stageIndex(status) {
  const i = STAGE_ORDER.indexOf(status);
  return i === -1 ? -1 : i;
}

export default function AnalysisPage({ filePath, mode, onDone, onError }) {
  const [events, setEvents]       = useState([]);
  const [status, setStatus]       = useState("created");
  const [question, setQuestion]   = useState(null);
  const [answering, setAnswering] = useState(false);
  const [sessionId, setSessionId] = useState(null);
  const esRef    = useRef(null);
  const eventsRef = useRef([]);

  useEffect(() => {
    let mounted = true;

    const start = async () => {
      try {
        const res = await analyseAPI.start(filePath, mode);
        const sid = res.data.session_id;
        setSessionId(sid);

        const es = new EventSource(`/analyse/${sid}/events`);
        esRef.current = es;

        es.onmessage = (e) => {
          if (!mounted) return;
          try {
            const msg = JSON.parse(e.data);

            if (msg.type === "session_status") {
              setStatus(msg.status);
              es.close();
              if (msg.status === "done") {
                analyseAPI.getStatus(sid).then((r) => {
                  onDone(sid, r.data.dashboard, r.data.downloads || [], eventsRef.current);
                });
              } else if (msg.status === "error") {
                onError(msg.error || "Analysis failed.");
              }
              return;
            }

            if (msg.type === "pending_question") {
              setQuestion(msg.question);
              return;
            }

            if (msg.type === "log" && msg.from === "system") {
              const text = msg.payload?.text || "";
              if (text.includes("Parsing") || text.includes("parsing"))  setStatus("parsing");
              else if (text.includes("Cleaning"))  setStatus("cleaning");
              else if (text.includes("planning") || text.includes("Planning")) setStatus("planning");
              else if (text.includes("analy"))     setStatus("analysing");
              else if (text.includes("insight"))   setStatus("insight");
              else if (text.includes("Design") || text.includes("Building")) setStatus("designing");
              else if (text.includes("ready") || text.includes("Done"))  setStatus("done");
            }

            setEvents((prev) => {
              const next = [...prev, msg];
              eventsRef.current = next;
              return next;
            });
          } catch {}
        };

        es.onerror = () => {
          if (!mounted) return;
          es.close();
          analyseAPI.getStatus(sid).then((r) => {
            if (r.data.status === "done") {
              onDone(sid, r.data.dashboard, r.data.downloads || [], eventsRef.current);
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

  const isDone  = status === "done";
  const isError = status === "error";
  const current = stageIndex(status);

  return (
    <div className="max-w-2xl mx-auto px-6 py-10 space-y-8 animate-fade-in">

      {/* ── Header ─────────────────────────────────────────────────────────── */}
      <div className="text-center">
        {isDone ? (
          <div className="flex flex-col items-center gap-3">
            <div className="w-16 h-16 rounded-full bg-emerald-100 flex items-center justify-center">
              <CheckCircle2 className="w-8 h-8 text-emerald-600" />
            </div>
            <h2 className="text-2xl font-extrabold text-slate-900">
              Analysis Complete
            </h2>
            <p className="text-slate-500">
              Loading your dashboard…
            </p>
          </div>
        ) : isError ? (
          <div className="flex flex-col items-center gap-3">
            <div className="w-16 h-16 rounded-full bg-red-100 flex items-center justify-center">
              <XCircle className="w-8 h-8 text-red-600" />
            </div>
            <h2 className="text-2xl font-extrabold text-slate-900">
              Analysis Failed
            </h2>
          </div>
        ) : (
          <div className="flex flex-col items-center gap-3">
            <div className="relative w-16 h-16">
              <div className="absolute inset-0 rounded-full bg-brand-100 animate-ping opacity-30" />
              <div className="relative w-16 h-16 rounded-full bg-brand-100 flex items-center justify-center">
                <Loader2 className="w-7 h-7 text-brand-600 animate-spin" />
              </div>
            </div>
            <h2 className="text-2xl font-extrabold text-slate-900">
              Agents are working
            </h2>
            {mode === "autonomous" ? (
              <span className="badge bg-amber-100 text-amber-700">
                ⚡ Autonomous mode — no interruptions
              </span>
            ) : (
              <span className="badge bg-blue-100 text-blue-700">
                👥 Collaborative mode
              </span>
            )}
          </div>
        )}
      </div>

      {/* ── Stage pipeline ─────────────────────────────────────────────────── */}
      {!isError && (
        <div className="card p-6">
          <div className="flex items-center justify-between gap-1">
            {STAGES.map(({ id, label, icon: Icon }, i) => {
              const done    = isDone || i < current;
              const active  = !isDone && i === current;
              const pending = !isDone && i > current;

              return (
                <React.Fragment key={id}>
                  <div className="flex flex-col items-center gap-1.5 flex-1 min-w-0">
                    <div className={`
                      w-9 h-9 rounded-xl flex items-center justify-center transition-all duration-500
                      ${done   ? "bg-emerald-100" :
                        active ? "bg-brand-100 ring-2 ring-brand-400 ring-offset-2" :
                                 "bg-slate-100"}
                    `}>
                      {done ? (
                        <CheckCircle2 className="w-4.5 h-4.5 text-emerald-600" />
                      ) : (
                        <Icon className={`w-4 h-4 transition-colors duration-500
                          ${active  ? "text-brand-600" :
                            pending ? "text-slate-300" :
                                      "text-slate-400"}`}
                        />
                      )}
                    </div>
                    <span className={`text-[10px] font-medium text-center leading-tight transition-colors duration-300
                      ${done   ? "text-emerald-600" :
                        active ? "text-brand-600" :
                                 "text-slate-400"}`}
                    >
                      {label}
                    </span>
                  </div>

                  {/* Connector */}
                  {i < STAGES.length - 1 && (
                    <div className={`h-0.5 flex-1 max-w-8 rounded-full transition-all duration-700
                      ${done || (isDone && i < STAGES.length - 1)
                        ? "bg-emerald-300"
                        : "bg-slate-200"}`}
                    />
                  )}
                </React.Fragment>
              );
            })}
          </div>
        </div>
      )}

      {/* ── Live agent feed ────────────────────────────────────────────────── */}
      <AgentProgressFeed events={events} status={status} />

      {/* ── Collaborative question ─────────────────────────────────────────── */}
      {question && mode === "collaborative" && (
        <AgentQuestionCard
          question={question}
          onAnswer={handleAnswer}
          loading={answering}
        />
      )}
    </div>
  );
}
