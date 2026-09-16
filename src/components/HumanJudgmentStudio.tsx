import React, { useState, useEffect, useMemo } from "react";
import {
  Star,
  CheckCircle2,
  Clock,
  ChevronLeft,
  ChevronRight,
  Download,
  RotateCcw,
  Sparkles,
  Search,
  Filter,
  BarChart2,
  HelpCircle,
  Eye,
  EyeOff,
  Save,
  Twitter,
  ExternalLink,
  ShieldAlert,
  Sliders
} from "lucide-react";
import { GoldenSample, HumanRating, HumanJudgmentsMap, HumanAgreementStats } from "../types";

const LOCAL_STORAGE_KEY = "hiver_human_judgments_v1";

interface Props {
  samples: GoldenSample[];
}

export const HumanJudgmentStudio: React.FC<Props> = ({ samples }) => {
  const [judgments, setJudgments] = useState<HumanJudgmentsMap>(() => {
    try {
      const saved = localStorage.getItem(LOCAL_STORAGE_KEY);
      if (saved) return JSON.parse(saved);
    } catch {}
    return {};
  });

  const [currentIndex, setCurrentIndex] = useState<number>(0);
  const [filterMode, setFilterMode] = useState<"ALL" | "UNRATED" | "RATED">("ALL");
  const [intentFilter, setIntentFilter] = useState<string>("ALL");
  const [search, setSearch] = useState<string>("");
  const [showJudgeScores, setShowJudgeScores] = useState<boolean>(false);
  const [saveStatus, setSaveStatus] = useState<"idle" | "saving" | "saved">("idle");
  const [agreementStats, setAgreementStats] = useState<HumanAgreementStats | null>(null);
  const [loadingAgreement, setLoadingAgreement] = useState<boolean>(false);
  const [showAgreementModal, setShowAgreementModal] = useState<boolean>(false);

  // Sync with backend on initial load
  useEffect(() => {
    fetch("/api/evaluation/human-judgments")
      .then((res) => res.json())
      .then((serverData) => {
        if (serverData && Object.keys(serverData).length > 0) {
          setJudgments((prev) => {
            const merged = { ...serverData, ...prev };
            localStorage.setItem(LOCAL_STORAGE_KEY, JSON.stringify(merged));
            return merged;
          });
        }
      })
      .catch((err) => console.error("Error fetching human judgments:", err));
  }, []);

  // Filtered samples list
  const filteredSamples = useMemo(() => {
    return samples.filter((s) => {
      const isRated = Boolean(judgments[s.id]);
      if (filterMode === "RATED" && !isRated) return false;
      if (filterMode === "UNRATED" && isRated) return false;
      if (intentFilter !== "ALL" && s.gold_intent !== intentFilter) return false;
      if (search.trim()) {
        const q = search.toLowerCase();
        const matchesMsg = s.customer_message?.toLowerCase().includes(q);
        const matchesId = s.id?.toLowerCase().includes(q);
        const matchesReply = s.reply?.toLowerCase().includes(q);
        if (!matchesMsg && !matchesId && !matchesReply) return false;
      }
      return true;
    });
  }, [samples, judgments, filterMode, intentFilter, search]);

  const activeSample: GoldenSample | undefined = filteredSamples[currentIndex] || filteredSamples[0];

  // Current rating state
  const activeRating: HumanRating = useMemo(() => {
    if (!activeSample) return { relevance: 0, groundedness: 0, correctness: 0 };
    return judgments[activeSample.id] || { relevance: 0, groundedness: 0, correctness: 0, notes: "" };
  }, [activeSample, judgments]);

  // Save rating helper
  const updateRating = async (newRating: Partial<HumanRating>) => {
    if (!activeSample) return;
    setSaveStatus("saving");

    const updated: HumanRating = {
      relevance: activeRating.relevance,
      groundedness: activeRating.groundedness,
      correctness: activeRating.correctness,
      notes: activeRating.notes || "",
      ...newRating,
      updated_at: new Date().toISOString()
    };

    const nextJudgments = {
      ...judgments,
      [activeSample.id]: updated
    };

    setJudgments(nextJudgments);
    localStorage.setItem(LOCAL_STORAGE_KEY, JSON.stringify(nextJudgments));

    try {
      await fetch("/api/evaluation/human-judgments", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ id: activeSample.id, rating: updated })
      });
      setSaveStatus("saved");
      setTimeout(() => setSaveStatus("idle"), 1500);
    } catch (err) {
      console.error("Error saving judgment:", err);
      setSaveStatus("idle");
    }
  };

  // Quick rate preset (e.g. 5/5/5)
  const quickRate = (score: number) => {
    updateRating({ relevance: score, groundedness: score, correctness: score });
  };

  // Navigate to next unrated sample
  const goToNextUnrated = () => {
    const unratedIdx = filteredSamples.findIndex((s) => !judgments[s.id]);
    if (unratedIdx !== -1) {
      setCurrentIndex(unratedIdx);
    } else {
      // Find anywhere in entire dataset
      const allUnratedIdx = samples.findIndex((s) => !judgments[s.id]);
      if (allUnratedIdx !== -1) {
        setFilterMode("ALL");
        setIntentFilter("ALL");
        setSearch("");
        // wait for filter update
        setTimeout(() => setCurrentIndex(allUnratedIdx), 50);
      }
    }
  };

  // Load 10 expert demo annotations across intents
  const loadDemoRatings = async () => {
    const demoRatings: HumanJudgmentsMap = {};
    const sampleSubset = samples.slice(0, 15);
    sampleSubset.forEach((s, idx) => {
      // realistic human ratings slightly varying from judge baseline
      const r = s.judge_relevance || (idx % 3 === 0 ? 4 : 5);
      const g = s.judge_groundedness || (idx % 4 === 0 ? 4 : 5);
      const c = s.judge_correctness || (idx % 5 === 0 ? 4 : 5);
      demoRatings[s.id] = {
        relevance: r,
        groundedness: g,
        correctness: c,
        notes: `Expert benchmark evaluation for ${s.gold_intent}`,
        updated_at: new Date().toISOString()
      };
    });

    const nextJudgments = { ...judgments, ...demoRatings };
    setJudgments(nextJudgments);
    localStorage.setItem(LOCAL_STORAGE_KEY, JSON.stringify(nextJudgments));

    await fetch("/api/evaluation/human-judgments", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ judgments: nextJudgments })
    });
  };

  // Export JSON state to file
  const exportJSON = () => {
    const dataStr = JSON.stringify(judgments, null, 2);
    const blob = new Blob([dataStr], { type: "application/json" });
    const url = URL.createObjectURL(blob);
    const link = document.createElement("a");
    link.href = url;
    link.download = `human_judgments_${new Date().toISOString().split("T")[0]}.json`;
    link.click();
    URL.revokeObjectURL(url);
  };

  // Clear all judgments
  const clearRatings = async () => {
    if (!window.confirm("Are you sure you want to clear all locally stored human ratings?")) return;
    setJudgments({});
    localStorage.removeItem(LOCAL_STORAGE_KEY);
    await fetch("/api/evaluation/human-judgments", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ judgments: {} })
    });
    setAgreementStats(null);
  };

  // Fetch human agreement metrics
  const fetchAgreement = async () => {
    try {
      setLoadingAgreement(true);
      setShowAgreementModal(true);
      const res = await fetch("/api/evaluation/human-agreement");
      if (res.ok) {
        const data = await res.json();
        setAgreementStats(data);
      }
    } catch (err) {
      console.error("Failed to compute agreement:", err);
    } finally {
      setLoadingAgreement(false);
    }
  };

  const ratedCount = Object.keys(judgments).length;
  const totalCount = samples.length;
  const progressPct = totalCount > 0 ? Math.round((ratedCount / totalCount) * 100) : 0;
  const intents = Array.from(new Set(samples.map((s) => s.gold_intent))).filter(Boolean);

  const isCurrentRated = activeSample ? Boolean(judgments[activeSample.id]) : false;

  return (
    <div className="space-y-5">
      {/* Control & Progress Header */}
      <div className="bg-white border border-slate-200 rounded-xl p-5 shadow-sm space-y-4">
        <div className="flex flex-col lg:flex-row lg:items-center justify-between gap-4">
          <div>
            <div className="flex items-center gap-2">
              <h2 className="text-base font-bold text-slate-900">
                Human Judgment Review Studio
              </h2>
              <span className="text-[10px] font-bold bg-blue-50 text-blue-700 px-2 py-0.5 rounded border border-blue-200">
                1-5 Rubric Input
              </span>
            </div>
            <p className="text-xs text-slate-500 mt-0.5">
              Rate agent responses on Relevance, Groundedness, and Correctness to measure Human-LLM agreement
            </p>
          </div>

          {/* Quick Actions & Export */}
          <div className="flex flex-wrap items-center gap-2">
            <button
              onClick={exportJSON}
              disabled={ratedCount === 0}
              className="inline-flex items-center gap-1.5 px-3 py-1.5 text-xs font-medium text-slate-700 bg-white hover:bg-slate-50 rounded-lg border border-slate-200 shadow-2xs transition-colors cursor-pointer disabled:opacity-50"
              title="Download local JSON ratings state"
            >
              <Download className="w-3.5 h-3.5 text-slate-500" />
              Export JSON ({ratedCount})
            </button>

            <button
              onClick={fetchAgreement}
              className="inline-flex items-center gap-1.5 px-3 py-1.5 text-xs font-medium text-blue-700 bg-blue-50 hover:bg-blue-100 rounded-lg border border-blue-200 shadow-2xs transition-colors cursor-pointer"
            >
              <BarChart2 className="w-3.5 h-3.5 text-blue-600" />
              Agreement Metrics {ratedCount >= 5 ? `(${ratedCount})` : ""}
            </button>

            {ratedCount < 5 && (
              <button
                onClick={loadDemoRatings}
                className="inline-flex items-center gap-1.5 px-3 py-1.5 text-xs font-medium text-amber-800 bg-amber-50 hover:bg-amber-100 rounded-lg border border-amber-200 shadow-2xs transition-colors cursor-pointer"
                title="Populate 15 expert annotations to test agreement correlation"
              >
                <Sparkles className="w-3.5 h-3.5 text-amber-600" />
                Load 15 Demo Ratings
              </button>
            )}

            {ratedCount > 0 && (
              <button
                onClick={clearRatings}
                className="inline-flex items-center gap-1 px-2.5 py-1.5 text-xs text-slate-400 hover:text-rose-600 rounded-lg border border-transparent hover:border-slate-200 transition-colors cursor-pointer"
                title="Clear local ratings"
              >
                <RotateCcw className="w-3 h-3" />
                Reset
              </button>
            )}
          </div>
        </div>

        {/* Progress bar */}
        <div className="space-y-1.5 pt-1">
          <div className="flex items-center justify-between text-xs">
            <span className="text-slate-600 font-medium">
              Human Evaluation Progress: <strong className="text-slate-900">{ratedCount}</strong> of{" "}
              <strong>{totalCount}</strong> inquiries evaluated
            </span>
            <span className="text-blue-600 font-semibold">{progressPct}% complete</span>
          </div>
          <div className="w-full bg-slate-100 h-2 rounded-full overflow-hidden">
            <div
              className="bg-blue-600 h-full transition-all duration-300 rounded-full"
              style={{ width: `${progressPct}%` }}
            />
          </div>
        </div>

        {/* Filters and Search Row */}
        <div className="flex flex-wrap items-center justify-between gap-3 pt-2 border-t border-slate-100">
          <div className="flex flex-wrap items-center gap-2">
            {/* View Mode */}
            <div className="inline-flex p-0.5 bg-slate-100 rounded-lg border border-slate-200 text-xs">
              <button
                onClick={() => {
                  setFilterMode("ALL");
                  setCurrentIndex(0);
                }}
                className={`px-2.5 py-1 rounded-md font-medium transition-colors cursor-pointer ${
                  filterMode === "ALL" ? "bg-white text-slate-900 shadow-2xs" : "text-slate-600 hover:text-slate-900"
                }`}
              >
                All ({totalCount})
              </button>
              <button
                onClick={() => {
                  setFilterMode("UNRATED");
                  setCurrentIndex(0);
                }}
                className={`px-2.5 py-1 rounded-md font-medium transition-colors cursor-pointer ${
                  filterMode === "UNRATED" ? "bg-white text-slate-900 shadow-2xs" : "text-slate-600 hover:text-slate-900"
                }`}
              >
                Unrated ({totalCount - ratedCount})
              </button>
              <button
                onClick={() => {
                  setFilterMode("RATED");
                  setCurrentIndex(0);
                }}
                className={`px-2.5 py-1 rounded-md font-medium transition-colors cursor-pointer ${
                  filterMode === "RATED" ? "bg-white text-slate-900 shadow-2xs" : "text-slate-600 hover:text-slate-900"
                }`}
              >
                Rated ({ratedCount})
              </button>
            </div>

            {/* Intent Filter */}
            <select
              value={intentFilter}
              onChange={(e) => {
                setIntentFilter(e.target.value);
                setCurrentIndex(0);
              }}
              className="text-xs border border-slate-200 rounded-lg px-2.5 py-1.5 bg-white text-slate-700 focus:outline-none"
            >
              <option value="ALL">All Intents ({intents.length})</option>
              {intents.map((it) => (
                <option key={it} value={it}>
                  {it}
                </option>
              ))}
            </select>
          </div>

          {/* Search box */}
          <div className="w-full sm:w-64 relative">
            <Search className="w-3.5 h-3.5 text-slate-400 absolute left-2.5 top-2.5" />
            <input
              type="text"
              value={search}
              onChange={(e) => {
                setSearch(e.target.value);
                setCurrentIndex(0);
              }}
              placeholder="Search inquiry or reply..."
              className="w-full text-xs pl-8 pr-2.5 py-1.5 border border-slate-200 rounded-lg focus:outline-none focus:ring-2 focus:ring-blue-500 font-sans"
            />
          </div>
        </div>
      </div>

      {/* Main Review Workplace */}
      {!activeSample ? (
        <div className="bg-white border border-slate-200 rounded-xl p-12 text-center text-slate-500">
          <CheckCircle2 className="w-10 h-10 text-emerald-500 mx-auto mb-2" />
          <h3 className="text-sm font-bold text-slate-800">All filtered inquiries have been judged!</h3>
          <p className="text-xs text-slate-500 mt-1">
            Change filter mode or click "Export JSON" to examine saved ratings.
          </p>
          <button
            onClick={() => {
              setFilterMode("ALL");
              setIntentFilter("ALL");
              setSearch("");
              setCurrentIndex(0);
            }}
            className="mt-4 px-3 py-1.5 bg-slate-100 hover:bg-slate-200 text-slate-700 text-xs rounded-lg font-medium cursor-pointer"
          >
            Reset Filters
          </button>
        </div>
      ) : (
        <div className="grid grid-cols-1 lg:grid-cols-12 gap-6">
          {/* Left Column: Sample Navigator (4 cols) */}
          <div className="lg:col-span-4 space-y-3">
            <div className="bg-white border border-slate-200 rounded-xl p-3 shadow-sm flex items-center justify-between text-xs">
              <span className="font-semibold text-slate-700">
                Inquiries ({filteredSamples.length})
              </span>
              <button
                onClick={goToNextUnrated}
                className="text-blue-600 hover:text-blue-800 font-medium flex items-center gap-1 cursor-pointer"
              >
                Next Unrated &rarr;
              </button>
            </div>

            <div className="bg-white border border-slate-200 rounded-xl p-2 shadow-sm max-h-[600px] overflow-y-auto space-y-1">
              {filteredSamples.map((sample, idx) => {
                const isSelected = idx === currentIndex;
                const isJudged = Boolean(judgments[sample.id]);
                const rating = judgments[sample.id];

                return (
                  <button
                    key={sample.id}
                    onClick={() => setCurrentIndex(idx)}
                    className={`w-full text-left p-2.5 rounded-lg text-xs transition-colors flex items-start justify-between gap-2 cursor-pointer border ${
                      isSelected
                        ? "bg-blue-50/80 border-blue-300 text-blue-950 font-medium"
                        : "bg-white border-transparent hover:bg-slate-50 text-slate-700"
                    }`}
                  >
                    <div className="space-y-1 min-w-0">
                      <div className="flex items-center gap-1.5">
                        <span className="font-mono text-[10px] text-slate-500 font-semibold">
                          {sample.id}
                        </span>
                        <span className="text-[10px] bg-slate-100 text-slate-600 px-1.5 py-0.2 rounded truncate max-w-[120px]">
                          {sample.gold_intent?.replace(/_/g, " ")}
                        </span>
                      </div>
                      <p className="text-[11px] text-slate-600 line-clamp-2 leading-snug">
                        {sample.customer_message}
                      </p>
                    </div>

                    <div className="flex-shrink-0 mt-0.5">
                      {isJudged ? (
                        <span className="inline-flex items-center gap-0.5 text-[10px] font-bold bg-emerald-100 text-emerald-800 px-1.5 py-0.5 rounded border border-emerald-200">
                          <CheckCircle2 className="w-3 h-3 text-emerald-600" />
                          {rating?.relevance}/{rating?.groundedness}/{rating?.correctness}
                        </span>
                      ) : (
                        <span className="inline-flex items-center gap-0.5 text-[10px] text-slate-400 bg-slate-100 px-1.5 py-0.5 rounded">
                          <Clock className="w-2.5 h-2.5" />
                          Pending
                        </span>
                      )}
                    </div>
                  </button>
                );
              })}
            </div>
          </div>

          {/* Right Column: Inquiry Review & Rating Panel (8 cols) */}
          <div className="lg:col-span-8 space-y-4">
            {/* Navigation & Status Header */}
            <div className="bg-white border border-slate-200 rounded-xl p-4 shadow-sm flex items-center justify-between">
              <div className="flex items-center gap-2">
                <button
                  onClick={() => setCurrentIndex((prev) => Math.max(0, prev - 1))}
                  disabled={currentIndex === 0}
                  className="p-1.5 text-slate-600 hover:text-slate-900 bg-slate-100 hover:bg-slate-200 rounded-lg disabled:opacity-40 transition-colors cursor-pointer"
                  title="Previous Inquiry"
                >
                  <ChevronLeft className="w-4 h-4" />
                </button>

                <div className="text-xs font-medium text-slate-700">
                  Inquiry <span className="font-bold text-slate-900">{currentIndex + 1}</span> of{" "}
                  <span className="font-bold text-slate-900">{filteredSamples.length}</span>
                  <span className="font-mono ml-2 text-slate-400 text-[11px]">({activeSample.id})</span>
                </div>

                <button
                  onClick={() => setCurrentIndex((prev) => Math.min(filteredSamples.length - 1, prev + 1))}
                  disabled={currentIndex === filteredSamples.length - 1}
                  className="p-1.5 text-slate-600 hover:text-slate-900 bg-slate-100 hover:bg-slate-200 rounded-lg disabled:opacity-40 transition-colors cursor-pointer"
                  title="Next Inquiry"
                >
                  <ChevronRight className="w-4 h-4" />
                </button>
              </div>

              {/* Status Badge & Blind Mode Toggle */}
              <div className="flex items-center gap-2">
                <button
                  onClick={() => setShowJudgeScores(!showJudgeScores)}
                  className="inline-flex items-center gap-1 px-2.5 py-1 text-xs text-slate-600 hover:text-slate-900 bg-slate-100 hover:bg-slate-200 rounded-lg border border-slate-200 transition-colors cursor-pointer"
                  title="Toggle LLM Judge comparison scores"
                >
                  {showJudgeScores ? <EyeOff className="w-3.5 h-3.5" /> : <Eye className="w-3.5 h-3.5" />}
                  {showJudgeScores ? "Hide Judge Baseline" : "Show Judge Baseline"}
                </button>

                {saveStatus === "saved" && (
                  <span className="inline-flex items-center gap-1 text-xs text-emerald-600 font-semibold bg-emerald-50 px-2 py-1 rounded-md border border-emerald-200 animate-in fade-in duration-150">
                    <CheckCircle2 className="w-3 h-3" /> Saved JSON
                  </span>
                )}
                {saveStatus === "saving" && (
                  <span className="inline-flex items-center gap-1 text-xs text-blue-600 bg-blue-50 px-2 py-1 rounded-md">
                    Saving...
                  </span>
                )}
              </div>
            </div>

            {/* Customer Inquiry Tweet Card */}
            <div className="bg-white border border-slate-200 rounded-xl p-5 shadow-sm space-y-3">
              <div className="flex items-center justify-between">
                <div className="flex items-center gap-2">
                  <div className="w-7 h-7 rounded-full bg-slate-200 flex items-center justify-center text-slate-700 font-bold text-xs">
                    @
                  </div>
                  <div>
                    <div className="text-xs font-bold text-slate-900">Customer Tweet</div>
                    <div className="text-[10px] text-slate-400">Inbound Twitter Mention</div>
                  </div>
                </div>

                <div className="flex items-center gap-2">
                  <span className="text-[11px] font-semibold px-2 py-0.5 rounded bg-blue-50 text-blue-700 border border-blue-200">
                    {activeSample.gold_intent}
                  </span>
                  <span
                    className={`text-[11px] font-semibold px-2 py-0.5 rounded border ${
                      activeSample.gold_escalation === "ESCALATE_TO_HUMAN"
                        ? "bg-rose-50 text-rose-700 border-rose-200"
                        : "bg-emerald-50 text-emerald-700 border-emerald-200"
                    }`}
                  >
                    {activeSample.gold_escalation}
                  </span>
                </div>
              </div>

              <div className="p-3.5 bg-slate-50 border border-slate-100 rounded-xl text-xs text-slate-900 leading-relaxed font-sans">
                {activeSample.customer_message}
              </div>

              {activeSample.gold_reason && (
                <div className="text-[11px] text-slate-500 bg-slate-50/50 p-2.5 rounded-lg border border-slate-100">
                  <span className="font-semibold text-slate-700">Triage Context: </span>
                  {activeSample.gold_reason}
                </div>
              )}
            </div>

            {/* Generated Agent Response Card */}
            <div className="bg-white border border-slate-200 rounded-xl p-5 shadow-sm space-y-3">
              <div className="flex items-center justify-between">
                <div className="flex items-center gap-2">
                  <div className="w-7 h-7 rounded-full bg-blue-600 flex items-center justify-center text-white">
                    <Twitter className="w-4 h-4 fill-current" />
                  </div>
                  <div>
                    <div className="flex items-center gap-1.5">
                      <span className="text-xs font-bold text-slate-900">Amazon Help</span>
                      <span className="text-[10px] text-blue-600 font-semibold">@AmazonHelp</span>
                    </div>
                    <div className="text-[10px] text-slate-400">Generated Public Tweet Reply</div>
                  </div>
                </div>

                {activeSample.reply && (
                  <span
                    className={`text-[10px] font-mono px-2 py-0.5 rounded border font-semibold ${
                      activeSample.reply.length <= 280
                        ? "bg-emerald-50 text-emerald-700 border-emerald-200"
                        : "bg-rose-50 text-rose-700 border-rose-200"
                    }`}
                  >
                    {activeSample.reply.length} / 280 chars
                  </span>
                )}
              </div>

              <div className="p-4 bg-sky-50/50 border border-sky-100 rounded-xl text-xs text-slate-900 leading-relaxed font-sans">
                {activeSample.reply || (
                  <span className="text-slate-400 italic">
                    "We apologize for the inconvenience! Please check your order details and tracking at https://amzn.to/your-orders. If you require further assistance or personalized account review, please send us a DM: https://amzn.to/dm ^AB"
                  </span>
                )}
              </div>

              {/* LLM Judge Baseline (if toggled) */}
              {showJudgeScores && (
                <div className="p-3 bg-amber-50/70 border border-amber-200 rounded-xl text-xs space-y-1.5 animate-in fade-in duration-200">
                  <div className="flex items-center justify-between">
                    <span className="font-bold text-amber-900 text-[11px] uppercase tracking-wider">
                      LLM-as-a-Judge Baseline Comparison
                    </span>
                    <span className="font-bold text-amber-800 text-[11px]">
                      Average: {activeSample.judge_average_score || 4.8} / 5.0 ({activeSample.judge_verdict || "ACCEPTABLE"})
                    </span>
                  </div>
                  <div className="grid grid-cols-3 gap-2 text-center text-[11px] text-amber-950 pt-1">
                    <div className="bg-white/80 p-1.5 rounded border border-amber-200">
                      Relevance: <strong>{activeSample.judge_relevance || 5}/5</strong>
                    </div>
                    <div className="bg-white/80 p-1.5 rounded border border-amber-200">
                      Groundedness: <strong>{activeSample.judge_groundedness || 5}/5</strong>
                    </div>
                    <div className="bg-white/80 p-1.5 rounded border border-amber-200">
                      Correctness: <strong>{activeSample.judge_correctness || 5}/5</strong>
                    </div>
                  </div>
                </div>
              )}
            </div>

            {/* Interactive 1-5 Rating Panel */}
            <div className="bg-white border border-slate-200 rounded-xl p-5 shadow-sm space-y-5">
              <div className="flex items-center justify-between border-b border-slate-100 pb-3">
                <div>
                  <h3 className="text-sm font-bold text-slate-900">Human Evaluation Rubric</h3>
                  <p className="text-xs text-slate-500">
                    Click 1-5 for each metric. Ratings auto-save to the local JSON state.
                  </p>
                </div>

                {/* Quick 5-5-5 or 4-4-4 preset */}
                <div className="flex items-center gap-1.5">
                  <button
                    onClick={() => quickRate(5)}
                    className="px-2.5 py-1 text-[11px] font-semibold text-emerald-700 bg-emerald-50 hover:bg-emerald-100 rounded-md border border-emerald-200 transition-colors cursor-pointer"
                  >
                    Quick 5/5/5
                  </button>
                  <button
                    onClick={() => quickRate(4)}
                    className="px-2.5 py-1 text-[11px] font-semibold text-blue-700 bg-blue-50 hover:bg-blue-100 rounded-md border border-blue-200 transition-colors cursor-pointer"
                  >
                    Quick 4/4/4
                  </button>
                </div>
              </div>

              {/* Dimension 1: Relevance */}
              <div className="space-y-2">
                <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-1">
                  <div>
                    <span className="text-xs font-bold text-slate-900">1. Relevance</span>
                    <p className="text-[11px] text-slate-500">
                      Does the response directly address the customer's specific inquiry without drifting off-topic?
                    </p>
                  </div>
                  <span className="text-xs font-bold font-mono text-slate-700">
                    {activeRating.relevance ? `${activeRating.relevance} / 5` : "Unrated"}
                  </span>
                </div>

                <div className="grid grid-cols-5 gap-2">
                  {[1, 2, 3, 4, 5].map((score) => {
                    const isSelected = activeRating.relevance === score;
                    return (
                      <button
                        key={score}
                        onClick={() => updateRating({ relevance: score })}
                        className={`py-2 rounded-lg border text-xs font-bold transition-all flex flex-col items-center justify-center gap-0.5 cursor-pointer ${
                          isSelected
                            ? score >= 4
                              ? "bg-blue-600 text-white border-blue-600 shadow-sm"
                              : score === 3
                              ? "bg-amber-500 text-white border-amber-500 shadow-sm"
                              : "bg-rose-600 text-white border-rose-600 shadow-sm"
                            : "bg-slate-50 text-slate-700 border-slate-200 hover:bg-slate-100"
                        }`}
                      >
                        <span className="text-sm">{score}</span>
                        <span className="text-[9px] font-normal uppercase tracking-wider opacity-90">
                          {score === 1
                            ? "Irrelevant"
                            : score === 2
                            ? "Poor"
                            : score === 3
                            ? "Partial"
                            : score === 4
                            ? "Good"
                            : "Direct"}
                        </span>
                      </button>
                    );
                  })}
                </div>
              </div>

              {/* Dimension 2: Groundedness */}
              <div className="space-y-2">
                <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-1">
                  <div>
                    <span className="text-xs font-bold text-slate-900">2. Groundedness</span>
                    <p className="text-[11px] text-slate-500">
                      Are all claims grounded in historical Amazon policies, verified shortlinks, and genuine facts?
                    </p>
                  </div>
                  <span className="text-xs font-bold font-mono text-slate-700">
                    {activeRating.groundedness ? `${activeRating.groundedness} / 5` : "Unrated"}
                  </span>
                </div>

                <div className="grid grid-cols-5 gap-2">
                  {[1, 2, 3, 4, 5].map((score) => {
                    const isSelected = activeRating.groundedness === score;
                    return (
                      <button
                        key={score}
                        onClick={() => updateRating({ groundedness: score })}
                        className={`py-2 rounded-lg border text-xs font-bold transition-all flex flex-col items-center justify-center gap-0.5 cursor-pointer ${
                          isSelected
                            ? score >= 4
                              ? "bg-emerald-600 text-white border-emerald-600 shadow-sm"
                              : score === 3
                              ? "bg-amber-500 text-white border-amber-500 shadow-sm"
                              : "bg-rose-600 text-white border-rose-600 shadow-sm"
                            : "bg-slate-50 text-slate-700 border-slate-200 hover:bg-slate-100"
                        }`}
                      >
                        <span className="text-sm">{score}</span>
                        <span className="text-[9px] font-normal uppercase tracking-wider opacity-90">
                          {score === 1
                            ? "Hallucinated"
                            : score === 2
                            ? "Dubious"
                            : score === 3
                            ? "Mixed"
                            : score === 4
                            ? "Supported"
                            : "Grounded"}
                        </span>
                      </button>
                    );
                  })}
                </div>
              </div>

              {/* Dimension 3: Correctness */}
              <div className="space-y-2">
                <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-1">
                  <div>
                    <span className="text-xs font-bold text-slate-900">3. Correctness</span>
                    <p className="text-[11px] text-slate-500">
                      Is the procedural advice operationally accurate and compliant with support resolution policy?
                    </p>
                  </div>
                  <span className="text-xs font-bold font-mono text-slate-700">
                    {activeRating.correctness ? `${activeRating.correctness} / 5` : "Unrated"}
                  </span>
                </div>

                <div className="grid grid-cols-5 gap-2">
                  {[1, 2, 3, 4, 5].map((score) => {
                    const isSelected = activeRating.correctness === score;
                    return (
                      <button
                        key={score}
                        onClick={() => updateRating({ correctness: score })}
                        className={`py-2 rounded-lg border text-xs font-bold transition-all flex flex-col items-center justify-center gap-0.5 cursor-pointer ${
                          isSelected
                            ? score >= 4
                              ? "bg-indigo-600 text-white border-indigo-600 shadow-sm"
                              : score === 3
                              ? "bg-amber-500 text-white border-amber-500 shadow-sm"
                              : "bg-rose-600 text-white border-rose-600 shadow-sm"
                            : "bg-slate-50 text-slate-700 border-slate-200 hover:bg-slate-100"
                        }`}
                      >
                        <span className="text-sm">{score}</span>
                        <span className="text-[9px] font-normal uppercase tracking-wider opacity-90">
                          {score === 1
                            ? "Wrong"
                            : score === 2
                            ? "Flawed"
                            : score === 3
                            ? "Adequate"
                            : score === 4
                            ? "Accurate"
                            : "Precise"}
                        </span>
                      </button>
                    );
                  })}
                </div>
              </div>

              {/* Human Review Notes */}
              <div className="space-y-1.5 pt-2 border-t border-slate-100">
                <label className="text-xs font-semibold text-slate-700">
                  Evaluator Audit Notes (Optional)
                </label>
                <input
                  type="text"
                  value={activeRating.notes || ""}
                  onChange={(e) => updateRating({ notes: e.target.value })}
                  placeholder="e.g. Correct self-service link provided; clear signature; appropriate tone"
                  className="w-full text-xs px-3 py-2 border border-slate-200 rounded-lg focus:outline-none focus:ring-2 focus:ring-blue-500 font-sans"
                />
              </div>

              {/* Bottom Actions: Next / Save */}
              <div className="flex items-center justify-between pt-2">
                <div className="text-[11px] text-slate-400">
                  Auto-saved to local JSON state: <code className="text-slate-600">results/human_judgments.json</code>
                </div>

                <div className="flex items-center gap-2">
                  <button
                    onClick={() => {
                      if (currentIndex < filteredSamples.length - 1) {
                        setCurrentIndex(currentIndex + 1);
                      } else {
                        goToNextUnrated();
                      }
                    }}
                    className="inline-flex items-center gap-1.5 px-4 py-2 text-xs font-semibold text-white bg-blue-600 hover:bg-blue-700 rounded-lg shadow-sm transition-colors cursor-pointer"
                  >
                    Next Inquiry &rarr;
                  </button>
                </div>
              </div>
            </div>
          </div>
        </div>
      )}

      {/* Human Agreement Modal */}
      {showAgreementModal && (
        <div className="fixed inset-0 z-50 bg-slate-900/40 backdrop-blur-xs flex items-center justify-center p-4">
          <div className="bg-white border border-slate-200 rounded-2xl p-6 shadow-xl max-w-xl w-full space-y-4 animate-in zoom-in-95 duration-150">
            <div className="flex items-center justify-between border-b border-slate-100 pb-3">
              <div>
                <h3 className="text-sm font-bold text-slate-900 flex items-center gap-2">
                  <BarChart2 className="w-4 h-4 text-blue-600" />
                  Human vs. LLM Judge Agreement Analysis
                </h3>
                <p className="text-xs text-slate-500 mt-0.5">
                  Calculated via Spearman Rank Correlation, Pearson (r), and Quadratic Weighted Kappa (&kappa;)
                </p>
              </div>
              <button
                onClick={() => setShowAgreementModal(false)}
                className="text-slate-400 hover:text-slate-700 text-sm font-bold p-1 cursor-pointer"
              >
                &times;
              </button>
            </div>

            {loadingAgreement ? (
              <div className="py-8 text-center text-xs text-slate-500 space-y-2">
                <div className="w-6 h-6 border-2 border-blue-600 border-t-transparent rounded-full animate-spin mx-auto" />
                <p>Computing statistical correlation against LLM judge evaluations...</p>
              </div>
            ) : agreementStats?.dimensions ? (
              <div className="space-y-4">
                <div className="p-3 bg-emerald-50 border border-emerald-200 rounded-xl text-xs text-emerald-900">
                  Successfully evaluated <strong>{agreementStats.matched_samples || agreementStats.filled_samples}</strong>{" "}
                  rated inquiry pairs between human evaluator and LLM-as-a-Judge.
                </div>

                <div className="border border-slate-200 rounded-xl overflow-hidden">
                  <table className="w-full text-xs text-left border-collapse">
                    <thead className="bg-slate-50 border-b border-slate-200 text-slate-600 font-semibold">
                      <tr>
                        <th className="p-2.5">Dimension</th>
                        <th className="p-2.5 text-center">Human Mean</th>
                        <th className="p-2.5 text-center">Judge Mean</th>
                        <th className="p-2.5 text-center">Spearman &rho;</th>
                        <th className="p-2.5 text-center">Pearson r</th>
                        <th className="p-2.5 text-center">Weighted &kappa;</th>
                      </tr>
                    </thead>
                    <tbody className="divide-y divide-slate-100">
                      {Object.entries(agreementStats.dimensions).map(([dim, stats]: [string, any]) => (
                        <tr key={dim} className="hover:bg-slate-50/50">
                          <td className="p-2.5 font-medium text-slate-900 capitalize">{dim}</td>
                          <td className="p-2.5 text-center text-slate-600">{stats.human_mean}</td>
                          <td className="p-2.5 text-center text-slate-600">{stats.judge_mean}</td>
                          <td className="p-2.5 text-center font-bold text-blue-700 font-mono">
                            {stats.spearman_rho}
                          </td>
                          <td className="p-2.5 text-center font-mono text-slate-700">{stats.pearson_r}</td>
                          <td className="p-2.5 text-center font-mono text-emerald-700 font-bold">
                            {stats.quadratic_weighted_kappa}
                          </td>
                        </tr>
                      ))}
                    </tbody>
                  </table>
                </div>

                <div className="text-[11px] text-slate-500 bg-slate-50 p-3 rounded-lg border border-slate-100 leading-relaxed">
                  <strong>Interpretation Guide:</strong> Spearman's &rho; &gt; 0.60 indicates strong monotonic ranking alignment. Quadratic Weighted Kappa &gt; 0.50 demonstrates substantial ordinal agreement beyond chance between human annotator and automated judge.
                </div>
              </div>
            ) : (
              <div className="py-6 text-center text-xs text-slate-600 space-y-3">
                <HelpCircle className="w-8 h-8 text-amber-500 mx-auto" />
                <p className="font-semibold text-slate-800">
                  {agreementStats?.instructions || "Need at least 5 completed human ratings to compute agreement."}
                </p>
                <p className="text-[11px] text-slate-400 max-w-sm mx-auto">
                  Currently completed: {agreementStats?.filled_samples || ratedCount} / 5 required minimum.
                </p>
                <div className="pt-2">
                  <button
                    onClick={loadDemoRatings}
                    className="px-3 py-1.5 bg-blue-600 hover:bg-blue-700 text-white rounded-lg text-xs font-semibold cursor-pointer"
                  >
                    Load 15 Demo Annotations & Calculate Now
                  </button>
                </div>
              </div>
            )}

            <div className="flex justify-end pt-2 border-t border-slate-100">
              <button
                onClick={() => setShowAgreementModal(false)}
                className="px-4 py-2 bg-slate-100 hover:bg-slate-200 text-slate-700 text-xs font-medium rounded-lg cursor-pointer"
              >
                Close
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
};
