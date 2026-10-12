import React, { useState, useId } from 'react';
import {
  Eye,
  EyeOff,
  Sparkles,
  ArrowRight,
  ShieldCheck,
  CheckCircle2,
  AlertCircle,
  KeyRound,
  Mail,
  User as UserIcon,
  Bot,
  Zap,
  Globe2,
} from 'lucide-react';
import { useAuth } from '../../context/AuthContext';

type AuthMode = 'login' | 'register' | 'forgot_password';

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

  // Password validation checks
  const hasMinLength = password.length >= 8;
  const hasNumber = /\d/.test(password);
  const hasSpecialOrUpper = /[A-Z!@#$%^&*(),.?":{}|<>]/.test(password);

  const strengthScore = [hasMinLength, hasNumber, hasSpecialOrUpper].filter(Boolean).length;
  const strengthLabels = ['Weak', 'Moderate', 'Strong'];
  const strengthColors = ['bg-rose-500', 'bg-amber-500', 'bg-emerald-500'];

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    clearError();
    setLocalMessage(null);
    setSubmitting(true);

    try {
      if (mode === 'login') {
        await login(email, password);
      } else if (mode === 'register') {
        if (!hasMinLength) {
          throw new Error('Password must be at least 8 characters long.');
        }
        await register(email, password, fullName);
      } else if (mode === 'forgot_password') {
        const res = await forgotPassword(email);
        setLocalMessage(res.message);
        if (res.demo_reset_token) setDemoToken(res.demo_reset_token);
      }
    } catch {
      // Error handled by AuthContext
    } finally {
      setSubmitting(false);
    }
  };

  const handleDemoSignIn = async () => {
    clearError();
    setSubmitting(true);
    try {
      await login('demo@nexusai.dev', 'Password123!');
    } catch {
      // If demo user doesn't exist yet, register it directly
      await register('demo@nexusai.dev', 'Password123!', 'Alex Mercer');
    } finally {
      setSubmitting(false);
    }
  };

  const handleGoogleSignIn = async () => {
    clearError();
    setSubmitting(true);
    try {
      await googleAuth(
        'jordan.nexus@gmail.com',
        'Jordan Lee',
        'https://api.dicebear.com/7.x/avataaars/svg?seed=Jordan',
      );
    } catch {
      // Handled by context
    } finally {
      setSubmitting(false);
    }
  };

  return (
    <div className="min-h-screen w-full flex items-center justify-center p-4 md:p-8 bg-[#0b0f17] text-slate-100 relative overflow-hidden font-sans selection:bg-blue-600/30">
      {/* Ambient background glows */}
      <div className="absolute -top-40 -left-40 w-96 h-96 bg-blue-600/15 rounded-full blur-[120px] pointer-events-none" />
      <div className="absolute -bottom-40 -right-40 w-96 h-96 bg-indigo-600/15 rounded-full blur-[120px] pointer-events-none" />
      <div className="absolute top-1/2 left-1/2 -translate-x-1/2 -translate-y-1/2 w-[600px] h-[600px] bg-sky-500/5 rounded-full blur-[160px] pointer-events-none" />

      {/* Main Container Card */}
      <div className="w-full max-w-4xl grid grid-cols-1 md:grid-cols-12 rounded-3xl border border-slate-800/80 bg-slate-900/60 backdrop-blur-2xl shadow-2xl shadow-black/80 overflow-hidden relative z-10">
        
        {/* Left Side: Brand & Agent Highlights */}
        <div className="md:col-span-5 p-8 md:p-10 flex flex-col justify-between border-b md:border-b-0 md:border-r border-slate-800/60 bg-gradient-to-b from-slate-900/80 to-slate-950/90 relative">
          <div>
            {/* Logo & Product Name */}
            <div className="flex items-center gap-3 mb-6">
              <div className="w-10 h-10 rounded-xl bg-gradient-to-tr from-blue-600 to-indigo-500 flex items-center justify-center shadow-lg shadow-blue-500/25 ring-1 ring-white/20">
                <Sparkles className="w-5 h-5 text-white" />
              </div>
              <div>
                <span className="text-xl font-bold tracking-tight text-white flex items-center gap-2">
                  Nexus AI
                  <span className="text-[10px] px-2 py-0.5 rounded-full bg-blue-500/20 text-blue-400 font-mono font-medium border border-blue-500/30">
                    OS v1.0
                  </span>
                </span>
                <p className="text-xs text-slate-400 font-normal">Autonomous Intelligence Suite</p>
              </div>
            </div>

            <p className="text-sm text-slate-300 leading-relaxed mb-8">
              A private, autonomous multi-agent operating system for deep research, job intelligence, and automated outreach.
            </p>

            {/* Feature Badges */}
            <div className="space-y-4">
              <div className="flex items-start gap-3 p-3 rounded-2xl bg-slate-800/40 border border-slate-700/40">
                <Bot className="w-4 h-4 text-blue-400 mt-0.5 shrink-0" />
                <div>
                  <div className="text-xs font-semibold text-slate-200">Autonomous Research Studio</div>
                  <div className="text-[11px] text-slate-400">Multi-stage LangGraph planner, citation grounding & factual critique.</div>
                </div>
              </div>

              <div className="flex items-start gap-3 p-3 rounded-2xl bg-slate-800/40 border border-slate-700/40">
                <Zap className="w-4 h-4 text-amber-400 mt-0.5 shrink-0" />
                <div>
                  <div className="text-xs font-semibold text-slate-200">Long-Running Outreach Agents</div>
                  <div className="text-[11px] text-slate-400">Multimodal JD screenshot intake with autonomous draft & follow-up queues.</div>
                </div>
              </div>

              <div className="flex items-start gap-3 p-3 rounded-2xl bg-slate-800/40 border border-slate-700/40">
                <Globe2 className="w-4 h-4 text-emerald-400 mt-0.5 shrink-0" />
                <div>
                  <div className="text-xs font-semibold text-slate-200">Unified Knowledge Vault</div>
                  <div className="text-[11px] text-slate-400">Self-hosted Qdrant vector memory with PostgreSQL session persistence.</div>
                </div>
              </div>
            </div>
          </div>

          <div className="mt-8 pt-6 border-t border-slate-800/60 flex items-center justify-between text-xs text-slate-500">
            <span className="flex items-center gap-1.5">
              <ShieldCheck className="w-3.5 h-3.5 text-blue-400" />
              Private & Local-First
            </span>
            <span>FastAPI &bull; LangGraph &bull; React 19</span>
          </div>
        </div>

        {/* Right Side: Auth Forms */}
        <div className="md:col-span-7 p-8 md:p-10 flex flex-col justify-center bg-slate-900/40">
          {/* Header Switcher */}
          <div className="mb-6">
            <div className="flex items-center justify-between mb-2">
              <h1 className="text-2xl font-bold tracking-tight text-white">
                {mode === 'login' && 'Welcome back'}
                {mode === 'register' && 'Create your account'}
                {mode === 'forgot_password' && 'Reset your password'}
              </h1>
              <span className="text-xs text-slate-400">
                {mode === 'login' ? 'No account?' : 'Have an account?'}
                <button
                  type="button"
                  onClick={() => {
                    clearError();
                    setLocalMessage(null);
                    setMode(mode === 'login' ? 'register' : 'login');
                  }}
                  className="ml-1 text-blue-400 hover:text-blue-300 font-medium transition-colors"
                >
                  {mode === 'login' ? 'Sign up' : 'Sign in'}
                </button>
              </span>
            </div>
            <p className="text-xs text-slate-400">
              {mode === 'login' && 'Enter your credentials to access your autonomous agents.'}
              {mode === 'register' && 'Get started with your personal intelligence workspace in seconds.'}
              {mode === 'forgot_password' && 'Enter your registered email and we will send you a reset link.'}
            </p>
          </div>

          {/* Error Message Toast */}
          {error && (
            <div className="mb-5 p-3 rounded-xl bg-rose-500/10 border border-rose-500/30 flex items-start gap-2.5 text-rose-300 text-xs">
              <AlertCircle className="w-4 h-4 mt-0.5 shrink-0 text-rose-400" />
              <div className="flex-1">{error}</div>
              <button
                type="button"
                onClick={clearError}
                className="text-rose-400 hover:text-rose-200 text-sm leading-none"
              >
                &times;
              </button>
            </div>
          )}

          {/* Local Success Message */}
          {localMessage && (
            <div className="mb-5 p-3.5 rounded-xl bg-emerald-500/10 border border-emerald-500/30 flex flex-col gap-1.5 text-emerald-300 text-xs">
              <div className="flex items-center gap-2">
                <CheckCircle2 className="w-4 h-4 shrink-0 text-emerald-400" />
                <span className="font-medium">{localMessage}</span>
              </div>
              {demoToken && (
                <div className="mt-1 p-2 rounded bg-slate-950/70 border border-emerald-500/20 text-[11px] font-mono text-slate-300 break-all">
                  <span className="text-emerald-400 font-semibold">Demo Token:</span> {demoToken}
                </div>
              )}
            </div>
          )}

          {/* Google 1-Click Button */}
          {mode !== 'forgot_password' && (
            <div className="mb-5">
              <button
                type="button"
                onClick={handleGoogleSignIn}
                disabled={submitting}
                className="w-full flex items-center justify-center gap-3 py-2.5 px-4 rounded-xl border border-slate-700/70 bg-slate-800/40 hover:bg-slate-800/80 text-slate-200 text-sm font-medium transition-all shadow-sm hover:border-slate-600 focus:outline-none focus:ring-2 focus:ring-blue-500/40 disabled:opacity-50"
              >
                <svg className="w-4 h-4" viewBox="0 0 24 24">
                  <path
                    fill="#4285F4"
                    d="M23.745 12.27c0-.7-.06-1.4-.19-2.07H12v4.51h6.6c-.29 1.52-1.14 2.8-2.4 3.66v3.05h3.88c2.27-2.09 3.665-5.17 3.665-9.15z"
                  />
                  <path
                    fill="#34A853"
                    d="M12 24c3.24 0 5.95-1.08 7.93-2.91l-3.88-3.05c-1.08.72-2.45 1.16-4.05 1.16-3.12 0-5.77-2.1-6.72-4.93H1.24v3.15C3.26 21.36 7.33 24 12 24z"
                  />
                  <path
                    fill="#FBBC05"
                    d="M5.28 14.27c-.25-.72-.38-1.49-.38-2.27s.13-1.55.38-2.27V6.58H1.24C.45 8.16 0 9.94 0 12s.45 3.84 1.24 5.42l4.04-3.15z"
                  />
                  <path
                    fill="#EA4335"
                    d="M12 4.75c1.77 0 3.35.61 4.6 1.8l3.42-3.42C17.95 1.19 15.24 0 12 0 7.33 0 3.26 2.64 1.24 6.58l4.04 3.15c.95-2.83 3.6-4.98 6.72-4.98z"
                  />
                </svg>
                Continue with Google
              </button>

              <div className="relative my-4">
                <div className="absolute inset-0 flex items-center">
                  <div className="w-full border-t border-slate-800" />
                </div>
                <div className="relative flex justify-center text-[11px] uppercase tracking-wider text-slate-500">
                  <span className="bg-[#111622] px-3">or continue with email</span>
                </div>
              </div>
            </div>
          )}

          {/* Form */}
          <form onSubmit={handleSubmit} className="space-y-4">
            {mode === 'register' && (
              <div>
                <label htmlFor={fullNameId} className="block text-xs font-medium text-slate-300 mb-1.5">
                  Full Name
                </label>
                <div className="relative">
                  <UserIcon className="w-4 h-4 text-slate-500 absolute left-3.5 top-1/2 -translate-y-1/2" />
                  <input
                    id={fullNameId}
                    type="text"
                    required
                    value={fullName}
                    onChange={(e) => setFullName(e.target.value)}
                    placeholder="Alex Mercer"
                    className="w-full pl-10 pr-4 py-2.5 rounded-xl border border-slate-700/70 bg-slate-950/60 text-slate-100 placeholder:text-slate-600 text-sm focus:outline-none focus:ring-2 focus:ring-blue-500/40 focus:border-blue-500/80 transition-all"
                  />
                </div>
              </div>
            )}

            <div>
              <label htmlFor={emailId} className="block text-xs font-medium text-slate-300 mb-1.5">
                Email Address
              </label>
              <div className="relative">
                <Mail className="w-4 h-4 text-slate-500 absolute left-3.5 top-1/2 -translate-y-1/2" />
                <input
                  id={emailId}
                  type="email"
                  required
                  value={email}
                  onChange={(e) => setEmail(e.target.value)}
                  placeholder="alex@nexusai.dev"
                  className="w-full pl-10 pr-4 py-2.5 rounded-xl border border-slate-700/70 bg-slate-950/60 text-slate-100 placeholder:text-slate-600 text-sm focus:outline-none focus:ring-2 focus:ring-blue-500/40 focus:border-blue-500/80 transition-all"
                />
              </div>
            </div>

            {mode !== 'forgot_password' && (
              <div>
                <div className="flex items-center justify-between mb-1.5">
                  <label htmlFor={passwordId} className="block text-xs font-medium text-slate-300">
                    Password
                  </label>
                  {mode === 'login' && (
                    <button
                      type="button"
                      onClick={() => {
                        clearError();
                        setLocalMessage(null);
                        setMode('forgot_password');
                      }}
                      className="text-xs text-blue-400 hover:text-blue-300 transition-colors"
                    >
                      Forgot password?
                    </button>
                  )}
                </div>
                <div className="relative">
                  <KeyRound className="w-4 h-4 text-slate-500 absolute left-3.5 top-1/2 -translate-y-1/2" />
                  <input
                    id={passwordId}
                    type={showPassword ? 'text' : 'password'}
                    required
                    value={password}
                    onChange={(e) => setPassword(e.target.value)}
                    placeholder="••••••••••••"
                    className="w-full pl-10 pr-11 py-2.5 rounded-xl border border-slate-700/70 bg-slate-950/60 text-slate-100 placeholder:text-slate-600 text-sm focus:outline-none focus:ring-2 focus:ring-blue-500/40 focus:border-blue-500/80 transition-all"
                  />
                  <button
                    type="button"
                    onClick={() => setShowPassword(!showPassword)}
                    className="absolute right-3.5 top-1/2 -translate-y-1/2 text-slate-500 hover:text-slate-300 transition-colors p-0.5"
                    aria-label={showPassword ? 'Hide password' : 'Show password'}
                  >
                    {showPassword ? <EyeOff className="w-4 h-4" /> : <Eye className="w-4 h-4" />}
                  </button>
                </div>

                {/* Password Strength Validator Bar for Registration */}
                {mode === 'register' && password.length > 0 && (
                  <div className="mt-2.5 p-2.5 rounded-lg bg-slate-950/40 border border-slate-800/80 space-y-1.5">
                    <div className="flex items-center justify-between text-[11px]">
                      <span className="text-slate-400">Password strength:</span>
                      <span
                        className={`font-medium ${
                          strengthScore === 3
                            ? 'text-emerald-400'
                            : strengthScore === 2
                              ? 'text-amber-400'
                              : 'text-rose-400'
                        }`}
                      >
                        {strengthLabels[strengthScore - 1] || 'Too weak'}
                      </span>
                    </div>
                    <div className="h-1.5 w-full bg-slate-800 rounded-full overflow-hidden flex gap-1">
                      {[0, 1, 2].map((idx) => (
                        <div
                          key={idx}
                          className={`h-full flex-1 transition-all duration-300 rounded-full ${
                            idx < strengthScore ? strengthColors[strengthScore - 1] : 'bg-transparent'
                          }`}
                        />
                      ))}
                    </div>
                    <div className="grid grid-cols-2 gap-1 text-[10px] text-slate-400 pt-1">
                      <div className={`flex items-center gap-1 ${hasMinLength ? 'text-emerald-400' : ''}`}>
                        <div className={`w-1.5 h-1.5 rounded-full ${hasMinLength ? 'bg-emerald-400' : 'bg-slate-600'}`} />
                        8+ characters
                      </div>
                      <div className={`flex items-center gap-1 ${hasNumber ? 'text-emerald-400' : ''}`}>
                        <div className={`w-1.5 h-1.5 rounded-full ${hasNumber ? 'bg-emerald-400' : 'bg-slate-600'}`} />
                        At least 1 number
                      </div>
                      <div className={`flex items-center gap-1 ${hasSpecialOrUpper ? 'text-emerald-400' : ''}`}>
                        <div className={`w-1.5 h-1.5 rounded-full ${hasSpecialOrUpper ? 'bg-emerald-400' : 'bg-slate-600'}`} />
                        Uppercase / symbol
                      </div>
                    </div>
                  </div>
                )}
              </div>
            )}

            <button
              type="submit"
              disabled={submitting}
              className="w-full py-2.5 px-4 rounded-xl bg-gradient-to-r from-blue-600 to-indigo-600 hover:from-blue-500 hover:to-indigo-500 text-white font-medium text-sm transition-all shadow-lg shadow-blue-500/20 flex items-center justify-center gap-2 focus:outline-none focus:ring-2 focus:ring-blue-500/50 disabled:opacity-50"
            >
              {submitting ? (
                <div className="w-4 h-4 border-2 border-white/30 border-t-white rounded-full animate-spin" />
              ) : (
                <>
                  {mode === 'login' && 'Sign in to Nexus'}
                  {mode === 'register' && 'Create Free Account'}
                  {mode === 'forgot_password' && 'Send Reset Instructions'}
                  <ArrowRight className="w-4 h-4" />
                </>
              )}
            </button>
          </form>

          {/* Quick Demo Access Bar */}
          <div className="mt-6 pt-5 border-t border-slate-800/60 flex items-center justify-between text-xs">
            <span className="text-slate-400">Quick Testing:</span>
            <button
              type="button"
              onClick={handleDemoSignIn}
              disabled={submitting}
              className="px-3 py-1.5 rounded-lg bg-blue-500/10 hover:bg-blue-500/20 text-blue-400 border border-blue-500/20 font-medium transition-colors"
            >
              ⚡ 1-Click Demo Login
            </button>
          </div>

          {mode === 'forgot_password' && (
            <div className="mt-4 text-center">
              <button
                type="button"
                onClick={() => setMode('login')}
                className="text-xs text-slate-400 hover:text-slate-200 transition-colors"
              >
                &larr; Back to sign in
              </button>
            </div>
          )}
        </div>
      </div>
    </div>
  );
};
