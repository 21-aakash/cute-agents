import React, { useState, useEffect, useRef, useCallback } from 'react';
import {
  Mic,
  MicOff,
  Sparkles,
  Plus,
  CheckCircle2,
  Circle,
  Trash2,
  Calendar,
  Clock,
  ArrowRight,
  TrendingUp,
  Tag,
  AlertCircle,
  Edit2,
  Check,
  X,
  Target,
  Sun,
  Flame,
  Milestone,
} from 'lucide-react';
import { useAuth } from '../../context/AuthContext';
import * as api from '../../api/client';
import type { TodoHorizon, TodoPriority, TodoRecord, TodoStats } from '../../types';

const HORIZONS: { key: TodoHorizon | 'all'; label: string; icon: any; desc: string }[] = [
  { key: 'daily', label: 'Today', icon: Sun, desc: 'Daily Non-Negotiables' },
  { key: 'weekly', label: 'This Week', icon: Flame, desc: 'Deliverables & Habits' },
  { key: 'monthly', label: 'This Month', icon: Milestone, desc: 'Strategic Milestones' },
  { key: 'yearly', label: 'Yearly Vision', icon: Target, desc: 'Long-term Aspirations' },
  { key: 'all', label: 'All Horizons', icon: Calendar, desc: 'Complete Picture' },
];

