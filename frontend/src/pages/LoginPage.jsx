import React, { useState } from "react";
import {
  BarChart3, Loader2, AlertCircle, Eye, EyeOff,
  TrendingUp, Brain, Zap,
} from "lucide-react";
import { authAPI } from "../lib/api";
import { setUser } from "../lib/auth";
import { useToast } from "../components/Toast";

const FEATURES = [
  {
    icon:  Brain,
    title: "Multi-Agent AI",
    desc:  "Specialised agents clean, analyse, and design your dashboard autonomously.",
  },
  {
    icon:  TrendingUp,
    title: "Instant Insights",
    desc:  "From raw CSV to production-ready charts in seconds.",
  },
  {
    icon:  Zap,
    title: "Autonomous or Guided",
    desc:  "Let AI decide everything, or collaborate at every decision point.",
  },
];

export default function LoginPage({ onAuth, onSkip }) {
  const [mode, setMode]         = useState("login");
  const [email, setEmail]       = useState("");
  const [password, setPass]     = useState("");
  const [showPass, setShowPass] = useState(false);
  const [loading, setLoading]   = useState(false);
  const [error, setError]       = useState(null);
  const toast = useToast();

  const submit = async (e) => {
    e.preventDefault();
    setError(null);
    setLoading(true);
    try {
      const fn  = mode === "login" ? authAPI.login : authAPI.register;
      const res = await fn(email, password);
      setUser(res.data.token, res.data.user_id);
      toast.success(
        mode === "login" ? "Welcome back!" : "Account created",
        "You are now signed in."
      );
      onAuth();
    } catch (err) {
      const msg = err.response?.data?.detail || err.message || "Something went wrong.";
      setError(msg);
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="min-h-screen flex">

      {/* ── Left panel — branding ──────────────────────────────────────── */}
      <div className="hidden lg:flex lg:w-[55%] bg-gradient-brand relative overflow-hidden flex-col justify-between p-12">
        <div className="absolute inset-0 bg-gradient-mesh opacity-40 pointer-events-none" />

        {/* Logo */}
        <div className="relative z-10 flex items-center gap-3">
          <div className="w-10 h-10 rounded-2xl bg-white/20 backdrop-blur-sm flex items-center justify-center">
            <BarChart3 className="w-5 h-5 text-white" />
          </div>
          <div>
            <p className="font-bold text-white text-base leading-tight">AI BI Dashboard</p>
            <p className="text-white/60 text-xs">Multi-Agent Analytics Platform</p>
          </div>
        </div>

        {/* Headline */}
        <div className="relative z-10">
          <h1 className="text-4xl font-extrabold text-white leading-tight mb-4">
            Turn raw data into<br />
            <span className="text-white/80">production dashboards</span><br />
            in seconds.
          </h1>
          <p className="text-white/70 text-base max-w-md leading-relaxed">
            Upload any spreadsheet. Our AI agents clean, analyse, and design a
            full interactive dashboard — no SQL, no code.
          </p>

          <div className="mt-10 space-y-5">
            {FEATURES.map(({ icon: Icon, title, desc }) => (
              <div key={title} className="flex items-start gap-4">
                <div className="w-9 h-9 rounded-xl bg-white/15 flex items-center justify-center flex-shrink-0">
                  <Icon className="w-4 h-4 text-white" />
                </div>
                <div>
                  <p className="text-white font-semibold text-sm">{title}</p>
                  <p className="text-white/60 text-xs mt-0.5 leading-relaxed">{desc}</p>
                </div>
              </div>
            ))}
          </div>
        </div>

        <p className="relative z-10 text-white/40 text-xs">
          © {new Date().getFullYear()} AI BI Dashboard Builder
        </p>
      </div>

      {/* ── Right panel — form ─────────────────────────────────────────── */}
      <div className="flex-1 flex flex-col bg-white">
        {/* Mobile logo */}
        <div className="flex items-center gap-2 px-8 pt-8 lg:hidden">
          <div className="w-8 h-8 rounded-xl bg-gradient-brand flex items-center justify-center">
            <BarChart3 className="w-4 h-4 text-white" />
          </div>
          <span className="font-bold text-slate-900 text-sm">AI BI Dashboard</span>
        </div>

        {/* Form */}
        <div className="flex-1 flex items-center justify-center px-8 py-10">
          <div className="w-full max-w-sm animate-fade-in">
            <h2 className="text-2xl font-extrabold text-slate-900 mb-1">
              {mode === "login" ? "Welcome back" : "Create account"}
            </h2>
            <p className="text-slate-500 text-sm mb-8">
              {mode === "login"
                ? "Sign in to access your dashboards."
                : "Get started — it's free."}
            </p>

            <form onSubmit={submit} className="space-y-4">
              {/* Email */}
              <div>
                <label className="block text-sm font-medium text-slate-700 mb-1.5">
                  Email address
                </label>
                <input
                  type="email"
                  required
                  value={email}
                  onChange={(e) => setEmail(e.target.value)}
                  className="input"
                  placeholder="you@example.com"
                  autoComplete="email"
                />
              </div>

              {/* Password */}
              <div>
                <label className="block text-sm font-medium text-slate-700 mb-1.5">
                  Password
                </label>
                <div className="relative">
                  <input
                    type={showPass ? "text" : "password"}
                    required
                    value={password}
                    onChange={(e) => setPass(e.target.value)}
                    className="input pr-10"
                    placeholder={mode === "register" ? "At least 6 characters" : "••••••••"}
                    autoComplete={mode === "login" ? "current-password" : "new-password"}
                  />
                  <button
                    type="button"
                    onClick={() => setShowPass(!showPass)}
                    className="absolute right-3 top-1/2 -translate-y-1/2 text-slate-400
                               hover:text-slate-600 transition-colors"
                  >
                    {showPass ? <EyeOff className="w-4 h-4" /> : <Eye className="w-4 h-4" />}
                  </button>
                </div>
              </div>

              {/* Error */}
              {error && (
                <div className="flex items-start gap-2.5 bg-red-50 border border-red-200
                                rounded-xl px-4 py-3 animate-fade-in">
                  <AlertCircle className="w-4 h-4 text-red-500 mt-0.5 flex-shrink-0" />
                  <p className="text-sm text-red-700">{error}</p>
                </div>
              )}

              {/* Submit */}
              <button
                type="submit"
                disabled={loading}
                className="btn-primary w-full justify-center py-3 text-base mt-2"
              >
                {loading && <Loader2 className="w-4 h-4 animate-spin" />}
                {mode === "login" ? "Sign In" : "Create Account"}
              </button>
            </form>

            {/* Switch mode */}
            <p className="mt-6 text-center text-sm text-slate-500">
              {mode === "login" ? (
                <>
                  Don&apos;t have an account?{" "}
                  <button
                    onClick={() => { setMode("register"); setError(null); }}
                    className="text-brand-600 font-semibold hover:underline"
                  >
                    Sign up
                  </button>
                </>
              ) : (
                <>
                  Already have an account?{" "}
                  <button
                    onClick={() => { setMode("login"); setError(null); }}
                    className="text-brand-600 font-semibold hover:underline"
                  >
                    Sign in
                  </button>
                </>
              )}
            </p>

            {/* Skip */}
            {onSkip && (
              <div className="mt-4 pt-4 border-t border-slate-100 text-center">
                <button
                  onClick={onSkip}
                  className="text-xs text-slate-400 hover:text-slate-600
                             transition-colors underline underline-offset-2"
                >
                  Continue without an account
                </button>
              </div>
            )}
          </div>
        </div>
      </div>
    </div>
  );
}
