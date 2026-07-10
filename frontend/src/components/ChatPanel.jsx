/**
 * ChatPanel — unified chat for both analysis and dashboard screens.
 *
 * mode="hint"      — shown during analysis; sends hints to /analyse/{id}/hint
 * mode="dashboard" — shown after analysis; full Q&A + spec editing via /chat/{id}
 *
 * No hardcoded suggestion chips — user types freely.
 */

import React, { useEffect, useRef, useState } from "react";
import {
  Send, Loader2, Bot, User, Sparkles,
  ChevronDown, Lightbulb, Clock, CheckCircle2,
  LayoutDashboard, MessageSquareDot,
} from "lucide-react";
import { chatAPI, hintAPI } from "../lib/api";
import { useToast } from "./Toast";

/* ── Component ───────────────────────────────────────────────────────────── */

export default function ChatPanel({
  mode = "dashboard",   // "hint" | "dashboard"
  sessionId,
  onSpecUpdate,
}) {
  const [open, setOpen]       = useState(false);
  const [unread, setUnread]   = useState(0);
  const [input, setInput]     = useState("");
  const [loading, setLoading] = useState(false);
  const [messages, setMessages] = useState(() => [
    {
      role: "assistant",
      text: mode === "hint"
        ? "The agents are building your dashboard. Send me any preferences or focus areas — I'll pass them to the analysis plan and layout."
        : "Ask me anything about this data, or tell me how you'd like to customise the dashboard — rename a tab, add an insight, change a chart.",
    },
  ]);

  const bottomRef = useRef(null);
  const inputRef  = useRef(null);
  useToast(); // keep provider alive even if unused here

  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [messages]);

  useEffect(() => {
    if (open) {
      setUnread(0);
      setTimeout(() => inputRef.current?.focus(), 120);
    }
  }, [open]);

  const addMessage = (msg) => {
    setMessages((prev) => [...prev, msg]);
    if (!open) setUnread((n) => n + 1);
  };

  /* ── Send ───────────────────────────────────────────────────────────────── */

  const send = async (text) => {
    const msg = (text ?? input).trim();
    if (!msg || loading || !sessionId) return;
    setInput("");
    addMessage({ role: "user", text: msg });
    setLoading(true);
    try {
      mode === "hint" ? await sendHint(msg) : await sendChat(msg);
    } finally {
      setLoading(false);
    }
  };

  const sendHint = async (text) => {
    try {
      const res = await hintAPI.send(sessionId, text);
      const { pipeline_status, hint_count } = res.data;
      const label =
        pipeline_status === "designing" ? "being applied by the Architect now" :
        pipeline_status === "done"      ? "noted — use dashboard chat below to refine further" :
        ["analysing", "insight"].includes(pipeline_status)
                                        ? "queued — will shape the dashboard layout" :
                                          "queued — will shape the analysis plan";
      addMessage({ role: "assistant", text: `Received (#${hint_count}) — ${label}.`, kind: "hint_ack" });
    } catch (err) {
      const detail = err.response?.data?.detail || err.message;
      addMessage({
        role: "assistant",
        text: err.response?.status === 404
          ? "Session not found. Please start a new analysis."
          : detail || "Failed to send hint.",
        error: true,
      });
    }
  };

  const sendChat = async (text) => {
    try {
      const res = await chatAPI.send(sessionId, text);
      const { reply, updated_spec, action } = res.data;
      addMessage({ role: "assistant", text: reply, action, updated: action === "updated_dashboard" });
      if (updated_spec && onSpecUpdate) onSpecUpdate(updated_spec);
    } catch (err) {
      const status = err.response?.status;
      const detail = err.response?.data?.detail || err.message;
      addMessage({
        role: "assistant",
        text: status === 429 ? "Rate-limited — wait a moment and try again."
            : status === 404 ? "Session not found. Re-upload your file to start a new analysis."
            : detail || "Something went wrong.",
        error: true,
      });
    }
  };

  const handleKey = (e) => {
    if (e.key === "Enter" && !e.shiftKey) { e.preventDefault(); send(); }
  };

  /* ── Render ─────────────────────────────────────────────────────────────── */

  return (
    <>
      {/* ── Floating trigger ─────────────────────────────────────────────── */}
      {!open && (
        <button
          onClick={() => setOpen(true)}
          className="
            fixed bottom-6 right-6 z-40
            flex items-center gap-2.5
            pl-4 pr-5 py-3 rounded-2xl
            bg-gradient-brand text-white
            shadow-glow hover:opacity-90 hover:scale-[1.03]
            transition-all duration-200
          "
          title={mode === "hint" ? "Send a suggestion to the agents" : "Customise your dashboard"}
          aria-label={mode === "hint" ? "Open agent suggestions" : "Open dashboard chat"}
        >
          {/* Icon */}
          <div className="w-8 h-8 rounded-xl bg-white/20 flex items-center justify-center flex-shrink-0">
            {mode === "hint"
              ? <Lightbulb      className="w-4 h-4" />
              : <LayoutDashboard className="w-4 h-4" />
            }
          </div>

          {/* Label */}
          <div className="text-left leading-tight">
            <p className="text-sm font-bold">
              {mode === "hint" ? "Guide the Agents" : "Customise Dashboard"}
            </p>
            <p className="text-xs text-white/75">
              {mode === "hint" ? "Send a focus area or preference" : "Ask, edit, explore"}
            </p>
          </div>

          {/* Unread badge */}
          {unread > 0 && (
            <span className="
              absolute -top-1.5 -right-1.5 w-5 h-5 rounded-full
              bg-red-500 text-white text-xs font-bold
              flex items-center justify-center
            ">
              {unread}
            </span>
          )}
        </button>
      )}

      {/* ── Panel ────────────────────────────────────────────────────────── */}
      {open && (
        <div
          role="dialog"
          aria-label={mode === "hint" ? "Agent suggestion panel" : "Dashboard customisation chat"}
          className="
            fixed bottom-0 right-0 z-40
            w-full sm:w-[420px] sm:bottom-6 sm:right-6
            bg-white rounded-t-3xl sm:rounded-3xl
            shadow-card-lg border border-slate-200
            flex flex-col overflow-hidden animate-slide-up
          "
          style={{ maxHeight: "72vh", minHeight: "460px" }}
        >
          {/* ── Header ───────────────────────────────────────────────────── */}
          <div className="
            flex items-center justify-between px-5 py-4
            bg-gradient-brand text-white rounded-t-3xl flex-shrink-0
          ">
            <div className="flex items-center gap-3">
              <div className="w-9 h-9 rounded-xl bg-white/20 flex items-center justify-center">
                {mode === "hint"
                  ? <Lightbulb       className="w-5 h-5" />
                  : <LayoutDashboard className="w-5 h-5" />
                }
              </div>
              <div>
                <p className="font-bold text-sm leading-tight">
                  {mode === "hint" ? "Guide the Agents" : "Dashboard Assistant"}
                </p>
                <p className="text-xs text-white/70 mt-0.5">
                  {mode === "hint"
                    ? "Steer the analysis in real-time"
                    : "Customise, ask questions, explore insights"
                  }
                </p>
              </div>
            </div>
            <button
              onClick={() => setOpen(false)}
              className="text-white/60 hover:text-white transition-colors p-1"
              aria-label="Close"
            >
              <ChevronDown className="w-5 h-5" />
            </button>
          </div>

          {/* ── Hint info strip ──────────────────────────────────────────── */}
          {mode === "hint" && (
            <div className="flex items-start gap-2.5 px-4 py-2.5 bg-amber-50 border-b border-amber-100">
              <Clock className="w-3.5 h-3.5 text-amber-600 flex-shrink-0 mt-0.5" />
              <p className="text-xs text-amber-700 leading-relaxed">
                Your input shapes task priority and tab layout.
                Data cleaning and code generation are not affected.
              </p>
            </div>
          )}

          {/* ── Dashboard mode capabilities strip ────────────────────────── */}
          {mode === "dashboard" && messages.length === 1 && (
            <div className="flex items-start gap-2.5 px-4 py-2.5 bg-brand-50 border-b border-brand-100">
              <MessageSquareDot className="w-3.5 h-3.5 text-brand-600 flex-shrink-0 mt-0.5" />
              <p className="text-xs text-brand-700 leading-relaxed">
                You can <strong>rename tabs</strong>, <strong>add insight cards</strong>,
                {" "}<strong>remove sections</strong>, ask data questions, or request a chart change.
              </p>
            </div>
          )}

          {/* ── Messages ─────────────────────────────────────────────────── */}
          <div className="flex-1 overflow-y-auto px-4 py-4 space-y-3">
            {messages.map((msg, i) => (
              <MessageBubble key={i} msg={msg} />
            ))}
            {loading && <TypingIndicator />}
            <div ref={bottomRef} />
          </div>

          {/* ── Input ────────────────────────────────────────────────────── */}
          <div className="border-t border-slate-100 px-4 py-3 flex gap-2 flex-shrink-0 bg-white">
            <textarea
              ref={inputRef}
              value={input}
              onChange={(e) => setInput(e.target.value)}
              onKeyDown={handleKey}
              disabled={loading}
              rows={1}
              placeholder={
                mode === "hint"
                  ? "e.g. focus on Q4, highlight the UK market…"
                  : "e.g. rename the Overview tab, add an insight about revenue…"
              }
              className="
                flex-1 text-sm border border-slate-200 bg-slate-50
                text-slate-900 placeholder:text-slate-400
                rounded-2xl px-3.5 py-2.5 resize-none
                focus:outline-none focus:ring-2 focus:ring-brand-500 focus:border-transparent
                disabled:opacity-60 transition-all
              "
              style={{ maxHeight: "120px" }}
              aria-label={mode === "hint" ? "Send a suggestion to the agents" : "Chat with your dashboard"}
            />
            <button
              onClick={() => send()}
              disabled={!input.trim() || loading}
              className="
                w-10 h-10 rounded-2xl self-end
                bg-gradient-brand text-white
                flex items-center justify-center flex-shrink-0
                disabled:opacity-40 hover:opacity-90 transition-opacity
              "
              aria-label="Send"
            >
              {loading ? <Loader2 className="w-4 h-4 animate-spin" /> : <Send className="w-4 h-4" />}
            </button>
          </div>
        </div>
      )}
    </>
  );
}

