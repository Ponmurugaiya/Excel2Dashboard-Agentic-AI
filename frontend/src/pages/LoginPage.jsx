import React, { useState } from "react";
import { BarChart2, Loader2, AlertCircle } from "lucide-react";
import { authAPI } from "../lib/api";
import { setUser } from "../lib/auth";

/**
 * Login / Register screen.
 * On success: calls onAuth() so App switches to UploadPage.
 */
export default function LoginPage({ onAuth, onSkip }) {
  const [mode, setMode]       = useState("login"); // "login" | "register"
  const [email, setEmail]     = useState("");
  const [password, setPass]   = useState("");
  const [loading, setLoading] = useState(false);
  const [error, setError]     = useState(null);

  const submit = async (e) => {
    e.preventDefault();
    setError(null);
    setLoading(true);
    try {
      const fn = mode === "login" ? authAPI.login : authAPI.register;
      const res = await fn(email, password);
      setUser(res.data.token, res.data.user_id);
      onAuth();
    } catch (err) {
      setError(err.response?.data?.detail || err.message || "Something went wrong.");
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="min-h-screen flex flex-col items-center justify-center bg-gray-50 px-4">
      {/* Brand */}
      <div className="flex items-center gap-3 mb-8">
        <div className="bg-blue-600 p-2.5 rounded-xl">
          <BarChart2 className="w-6 h-6 text-white" />
        </div>
        <div>
          <h1 className="text-xl font-bold text-gray-900 leading-tight">AI BI Dashboard</h1>
          <p className="text-xs text-gray-500">Multi-Agent Analytics Platform</p>
        </div>
      </div>

      {/* Card */}
      <div className="bg-white rounded-2xl shadow-sm border border-gray-200 w-full max-w-sm p-8">
        <h2 className="text-lg font-semibold text-gray-800 mb-6">
          {mode === "login" ? "Sign in to your account" : "Create an account"}
        </h2>

        <form onSubmit={submit} className="space-y-4">
          <div>
            <label className="block text-sm font-medium text-gray-700 mb-1">Email</label>
            <input
              type="email"
              required
              value={email}
              onChange={(e) => setEmail(e.target.value)}
              className="w-full border border-gray-300 rounded-lg px-3 py-2 text-sm
                         focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-transparent"
              placeholder="you@example.com"
            />
          </div>

          <div>
            <label className="block text-sm font-medium text-gray-700 mb-1">Password</label>
            <input
              type="password"
              required
              value={password}
              onChange={(e) => setPass(e.target.value)}
              className="w-full border border-gray-300 rounded-lg px-3 py-2 text-sm
                         focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-transparent"
              placeholder={mode === "register" ? "At least 6 characters" : "••••••••"}
            />
          </div>

          {error && (
            <div className="flex items-start gap-2 text-red-600 bg-red-50 border border-red-200
                            rounded-lg px-3 py-2 text-sm">
              <AlertCircle className="w-4 h-4 mt-0.5 flex-shrink-0" />
              {error}
            </div>
          )}

          <button
            type="submit"
            disabled={loading}
            className="w-full bg-blue-600 hover:bg-blue-700 text-white font-medium py-2.5
                       rounded-lg text-sm transition-colors disabled:opacity-60 flex items-center justify-center gap-2"
          >
            {loading && <Loader2 className="w-4 h-4 animate-spin" />}
            {mode === "login" ? "Sign In" : "Create Account"}
          </button>
        </form>

        <p className="mt-5 text-center text-sm text-gray-500">
          {mode === "login" ? (
            <>No account?{" "}
              <button onClick={() => setMode("register")} className="text-blue-600 hover:underline font-medium">
                Sign up
              </button>
            </>
          ) : (
            <>Already have an account?{" "}
              <button onClick={() => setMode("login")} className="text-blue-600 hover:underline font-medium">
                Sign in
              </button>
            </>
          )}
        </p>

        {onSkip && (
          <p className="mt-3 text-center">
            <button onClick={onSkip} className="text-xs text-gray-400 hover:text-gray-600 underline">
              Continue without an account
            </button>
          </p>
        )}
      </div>
    </div>
  );
}
