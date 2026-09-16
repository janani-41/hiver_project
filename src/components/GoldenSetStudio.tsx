import React, { useState, useEffect } from "react";
import { CheckCircle2, Clock, Search, Filter, ShieldCheck, RefreshCw, Star, Table, UserCheck } from "lucide-react";
import { GoldenSample } from "../types";
import { HumanJudgmentStudio } from "./HumanJudgmentStudio";

export const GoldenSetStudio: React.FC = () => {
  const [samples, setSamples] = useState<GoldenSample[]>([]);
  const [loading, setLoading] = useState(true);
  const [activeSubView, setActiveSubView] = useState<"benchmark" | "judgment">("judgment");
  const [search, setSearch] = useState("");
  const [selectedIntent, setSelectedIntent] = useState("ALL");
  const [selectedEsc, setSelectedEsc] = useState("ALL");
  const [verifyingId, setVerifyingId] = useState<string | null>(null);
  const [judgedCount, setJudgedCount] = useState<number>(0);

  const fetchSamples = async () => {
    try {
      setLoading(true);
      const res = await fetch("/api/evaluation/golden-set");
      if (res.ok) {
        const data = await res.json();
        setSamples(data);
      }
    } catch (err) {
      console.error(err);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchSamples();
    try {
      const saved = localStorage.getItem("hiver_human_judgments_v1");
      if (saved) {
        const parsed = JSON.parse(saved);
        setJudgedCount(Object.keys(parsed).length);
      }
    } catch {}
  }, []);

  const handleVerify = async (id: string) => {
    try {
      setVerifyingId(id);
      const res = await fetch("/api/evaluation/verify", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ id })
      });
      if (res.ok) {
        setSamples((prev) =>
          prev.map((s) => (s.id === id ? { ...s, review_status: "VERIFIED_BY_HUMAN" } : s))
        );
      }
    } catch (err) {
      console.error(err);
    } finally {
      setVerifyingId(null);
    }
  };

  const intents = Array.from(new Set(samples.map((s) => s.gold_intent))).filter(Boolean);

  const filtered = samples.filter((s) => {
    const matchesSearch =
      s.customer_message?.toLowerCase().includes(search.toLowerCase()) ||
      s.id?.toLowerCase().includes(search.toLowerCase()) ||
      s.gold_reason?.toLowerCase().includes(search.toLowerCase());
    const matchesIntent = selectedIntent === "ALL" || s.gold_intent === selectedIntent;
    const matchesEsc = selectedEsc === "ALL" || s.gold_escalation === selectedEsc;
    return matchesSearch && matchesIntent && matchesEsc;
  });

  const verifiedCount = samples.filter((s) => s.review_status === "VERIFIED_BY_HUMAN").length;

  return (
    <div className="space-y-5">
      {/* View Switcher Header */}
      <div className="bg-white border border-slate-200 rounded-xl p-4 shadow-sm flex flex-col sm:flex-row sm:items-center justify-between gap-4">
        <div>
          <h2 className="text-base font-bold text-slate-900">
            Golden Evaluation Benchmark & Human Judgment
          </h2>
          <p className="text-xs text-slate-500 mt-0.5">
            Evaluate agent quality, inspect 200 benchmark samples, and provide 1-5 rubric ratings for agreement calculations
          </p>
        </div>

        {/* View Switcher Tabs */}
        <div className="flex items-center gap-1.5 p-1 bg-slate-100 rounded-xl border border-slate-200 text-xs">
          <button
            onClick={() => setActiveSubView("judgment")}
            className={`flex items-center gap-1.5 px-3 py-1.5 rounded-lg font-medium transition-all cursor-pointer ${
              activeSubView === "judgment"
                ? "bg-white text-blue-700 shadow-xs font-semibold"
                : "text-slate-600 hover:text-slate-900"
            }`}
          >
            <UserCheck className="w-3.5 h-3.5" />
            Human Judgment
            <span className="text-[10px] bg-blue-100 text-blue-800 px-1.5 py-0.2 rounded font-bold">
              1-5
            </span>
          </button>

          <button
            onClick={() => setActiveSubView("benchmark")}
            className={`flex items-center gap-1.5 px-3 py-1.5 rounded-lg font-medium transition-all cursor-pointer ${
              activeSubView === "benchmark"
                ? "bg-white text-blue-700 shadow-xs font-semibold"
                : "text-slate-600 hover:text-slate-900"
            }`}
          >
            <Table className="w-3.5 h-3.5" />
            Benchmark Explorer
            <span className="text-[10px] bg-slate-200 text-slate-700 px-1.5 py-0.2 rounded font-medium">
              200
            </span>
          </button>
        </div>
      </div>

      {/* Sub-view: Human Judgment View */}
      {activeSubView === "judgment" && (
        <HumanJudgmentStudio samples={samples} />
      )}

      {/* Sub-view: Benchmark Table View */}
      {activeSubView === "benchmark" && (
        <div className="space-y-4">
          {/* Header & Status */}
          <div className="bg-white border border-slate-200 rounded-xl p-4 shadow-sm flex flex-col sm:flex-row sm:items-center justify-between gap-4">
            <div>
              <h3 className="text-sm font-bold text-slate-800">
                Ground Truth Benchmark Table ({samples.length} Inquiries)
              </h3>
              <p className="text-xs text-slate-500 mt-0.5">
                Stratified dataset across 8 intents for automated accuracy and triage metrics
              </p>
            </div>
            <div className="text-xs bg-slate-50 border border-slate-200 px-3 py-1.5 rounded-lg">
              <span className="font-semibold text-emerald-700">{verifiedCount}</span>
              <span className="text-slate-500"> / {samples.length} Verified by Human</span>
            </div>
          </div>

          {/* Filter Toolbar */}
          <div className="bg-white border border-slate-200 rounded-xl p-4 shadow-sm flex flex-wrap items-center gap-3">
            <div className="flex-1 min-w-[240px] relative">
              <Search className="w-4 h-4 text-slate-400 absolute left-3 top-2.5" />
              <input
                type="text"
                value={search}
                onChange={(e) => setSearch(e.target.value)}
                placeholder="Search tweet text, order #, or escalation reason..."
                className="w-full text-xs pl-9 pr-3 py-2 border border-slate-200 rounded-lg focus:outline-none focus:ring-2 focus:ring-blue-500 font-sans"
              />
            </div>

            <div className="flex items-center gap-2">
              <Filter className="w-3.5 h-3.5 text-slate-400" />
              <select
                value={selectedIntent}
                onChange={(e) => setSelectedIntent(e.target.value)}
                className="text-xs border border-slate-200 rounded-lg px-2.5 py-2 bg-white text-slate-700 focus:outline-none"
              >
                <option value="ALL">All Intents ({intents.length})</option>
                {intents.map((it) => (
                  <option key={it} value={it}>
                    {it}
                  </option>
                ))}
              </select>

              <select
                value={selectedEsc}
                onChange={(e) => setSelectedEsc(e.target.value)}
                className="text-xs border border-slate-200 rounded-lg px-2.5 py-2 bg-white text-slate-700 focus:outline-none"
              >
                <option value="ALL">All Triage Decisions</option>
                <option value="AUTO_HANDLE">AUTO_HANDLE</option>
                <option value="ESCALATE_TO_HUMAN">ESCALATE_TO_HUMAN</option>
              </select>
            </div>
          </div>

          {/* Table of Benchmark Samples */}
          {loading ? (
            <div className="p-12 text-center text-xs text-slate-500 bg-white border border-slate-200 rounded-xl">
              <RefreshCw className="w-5 h-5 animate-spin mx-auto mb-2 text-slate-400" />
              Loading benchmark dataset...
            </div>
          ) : (
            <div className="bg-white border border-slate-200 rounded-xl shadow-sm overflow-hidden">
              <div className="overflow-x-auto max-h-[600px]">
                <table className="w-full text-xs text-left border-collapse">
                  <thead className="sticky top-0 bg-slate-50 border-b border-slate-200 text-slate-500 font-semibold z-10">
                    <tr>
                      <th className="p-3 w-20">ID</th>
                      <th className="p-3">Customer Inquiry Tweet</th>
                      <th className="p-3 w-48">Gold Intent</th>
                      <th className="p-3 w-36">Gold Triage</th>
                      <th className="p-3 w-48">Escalation Rationale</th>
                      <th className="p-3 w-36 text-right">Verification</th>
                    </tr>
                  </thead>
                  <tbody className="divide-y divide-slate-100">
                    {filtered.map((row) => (
                      <tr key={row.id} className="hover:bg-slate-50/70 transition-colors">
                        <td className="p-3 font-mono text-[11px] text-slate-400 font-medium">
                          {row.id}
                        </td>
                        <td className="p-3 text-slate-800 max-w-md font-sans">
                          {row.customer_message}
                        </td>
                        <td className="p-3">
                          <span className="inline-block px-2 py-0.5 rounded text-[11px] font-medium bg-blue-50 text-blue-700 border border-blue-100">
                            {row.gold_intent}
                          </span>
                        </td>
                        <td className="p-3">
                          <span
                            className={`inline-block px-2 py-0.5 rounded text-[11px] font-semibold ${
                              row.gold_escalation === "ESCALATE_TO_HUMAN"
                                ? "bg-rose-50 text-rose-700 border border-rose-200"
                                : "bg-emerald-50 text-emerald-700 border border-emerald-200"
                            }`}
                          >
                            {row.gold_escalation}
                          </span>
                        </td>
                        <td className="p-3 text-slate-500 text-[11px]">
                          {row.gold_reason}
                        </td>
                        <td className="p-3 text-right">
                          {row.review_status === "VERIFIED_BY_HUMAN" ? (
                            <span className="inline-flex items-center gap-1 text-[11px] text-emerald-600 font-semibold">
                              <CheckCircle2 className="w-3.5 h-3.5" />
                              Verified
                            </span>
                          ) : (
                            <button
                              onClick={() => handleVerify(row.id)}
                              disabled={verifyingId === row.id}
                              className="inline-flex items-center gap-1 px-2.5 py-1 text-[11px] font-medium text-slate-600 hover:text-slate-900 bg-slate-100 hover:bg-slate-200 rounded border border-slate-200 transition-colors cursor-pointer"
                            >
                              <ShieldCheck className="w-3 h-3" />
                              Verify
                            </button>
                          )}
                        </td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
              <div className="p-3 bg-slate-50 border-t border-slate-200 text-xs text-slate-500 text-right">
                Showing {filtered.length} of {samples.length} benchmark records
              </div>
            </div>
          )}
        </div>
      )}
    </div>
  );
};
