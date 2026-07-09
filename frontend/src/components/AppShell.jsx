import React, { useState } from "react";
import {
  BarChart3, Upload, LayoutDashboard,
  LogOut, User, ChevronRight,
} from "lucide-react";
import { isLoggedIn } from "../lib/auth";

/**
 * Persistent application shell — sidebar + topbar + content slot.
 * Collapses to icon-only on narrow viewports.
 *
 * Props:
 *   screen     – current active screen ("upload" | "analysis" | "dashboard")
 *   onNavigate – fn(screen) called when nav item clicked
 *   onLogout   – fn()
 *   children   – page content
 */
export default function AppShell({ screen, onNavigate, onLogout, children }) {
  const [collapsed, setCollapsed] = useState(false);

  const navItems = [
    {
      id:      "upload",
      label:   "New Analysis",
      icon:    Upload,
      enabled: true,
    },
    {
      id:      "dashboard",
      label:   "Dashboard",
      icon:    LayoutDashboard,
      enabled: screen === "dashboard" || screen === "analysis",
    },
  ];

  return (
    <div className="flex h-screen overflow-hidden bg-surface-50">

      {/* ── Sidebar ──────────────────────────────────────────────────────── */}
      <aside
        className={`
          flex flex-col flex-shrink-0 h-full
          border-r border-slate-200 bg-white
          transition-all duration-300 z-30
          ${collapsed ? "w-16" : "w-60"}
        `}
      >
        {/* Logo */}
        <div className={`flex items-center gap-3 px-4 py-5 ${collapsed ? "justify-center" : ""}`}>
          <div className="w-8 h-8 rounded-xl bg-gradient-brand flex items-center justify-center flex-shrink-0">
            <BarChart3 className="w-4 h-4 text-white" />
          </div>
          {!collapsed && (
            <div className="min-w-0">
              <p className="font-bold text-slate-900 text-sm leading-tight">BI Dashboard</p>
              <p className="text-xs text-slate-400">AI-Powered Analytics</p>
            </div>
          )}
        </div>

        {/* Collapse toggle */}
        <button
          onClick={() => setCollapsed(!collapsed)}
          className={`
            mx-3 mb-2 flex items-center justify-center p-1.5 rounded-lg
            text-slate-400 hover:text-slate-600 hover:bg-slate-100
            transition-all text-xs gap-1
          `}
        >
          <ChevronRight
            className={`w-3.5 h-3.5 transition-transform duration-300 ${collapsed ? "" : "rotate-180"}`}
          />
          {!collapsed && <span>Collapse</span>}
        </button>

        {/* Nav items */}
        <nav className="flex-1 px-3 space-y-1">
          {!collapsed && (
            <p className="section-heading px-2 pt-2 pb-1">Navigation</p>
          )}
          {navItems.map(({ id, label, icon: Icon, enabled }) => (
            <NavItem
              key={id}
              label={label}
              Icon={Icon}
              active={screen === id}
              enabled={enabled}
              collapsed={collapsed}
              onClick={() => enabled && onNavigate(id)}
            />
          ))}
        </nav>

        {/* Bottom controls */}
        <div className="border-t border-slate-200 p-3 space-y-1">
          {isLoggedIn() ? (
            <button
              onClick={onLogout}
              className={`
                w-full flex items-center gap-3 px-3 py-2.5 rounded-xl text-sm
                text-slate-500 hover:text-red-600 hover:bg-red-50
                transition-all ${collapsed ? "justify-center" : ""}
              `}
              title="Sign out"
            >
              <LogOut className="w-4 h-4 flex-shrink-0" />
              {!collapsed && "Sign Out"}
            </button>
          ) : (
            <button
              onClick={() => onNavigate("login")}
              className={`
                w-full flex items-center gap-3 px-3 py-2.5 rounded-xl text-sm
                text-slate-500 hover:text-brand-600 hover:bg-brand-50
                transition-all ${collapsed ? "justify-center" : ""}
              `}
              title="Sign in"
            >
              <User className="w-4 h-4 flex-shrink-0" />
              {!collapsed && "Sign In"}
            </button>
          )}
        </div>
      </aside>

      {/* ── Main area ────────────────────────────────────────────────────── */}
      <main className="flex-1 flex flex-col min-w-0 overflow-hidden">
        {/* Topbar */}
        <header className="
          flex-shrink-0 h-14 bg-white border-b border-slate-200
          flex items-center px-6
        ">
          <Breadcrumb screen={screen} />
        </header>

        {/* Page content */}
        <div className="flex-1 overflow-auto">
          {children}
        </div>
      </main>
    </div>
  );
}

/* ── Nav Item ─────────────────────────────────────────────────────────────── */

function NavItem({ label, Icon, active, enabled, collapsed, onClick }) {
  return (
    <button
      onClick={onClick}
      disabled={!enabled}
      title={collapsed ? label : undefined}
      className={`
        w-full flex items-center gap-3 px-3 py-2.5 rounded-xl text-sm font-medium
        transition-all duration-150
        ${collapsed ? "justify-center" : ""}
        ${active
          ? "bg-brand-50 text-brand-700"
          : enabled
            ? "text-slate-600 hover:bg-slate-100 hover:text-slate-900"
            : "text-slate-300 cursor-not-allowed"
        }
      `}
    >
      <Icon className={`w-4 h-4 flex-shrink-0 ${active ? "text-brand-600" : ""}`} />
      {!collapsed && label}
      {active && !collapsed && (
        <span className="ml-auto w-1.5 h-1.5 rounded-full bg-brand-600" />
      )}
    </button>
  );
}

/* ── Breadcrumb ───────────────────────────────────────────────────────────── */

const SCREEN_LABELS = {
  login:     "Sign In",
  upload:    "New Analysis",
  analysis:  "Running Analysis",
  dashboard: "Dashboard",
};

function Breadcrumb({ screen }) {
  return (
    <div className="flex items-center gap-2 text-sm">
      <span className="text-slate-400">Home</span>
      <ChevronRight className="w-3.5 h-3.5 text-slate-300" />
      <span className="font-medium text-slate-700">
        {SCREEN_LABELS[screen] || screen}
      </span>
    </div>
  );
}
