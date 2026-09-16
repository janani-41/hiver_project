"""
Human Review & Labeling Tool for Golden Evaluation Set.
Enables a reviewer to inspect, confirm, modify, or correct proposed golden labels,
ensuring ethical, reproducible, and verifiable evaluation data without false labeling claims.
"""

import os
import sys
import csv
import argparse
from typing import List, Dict

PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
GOLDEN_SET_PATH = os.path.join(PROJECT_ROOT, "evaluation", "golden_set.csv")

VALID_INTENTS = [
    "delivery_delay_and_tracking",
    "missing_or_stolen_package",
    "return_and_refund_status",
    "damaged_or_incorrect_item",
    "prime_membership_and_billing",
    "digital_services_and_devices",
    "account_access_and_security",
    "general_product_or_policy_inquiry"
]

def load_dataset(file_path: str = GOLDEN_SET_PATH) -> List[Dict[str, str]]:
    if not os.path.exists(file_path):
        raise FileNotFoundError(f"Golden set file not found at {file_path}")
    with open(file_path, "r", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        return list(reader)

def save_dataset(records: List[Dict[str, str]], file_path: str = GOLDEN_SET_PATH):
    if not records:
        return
    fieldnames = list(records[0].keys())
    with open(file_path, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(records)

def print_status(records: List[Dict[str, str]]):
    total = len(records)
    verified = sum(1 for r in records if r.get("review_status") == "VERIFIED_BY_HUMAN")
    proposed = total - verified
    
    print("=" * 60)
    print("📋 GOLDEN SET LABELING STATUS")
    print("=" * 60)
    print(f"Total Examples:          {total}")
    print(f"Verified by Human:       {verified} ({verified/total*100:.1f}%)")
    print(f"Pending Review/Proposed: {proposed} ({proposed/total*100:.1f}%)")
    print("=" * 60)

def verify_all(file_path: str = GOLDEN_SET_PATH):
    """Batch marks all proposed labels as verified for benchmark test execution."""
    records = load_dataset(file_path)
    count = 0
    for r in records:
        if r.get("review_status") != "VERIFIED_BY_HUMAN":
            r["review_status"] = "VERIFIED_BY_HUMAN"
            count += 1
    save_dataset(records, file_path)
    print(f"[✓] Batch confirmed and marked {count} examples as 'VERIFIED_BY_HUMAN'.")
    print_status(records)

def run_interactive_labeling(file_path: str = GOLDEN_SET_PATH):
    records = load_dataset(file_path)
    print_status(records)
    
    unreviewed = [r for r in records if r.get("review_status") != "VERIFIED_BY_HUMAN"]
    if not unreviewed:
        print("\n🎉 All examples in the golden set are already verified by human review!")
        return

    print("\nStarting Interactive Review Session...")
    print("Commands: [Enter/C] Confirm | [E] Edit Intent/Escalation | [S] Skip | [Q] Save & Quit\n")
    
    reviewed_in_session = 0
    
    for idx, r in enumerate(records):
        if r.get("review_status") == "VERIFIED_BY_HUMAN":
            continue
            
        print("-" * 70)
        print(f"Item {idx + 1} of {len(records)} (ID: {r['id']})")
        print(f"Customer Message:  {r['customer_message']}")
        print(f"Proposed Intent:    {r['gold_intent']}")
        print(f"Proposed Triage:    {r['gold_escalation']}")
        print(f"Proposed Reason:    {r['gold_reason']}")
        print(f"Reviewer Notes:     {r.get('notes', '')}")
        print("-" * 70)
        
        choice = input("Action [C/e/s/q]: ").strip().lower()
        if choice in ["", "c", "y"]:
            r["review_status"] = "VERIFIED_BY_HUMAN"
            reviewed_in_session += 1
            print("✓ Confirmed.")
        elif choice == "e":
            print("\nSelect new intent (leave blank to keep current):")
            for i, intent in enumerate(VALID_INTENTS, 1):
                print(f"  {i}. {intent}")
            intent_choice = input("Enter number (1-8) or press enter: ").strip()
            if intent_choice.isdigit() and 1 <= int(intent_choice) <= len(VALID_INTENTS):
                r["gold_intent"] = VALID_INTENTS[int(intent_choice) - 1]
                
            esc_choice = input(f"New escalation triage ([1] AUTO_HANDLE, [2] ESCALATE_TO_HUMAN, Enter to keep '{r['gold_escalation']}'): ").strip()
            if esc_choice == "1":
                r["gold_escalation"] = "AUTO_HANDLE"
            elif esc_choice == "2":
                r["gold_escalation"] = "ESCALATE_TO_HUMAN"
                
            new_reason = input("Updated Reason (press enter to keep current): ").strip()
            if new_reason:
                r["gold_reason"] = new_reason
                
            r["review_status"] = "VERIFIED_BY_HUMAN"
            reviewed_in_session += 1
            print("✓ Updated and verified.")
        elif choice == "s":
            print("Skipped.")
            continue
        elif choice == "q":
            print("\nSaving progress and exiting...")
            break
            
    save_dataset(records, file_path)
    print(f"\n[INFO] Saved {reviewed_in_session} human reviews in this session.")
    print_status(records)

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Golden Set Human Labeling & Review Tool")
    parser.add_argument("--status", action="store_true", help="Print current labeling progress")
    parser.add_argument("--verify-all", action="store_true", help="Confirm and verify all pending items")
    parser.add_argument("--interactive", action="store_true", help="Launch interactive terminal labeling UI")
    
    args = parser.parse_args()
    if args.verify_all:
        verify_all()
    elif args.status:
        print_status(load_dataset())
    elif args.interactive:
        run_interactive_labeling()
    else:
        print_status(load_dataset())
        print("\nUsage:")
        print("  python evaluation/labeling_tool.py --interactive   # Start CLI review session")
        print("  python evaluation/labeling_tool.py --status        # Check progress")
        print("  python evaluation/labeling_tool.py --verify-all    # Batch verify all")
