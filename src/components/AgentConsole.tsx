import React, { useState } from "react";
import { Send, AlertTriangle, ShieldCheck, CheckCircle2, Copy, Sparkles, RefreshCw, MessageSquare } from "lucide-react";
import { AgentResponse } from "../types";

const PRESETS = [
  {
    label: "Routine Tracking (Auto-Handle)",
    message: "@AmazonHelp Where is my package? It was supposed to arrive today by 8 PM but tracking says in transit.",
    type: "auto"
  },
  {
    label: "Urgent Medical Delay (Critical Escalation)",
    message: "@AmazonHelp URGENT: My child needs the nebulizer medication in order #111-2299182. Tracking has not updated for 3 days.",
    type: "escalate"
  },
  {
    label: "Account Hacked / Fraud (Critical Escalation)",
    message: "@AmazonHelp Someone hacked into my account from Russia and placed $800 in gift card orders! Please freeze my account now!",
    type: "escalate"
  },
  {
    label: "Standard Return Policy (Auto-Handle)",
    message: "@AmazonHelp Can I drop off my Amazon return at Kohl's without a box or shipping label?",
    type: "auto"
  },
  {
    label: "Defective Lithium Battery (Safety Hazard)",
    message: "@AmazonHelp The portable charger I bought last week started smoking and got burning hot while charging my phone.",
    type: "escalate"
  }
];

