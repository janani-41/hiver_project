# Dataset Guide: Customer Support on Twitter

This project uses the **Customer Support on Twitter** dataset from Kaggle:
- **Kaggle Link:** [thoughtvector/customer-support-on-twitter](https://www.kaggle.com/datasets/thoughtvector/customer-support-on-twitter)
- **Original File:** `twcs.csv` (~3 million tweets across major brands like AmazonHelp, AppleSupport, SpotifyCares, Delta, etc.)

---

## 1. Quick Start (Sample Prepared Out of the Box)

For immediate, 100% reproducible execution without requiring a Kaggle account or downloading the full 500MB file:
```bash
python data/download_or_prepare.py --use-curated-sample
```
This prepares a curated, high-fidelity corpus of historical Twitter support interactions for `@AmazonHelp` directly into:
- `data/raw/amazon_support_sample.csv`
- `data/processed/train_corpus.json` (grounding retrieval knowledge base)
- `data/processed/eval_pool.json` (evaluation candidates with strict leakage filtering)

---

## 2. Using the Full Kaggle Dataset (`twcs.csv`)

If you have downloaded the full `twcs.csv` (or downloaded via `kaggle datasets download -d thoughtvector/customer-support-on-twitter`):

1. Place `twcs.csv` in `data/raw/twcs.csv` (or specify path with `--data-path`).
2. Run data exploration to inspect brand distributions:
   ```bash
   python data/explore.py --data-path data/raw/twcs.csv
   ```
3. Run preprocessing for `@AmazonHelp` (or any target brand like `AppleSupport`):
   ```bash
   python data/preprocess.py --data-path data/raw/twcs.csv --brand AmazonHelp --sample-size 50000 --seed 42
   ```

---

## 3. Brand Selection Rationale: Why `@AmazonHelp`?

We selected **`@AmazonHelp`** as the primary focus brand for the following reasons:
1. **High Volume & Diversity:** Over 500,000 tweets covering delivery, returns, digital streaming, Prime billing, hardware devices, and account security.
2. **Clear Auto-Handle vs. Escalation Triage:** Unlike brands that immediately reply with generic DM requests to 100% of tweets (e.g. Apple), Amazon historically resolved many inquiries with public self-service links (tracking, returns portal, device reboots) while escalating high-risk security/financial cases to private DM.
3. **Realistic Edge Cases:** Rich presence of frustrated customers, courier handoff failures, and multi-turn exchanges that test agent reliability.

---

## 4. Leakage Prevention Methodology

In accordance with strict ML engineering standards:
- Exact string duplicate removal on normalized customer inquiries.
- MinHash / Jaccard n-gram similarity filtering (> 0.70 threshold discarded from eval pool).
- Train/Evaluation splits are stratified across intent clusters to guarantee representative coverage without test set contamination.
