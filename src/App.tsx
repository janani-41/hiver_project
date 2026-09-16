import React, { useState } from "react";
import { MessageSquare, BarChart3, Database, BookOpen, ShieldCheck, Twitter, Sparkles } from "lucide-react";
import { AgentConsole } from "./components/AgentConsole";
import { MetricsDashboard } from "./components/MetricsDashboard";
import { GoldenSetStudio } from "./components/GoldenSetStudio";
import { TaxonomyExplorer } from "./components/TaxonomyExplorer";

export default function App() {
  const [activeTab, setActiveTab] = useState<"console" | "metrics" | "golden" | "taxonomy">("console");

  return (
    <div className="min-h-screen bg-slate-50 text-slate-900 font-sans flex flex-col">
      {/* Top Header */}
      <header className="bg-white border-b border-slate-200 sticky top-0 z-30 shadow-xs">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
          <div className="flex items-center justify-between h-16">
            <div className="flex items-center gap-3">
              <div className="w-9 h-9 rounded-lg bg-blue-600 flex items-center justify-center text-white shadow-xs">
                <Twitter className="w-5 h-5 fill-current" />
              </div>
              <div>
                <div className="flex items-center gap-2">
                  <h1 className="text-sm font-bold text-slate-900">
                    Twitter Support & Escalation Agent
                  </h1>
                  <span className="text-[10px] font-bold bg-amber-100 text-amber-800 px-2 py-0.5 rounded border border-amber-200">
                    @AmazonHelp
                  </span>
                </div>
                <p className="text-[11px] text-slate-500">
                  Hiver SDE Intern Take-Home Solution • Retrieval Grounded + Safety Overrides
                </p>
              </div>
            </div>

            {/* Navigation Tabs */}
            <nav className="flex items-center gap-1 bg-slate-100 p-1 rounded-xl">
              <button
                onClick={() => setActiveTab("console")}
                className={`flex items-center gap-1.5 px-3 py-1.5 rounded-lg text-xs font-medium transition-all cursor-pointer ${
                  activeTab === "console"
                    ? "bg-white text-blue-600 shadow-xs"
                    : "text-slate-600 hover:text-slate-900"
                }`}
              >
                <MessageSquare className="w-3.5 h-3.5" />
                Live Agent Console
              </button>
              <button
                onClick={() => setActiveTab("metrics")}
                className={`flex items-center gap-1.5 px-3 py-1.5 rounded-lg text-xs font-medium transition-all cursor-pointer ${
                  activeTab === "metrics"
                    ? "bg-white text-blue-600 shadow-xs"
                    : "text-slate-600 hover:text-slate-900"
                }`}
              >
                <BarChart3 className="w-3.5 h-3.5" />
                Evaluation Metrics
              </button>
              <button
                onClick={() => setActiveTab("golden")}
                className={`flex items-center gap-1.5 px-3 py-1.5 rounded-lg text-xs font-medium transition-all cursor-pointer ${
                  activeTab === "golden"
                    ? "bg-white text-blue-600 shadow-xs"
                    : "text-slate-600 hover:text-slate-900"
                }`}
              >
                <Database className="w-3.5 h-3.5" />
                Golden Benchmark (200)
              </button>
              <button
                onClick={() => setActiveTab("taxonomy")}
                className={`flex items-center gap-1.5 px-3 py-1.5 rounded-lg text-xs font-medium transition-all cursor-pointer ${
                  activeTab === "taxonomy"
                    ? "bg-white text-blue-600 shadow-xs"
                    : "text-slate-600 hover:text-slate-900"
                }`}
              >
                <BookOpen className="w-3.5 h-3.5" />
                Taxonomy
              </button>
            </nav>
          </div>
        </div>
      </header>

      {/* Main Content Area */}
      <main className="flex-1 max-w-7xl w-full mx-auto px-4 sm:px-6 lg:px-8 py-6">
        {activeTab === "console" && <AgentConsole />}
        {activeTab === "metrics" && <MetricsDashboard />}
        {activeTab === "golden" && <GoldenSetStudio />}
        {activeTab === "taxonomy" && <TaxonomyExplorer />}
      </main>

      {/* Clean Footer */}
      <footer className="bg-white border-t border-slate-200 py-3 text-center text-xs text-slate-400">
        Hiver SDE Intern Take-Home Project • Powered by Groq API LLaMA-3.3-70B & TF-IDF Retrieval Grounding
      </footer>
    </div>
  );
}
