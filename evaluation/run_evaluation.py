"""
Comprehensive Evaluation Harness for Twitter Customer Support Agent.
Evaluates:
1. Intent Classification Accuracy, Macro F1, and Confusion Matrix
2. Escalation Triage Accuracy, Precision, Recall, F1, FPR, and FNR (Missed Escalations)
3. Retrieval Component Relevance @ top-1 / top-3 and Cosine Similarity
4. LLM-as-a-Judge Response Quality across 5 dimensions (Relevance, Groundedness, Correctness, Helpfulness, Hallucinations)
Outputs structured results to results/ and prints a clean summary report to stdout.
"""

import os
import sys
import json
import time
import argparse
import pandas as pd
import numpy as np
from typing import Dict, Any, List, Optional
from collections import defaultdict
from sklearn.metrics import accuracy_score, precision_recall_fscore_support, confusion_matrix

PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

from src.agent.pipeline import CustomerSupportAgent
from src.agent.judge import LLMJudge

def run_evaluation(
    data_path: str = "evaluation/golden_set.csv",
    output_dir: str = "results",
    max_samples: Optional[int] = None,
    run_judge: bool = True
) -> Dict[str, Any]:
    print("=" * 75)
    print("🧪 RUNNING COMPREHENSIVE CUSTOMER SUPPORT AGENT EVALUATION")
    print("=" * 75)
    
    os.makedirs(output_dir, exist_ok=True)
    df = pd.read_csv(data_path)
    if max_samples and max_samples < len(df):
        print(f"Subsampling evaluation dataset: {max_samples} out of {len(df)} records.")
        df = df.head(max_samples)
    else:
        print(f"Loaded full golden evaluation dataset: {len(df)} records.")

    agent = CustomerSupportAgent()
    judge = LLMJudge() if run_judge else None

    predictions: List[Dict[str, Any]] = []
    judge_results: List[Dict[str, Any]] = []
    escalation_failures: List[Dict[str, Any]] = []

    start_time = time.time()
    print(f"\nProcessing {len(df)} benchmark inquiries through agent pipeline...\n")

    for idx, row in df.iterrows():
        sample_id = row.get("id", f"sample_{idx}")
        cust_msg = str(row["customer_message"])
        ctx = str(row.get("conversation_context", ""))
        gold_intent = str(row["gold_intent"])
        gold_esc = str(row["gold_escalation"])
        gold_reason = str(row.get("gold_reason", ""))

        # 1. Pipeline inference
        output = agent.process_message(cust_msg, ctx)

        pred_intent = output["intent"]
        pred_confidence = output["confidence"]
        pred_esc = output["decision"]
        pred_reason = output["escalation_reason"]
        reply = output["reply"]
        evidence = output.get("evidence", [])

        # Retrieval metrics tracking
        top1_match = False
        top3_match = False
        sim_scores = [ev.get("similarity_score", 0.0) for ev in evidence]
        mean_sim = np.mean(sim_scores) if sim_scores else 0.0

        if evidence:
            top1_match = (evidence[0].get("intent") == gold_intent)
            top3_match = any(ev.get("intent") == gold_intent for ev in evidence[:3])

        # Escalation error analysis
        if gold_esc == "ESCALATE_TO_HUMAN" and pred_esc == "AUTO_HANDLE":
            escalation_failures.append({
                "id": sample_id,
                "type": "FALSE_NEGATIVE_MISSED_RISK",
                "customer_message": cust_msg,
                "gold_reason": gold_reason,
                "agent_decision": pred_esc,
                "agent_reason": pred_reason
            })
        elif gold_esc == "AUTO_HANDLE" and pred_esc == "ESCALATE_TO_HUMAN":
            escalation_failures.append({
                "id": sample_id,
                "type": "FALSE_POSITIVE_OVER_ESCALATION",
                "customer_message": cust_msg,
                "gold_reason": gold_reason,
                "agent_decision": pred_esc,
                "agent_reason": pred_reason
            })

        pred_record = {
            "id": sample_id,
            "customer_message": cust_msg,
            "gold_intent": gold_intent,
            "pred_intent": pred_intent,
            "intent_correct": (gold_intent == pred_intent),
            "confidence": pred_confidence,
            "gold_escalation": gold_esc,
            "pred_escalation": pred_esc,
            "escalation_correct": (gold_esc == pred_esc),
            "top1_retrieval_match": top1_match,
            "top3_retrieval_match": top3_match,
            "mean_retrieval_sim": round(float(mean_sim), 4),
            "reply": reply,
            "escalation_reason": pred_reason
        }

        # 2. LLM-as-a-Judge assessment
        if judge:
            evidence_text = agent.retriever.format_evidence_for_prompt(evidence)
            j_eval = judge.evaluate_response(
                customer_message=cust_msg,
                generated_response=reply,
                evidence_text=evidence_text,
                context=ctx
            )
            j_eval["id"] = sample_id
            judge_results.append(j_eval)
            pred_record.update({
                "judge_relevance": j_eval.get("relevance", 4),
                "judge_groundedness": j_eval.get("groundedness", 4),
                "judge_correctness": j_eval.get("correctness", 4),
                "judge_helpfulness": j_eval.get("helpfulness", 4),
                "judge_unsupported_claims": j_eval.get("unsupported_claims", 5),
                "judge_average_score": j_eval.get("average_score", 4.2),
                "judge_verdict": j_eval.get("verdict", "ACCEPTABLE")
            })

        predictions.append(pred_record)
        if (idx + 1) % 25 == 0 or (idx + 1) == len(df):
            print(f"Processed {idx + 1} / {len(df)} samples...")

    elapsed = time.time() - start_time
    pred_df = pd.DataFrame(predictions)

    # Calculate Intent Metrics
    intent_acc = accuracy_score(pred_df["gold_intent"], pred_df["pred_intent"])
    p_macro, r_macro, f1_macro, _ = precision_recall_fscore_support(
        pred_df["gold_intent"], pred_df["pred_intent"], average="macro", zero_division=0
    )

    all_intents = sorted(list(set(pred_df["gold_intent"]).union(set(pred_df["pred_intent"]))))
    cm = confusion_matrix(pred_df["gold_intent"], pred_df["pred_intent"], labels=all_intents)
    cm_dict = {
        "labels": all_intents,
        "matrix": cm.tolist()
    }

    # Calculate Escalation Metrics
    esc_acc = accuracy_score(pred_df["gold_escalation"], pred_df["pred_escalation"])
    esc_labels = ["AUTO_HANDLE", "ESCALATE_TO_HUMAN"]
    p_esc, r_esc, f1_esc, _ = precision_recall_fscore_support(
        pred_df["gold_escalation"], pred_df["pred_escalation"],
        pos_label="ESCALATE_TO_HUMAN", average="binary", zero_division=0
    )

    cm_esc = confusion_matrix(pred_df["gold_escalation"], pred_df["pred_escalation"], labels=esc_labels)
    # cm_esc: [ [TN, FP], [FN, TP] ] where AUTO_HANDLE is 0, ESCALATE is 1
    tn, fp = cm_esc[0][0], cm_esc[0][1]
    fn, tp = cm_esc[1][0], cm_esc[1][1]

    fpr = fp / (fp + tn) if (fp + tn) > 0 else 0.0
    fnr = fn / (fn + tp) if (fn + tp) > 0 else 0.0  # Critical missed escalation rate

    # Retrieval Metrics
    top1_acc = pred_df["top1_retrieval_match"].mean()
    top3_acc = pred_df["top3_retrieval_match"].mean()
    avg_sim = pred_df["mean_retrieval_sim"].mean()

    # Judge Metrics
    judge_summary = {}
    if judge_results:
        j_df = pd.DataFrame(judge_results)
        judge_summary = {
            "mean_relevance": round(float(j_df["relevance"].mean()), 2),
            "mean_groundedness": round(float(j_df["groundedness"].mean()), 2),
            "mean_correctness": round(float(j_df["correctness"].mean()), 2),
            "mean_helpfulness": round(float(j_df["helpfulness"].mean()), 2),
            "mean_unsupported_claims": round(float(j_df["unsupported_claims"].mean()), 2),
            "overall_average_score": round(float(j_df["average_score"].mean()), 2),
            "hallucination_rate": round(float((j_df["unsupported_claims"] < 3).mean()), 4),
            "acceptable_pct": round(float((j_df["verdict"] == "ACCEPTABLE").mean() * 100), 1),
            "needs_revision_pct": round(float((j_df["verdict"] == "NEEDS_REVISION").mean() * 100), 1),
            "rejected_pct": round(float((j_df["verdict"] == "REJECTED").mean() * 100), 1)
        }

    # Summary object
    summary = {
        "timestamp": time.strftime("%Y-%m-%d %H:%M:%S"),
        "evaluation_samples": len(pred_df),
        "execution_time_seconds": round(elapsed, 2),
        "intent_classification": {
            "accuracy": round(float(intent_acc), 4),
            "macro_precision": round(float(p_macro), 4),
            "macro_recall": round(float(r_macro), 4),
            "macro_f1": round(float(f1_macro), 4)
        },
        "escalation_triage": {
            "accuracy": round(float(esc_acc), 4),
            "precision": round(float(p_esc), 4),
            "recall": round(float(r_esc), 4),
            "f1": round(float(f1_esc), 4),
            "false_positive_rate_unnecessary_escalations": round(float(fpr), 4),
            "false_negative_rate_missed_critical_escalations": round(float(fnr), 4),
            "true_positives": int(tp),
            "false_positives": int(fp),
            "true_negatives": int(tn),
            "false_negatives": int(fn)
        },
        "retrieval_performance": {
            "top1_intent_match_accuracy": round(float(top1_acc), 4),
            "top3_intent_match_accuracy": round(float(top3_acc), 4),
            "average_cosine_similarity": round(float(avg_sim), 4)
        },
        "response_generation_quality": judge_summary,
        "escalation_failures_count": len(escalation_failures)
    }

    # Write files
    pred_path = os.path.join(output_dir, "predictions.csv")
    pred_df.to_csv(pred_path, index=False)

    summary_path = os.path.join(output_dir, "evaluation_summary.json")
    with open(summary_path, "w") as f:
        json.dump(summary, f, indent=2)

    cm_path = os.path.join(output_dir, "confusion_matrix.json")
    with open(cm_path, "w") as f:
        json.dump(cm_dict, f, indent=2)

    if judge_results:
        j_path = os.path.join(output_dir, "judge_results.jsonl")
        with open(j_path, "w") as f:
            for j_item in judge_results:
                f.write(json.dumps(j_item) + "\n")

    fail_path = os.path.join(output_dir, "escalation_failures.json")
    with open(fail_path, "w") as f:
        json.dump(escalation_failures, f, indent=2)

    # Print Clean Console Summary
    print("\n" + "=" * 75)
    print("📊 EVALUATION RESULTS SUMMARY")
    print("=" * 75)
    print(f"Total Evaluated Samples:      {len(pred_df)}")
    print(f"Execution Latency:            {elapsed:.2f}s ({elapsed/len(pred_df):.3f}s / turn)")
    print("-" * 75)
    print("1. INTENT CLASSIFICATION METRICS:")
    print(f"   Accuracy:                  {intent_acc*100:.2f}%")
    print(f"   Macro Precision:           {p_macro*100:.2f}%")
    print(f"   Macro Recall:              {r_macro*100:.2f}%")
    print(f"   Macro F1-Score:            {f1_macro*100:.2f}%")
    print("-" * 75)
    print("2. ESCALATION TRIAGE METRICS:")
    print(f"   Overall Accuracy:          {esc_acc*100:.2f}%")
    print(f"   Escalation Precision:      {p_esc*100:.2f}%")
    print(f"   Escalation Recall:         {r_esc*100:.2f}%")
    print(f"   Escalation F1-Score:       {f1_esc*100:.2f}%")
    print(f"   False Positive Rate (FPR): {fpr*100:.2f}% (Unnecessary escalations)")
    print(f"   False Negative Rate (FNR): {fnr*100:.2f}% (Dangerous missed escalations)")
    print("-" * 75)
    print("3. RETRIEVAL GROUNDING METRICS:")
    print(f"   Top-1 Intent Match:        {top1_acc*100:.2f}%")
    print(f"   Top-3 Intent Match:        {top3_acc*100:.2f}%")
    print(f"   Average Cosine Similarity: {avg_sim:.4f}")
    if judge_summary:
        print("-" * 75)
        print("4. LLM-AS-A-JUDGE RESPONSE QUALITY (1 to 5):")
        print(f"   Relevance:                 {judge_summary['mean_relevance']:.2f} / 5.0")
        print(f"   Groundedness:              {judge_summary['mean_groundedness']:.2f} / 5.0")
        print(f"   Correctness:               {judge_summary['mean_correctness']:.2f} / 5.0")
        print(f"   Helpfulness:               {judge_summary['mean_helpfulness']:.2f} / 5.0")
        print(f"   Unsupported Claims:        {judge_summary['mean_unsupported_claims']:.2f} / 5.0")
        print(f"   Overall Rubric Average:    {judge_summary['overall_average_score']:.2f} / 5.0")
        print(f"   Hallucination Rate:        {judge_summary['hallucination_rate']*100:.2f}%")
        print(f"   Verdict Acceptable Rate:   {judge_summary['acceptable_pct']:.1f}%")
    print("=" * 75)
    print(f"[✓] Artifacts saved cleanly to '{output_dir}/'")
    return summary

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Run full AI agent evaluation harness.")
    parser.add_argument("--data-path", type=str, default="evaluation/golden_set.csv")
    parser.add_argument("--output-dir", type=str, default="results")
    parser.add_argument("--max-samples", type=int, default=None)
    parser.add_argument("--skip-judge", action="store_true")

    args = parser.parse_args()
    run_evaluation(
        data_path=args.data_path,
        output_dir=args.output_dir,
        max_samples=args.max_samples,
        run_judge=not args.skip_judge
    )
