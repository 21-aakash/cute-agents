import React, { useState, useId } from 'react';
import {
  Eye, EyeOff, ArrowRight, AlertCircle, CheckCircle2,
  KeyRound, Mail, User as UserIcon, Sparkles,
} from 'lucide-react';
import { useAuth } from '../../context/AuthContext';

type AuthMode = 'login' | 'register' | 'forgot_password';

// ── Minimal Input ─────────────────────────────────────────────────────────────

function Field({
  id, label, type = 'text', value, onChange, placeholder, required, suffix,
}: {
  id: string; label: string; type?: string; value: string;
  onChange: (v: string) => void; placeholder?: string; required?: boolean;
  suffix?: React.ReactNode;
}) {
  return (
    <div className="space-y-1.5">
      <label htmlFor={id} className="block text-xs font-medium text-[#374151]">{label}</label>
      <div className="relative">
        <input
          id={id}
          type={type}
          value={value}
          onChange={e => onChange(e.target.value)}
          placeholder={placeholder}
          required={required}
          className="w-full px-3 py-2.5 text-sm rounded-lg border border-[#e5e7eb] bg-white text-[#111827] placeholder:text-[#9ca3af] focus:outline-none focus:border-[#2563eb] focus:ring-2 focus:ring-[#2563eb]/15 transition-all"
          style={{ paddingRight: suffix ? '2.75rem' : undefined }}
        />
        {suffix && (
          <div className="absolute right-3 top-1/2 -translate-y-1/2">{suffix}</div>
        )}
      </div>
    </div>
  );
}

// ── Auth Page ─────────────────────────────────────────────────────────────────

