"""
Data Preprocessing Pipeline for Twitter Customer Support.
Handles:
- Loading raw/curated data
- Deduplication of identical customer inquiries
- Clean context formulation
- Train vs Evaluation split with strict Jaccard shingle leakage prevention
"""

import os
import re
import sys
import json
import random
import argparse
import pandas as pd
from typing import List, Dict, Any, Set

PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

def clean_text(text: str) -> str:
    if not isinstance(text, str):
        return ""
    return re.sub(r'\s+', ' ', text).strip()

def calculate_jaccard(tokens1: Set[str], tokens2: Set[str]) -> float:
    if not tokens1 or not tokens2:
        return 0.0
    intersection = len(tokens1.intersection(tokens2))
    union = len(tokens1.union(tokens2))
    return intersection / union if union > 0 else 0.0

def tokenize_shingles(text: str, n: int = 4) -> Set[str]:
    # Strip twitter handles, numbers, punctuation
    normalized = re.sub(r'@\w+', '', text.lower())
    normalized = re.sub(r'\b\d+\b', '', normalized)
    words = re.sub(r'[^\w\s]', '', normalized).split()
    if len(words) < n:
        return set(words)
    return set(' '.join(words[i:i+n]) for i in range(len(words) - n + 1))

def preprocess_pipeline(
    raw_path: str,
    output_dir: str = "data/processed",
    brand: str = "AmazonHelp",
    seed: int = 42,
    leakage_threshold: float = 0.70
):
    print(f"\n🚀 Running Data Preprocessing Pipeline...")
    print(f"Target Brand: {brand}")
    print(f"Source: {raw_path}")
    print(f"Random Seed: {seed}")
    
    random.seed(seed)
    os.makedirs(output_dir, exist_ok=True)
    
    if not os.path.exists(raw_path):
        from data.download_or_prepare import prepare_dataset
        raw_path = prepare_dataset(brand=brand, use_sample=True, seed=seed)
        
    df = pd.read_csv(raw_path)
    print(f"Loaded {len(df):,} raw records.")
    
    records: List[Dict[str, Any]] = []
    
    if "customer_message" in df.columns and "historical_response" in df.columns:
        for idx, row in df.iterrows():
            cust_text = clean_text(str(row["customer_message"]))
            resp_text = clean_text(str(row["historical_response"]))
            if len(cust_text) < 15 or len(resp_text) < 10:
                continue
            records.append({
                "id": f"conv_{idx:05d}",
                "brand": str(row.get("brand", brand)),
                "customer_message": cust_text,
                "historical_response": resp_text,
                "conversation_context": str(row.get("conversation_context", "Customer contacted support on Twitter.")),
                "intent": str(row.get("intent", "general_product_or_policy_inquiry")),
                "gold_escalation": str(row.get("gold_escalation", "AUTO_HANDLE")),
                "gold_reason": str(row.get("gold_reason", "Standard inquiry."))
            })
    else:
        brand_df = df[df["author_id"] == brand]
        customer_df = df[df["inbound"] == True]
        merged = pd.merge(
            customer_df, brand_df,
            left_on="tweet_id", right_on="in_reply_to_tweet_id",
            suffixes=("_cust", "_brand")
        )
        for idx, row in merged.iterrows():
            cust_text = clean_text(str(row["text_cust"]))
            resp_text = clean_text(str(row["text_brand"]))
            if len(cust_text) < 20 or len(resp_text) < 15:
                continue
            records.append({
                "id": f"twcs_{idx:06d}",
                "brand": brand,
                "customer_message": cust_text,
                "historical_response": resp_text,
                "conversation_context": f"Twitter conversation turn with @{brand}.",
                "intent": "general_product_or_policy_inquiry",
                "gold_escalation": "AUTO_HANDLE",
                "gold_reason": "Historical resolution."
            })
            
    print(f"Valid paired interactions: {len(records):,}")
    
    # Exact deduplication on customer message
    seen = set()
    unique_records = []
    for r in records:
        key = r["customer_message"].strip().lower()
        if key not in seen:
            seen.add(key)
            unique_records.append(r)
            
    print(f"After exact deduplication: {len(unique_records):,} distinct conversations.")
    
    # Shuffle deterministically
    random.shuffle(unique_records)
    
    # Train/Eval split: 75% train (retrieval corpus), 25% eval candidate pool
    split_idx = int(len(unique_records) * 0.75)
    train_corpus = unique_records[:split_idx]
    candidate_eval = unique_records[split_idx:]
    
    # Strict Leakage Filtering
    train_shingles = [tokenize_shingles(item["customer_message"]) for item in train_corpus]
    leak_free_eval = []
    leaked_count = 0
    
    for cand in candidate_eval:
        cand_shingles = tokenize_shingles(cand["customer_message"])
        is_leaked = False
        for t_shingles in train_shingles:
            sim = calculate_jaccard(cand_shingles, t_shingles)
            if sim >= leakage_threshold:
                is_leaked = True
                leaked_count += 1
                break
        if not is_leaked:
            leak_free_eval.append(cand)
            
    print(f"[LEAKAGE AUDIT] Filtered {leaked_count} candidate records exceeding {int(leakage_threshold*100)}% shingle overlap.")
    print(f"Final Train / Retrieval Knowledge Corpus: {len(train_corpus):,} items")
    print(f"Final Leak-Free Candidate Evaluation Pool: {len(leak_free_eval):,} items")
    
    train_path = os.path.join(output_dir, "train_corpus.json")
    eval_path = os.path.join(output_dir, "eval_pool.json")
    
    with open(train_path, "w") as f:
        json.dump(train_corpus, f, indent=2)
    with open(eval_path, "w") as f:
        json.dump(leak_free_eval, f, indent=2)
        
    stats = {
        "brand": brand,
        "raw_records_read": len(df),
        "unique_records": len(unique_records),
        "train_corpus_size": len(train_corpus),
        "eval_pool_size": len(leak_free_eval),
        "leaked_records_discarded": leaked_count,
        "leakage_threshold": leakage_threshold,
        "random_seed": seed
    }
    stats_path = os.path.join(output_dir, "brand_stats.json")
    with open(stats_path, "w") as f:
        json.dump(stats, f, indent=2)
        
    print(f"[SUCCESS] Processed datasets written to '{output_dir}/'")
    return train_path, eval_path

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Preprocess Twitter support data.")
    parser.add_argument("--data-path", type=str, default="data/raw/amazon_support_sample.csv")
    parser.add_argument("--output-dir", type=str, default="data/processed")
    parser.add_argument("--brand", type=str, default="AmazonHelp")
    parser.add_argument("--seed", type=int, default=42)
    parser.add_argument("--leakage-threshold", type=float, default=0.70)
    
    args = parser.parse_args()
    preprocess_pipeline(
        raw_path=args.data_path,
        output_dir=args.output_dir,
        brand=args.brand,
        seed=args.seed,
        leakage_threshold=args.leakage_threshold
    )
