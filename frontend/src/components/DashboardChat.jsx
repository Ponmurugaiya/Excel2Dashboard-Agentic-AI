import React, { useEffect, useRef, useState } from "react";
import { MessageCircle, X, Send, Loader2, Bot, User, Sparkles } from "lucide-react";
import { chatAPI } from "../lib/api";

const SUGGESTIONS = [
  "What are the key takeaways from this data?",
  "Add an insight card about the top product",
  "Which segment should we focus on first?",
  "Change the Overview tab title to 'Executive Summary'",
  "What does the retention data tell us?",
];

/**
 * Floating chat button + slide-up chat panel.
 * Can answer questions about the data or modify the dashboard spec.
 */
export default function DashboardChat({ sessionId, onSpecUpdate }) {
  const [open, setOpen]       = useState(false);
  const [messages, setMessages] = useState([
    {
      role: "assistant",
      text: "Hi! I can answer questions about this data or help you modify the dashboard. What would you like to know?",
    },
  ]);
  const [input, setInput]     = useState("");
  const [loading, setLoading] = useState(false);
  const bottomRef             = useRef(null);
  const inputRef              = useRef(null);

  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [messages]);

  useEffect(() => {
    if (open) setTimeout(() => inputRef.current?.focus(), 100);
  }, [open]);

  const send = async (text) => {
    const msg = text || input.trim();
    if (!msg || loading) return;

    setInput("");
    setMessages((prev) => [...prev, { role: "user", text: msg }]);
    setLoading(true);

    try {
      const res = await chatAPI.send(sessionId, msg);
      const { reply, updated_spec, action } = res.data;

      setMessages((prev) => [
        ...prev,
        {
          role: "assistant",
          text: reply,
          action,
          updated: action === "updated_dashboard",
        },
      ]);

      if (updated_spec) {
        onSpecUpdate(updated_spec);
      }
    } catch (err) {
      const status = err.response?.status;
      const detail = err.response?.data?.detail || err.message;

      let errorText = "Something went wrong. Please try again.";
      if (status === 429) {
        errorText = "The AI provider is rate-limited right now. Wait a moment and try again.";
      } else if (status === 404) {
        errorText = "Session not found. Please re-upload your file to start a new analysis.";
      } else if (detail) {
        errorText = detail;
      }

      setMessages((prev) => [
        ...prev,
        { role: "assistant", text: errorText, error: true },
      ]);
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
          className="fixed bottom-6 right-6 z-40 bg-blue-600 hover:bg-blue-700 text-white
                     rounded-full p-4 shadow-lg transition-all hover:scale-105"
          title="Chat with your dashboard"
        >
          <MessageCircle className="w-5 h-5" />
        </button>
      )}

      {/* Chat panel */}
      {open && (
        <div className="fixed bottom-0 right-0 z-40 w-full sm:w-96 sm:bottom-6 sm:right-6
                        bg-white rounded-t-2xl sm:rounded-2xl shadow-2xl border border-gray-200
                        flex flex-col overflow-hidden"
             style={{ maxHeight: "70vh", minHeight: "420px" }}
        >
          {/* Header */}
          <div className="flex items-center justify-between px-4 py-3
                          bg-blue-600 text-white rounded-t-2xl flex-shrink-0">
            <div className="flex items-center gap-2">
              <Sparkles className="w-4 h-4" />
              <span className="font-semibold text-sm">Dashboard Assistant</span>
            </div>
            <button
              onClick={() => setOpen(false)}
              className="text-blue-200 hover:text-white transition-colors"
            >
              <X className="w-4 h-4" />
            </button>
          </div>

          {/* Messages */}
          <div className="flex-1 overflow-y-auto p-4 space-y-3">
            {messages.map((msg, i) => (
              <MessageBubble key={i} msg={msg} />
            ))}
            {loading && (
              <div className="flex items-center gap-2 text-gray-400">
                <Bot className="w-4 h-4 flex-shrink-0" />
                <div className="flex gap-1">
                  <span className="w-1.5 h-1.5 bg-gray-400 rounded-full animate-bounce" style={{animationDelay:"0ms"}} />
                  <span className="w-1.5 h-1.5 bg-gray-400 rounded-full animate-bounce" style={{animationDelay:"150ms"}} />
                  <span className="w-1.5 h-1.5 bg-gray-400 rounded-full animate-bounce" style={{animationDelay:"300ms"}} />
                </div>
              </div>
            )}
            <div ref={bottomRef} />
          </div>

          {/* Suggestions (only at start) */}
          {messages.length === 1 && (
            <div className="px-4 pb-2 flex flex-wrap gap-1.5 flex-shrink-0">
              {SUGGESTIONS.slice(0, 3).map((s, i) => (
                <button
                  key={i}
                  onClick={() => send(s)}
                  disabled={loading}
                  className="text-xs bg-blue-50 hover:bg-blue-100 text-blue-700 border
                             border-blue-200 rounded-full px-3 py-1 transition-colors disabled:opacity-50"
                >
                  {s}
                </button>
              ))}
            </div>
          )}

          {/* Input */}
          <div className="border-t border-gray-100 px-3 py-3 flex gap-2 flex-shrink-0">
            <input
              ref={inputRef}
              value={input}
              onChange={(e) => setInput(e.target.value)}
              onKeyDown={handleKey}
              placeholder="Ask a question or request a change..."
              disabled={loading}
              className="flex-1 text-sm border border-gray-200 rounded-xl px-3 py-2
                         focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-transparent
                         disabled:opacity-60"
            />
            <button
              onClick={() => send()}
              disabled={!input.trim() || loading}
              className="bg-blue-600 hover:bg-blue-700 text-white p-2.5 rounded-xl
                         disabled:opacity-50 transition-colors"
            >
              {loading ? (
                <Loader2 className="w-4 h-4 animate-spin" />
              ) : (
                <Send className="w-4 h-4" />
              )}
            </button>
          </div>
        </div>
      )}
    </>
  );
}

function MessageBubble({ msg }) {
  const isUser = msg.role === "user";

  return (
    <div className={`flex gap-2 ${isUser ? "flex-row-reverse" : ""}`}>
      <div className={`flex-shrink-0 w-6 h-6 rounded-full flex items-center justify-center
                       ${isUser ? "bg-blue-600" : "bg-gray-100"}`}>
        {isUser
          ? <User className="w-3 h-3 text-white" />
          : <Bot className="w-3 h-3 text-gray-600" />
        }
      </div>
      <div className={`max-w-[80%] rounded-2xl px-3 py-2 text-sm leading-relaxed
        ${isUser
          ? "bg-blue-600 text-white rounded-tr-sm"
          : msg.error
            ? "bg-red-50 text-red-700 border border-red-200"
            : "bg-gray-100 text-gray-800 rounded-tl-sm"
        }`}>
        {msg.text}
        {msg.updated && (
          <p className="text-xs mt-1.5 text-blue-200 flex items-center gap-1">
            <Sparkles className="w-3 h-3" />
            Dashboard updated
          </p>
        )}
      </div>
    </div>
  );
}
