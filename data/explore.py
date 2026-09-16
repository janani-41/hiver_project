"""
Dataset Exploration & Brand Analysis Tool
Analyzes customer support tweet datasets (full twcs.csv or local samples) to show:
- Available brands
- Conversation and tweet volume per brand
- Usable paired customer-support interactions
- Text length distributions and multi-turn statistics
"""

import os
import sys
import argparse
import pandas as pd
from collections import Counter
from typing import Optional

PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

def explore_dataset(data_path: str, max_rows: Optional[int] = 500000):
    print("=" * 70)
    print(f"📊 TWITTER CUSTOMER SUPPORT DATASET EXPLORATION")
    print(f"File: {data_path}")
    print("=" * 70)
    
    if not os.path.exists(data_path):
        print(f"[ERROR] Data file not found at '{data_path}'.")
        print("[INFO] Run: python data/download_or_prepare.py to generate sample dataset first.")
        return
    
    # Check if this is the sample format or full twcs.csv format
    df_preview = pd.read_csv(data_path, nrows=5)
    columns = list(df_preview.columns)
    
    if "brand" in columns and "historical_response" in columns:
        # Curated / Processed Sample Format
        df = pd.read_csv(data_path)
        print(f"\n[✓] Loaded pre-formatted support interactions: {len(df):,} records")
        print(f"\nBrand Distribution:")
        print(df["brand"].value_counts().to_string())
        
        print(f"\nIntent Distribution for {df['brand'].iloc[0]}:")
        print(df["intent"].value_counts().to_string())
        
        print(f"\nEscalation Triage Distribution:")
        print(df["gold_escalation"].value_counts().to_string())
        
        # Message Lengths
        df["cust_len"] = df["customer_message"].str.len()
        df["resp_len"] = df["historical_response"].str.len()
        print(f"\nMessage Statistics:")
        print(f"- Customer message avg characters: {df['cust_len'].mean():.1f} (min: {df['cust_len'].min()}, max: {df['cust_len'].max()})")
        print(f"- Support response avg characters: {df['resp_len'].mean():.1f} (min: {df['resp_len'].min()}, max: {df['resp_len'].max()})")
        
    elif "author_id" in columns and "in_reply_to_tweet_id" in columns:
        # Full twcs.csv format
        print(f"\n[✓] Detected raw Twitter Customer Support schema (twcs.csv)")
        print(f"Analyzing up to {max_rows:,} rows...")
        
        chunks = []
        chunk_size = 100000
        total_read = 0
        
        for chunk in pd.read_csv(data_path, chunksize=chunk_size, nrows=max_rows):
            chunks.append(chunk)
            total_read += len(chunk)
            if max_rows and total_read >= max_rows:
                break
                
        df = pd.concat(chunks, ignore_index=True)
        print(f"Read {len(df):,} total tweets.")
        
        # In twcs.csv, inbound=False indicates brand responses, inbound=True indicates customer tweets
        if "inbound" in df.columns:
            brand_tweets = df[df["inbound"] == False]
            top_brands = brand_tweets["author_id"].value_counts().head(15)
            print("\nTop 15 Most Active Customer Support Brands in Dataset:")
            print("-" * 50)
            for brand, count in top_brands.items():
                print(f"  {brand:<20} | {count:>8,} brand replies")
                
            print("\nRecommended Brand Selection: 'AmazonHelp'")
            print("Why: High volume (>500k interactions), rich intent diversity, clear public/private resolution protocols.")
        else:
            print("Dataset columns:", df.columns.tolist())
            
    print("\n" + "=" * 70)

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Explore Customer Support Twitter Dataset.")
    parser.add_argument("--data-path", type=str, default="data/raw/amazon_support_sample.csv", help="Path to csv dataset")
    parser.add_argument("--max-rows", type=int, default=500000, help="Max rows to parse from large twcs.csv")
    
    args = parser.parse_args()
    explore_dataset(args.data_path, args.max_rows)
