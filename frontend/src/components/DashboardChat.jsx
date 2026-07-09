import React, { useEffect, useRef, useState } from "react";
import {
  MessageCircle, X, Send, Loader2,
  Bot, User, Sparkles, ChevronDown,
} from "lucide-react";
import { chatAPI } from "../lib/api";

const SUGGESTIONS = [
  "What are the key takeaways?",
  "Which segment should we focus on?",
  "Add an insight about the top product",
  "Change the Overview tab title",
  "What does the retention data tell us?",
];

export default function DashboardChat({ sessionId, onSpecUpdate }) {
  const [open, setOpen]       = useState(false);
  const [unread, setUnread]   = useState(0);
  const [messages, setMessages] = useState([
    {
      role: "assistant",
      text: "Hi! I can answer questions about this data or help you modify the dashboard. What would you like to know?",
    },
  ]);
  const [input, setInput]   = useState("");
  const [loading, setLoading] = useState(false);
  const bottomRef  = useRef(null);
  const inputRef   = useRef(null);

  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [messages]);

  useEffect(() => {
    if (open) {
      setUnread(0);
      setTimeout(() => inputRef.current?.focus(), 100);
    }
  }, [open]);

  const addMessage = (msg) => {
    setMessages((prev) => [...prev, msg]);
    if (!open) setUnread((n) => n + 1);
  };

  const send = async (text) => {
    const msg = (text || input).trim();
    if (!msg || loading) return;
    setInput("");
    addMessage({ role: "user", text: msg });
    setLoading(true);

    try {
      const res = await chatAPI.send(sessionId, msg);
      const { reply, updated_spec, action } = res.data;
      addMessage({
        role: "assistant",
        text: reply,
        action,
        updated: action === "updated_dashboard",
      });
      if (updated_spec) onSpecUpdate(updated_spec);
    } catch (err) {
      const status = err.response?.status;
      const detail = err.response?.data?.detail || err.message;
      let errorText = "Something went wrong. Please try again.";
      if (status === 429)      errorText = "Rate-limited. Wait a moment and try again.";
      else if (status === 404) errorText = "Session not found. Re-upload your file to start a new analysis.";
      else if (detail)         errorText = detail;
      addMessage({ role: "assistant", text: errorText, error: true });
    } finally {
      setLoading(false);
    }
  };

  const handleKey = (e) => {
    if (e.key === "Enter" && !e.shiftKey) {
      e.preventDefault();
      send();
    }
  };

  return (
    <>
      {/* Floating button */}
      {!open && (
        <button
          onClick={() => setOpen(true)}
          className="
            fixed bottom-6 right-6 z-40
            w-14 h-14 rounded-full shadow-glow
            bg-gradient-brand text-white
            flex items-center justify-center
            hover:scale-105 transition-transform duration-200
          "
          title="Chat with your dashboard"
        >
          <MessageCircle className="w-6 h-6" />
          {unread > 0 && (
            <span className="
              absolute -top-1 -right-1 w-5 h-5 rounded-full
              bg-red-500 text-white text-xs font-bold
              flex items-center justify-center
            ">
              {unread}
            </span>
          )}
        </button>
      )}

      {/* Chat panel */}
      {open && (
        <div
          className="
            fixed bottom-0 right-0 z-40
            w-full sm:w-[400px] sm:bottom-6 sm:right-6
            bg-white
            rounded-t-3xl sm:rounded-3xl
            shadow-card-lg border border-slate-200
            flex flex-col overflow-hidden
            animate-slide-up
          "
          style={{ maxHeight: "72vh", minHeight: "440px" }}
        >
          {/* Header */}
          <div className="flex items-center justify-between px-5 py-4
                          bg-gradient-brand text-white rounded-t-3xl flex-shrink-0">
            <div className="flex items-center gap-2.5">
              <div className="w-8 h-8 rounded-xl bg-white/20 flex items-center justify-center">
                <Sparkles className="w-4 h-4" />
              </div>
              <div>
                <p className="font-bold text-sm">Dashboard Assistant</p>
              </div>
            </div>
            <button
              onClick={() => setOpen(false)}
              className="text-white/70 hover:text-white transition-colors"
            >
              <ChevronDown className="w-5 h-5" />
            </button>
          </div>

          {/* Messages */}
          <div className="flex-1 overflow-y-auto p-4 space-y-3">
            {messages.map((msg, i) => (
              <MessageBubble key={i} msg={msg} />
            ))}
            {loading && <TypingIndicator />}
            <div ref={bottomRef} />
          </div>

          {/* Quick suggestions (only at start) */}
          {messages.length === 1 && (
            <div className="px-4 pb-3 flex flex-wrap gap-1.5 flex-shrink-0">
              {SUGGESTIONS.slice(0, 3).map((s, i) => (
                <button
                  key={i}
                  onClick={() => send(s)}
                  disabled={loading}
                  className="
                    text-xs bg-brand-50
                    hover:bg-brand-100:bg-brand-900/50
                    text-brand-700
                    border border-brand-200
                    rounded-full px-3 py-1.5 transition-colors
                    disabled:opacity-50
                  "
                >
                  {s}
                </button>
              ))}
            </div>
          )}

          {/* Input */}
          <div className="border-t border-slate-100 px-4 py-3
                          flex gap-2 flex-shrink-0 bg-white">
            <textarea
              ref={inputRef}
              value={input}
              onChange={(e) => setInput(e.target.value)}
              onKeyDown={handleKey}
              placeholder="Ask a question or request a change…"
              disabled={loading}
              rows={1}
              className="
                flex-1 text-sm border border-slate-200
                bg-slate-50
                text-slate-900
                placeholder:text-slate-400:text-slate-500
                rounded-2xl px-3.5 py-2.5 resize-none
                focus:outline-none focus:ring-2 focus:ring-brand-500 focus:border-transparent
                disabled:opacity-60 transition-all
              "
              style={{ maxHeight: "120px" }}
            />
            <button
              onClick={() => send()}
              disabled={!input.trim() || loading}
              className="
                w-10 h-10 rounded-2xl self-end
                bg-gradient-brand text-white
                flex items-center justify-center flex-shrink-0
                disabled:opacity-40 transition-opacity hover:opacity-90
              "
            >
              {loading
                ? <Loader2 className="w-4 h-4 animate-spin" />
                : <Send    className="w-4 h-4" />
              }
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
  return (
    <div className={`flex gap-2.5 ${isUser ? "flex-row-reverse" : ""}`}>
      {/* Avatar */}
      <div className={`
        flex-shrink-0 w-7 h-7 rounded-full flex items-center justify-center
        ${isUser
          ? "bg-gradient-brand"
          : "bg-slate-100"}
      `}>
        {isUser
          ? <User className="w-3.5 h-3.5 text-white" />
          : <Bot  className="w-3.5 h-3.5 text-slate-500" />
        }
      </div>

      {/* Bubble */}
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
            <Sparkles className="w-3 h-3" />
            Dashboard updated
          </p>
        )}
      </div>
    </div>
  );
}

/* ── Simple markdown renderer (bold, code) ───────────────────────────────── */

function SimpleMarkdown({ text, isUser }) {
  // Split on **bold** and `code`
  const parts = text.split(/(\*\*[^*]+\*\*|`[^`]+`)/g);
  return (
    <>
      {parts.map((part, i) => {
        if (part.startsWith("**") && part.endsWith("**")) {
          return <strong key={i}>{part.slice(2, -2)}</strong>;
        }
        if (part.startsWith("`") && part.endsWith("`")) {
          return (
            <code key={i} className={`px-1 py-0.5 rounded text-xs font-mono
              ${isUser
                ? "bg-white/20"
                : "bg-slate-200 text-slate-700"}`}>
              {part.slice(1, -1)}
            </code>
          );
        }
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
          <span
            key={delay}
            className="w-2 h-2 bg-slate-400 rounded-full"
            style={{ animation: `bounceDot 1.4s ease-in-out ${delay}ms infinite` }}
          />
        ))}
      </div>
    </div>
  );
}
