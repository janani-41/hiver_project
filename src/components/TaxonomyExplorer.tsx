import React, { useState, useEffect } from "react";
import { BookOpen, AlertOctagon, CheckCircle2, ChevronRight } from "lucide-react";
import { TaxonomyIntent } from "../types";

export const TaxonomyExplorer: React.FC = () => {
  const [intents, setIntents] = useState<TaxonomyIntent[]>([]);
  const [loading, setLoading] = useState(true);
  const [activeIntent, setActiveIntent] = useState<TaxonomyIntent | null>(null);

  useEffect(() => {
    fetch("/api/taxonomy")
      .then((r) => r.json())
      .then((data) => {
        if (data.intents) {
          setIntents(data.intents);
          setActiveIntent(data.intents[0]);
        }
      })
      .catch(console.error)
      .finally(() => setLoading(false));
  }, []);

  if (loading) {
    return <div className="p-8 text-center text-xs text-slate-500">Loading taxonomy...</div>;
  }

  return (
    <div className="space-y-6">
      {/* Intro Header */}
      <div className="bg-white border border-slate-200 rounded-xl p-5 shadow-sm">
        <h2 className="text-base font-bold text-slate-900">
          Discovered Customer Support Intent Taxonomy (@AmazonHelp)
        </h2>
        <p className="text-xs text-slate-500 mt-1">
          An 8-class domain taxonomy discovered from historical Twitter customer support turns, formalizing clear boundary lines between automated self-service resolution and human escalation.
        </p>
      </div>

      {/* Two Column Layout */}
      <div className="grid grid-cols-1 md:grid-cols-12 gap-6">
        {/* Intent List (4 Cols) */}
        <div className="md:col-span-4 space-y-2">
          {intents.map((it) => {
            const isSelected = activeIntent?.name === it.name;
            return (
              <button
                key={it.name}
                onClick={() => setActiveIntent(it)}
                className={`w-full p-3 rounded-xl border text-left transition-all flex items-center justify-between cursor-pointer ${
                  isSelected
                    ? "bg-blue-50/70 border-blue-300 text-blue-900 shadow-sm"
                    : "bg-white border-slate-200 hover:border-slate-300 text-slate-700"
                }`}
              >
                <div>
                  <div className="text-xs font-bold">{it.name}</div>
                  <div className="text-[11px] text-slate-400 line-clamp-1 mt-0.5">
                    {it.description}
                  </div>
                </div>
                <ChevronRight
                  className={`w-4 h-4 flex-shrink-0 ml-2 ${
                    isSelected ? "text-blue-600" : "text-slate-300"
                  }`}
                />
              </button>
            );
          })}
        </div>

        {/* Intent Deep Dive (8 Cols) */}
        {activeIntent && (
          <div className="md:col-span-8 bg-white border border-slate-200 rounded-xl p-6 shadow-sm space-y-5 animate-in fade-in duration-200">
            <div>
              <div className="text-xs font-bold uppercase tracking-wider text-blue-600 mb-1">
                Intent Specification
              </div>
              <h3 className="text-lg font-bold text-slate-900">{activeIntent.name}</h3>
              <p className="text-xs text-slate-600 mt-1 leading-relaxed">
                {activeIntent.description}
              </p>
            </div>

            {/* Typical Customer Phrases */}
            <div>
              <div className="text-xs font-semibold uppercase tracking-wider text-slate-500 mb-2">
                Typical Customer Inquiries
              </div>
              <div className="grid grid-cols-1 sm:grid-cols-2 gap-2">
                {activeIntent.typical_customer_phrases?.map((phrase, idx) => (
                  <div
                    key={idx}
                    className="p-2.5 bg-slate-50 border border-slate-100 rounded-lg text-xs text-slate-700 italic"
                  >
                    "{phrase}"
                  </div>
                ))}
              </div>
            </div>

            {/* Triage Criteria: Auto-Handle vs Escalation */}
            <div className="grid grid-cols-1 sm:grid-cols-2 gap-4 pt-2">
              <div className="p-4 bg-emerald-50/70 border border-emerald-200 rounded-xl">
                <div className="flex items-center gap-1.5 text-xs font-bold uppercase tracking-wider text-emerald-800 mb-2">
                  <CheckCircle2 className="w-4 h-4 text-emerald-600" />
                  Auto-Handle Criteria
                </div>
                <p className="text-xs text-emerald-950 leading-relaxed">
                  {activeIntent.auto_handle_criteria}
                </p>
              </div>

              <div className="p-4 bg-rose-50/70 border border-rose-200 rounded-xl">
                <div className="flex items-center gap-1.5 text-xs font-bold uppercase tracking-wider text-rose-800 mb-2">
                  <AlertOctagon className="w-4 h-4 text-rose-600" />
                  Escalation Triggers
                </div>
                <ul className="text-xs text-rose-950 space-y-1 list-disc list-inside">
                  {activeIntent.escalation_triggers?.map((trig, idx) => (
                    <li key={idx}>{trig}</li>
                  ))}
                </ul>
              </div>
            </div>
          </div>
        )}
      </div>
    </div>
  );
};