/* ── Message bubble ──────────────────────────────────────────────────────── */

function MessageBubble({ msg }) {
  const isUser = msg.role === "user";

  if (msg.kind === "hint_ack") {
    return (
      <div className="flex gap-2.5">
        <div className="w-7 h-7 rounded-full bg-amber-100 flex items-center justify-center flex-shrink-0">
          <CheckCircle2 className="w-3.5 h-3.5 text-amber-600" />
        </div>
        <div className="max-w-[82%] rounded-2xl rounded-tl-sm px-4 py-2.5
                        bg-amber-50 border border-amber-200 text-sm text-amber-800 leading-relaxed">
          {msg.text}
        </div>
      </div>
    );
  }

  return (
    <div className={`flex gap-2.5 ${isUser ? "flex-row-reverse" : ""}`}>
      <div className={`
        flex-shrink-0 w-7 h-7 rounded-full flex items-center justify-center
        ${isUser ? "bg-gradient-brand" : "bg-slate-100"}
      `}>
        {isUser
          ? <User className="w-3.5 h-3.5 text-white" />
          : <Bot  className="w-3.5 h-3.5 text-slate-500" />
        }
      </div>
      <div className={`
        max-w-[78%] rounded-2xl px-4 py-2.5 text-sm leading-relaxed
        ${isUser
          ? "bg-gradient-brand text-white rounded-tr-sm"
          : msg.error
            ? "bg-red-50 text-red-700 border border-red-200 rounded-tl-sm"
            : "bg-slate-100 text-slate-800 rounded-tl-sm"
        }
      `}>
        <SimpleMarkdown text={msg.text} isUser={isUser} />
        {msg.updated && (
          <p className="text-xs mt-2 text-white/70 flex items-center gap-1">
            <Sparkles className="w-3 h-3" /> Dashboard updated
          </p>
        )}
      </div>
    </div>
  );
}

