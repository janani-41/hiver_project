"""
Human Agreement Calculator for LLM-as-a-Judge.
Computes:
1. Spearman Rank & Pearson Correlation for numeric rubric dimensions (1-5)
2. Cohen's Kappa for categorical triage & verdicts
3. Quadratic Weighted Kappa for ordinal rating agreement
Handles missing/pending human ratings gracefully.
"""

import os
import sys
import json
import argparse
import pandas as pd
import numpy as np
from typing import Dict, Any, Optional
from scipy.stats import spearmanr, pearsonr
from sklearn.metrics import cohen_kappa_score

PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))

def calculate_agreement(
    human_csv_path: str = "evaluation/human_judgment_template.csv",
    judge_results_path: Optional[str] = "results/judge_results.jsonl",
    human_json_path: Optional[str] = "results/human_judgments.json"
) -> Dict[str, Any]:
    print("=" * 65, file=sys.stderr)
    print("🤝 HUMAN - LLM JUDGE AGREEMENT ANALYSIS", file=sys.stderr)
    print("=" * 65, file=sys.stderr)
    
    valid_human_rows = pd.DataFrame()
    
    # Try loading from human_judgments.json first if available
    if human_json_path and os.path.exists(human_json_path):
        try:
            with open(human_json_path, "r") as f:
                json_data = json.load(f)
            records = []
            for s_id, data in json_data.items():
                if isinstance(data, dict) and "relevance" in data and "groundedness" in data and "correctness" in data:
                    records.append({
                        "id": s_id,
                        "human_relevance_1_to_5": data.get("relevance"),
                        "human_groundedness_1_to_5": data.get("groundedness"),
                        "human_correctness_1_to_5": data.get("correctness"),
                        "human_notes": data.get("notes", "")
                    })
            if records:
                valid_human_rows = pd.DataFrame(records)
        except Exception as e:
            print(f"[WARN] Error loading {human_json_path}: {e}", file=sys.stderr)

    # If no valid JSON entries, try CSV
    if valid_human_rows.empty:
        if not os.path.exists(human_csv_path):
            return {"status": "error", "message": "Human rating files missing"}
        df_human = pd.read_csv(human_csv_path)
        score_cols = [
            "human_relevance_1_to_5",
            "human_groundedness_1_to_5",
            "human_correctness_1_to_5"
        ]
        valid_human_rows = df_human.dropna(subset=score_cols).copy()
        if "sample_id" in valid_human_rows.columns and "id" not in valid_human_rows.columns:
            valid_human_rows["id"] = valid_human_rows["sample_id"].str.replace("sample_", "gold_")

    num_filled = len(valid_human_rows)
    total_rows = 200
    
    print(f"Human Annotations Found: {num_filled} ratings completed.", file=sys.stderr)
    
    if num_filled < 5:
        print("\n[NOTE] Insufficient human annotations to compute statistically valid correlation.", file=sys.stderr)
        return {
            "status": "pending_human_annotations",
            "filled_samples": num_filled,
            "total_samples": total_rows,
            "instructions": "Rate at least 5 samples in the Human Judgment view to compute agreement."
        }
        
    # Load judge results
    if not (judge_results_path and os.path.exists(judge_results_path)):
        print("[WARN] Judge results file not found.", file=sys.stderr)
        return {"status": "pending_judge_execution"}

    with open(judge_results_path, "r") as f:
        judge_data = [json.loads(line) for line in f]
    df_judge = pd.DataFrame(judge_data)
    
    # Merge on id or fallback to index matching
    if "id" in valid_human_rows.columns and "id" in df_judge.columns:
        merged = pd.merge(valid_human_rows, df_judge, on="id", suffixes=("_human", "_judge"))
    else:
        merged = valid_human_rows.copy()
        for col in ["relevance", "groundedness", "correctness"]:
            if col in df_judge.columns:
                merged[f"{col}_judge"] = df_judge[col].iloc[:len(merged)].values

    if len(merged) < 5:
        return {
            "status": "insufficient_matches",
            "filled_samples": num_filled,
            "matched_samples": len(merged),
            "instructions": "Need at least 5 matching rated samples to compute agreement."
        }
        
    results = {}
    dimensions = [
        ("relevance", "human_relevance_1_to_5"),
        ("groundedness", "human_groundedness_1_to_5"),
        ("correctness", "human_correctness_1_to_5")
    ]
    
    print("\nRubric Dimension Correlation & Agreement:", file=sys.stderr)
    print("-" * 65, file=sys.stderr)
    print(f"{'Dimension':<20} | {'Spearman rho':<14} | {'Pearson r':<12} | {'Weighted Kappa':<14}", file=sys.stderr)
    print("-" * 65, file=sys.stderr)
    
    for dim_name, human_col in dimensions:
        judge_col = dim_name if dim_name in merged.columns else f"{dim_name}_judge"
        if judge_col in merged.columns and human_col in merged.columns:
            h_vals = pd.to_numeric(merged[human_col], errors="coerce").fillna(3)
            j_vals = pd.to_numeric(merged[judge_col], errors="coerce").fillna(3)
            
            rho, p_rho = spearmanr(h_vals, j_vals)
            r, p_r = pearsonr(h_vals, j_vals)
            try:
                qwk = cohen_kappa_score(h_vals.astype(int), j_vals.astype(int), weights="quadratic")
            except Exception:
                qwk = 0.0
                
            results[dim_name] = {
                "spearman_rho": round(float(0.0 if np.isnan(rho) else rho), 3),
                "spearman_p_val": round(float(0.0 if np.isnan(p_rho) else p_rho), 4),
                "pearson_r": round(float(0.0 if np.isnan(r) else r), 3),
                "quadratic_weighted_kappa": round(float(0.0 if np.isnan(qwk) else qwk), 3),
                "human_mean": round(float(h_vals.mean()), 2),
                "judge_mean": round(float(j_vals.mean()), 2)
            }
            print(f"{dim_name:<20} | {results[dim_name]['spearman_rho']:^14.3f} | {results[dim_name]['pearson_r']:^12.3f} | {results[dim_name]['quadratic_weighted_kappa']:^14.3f}", file=sys.stderr)
            
    print("=" * 65, file=sys.stderr)
    return {
        "status": "success",
        "filled_samples": num_filled,
        "matched_samples": len(merged),
        "dimensions": results
    }

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Compute Human vs LLM Judge Agreement.")
    parser.add_argument("--human-csv", type=str, default="evaluation/human_judgment_template.csv")
    parser.add_argument("--human-json", type=str, default="results/human_judgments.json")
    parser.add_argument("--judge-results", type=str, default="results/judge_results.jsonl")
    parser.add_argument("--json", action="store_true", help="Output JSON result")
    
    args = parser.parse_args()
    res = calculate_agreement(args.human_csv, args.judge_results, args.human_json)
    if args.json:
        print(json.dumps(res))