export const AuthPage: React.FC = () => {
  const { login, register, googleAuth, forgotPassword, error, clearError } = useAuth();

  const [mode, setMode] = useState<AuthMode>('login');
  const [email, setEmail] = useState('');
  const [password, setPassword] = useState('');
  const [fullName, setFullName] = useState('');
  const [showPassword, setShowPassword] = useState(false);
  const [submitting, setSubmitting] = useState(false);
  const [localMessage, setLocalMessage] = useState<string | null>(null);
  const [demoToken, setDemoToken] = useState<string | null>(null);

  const emailId = useId();
  const passwordId = useId();
  const fullNameId = useId();

  const hasMinLength    = password.length >= 8;
  const hasNumber       = /\d/.test(password);
  const hasSpecialOrUpper = /[A-Z!@#$%^&*(),.?":{}|<>]/.test(password);
  const strengthScore   = [hasMinLength, hasNumber, hasSpecialOrUpper].filter(Boolean).length;

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    clearError();
    setLocalMessage(null);
    setSubmitting(true);
    try {
      if (mode === 'login') {
        await login(email, password);
      } else if (mode === 'register') {
        if (!hasMinLength) throw new Error('Password must be at least 8 characters.');
        await register(email, password, fullName);
      } else {
        const res = await forgotPassword(email);
        setLocalMessage(res.message);
        if (res.demo_reset_token) setDemoToken(res.demo_reset_token);
      }
    } catch { /* handled by context */ } finally {
      setSubmitting(false);
    }
  };

  const handleDemoSignIn = async () => {
    clearError();
    setSubmitting(true);
    try {
      // Always try login first
      await login('demo@nexusai.dev', 'Password123!');
    } catch (loginErr) {
      const msg = loginErr instanceof Error ? loginErr.message : String(loginErr);
      // Only register if the account genuinely doesn't exist yet
      if (msg.toLowerCase().includes('already') || msg.toLowerCase().includes('exists')) {
        // Account exists but login failed — wrong password / other issue, surface it
        clearError();
        setSubmitting(false);
        return;
      }
      try {
        await register('demo@nexusai.dev', 'Password123!', 'Demo User');
      } catch { /* surface error via context */ }
    } finally {
      setSubmitting(false);
    }
  };

  const handleGoogleSignIn = async () => {
    clearError();
    setSubmitting(true);
    try {
      await googleAuth('jordan.nexus@gmail.com', 'Jordan Lee', '');
    } catch { } finally { setSubmitting(false); }
  };

  const switchMode = (m: AuthMode) => { clearError(); setLocalMessage(null); setMode(m); };

  return (
    <div className="min-h-screen w-full flex" style={{ background: '#f9fafb' }}>
      {/* ── Left panel (brand) ── */}
      <div
        className="hidden lg:flex lg:w-[420px] xl:w-[480px] flex-shrink-0 flex-col justify-between p-12"
        style={{
          background: 'linear-gradient(135deg, #1e40af 0%, #1d4ed8 40%, #2563eb 100%)',
        }}
      >
        <div>
          {/* Logo */}
          <div className="flex items-center gap-3 mb-12">
            <div className="w-10 h-10 rounded-xl bg-white/15 border border-white/20 flex items-center justify-center">
              <Sparkles className="w-5 h-5 text-white" />
            </div>
            <div>
              <div className="text-white font-bold text-lg leading-tight tracking-tight">Nexus AI</div>
              <div className="text-blue-200 text-xs font-medium">Autonomous Intelligence Suite</div>
            </div>
          </div>

          {/* Value props */}
          <div className="space-y-6">
            <h2 className="text-white text-2xl font-bold leading-snug">
              Your personal tech career engine
            </h2>
            <p className="text-blue-100 text-sm leading-relaxed">
              Research agents, career intelligence, and automated outreach — all in one place.
            </p>

            <div className="space-y-4 pt-2">
              {[
                { emoji: '🔬', title: 'Deep Research Studio', desc: 'Multi-stage agent with citation grounding & factual critique.' },
                { emoji: '💼', title: 'Career Agent', desc: 'Job match scoring, resume tailoring, and Gmail follow-up automation.' },
                { emoji: '📋', title: 'Productivity OPS', desc: 'Paste your PRD or ticket — AI breaks it into your week.' },
              ].map(f => (
                <div key={f.title} className="flex items-start gap-3 p-3.5 rounded-xl bg-white/10 border border-white/10">
                  <span className="text-lg leading-none mt-0.5">{f.emoji}</span>
                  <div>
                    <div className="text-white text-xs font-semibold mb-0.5">{f.title}</div>
                    <div className="text-blue-200 text-[11px] leading-relaxed">{f.desc}</div>
                  </div>
                </div>
              ))}
            </div>
          </div>
        </div>

        <div className="text-blue-300 text-[11px]">
          FastAPI · LangGraph · Qdrant · React 18
        </div>
      </div>

      {/* ── Right panel (form) ── */}
      <div className="flex-1 flex items-center justify-center p-6">
        <div className="w-full max-w-[400px]">
          {/* Mobile logo */}
          <div className="lg:hidden flex items-center gap-2 mb-8">
            <div className="w-8 h-8 rounded-lg bg-[#2563eb] flex items-center justify-center">
              <Sparkles className="w-4 h-4 text-white" />
            </div>
            <span className="font-bold text-[#111827]">Nexus AI</span>
          </div>

          {/* Heading */}
          <div className="mb-7">
            <h1 className="text-[22px] font-bold text-[#111827] mb-1">
              {mode === 'login' && 'Welcome back'}
              {mode === 'register' && 'Create account'}
              {mode === 'forgot_password' && 'Reset password'}
            </h1>
            <p className="text-sm text-[#6b7280]">
              {mode === 'login' && 'Sign in to your workspace.'}
              {mode === 'register' && 'Get started for free.'}
              {mode === 'forgot_password' && 'Enter your email to receive reset instructions.'}
            </p>
          </div>

          {/* Error */}
          {error && (
            <div className="mb-4 flex items-start gap-2 text-[#dc2626] text-xs bg-red-50 border border-red-100 rounded-lg px-3 py-2.5">
              <AlertCircle className="w-3.5 h-3.5 mt-0.5 shrink-0" />
              <span>{error}</span>
              <button onClick={clearError} className="ml-auto text-red-400 hover:text-red-600">×</button>
            </div>
          )}

          {/* Success */}
          {localMessage && (
            <div className="mb-4 flex items-start gap-2 text-[#16a34a] text-xs bg-green-50 border border-green-100 rounded-lg px-3 py-2.5">
              <CheckCircle2 className="w-3.5 h-3.5 mt-0.5 shrink-0" />
              <div>
                <span>{localMessage}</span>
                {demoToken && (
                  <div className="mt-1 font-mono text-[10px] text-green-700 bg-green-100/60 rounded px-1.5 py-1 break-all">
                    Token: {demoToken}
                  </div>
                )}
              </div>
            </div>
          )}

          {/* Google */}
          {mode !== 'forgot_password' && (
            <>
              <button
                type="button"
                onClick={handleGoogleSignIn}
                disabled={submitting}
                className="w-full flex items-center justify-center gap-2.5 py-2.5 px-4 rounded-lg border border-[#e5e7eb] bg-white text-[#374151] text-sm font-medium hover:bg-[#f9fafb] transition-all mb-4 disabled:opacity-50"
              >
                <svg className="w-4 h-4" viewBox="0 0 24 24">
                  <path fill="#4285F4" d="M23.745 12.27c0-.7-.06-1.4-.19-2.07H12v4.51h6.6c-.29 1.52-1.14 2.8-2.4 3.66v3.05h3.88c2.27-2.09 3.665-5.17 3.665-9.15z"/>
                  <path fill="#34A853" d="M12 24c3.24 0 5.95-1.08 7.93-2.91l-3.88-3.05c-1.08.72-2.45 1.16-4.05 1.16-3.12 0-5.77-2.1-6.72-4.93H1.24v3.15C3.26 21.36 7.33 24 12 24z"/>
                  <path fill="#FBBC05" d="M5.28 14.27c-.25-.72-.38-1.49-.38-2.27s.13-1.55.38-2.27V6.58H1.24C.45 8.16 0 9.94 0 12s.45 3.84 1.24 5.42l4.04-3.15z"/>
                  <path fill="#EA4335" d="M12 4.75c1.77 0 3.35.61 4.6 1.8l3.42-3.42C17.95 1.19 15.24 0 12 0 7.33 0 3.26 2.64 1.24 6.58l4.04 3.15c.95-2.83 3.6-4.98 6.72-4.98z"/>
                </svg>
                Continue with Google
              </button>

              <div className="relative my-5">
                <div className="absolute inset-0 flex items-center">
                  <div className="w-full border-t border-[#e5e7eb]" />
                </div>
                <div className="relative flex justify-center">
                  <span className="bg-[#f9fafb] px-3 text-[11px] uppercase tracking-wider text-[#9ca3af]">or</span>
                </div>
              </div>
            </>
          )}

          {/* Form */}
          <form onSubmit={handleSubmit} className="space-y-4">
            {mode === 'register' && (
              <Field
                id={fullNameId} label="Full Name"
                value={fullName} onChange={setFullName}
                placeholder="Your name" required
              />
            )}

            <Field
              id={emailId} label="Email" type="email"
              value={email} onChange={setEmail}
              placeholder="you@example.com" required
            />

            {mode !== 'forgot_password' && (
              <div className="space-y-1.5">
                <div className="flex items-center justify-between">
                  <label htmlFor={passwordId} className="text-xs font-medium text-[#374151]">Password</label>
                  {mode === 'login' && (
                    <button type="button" onClick={() => switchMode('forgot_password')}
                      className="text-xs text-[#2563eb] hover:underline">Forgot?</button>
                  )}
                </div>
                <div className="relative">
                  <input
                    id={passwordId}
                    type={showPassword ? 'text' : 'password'}
                    value={password}
                    onChange={e => setPassword(e.target.value)}
                    placeholder="••••••••"
                    required
                    className="w-full px-3 py-2.5 pr-10 text-sm rounded-lg border border-[#e5e7eb] bg-white text-[#111827] placeholder:text-[#9ca3af] focus:outline-none focus:border-[#2563eb] focus:ring-2 focus:ring-[#2563eb]/15 transition-all"
                  />
                  <button type="button" onClick={() => setShowPassword(v => !v)}
                    className="absolute right-3 top-1/2 -translate-y-1/2 text-[#9ca3af] hover:text-[#6b7280]">
                    {showPassword ? <EyeOff className="w-4 h-4" /> : <Eye className="w-4 h-4" />}
                  </button>
                </div>

                {/* Strength meter for register */}
                {mode === 'register' && password.length > 0 && (
                  <div className="flex gap-1 mt-1.5">
                    {[0,1,2].map(i => (
                      <div key={i} className={`h-1 flex-1 rounded-full transition-all ${
                        i < strengthScore
                          ? strengthScore === 1 ? 'bg-red-400' : strengthScore === 2 ? 'bg-amber-400' : 'bg-emerald-400'
                          : 'bg-[#e5e7eb]'
                      }`} />
                    ))}
                  </div>
                )}
              </div>
            )}

            <button
              type="submit"
              disabled={submitting}
              className="w-full flex items-center justify-center gap-2 py-2.5 px-4 rounded-lg bg-[#2563eb] hover:bg-[#1d4ed8] text-white text-sm font-semibold transition-all disabled:opacity-50 mt-1"
            >
              {submitting
                ? <div className="w-4 h-4 border-2 border-white/30 border-t-white rounded-full animate-spin" />
                : <>
                    {mode === 'login' && 'Sign in'}
                    {mode === 'register' && 'Create account'}
                    {mode === 'forgot_password' && 'Send reset link'}
                    <ArrowRight className="w-3.5 h-3.5" />
                  </>
              }
            </button>
          </form>

          {/* Mode switcher */}
          <div className="mt-5 flex items-center justify-between text-xs text-[#6b7280]">
            <span>
              {mode === 'login' ? "Don't have an account?" : 'Have an account?'}
              <button
                onClick={() => switchMode(mode === 'login' ? 'register' : 'login')}
                className="ml-1 text-[#2563eb] font-medium hover:underline"
              >
                {mode === 'login' ? 'Sign up' : 'Sign in'}
              </button>
            </span>

            {mode === 'forgot_password' && (
              <button onClick={() => switchMode('login')} className="text-[#6b7280] hover:text-[#111827]">
                ← Back
              </button>
            )}

            {/* Demo login */}
            <button
              onClick={handleDemoSignIn}
              disabled={submitting}
              className="px-2.5 py-1 rounded-md bg-[#eff6ff] text-[#2563eb] text-[11px] font-medium hover:bg-[#dbeafe] transition-colors disabled:opacity-50"
            >
              ⚡ Demo login
            </button>
          </div>
        </div>
      </div>
    </div>
  );
};

// Suppress unused import warnings — kept for future use
const _icons = { Mail, UserIcon, KeyRound };
void _icons;