/* ── Inline markdown ─────────────────────────────────────────────────────── */

function SimpleMarkdown({ text, isUser }) {
  const parts = text.split(/(\*\*[^*]+\*\*|`[^`]+`)/g);
  return (
    <>
      {parts.map((part, i) => {
        if (part.startsWith("**") && part.endsWith("**"))
          return <strong key={i}>{part.slice(2, -2)}</strong>;
        if (part.startsWith("`") && part.endsWith("`"))
          return (
            <code key={i} className={`px-1 py-0.5 rounded text-xs font-mono
              ${isUser ? "bg-white/20" : "bg-slate-200 text-slate-700"}`}>
              {part.slice(1, -1)}
            </code>
          );
        return <span key={i}>{part}</span>;
      })}
    </>
  );
}

/* ── Typing indicator ────────────────────────────────────────────────────── */

function TypingIndicator() {
  return (
    <div className="flex items-center gap-2.5">
      <div className="w-7 h-7 rounded-full bg-slate-100 flex items-center justify-center">
        <Bot className="w-3.5 h-3.5 text-slate-500" />
      </div>
      <div className="bg-slate-100 rounded-2xl rounded-tl-sm px-4 py-3 flex gap-1.5">
        {[0, 150, 300].map((delay) => (
          <span key={delay} className="w-2 h-2 bg-slate-400 rounded-full"
            style={{ animation: `bounceDot 1.4s ease-in-out ${delay}ms infinite` }} />
        ))}
      </div>
    </div>
  );
}