export const TodoHub: React.FC = () => {
  const { token } = useAuth();
  const apiBase = import.meta.env.VITE_API_BASE ?? '';

  const [activeHorizon, setActiveHorizon] = useState<TodoHorizon | 'all'>('daily');
  const [todos, setTodos] = useState<TodoRecord[]>([]);
  const [stats, setStats] = useState<TodoStats | null>(null);
  const [loading, setLoading] = useState(true);

  // Quick manual add
  const [quickTitle, setQuickTitle] = useState('');
  const [quickPriority, setQuickPriority] = useState<TodoPriority>('medium');

  // AI Voice & Natural Language Bar
  const [voiceInput, setVoiceInput] = useState('');
  const [isRecording, setIsRecording] = useState(false);
  const [aiParsing, setAiParsing] = useState(false);
  const [aiNotice, setAiNotice] = useState<string | null>(null);

  // Editing state
  const [editingId, setEditingId] = useState<string | null>(null);
  const [editTitle, setEditTitle] = useState('');

  const recognitionRef = useRef<any>(null);

  const fetchTodos = useCallback(async () => {
    try {
      setLoading(true);
      const items = await api.listTodosApi(
        apiBase,
        token,
        activeHorizon === 'all' ? undefined : activeHorizon,
      );
      setTodos(items);
      const st = await api.getTodoStatsApi(apiBase, token);
      setStats(st);
    } catch (err) {
      console.error('Failed to load todos:', err);
    } finally {
      setLoading(false);
    }
  }, [apiBase, token, activeHorizon]);

  useEffect(() => {
    fetchTodos();
  }, [fetchTodos]);

  // Toggle To-do Status
  const handleToggle = async (item: TodoRecord) => {
    const nextStatus = item.status === 'completed' ? 'pending' : 'completed';
    // Optimistic UI update
    setTodos((prev) =>
      prev.map((t) => (t.id === item.id ? { ...t, status: nextStatus } : t)),
    );

    try {
      await api.updateTodoApi(apiBase, token, item.id, { status: nextStatus });
      const st = await api.getTodoStatsApi(apiBase, token);
      setStats(st);
    } catch {
      fetchTodos();
    }
  };

  // Delete To-do
  const handleDelete = async (id: string) => {
    setTodos((prev) => prev.filter((t) => t.id !== id));
    try {
      await api.deleteTodoApi(apiBase, token, id);
      const st = await api.getTodoStatsApi(apiBase, token);
      setStats(st);
    } catch {
      fetchTodos();
    }
  };

  // Quick Add To-do
  const handleQuickAdd = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!quickTitle.trim()) return;

    const horizonToAdd = activeHorizon === 'all' ? 'daily' : activeHorizon;
    try {
      const newItem = await api.createTodoApi(apiBase, token, {
        title: quickTitle.trim(),
        horizon: horizonToAdd,
        priority: quickPriority,
        tags: [horizonToAdd],
      });
      setTodos((prev) => [newItem, ...prev]);
      setQuickTitle('');
      const st = await api.getTodoStatsApi(apiBase, token);
      setStats(st);
    } catch (err) {
      console.error('Failed to create todo:', err);
    }
  };

  // Start/Stop Speech Recognition
  const toggleSpeechRecognition = () => {
    const SpeechRecognition =
      (window as any).SpeechRecognition || (window as any).webkitSpeechRecognition;

    if (!SpeechRecognition) {
      alert('Speech recognition is not supported in this browser. Please type your thoughts.');
      return;
    }

    if (isRecording) {
      recognitionRef.current?.stop();
      setIsRecording(false);
      return;
    }

    try {
      const recognition = new SpeechRecognition();
      recognition.continuous = true;
      recognition.interimResults = true;
      recognition.lang = 'en-US';

      recognition.onstart = () => {
        setIsRecording(true);
      };

      recognition.onresult = (event: any) => {
        let transcript = '';
        for (let i = 0; i < event.results.length; i++) {
          transcript += event.results[i][0].transcript + ' ';
        }
        setVoiceInput(transcript.trim());
      };

      recognition.onerror = (event: any) => {
        console.error('Speech recognition error:', event.error);
        setIsRecording(false);
      };

      recognition.onend = () => {
        setIsRecording(false);
      };

      recognitionRef.current = recognition;
      recognition.start();
    } catch (err) {
      console.error('Error starting speech recognition:', err);
      setIsRecording(false);
    }
  };

  // AI Parse and Decompose
  const handleAiDecompose = async () => {
    if (!voiceInput.trim()) return;
    if (isRecording) {
      recognitionRef.current?.stop();
      setIsRecording(false);
    }

    setAiParsing(true);
    setAiNotice(null);
    try {
      const res = await api.parseInputTodosApi(apiBase, token, voiceInput.trim());
      setVoiceInput('');
      setAiNotice(`✨ ${res.summary} (Created ${res.extracted_count} items)`);
      await fetchTodos();
    } catch (err: any) {
      setAiNotice(`⚠️ Failed to parse: ${err.message || 'Error decomposing tasks'}`);
    } finally {
      setAiParsing(false);
    }
  };

  // Save Inline Edit
  const handleSaveEdit = async (id: string) => {
    if (!editTitle.trim()) return;
    setTodos((prev) =>
      prev.map((t) => (t.id === id ? { ...t, title: editTitle.trim() } : t)),
    );
    setEditingId(null);

    try {
      await api.updateTodoApi(apiBase, token, id, { title: editTitle.trim() });
    } catch {
      fetchTodos();
    }
  };

  // Active Horizon Stats
  const activeStats = stats
    ? activeHorizon === 'all'
      ? { total: stats.total, completed: stats.completed }
      : stats[activeHorizon]
    : { total: todos.length, completed: todos.filter((t) => t.status === 'completed').length };

  const completionPct =
    activeStats && activeStats.total > 0
      ? Math.round((activeStats.completed / activeStats.total) * 100)
      : 0;

  return (
    <div className="flex-1 flex flex-col h-full bg-[#0b0f17] text-slate-100 overflow-y-auto font-sans selection:bg-blue-600/30">
      {/* Top Header Banner */}
      <div className="border-b border-slate-800/80 bg-slate-900/40 backdrop-blur-xl px-6 py-5 shrink-0">
        <div className="max-w-5xl mx-auto flex flex-col md:flex-row md:items-center justify-between gap-4">
          <div>
            <div className="flex items-center gap-2 mb-1">
              <span className="text-xl font-bold tracking-tight text-white flex items-center gap-2">
                Nexus Life OS
              </span>
              <span className="text-[10px] px-2 py-0.5 rounded-full bg-emerald-500/20 text-emerald-400 font-mono font-medium border border-emerald-500/30">
                4-Horizon Action System
              </span>
            </div>
            <p className="text-xs text-slate-400">
              Zero-friction voice brain-dump &bull; Auto-structured into Today, Week, Month & Yearly goals.
            </p>
          </div>

          {/* Quick Metrics Badge */}
          <div className="flex items-center gap-3">
            <div className="px-3.5 py-1.5 rounded-xl bg-slate-800/60 border border-slate-700/50 flex items-center gap-3 text-xs">
              <div className="flex items-center gap-1.5 text-slate-300">
                <TrendingUp className="w-4 h-4 text-emerald-400" />
                <span>
                  {activeStats.completed} / {activeStats.total} done
                </span>
              </div>
              <div className="w-16 h-2 bg-slate-700/60 rounded-full overflow-hidden">
                <div
                  className="h-full bg-gradient-to-r from-blue-500 to-emerald-400 transition-all duration-500 rounded-full"
                  style={{ width: `${completionPct}%` }}
                />
              </div>
              <span className="text-emerald-400 font-mono font-semibold">{completionPct}%</span>
            </div>
          </div>
        </div>
      </div>

      <div className="max-w-5xl mx-auto w-full px-6 py-6 flex-1 flex flex-col gap-6">
        
        {/* HERO VOICE BAR: The AI Decompose Assistant */}
        <div className="rounded-2xl border border-slate-800/90 bg-gradient-to-b from-slate-900/80 to-slate-950/90 p-4 shadow-xl shadow-black/40 relative overflow-hidden">
          <div className="flex items-center justify-between mb-2">
            <span className="text-xs font-semibold text-slate-300 flex items-center gap-1.5">
              <Sparkles className="w-3.5 h-3.5 text-blue-400" />
              Voice Brain-Dump & Natural Language Sorter
            </span>
            {isRecording && (
              <span className="text-xs text-rose-400 flex items-center gap-1.5 animate-pulse font-medium">
                <span className="w-2 h-2 rounded-full bg-rose-500" />
                Listening... Speak naturally
              </span>
            )}
          </div>

          <div className="flex items-center gap-2">
            {/* Record Mic Button */}
            <button
              type="button"
              onClick={toggleSpeechRecognition}
              className={`p-3 rounded-xl transition-all flex items-center justify-center shrink-0 shadow-lg ${
                isRecording
                  ? 'bg-rose-500 text-white shadow-rose-500/30 scale-105 animate-pulse'
                  : 'bg-blue-600 hover:bg-blue-500 text-white shadow-blue-500/25'
              }`}
              title={isRecording ? 'Stop recording' : 'Speak your tasks'}
            >
              {isRecording ? <MicOff className="w-5 h-5" /> : <Mic className="w-5 h-5" />}
            </button>

            {/* Input ramble field */}
            <input
              type="text"
              value={voiceInput}
              onChange={(e) => setVoiceInput(e.target.value)}
              onKeyDown={(e) => {
                if (e.key === 'Enter') handleAiDecompose();
              }}
              placeholder="Speak or type: 'Call tax advisor today, finish investor deck this week, hit $20k MRR this year'..."
              className="flex-1 bg-slate-950/70 border border-slate-800 rounded-xl px-4 py-2.5 text-sm text-slate-100 placeholder:text-slate-500 focus:outline-none focus:ring-2 focus:ring-blue-500/40 focus:border-blue-500/60 transition-all"
            />

            {/* AI Decompose Button */}
            <button
              type="button"
              onClick={handleAiDecompose}
              disabled={aiParsing || !voiceInput.trim()}
              className="px-4 py-2.5 rounded-xl bg-gradient-to-r from-blue-600 to-indigo-600 hover:from-blue-500 hover:to-indigo-500 text-white text-xs font-semibold flex items-center gap-1.5 shrink-0 shadow-md shadow-blue-500/20 disabled:opacity-40 transition-all"
            >
              {aiParsing ? (
                <div className="w-4 h-4 border-2 border-white/30 border-t-white rounded-full animate-spin" />
              ) : (
                <>
                  <Sparkles className="w-3.5 h-3.5" />
                  Decompose with AI
                </>
              )}
            </button>
          </div>

          {aiNotice && (
            <div className="mt-3 p-2.5 rounded-lg bg-blue-500/10 border border-blue-500/20 text-xs text-blue-300 flex items-center justify-between">
              <span>{aiNotice}</span>
              <button
                type="button"
                onClick={() => setAiNotice(null)}
                className="text-blue-400 hover:text-blue-200 text-sm leading-none ml-2"
              >
                &times;
              </button>
            </div>
          )}
        </div>

        {/* 4 HORIZON TABS */}
        <div className="flex items-center gap-1.5 p-1 rounded-xl bg-slate-900/60 border border-slate-800/80 overflow-x-auto scrollbar-hide">
          {HORIZONS.map((h) => {
            const Icon = h.icon;
            const count = stats
              ? h.key === 'all'
                ? stats.total
                : stats[h.key]?.total || 0
              : 0;

            const isActive = activeHorizon === h.key;
            return (
              <button
                key={h.key}
                onClick={() => setActiveHorizon(h.key)}
                className={`flex items-center gap-2 px-3.5 py-2 rounded-lg text-xs font-medium transition-all shrink-0 ${
                  isActive
                    ? 'bg-blue-600 text-white shadow-md shadow-blue-600/30 font-semibold'
                    : 'text-slate-400 hover:text-slate-200 hover:bg-slate-800/40'
                }`}
              >
                <Icon className={`w-3.5 h-3.5 ${isActive ? 'text-white' : 'text-slate-400'}`} />
                <span>{h.label}</span>
                <span
                  className={`text-[10px] px-1.5 py-0.2 rounded-full font-mono ${
                    isActive ? 'bg-white/20 text-white' : 'bg-slate-800 text-slate-400'
                  }`}
                >
                  {count}
                </span>
              </button>
            );
          })}
        </div>

        {/* QUICK MANUAL ADD INPUT */}
        <form onSubmit={handleQuickAdd} className="flex items-center gap-2">
          <div className="relative flex-1">
            <Plus className="w-4 h-4 text-slate-500 absolute left-3.5 top-1/2 -translate-y-1/2" />
            <input
              type="text"
              value={quickTitle}
              onChange={(e) => setQuickTitle(e.target.value)}
              placeholder={`+ Add a task to ${HORIZONS.find((h) => h.key === activeHorizon)?.label}...`}
              className="w-full bg-slate-900/40 border border-slate-800 rounded-xl pl-10 pr-4 py-2 text-sm text-slate-100 placeholder:text-slate-500 focus:outline-none focus:ring-2 focus:ring-blue-500/40 focus:border-blue-500/60 transition-all"
            />
          </div>

          <select
            value={quickPriority}
            onChange={(e) => setQuickPriority(e.target.value as TodoPriority)}
            className="bg-slate-900/40 border border-slate-800 rounded-xl px-3 py-2 text-xs text-slate-300 focus:outline-none"
          >
            <option value="high">🔴 High</option>
            <option value="medium">🟡 Medium</option>
            <option value="low">🟢 Low</option>
          </select>

          <button
            type="submit"
            className="px-4 py-2 bg-slate-800 hover:bg-slate-700 text-slate-200 text-xs font-semibold rounded-xl transition-colors shrink-0"
          >
            Add Task
          </button>
        </form>

        {/* TO-DO LIST CARDS */}
        <div className="space-y-2.5">
          {loading ? (
            <div className="py-12 flex flex-col items-center justify-center text-slate-500 gap-2">
              <div className="w-6 h-6 border-2 border-blue-500/30 border-t-blue-500 rounded-full animate-spin" />
              <span className="text-xs">Loading items...</span>
            </div>
          ) : todos.length === 0 ? (
            <div className="py-16 text-center rounded-2xl border border-dashed border-slate-800/80 p-8 flex flex-col items-center justify-center">
              <div className="w-12 h-12 rounded-2xl bg-blue-500/10 border border-blue-500/20 flex items-center justify-center text-blue-400 mb-3">
                <CheckCircle2 className="w-6 h-6" />
              </div>
              <h3 className="text-sm font-semibold text-slate-200 mb-1">
                Zero pending items for {HORIZONS.find((h) => h.key === activeHorizon)?.label}
              </h3>
              <p className="text-xs text-slate-500 max-w-sm mb-4">
                Use the microphone above to speak your thoughts or quickly add a task.
              </p>
            </div>
          ) : (
            todos.map((item) => {
              const isCompleted = item.status === 'completed';
              const isEditing = editingId === item.id;

              return (
                <div
                  key={item.id}
                  className={`group rounded-xl border p-3.5 transition-all flex items-start justify-between gap-3 ${
                    isCompleted
                      ? 'bg-slate-950/30 border-slate-800/40 opacity-60'
                      : 'bg-slate-900/50 hover:bg-slate-900/80 border-slate-800/80 shadow-sm'
                  }`}
                >
                  <div className="flex items-start gap-3 flex-1 min-w-0">
                    {/* Checkbox toggle */}
                    <button
                      type="button"
                      onClick={() => handleToggle(item)}
                      className="mt-0.5 text-slate-500 hover:text-emerald-400 transition-colors shrink-0 focus:outline-none"
                    >
                      {isCompleted ? (
                        <CheckCircle2 className="w-5 h-5 text-emerald-400" />
                      ) : (
                        <Circle className="w-5 h-5 text-slate-500 group-hover:text-slate-300" />
                      )}
                    </button>

                    {/* Content */}
                    <div className="flex-1 min-w-0">
                      {isEditing ? (
                        <div className="flex items-center gap-2">
                          <input
                            type="text"
                            value={editTitle}
                            onChange={(e) => setEditTitle(e.target.value)}
                            onKeyDown={(e) => {
                              if (e.key === 'Enter') handleSaveEdit(item.id);
                              if (e.key === 'Escape') setEditingId(null);
                            }}
                            autoFocus
                            className="flex-1 bg-slate-950 border border-blue-500 rounded px-2.5 py-1 text-sm text-slate-100 focus:outline-none"
                          />
                          <button
                            type="button"
                            onClick={() => handleSaveEdit(item.id)}
                            className="p-1 text-emerald-400 hover:text-emerald-300"
                          >
                            <Check className="w-4 h-4" />
                          </button>
                          <button
                            type="button"
                            onClick={() => setEditingId(null)}
                            className="p-1 text-slate-400 hover:text-slate-200"
                          >
                            <X className="w-4 h-4" />
                          </button>
                        </div>
                      ) : (
                        <div
                          onClick={() => {
                            setEditingId(item.id);
                            setEditTitle(item.title);
                          }}
                          className={`text-sm font-medium cursor-pointer transition-colors ${
                            isCompleted
                              ? 'line-through text-slate-500'
                              : 'text-slate-200 hover:text-white'
                          }`}
                        >
                          {item.title}
                        </div>
                      )}

                      {item.description && !isEditing && (
                        <p className="text-xs text-slate-400 mt-0.5 leading-relaxed">
                          {item.description}
                        </p>
                      )}

                      {/* Meta Chips */}
                      <div className="flex items-center gap-2 mt-2">
                        {/* Horizon Chip */}
                        <span className="text-[10px] px-2 py-0.5 rounded-md bg-slate-800 text-slate-400 font-medium">
                          {item.horizon}
                        </span>

                        {/* Priority Badge */}
                        <span
                          className={`text-[10px] px-2 py-0.5 rounded-md font-medium ${
                            item.priority === 'high'
                              ? 'bg-rose-500/15 text-rose-400 border border-rose-500/25'
                              : item.priority === 'medium'
                                ? 'bg-amber-500/15 text-amber-400 border border-amber-500/25'
                                : 'bg-slate-800 text-slate-400'
                          }`}
                        >
                          {item.priority}
                        </span>

                        {item.tags?.map((tag) => (
                          <span
                            key={tag}
                            className="text-[10px] px-1.5 py-0.5 rounded bg-slate-800/50 text-slate-500 flex items-center gap-1"
                          >
                            <Tag className="w-2.5 h-2.5" />
                            {tag}
                          </span>
                        ))}
                      </div>
                    </div>
                  </div>

                  {/* Actions (Edit & Delete) */}
                  <div className="flex items-center gap-1 opacity-0 group-hover:opacity-100 transition-opacity shrink-0">
                    <button
                      type="button"
                      onClick={() => {
                        setEditingId(item.id);
                        setEditTitle(item.title);
                      }}
                      className="p-1.5 text-slate-500 hover:text-slate-300 hover:bg-slate-800 rounded-lg transition-colors"
                      title="Edit task"
                    >
                      <Edit2 className="w-3.5 h-3.5" />
                    </button>
                    <button
                      type="button"
                      onClick={() => handleDelete(item.id)}
                      className="p-1.5 text-slate-500 hover:text-rose-400 hover:bg-rose-500/10 rounded-lg transition-colors"
                      title="Delete task"
                    >
                      <Trash2 className="w-3.5 h-3.5" />
                    </button>
                  </div>
                </div>
              );
            })
          )}
        </div>
      </div>
    </div>
  );
};