export const AgentConsole: React.FC = () => {
  const [inputMessage, setInputMessage] = useState(PRESETS[0].message);
  const [loading, setLoading] = useState(false);
  const [result, setResult] = useState<AgentResponse | null>(null);
  const [copied, setCopied] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const handleProcess = async (msgToProcess?: string) => {
    const text = msgToProcess || inputMessage;
    if (!text.trim()) return;

    setLoading(true);
    setError(null);
    try {
      const res = await fetch("/api/agent/process", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ message: text })
      });

      if (!res.ok) {
        const errData = await res.json();
        throw new Error(errData.error || "Failed to process inquiry");
      }

      const data = await res.json();
      setResult(data);
    } catch (err: any) {
      setError(err.message);
    } finally {
      setLoading(false);
    }
  };

  const copyToClipboard = () => {
    if (result?.reply) {
      navigator.clipboard.writeText(result.reply);
      setCopied(true);
      setTimeout(() => setCopied(false), 2000);
    }
  };

  return (
    <div className="space-y-6">
      {/* Preset Buttons */}
      <div>
        <div className="text-xs font-semibold uppercase tracking-wider text-slate-500 mb-2">
          Select Benchmark Inquiry or Test Custom Tweet
        </div>
        <div className="flex flex-wrap gap-2">
          {PRESETS.map((preset, idx) => (
            <button
              key={idx}
              onClick={() => {
                setInputMessage(preset.message);
                handleProcess(preset.message);
              }}
              className={`text-xs px-3 py-1.5 rounded-full border transition-all text-left ${
                inputMessage === preset.message
                  ? "bg-blue-600 text-white border-blue-600 shadow-sm"
                  : "bg-white text-slate-700 border-slate-200 hover:border-slate-300 hover:bg-slate-50"
              }`}
            >
              {preset.type === "escalate" ? "🚨 " : "📦 "}
              {preset.label}
            </button>
          ))}
        </div>
      </div>

      {/* Input Field */}
      <div className="bg-white border border-slate-200 rounded-xl p-4 shadow-sm">
        <label className="block text-xs font-semibold text-slate-600 mb-2">
          Inbound Customer Tweet to @AmazonHelp
        </label>
        <div className="flex flex-col gap-3">
          <textarea
            rows={3}
            value={inputMessage}
            onChange={(e) => setInputMessage(e.target.value)}
            placeholder="Type or paste customer inquiry tweet..."
            className="w-full text-sm border border-slate-200 rounded-lg p-3 focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-transparent font-sans"
          />
          <div className="flex items-center justify-between">
            <span className="text-xs text-slate-400">
              {inputMessage.length} characters
            </span>
            <button
              onClick={() => handleProcess()}
              disabled={loading || !inputMessage.trim()}
              className="inline-flex items-center gap-2 px-5 py-2 text-sm font-medium text-white bg-blue-600 rounded-lg hover:bg-blue-700 disabled:opacity-50 transition-colors shadow-sm cursor-pointer"
            >
              {loading ? (
                <>
                  <RefreshCw className="w-4 h-4 animate-spin" />
                  Analyzing Pipeline...
                </>
              ) : (
                <>
                  <Send className="w-4 h-4" />
                  Run Support Agent
                </>
              )}
            </button>
          </div>
        </div>
      </div>

      {/* Error alert */}
      {error && (
        <div className="p-4 bg-red-50 border border-red-200 rounded-xl text-red-700 text-sm flex items-center gap-3">
          <AlertTriangle className="w-5 h-5 flex-shrink-0" />
          <span>{error}</span>
        </div>
      )}

      {/* Result Display */}
      {result && (
        <div className="grid grid-cols-1 lg:grid-cols-12 gap-6 animate-in fade-in duration-300">
          {/* Main Decision & Output (8 Cols) */}
          <div className="lg:col-span-8 space-y-6">
            {/* Triage Status Banner */}
            <div
              className={`p-5 rounded-xl border ${
                result.decision === "ESCALATE_TO_HUMAN"
                  ? "bg-rose-50 border-rose-200 text-rose-950"
                  : "bg-emerald-50 border-emerald-200 text-emerald-950"
              }`}
            >
              <div className="flex items-start justify-between">
                <div className="flex items-center gap-3">
                  {result.decision === "ESCALATE_TO_HUMAN" ? (
                    <div className="w-10 h-10 rounded-full bg-rose-100 flex items-center justify-center text-rose-600">
                      <AlertTriangle className="w-5 h-5" />
                    </div>
                  ) : (
                    <div className="w-10 h-10 rounded-full bg-emerald-100 flex items-center justify-center text-emerald-600">
                      <CheckCircle2 className="w-5 h-5" />
                    </div>
                  )}
                  <div>
                    <div className="text-xs font-bold uppercase tracking-wider opacity-75">
                      Triage Decision
                    </div>
                    <div className="text-lg font-bold">
                      {result.decision === "ESCALATE_TO_HUMAN"
                        ? "ESCALATE TO HUMAN AGENT"
                        : "AUTO-HANDLE WITH GROUNDED GUIDANCE"}
                    </div>
                  </div>
                </div>
                <div className="text-right">
                  <span
                    className={`inline-block px-2.5 py-1 rounded-full text-xs font-semibold ${
                      result.risk_level === "CRITICAL"
                        ? "bg-rose-600 text-white"
                        : result.risk_level === "HIGH"
                        ? "bg-amber-600 text-white"
                        : "bg-emerald-600 text-white"
                    }`}
                  >
                    {result.risk_level} RISK
                  </span>
                </div>
              </div>

              <div className="mt-3 pt-3 border-t border-slate-200/50 text-xs">
                <span className="font-semibold">Reasoning: </span>
                {result.escalation_reason}
                {result.trigger_factor && (
                  <span className="ml-2 font-mono text-[11px] bg-white/70 px-2 py-0.5 rounded border">
                    trigger: {result.trigger_factor}
                  </span>
                )}
              </div>
            </div>

            {/* Generated Reply Card */}
            <div className="bg-white border border-slate-200 rounded-xl p-5 shadow-sm">
              <div className="flex items-center justify-between mb-3">
                <div className="flex items-center gap-2">
                  <Sparkles className="w-4 h-4 text-amber-500" />
                  <span className="text-xs font-bold uppercase tracking-wider text-slate-600">
                    Generated Grounded Reply (@AmazonHelp)
                  </span>
                </div>
                <button
                  onClick={copyToClipboard}
                  className="inline-flex items-center gap-1.5 text-xs text-slate-500 hover:text-slate-800 transition-colors"
                >
                  <Copy className="w-3.5 h-3.5" />
                  {copied ? "Copied!" : "Copy Tweet"}
                </button>
              </div>

              <div className="p-4 bg-slate-50 rounded-lg border border-slate-200 text-slate-800 text-sm leading-relaxed font-sans">
                {result.reply}
              </div>

              <div className="mt-3 flex items-center justify-between text-xs text-slate-400">
                <div className="flex items-center gap-2">
                  <span className="inline-block w-2 h-2 rounded-full bg-emerald-500"></span>
                  Grounded in historical support precedents
                </div>
                <span>
                  Length:{" "}
                  <strong
                    className={
                      result.reply.length <= 280
                        ? "text-emerald-600 font-semibold"
                        : "text-rose-600 font-semibold"
                    }
                  >
                    {result.reply.length} / 280
                  </strong>{" "}
                  chars
                </span>
              </div>
            </div>
          </div>

          {/* Side Pipeline Telemetry (4 Cols) */}
          <div className="lg:col-span-4 space-y-4">
            {/* Intent Classification Telemetry */}
            <div className="bg-white border border-slate-200 rounded-xl p-4 shadow-sm">
              <div className="text-xs font-bold uppercase tracking-wider text-slate-500 mb-3">
                Intent Classification
              </div>
              <div className="p-3 bg-blue-50/60 border border-blue-100 rounded-lg">
                <div className="text-xs text-blue-600 font-semibold">Predicted Intent</div>
                <div className="text-sm font-bold text-blue-900 mt-0.5">
                  {result.intent}
                </div>
              </div>

              <div className="mt-3">
                <div className="flex justify-between text-xs mb-1">
                  <span className="text-slate-500">Model Confidence</span>
                  <span className="font-semibold text-slate-700">
                    {Math.round(result.confidence * 100)}%
                  </span>
                </div>
                <div className="w-full bg-slate-100 rounded-full h-2 overflow-hidden">
                  <div
                    className={`h-2 rounded-full ${
                      result.confidence >= 0.8
                        ? "bg-blue-600"
                        : result.confidence >= 0.65
                        ? "bg-amber-500"
                        : "bg-rose-500"
                    }`}
                    style={{ width: `${result.confidence * 100}%` }}
                  ></div>
                </div>
              </div>

              {result.reasoning && (
                <div className="mt-3 text-xs text-slate-500 italic">
                  "{result.reasoning}"
                </div>
              )}
            </div>

            {/* Retrieved Historical Grounding Evidence */}
            <div className="bg-white border border-slate-200 rounded-xl p-4 shadow-sm">
              <div className="flex items-center justify-between mb-3">
                <div className="text-xs font-bold uppercase tracking-wider text-slate-500">
                  Retrieved Grounding Evidence
                </div>
                <span className="text-[11px] bg-slate-100 text-slate-600 px-2 py-0.5 rounded font-mono">
                  {result.evidence?.length || 0} matches
                </span>
              </div>

              <div className="space-y-3">
                {result.evidence?.map((ev, i) => (
                  <div
                    key={i}
                    className="p-3 bg-slate-50 rounded-lg border border-slate-200 text-xs space-y-1.5"
                  >
                    <div className="flex items-center justify-between">
                      <span className="font-mono text-[10px] text-slate-400">
                        #{ev.conversation_id}
                      </span>
                      <span className="text-[11px] font-semibold text-blue-600">
                        sim: {ev.similarity_score.toFixed(3)}
                      </span>
                    </div>
                    <div className="text-slate-600 line-clamp-2">
                      <strong>Cust:</strong> {ev.customer_message}
                    </div>
                    <div className="text-slate-800 line-clamp-2 bg-white p-1.5 rounded border border-slate-100">
                      <strong>Brand:</strong> {ev.historical_response}
                    </div>
                  </div>
                ))}
              </div>
            </div>
          </div>
        </div>
      )}
    </div>
  );
};
