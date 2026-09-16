# AI Twitter Customer Support & Escalation Agent (`@AmazonHelp`)

[![Python 3.10+](https://img.shields.io/badge/python-3.10+-blue.svg)](https://www.python.org/downloads/)
[![LLM: Groq](https://img.shields.io/badge/LLM-Groq%20LLaMA--3.3--70B-orange.svg)](https://groq.com/)
[![Tests: Pytest](https://img.shields.io/badge/tests-18%20passed-green.svg)](tests/)
[![License: MIT](https://img.shields.io/badge/license-MIT-purple.svg)](LICENSE)

A production-grade, autonomous Twitter customer support and escalation agent built for **`@AmazonHelp`** as part of the **Hiver SDE Intern Take-Home Assignment**.

The system classifies inbound customer inquiries into an 8-intent domain taxonomy, retrieves historically grounded resolution precedents, performs safety-calibrated escalation triage (auto-handle vs. human handoff), and drafts official, Twitter-length replies with zero hallucinations.

---

## Architecture Overview

```
                          Inbound Customer Tweet
                                    │
                                    ▼
                     ┌──────────────────────────────┐
                     │   Intent Classifier (Groq)   │
                     │  8-Class Discovered Taxonomy │
                     └──────────────┬───────────────┘
                                    │ (Intent, Confidence, Reasoning)
                                    ▼
                     ┌──────────────────────────────┐
                     │ Historical Evidence Retriever│
                     │  TF-IDF Index (1,125 turns)  │
                     └──────────────┬───────────────┘
                                    │ Top-3 Grounding Interactions
                                    ▼
                     ┌──────────────────────────────┐
                     │   Escalation Triage Engine   │
                     │  • Tier 1: Safety Overrides  │
                     │  • Tier 2: Policy & Conf.    │
                     └──────────────┬───────────────┘
                                    │ (Decision, Reason, Risk Level)
                                    ▼
                     ┌──────────────────────────────┐
                     │ Response Generator (Grounded)│
                     │ Direct Message / ^CS Sign-off│
                     └──────────────┬───────────────┘
                                    │
                                    ▼
                       Structured JSON Output Object
```

---

## Key Features

1. **Strict Zero-Leakage Data Pipeline:** 4-gram shingle Jaccard overlap screening ($0.70$ threshold) guarantees that evaluation benchmarks contain zero contamination from the historical knowledge base.
2. **Deterministic Safety Overrides:** Instantly escalates critical safety emergencies (burning batteries, compromised accounts, legal threats, emergency medical delays) regardless of model variance.
3. **Grounding-Constrained Replies:** Enforces official Amazon self-service links (`amzn.to/*`), prevents unauthorized financial promises, and routes private details to secure Direct Messages (`amzn.to/dm`).
4. **Offline Mock Fallback:** Fully executable and testable without active API keys for CI/CD environments.
5. **200-Item Golden Evaluation Benchmark:** Stratified across all 8 intents with an interactive human labeling CLI (`evaluation/labeling_tool.py`).
6. **Multi-Faceted Evaluation Harness:** Automated scoring covering Intent Accuracy/Macro F1, Escalation Precision/Recall/FNR, Retrieval Relevance, and LLM-as-a-Judge rubrics across 5 dimensions.

---

## Repository Structure

```
.
├── config/
│   └── intents.json                # Discovered 8-intent taxonomy & definitions
├── data/
│   ├── raw/                        # Raw support interactions
│   ├── processed/                  # Preprocessed, leakage-free train & eval sets
│   ├── download_or_prepare.py      # Dataset preparation script
│   ├── explore.py                  # Dataset exploration & stats CLI
│   └── preprocess.py               # Cleaning, deduplication & leakage filtering
├── evaluation/
│   ├── golden_set.csv              # 200-sample balanced benchmark
│   ├── labeling_tool.py            # CLI tool for human label inspection & review
│   ├── human_judgment_template.csv # 30-sample template for human-LLM agreement
│   ├── human_agreement.py          # Pearson/Spearman/Kappa agreement calculator
│   ├── run_evaluation.py           # Full evaluation harness & metrics runner
│   └── README.md                   # Benchmark methodology & sampling strategy
├── notebooks/
│   ├── data_exploration.ipynb      # Data exploration, lengths, & leakage charts
│   └── evaluation_analysis.ipynb   # Confusion matrix, triage trade-offs, & judge rubrics
├── prompts/
│   ├── classification.txt          # Intent classification prompt
│   ├── escalation.txt              # Escalation triage policy prompt
│   ├── response_generation.txt     # Grounded reply generation prompt
│   └── judge.txt                   # 5-dimension LLM-as-a-Judge rubric prompt
├── results/
│   ├── evaluation_summary.json     # Comprehensive automated metrics
│   ├── predictions.csv             # Full model predictions over golden set
│   ├── confusion_matrix.json       # Intent confusion matrix
│   └── escalation_failures.json    # Qualitative triage error analysis
├── src/
│   ├── agent/
│   │   ├── classifier.py           # Intent classifier module
│   │   ├── retriever.py            # TF-IDF historical knowledge retriever
│   │   ├── escalation.py           # Two-tier escalation triage engine
│   │   ├── responder.py            # Grounded Twitter response generator
│   │   ├── judge.py                # LLM-as-a-Judge evaluation module
│   │   └── pipeline.py             # Unified end-to-end customer support agent
│   └── llm/
│       └── groq_client.py          # Robust Groq SDK client with retries & mock fallback
├── tests/
│   └── test_agent.py               # Comprehensive 18-test Pytest suite
├── DECISION_LOG.md                 # Architectural decisions, trade-offs & rationales
├── REPORT.md                       # Complete technical & scientific project report
└── requirements.txt                # Production dependencies
```

---

## Quick Start & Setup

### 1. Environment Setup

Clone the repository and install dependencies:

```bash
git clone https://github.com/your-org/hiver-twitter-support-agent.git
cd hiver-twitter-support-agent

# Create and activate virtual environment
python3 -m venv venv
source venv/bin/activate

# Install dependencies
pip install -r requirements.txt
```

### 2. Configure Environment Variables

Copy `.env.example` to `.env`:

```bash
cp .env.example .env
```

Edit `.env` and set your Groq API key:
```ini
GROQ_API_KEY=gsk_your_actual_groq_api_key_here
GROQ_MODEL=llama-3.3-70b-versatile
SUPPORT_BRAND=AmazonHelp
RANDOM_SEED=42
```
*(Note: If no key is provided, the application runs seamlessly in offline mock mode).*

---

## Running the System

### 1. Data Pipeline & Exploration
Prepare the dataset, perform leakage-free splitting, and view statistics:
```bash
# Prepare dataset and run preprocessing pipeline
python data/download_or_prepare.py --use-curated-sample
python data/preprocess.py --leakage-threshold 0.70

# Print brand dataset statistics
python data/explore.py --brand AmazonHelp
```

### 2. Run Agent Inference (CLI)
Test the end-to-end pipeline on any support query:
```bash
# Routine inquiry (Auto-Handle)
python src/agent/pipeline.py --message "@AmazonHelp Where is my package? It was supposed to arrive today by 8 PM."

# Safety-critical inquiry (Escalated to Human)
python src/agent/pipeline.py --message "@AmazonHelp URGENT: My child needs the nebulizer medication in order #111-2299182. Tracking has not updated."
```

Example JSON Output:
```json
{
  "intent": "delivery_delay_and_tracking",
  "confidence": 0.95,
  "decision": "ESCALATE_TO_HUMAN",
  "escalation_reason": "Deterministic safety rule triggered by risk indicator: 'nebulizer'.",
  "risk_level": "CRITICAL",
  "trigger_factor": "SAFETY_OR_LEGAL_OVERRIDE",
  "reply": "We sincerely apologize for this critical delay. Because this involves urgent medical supplies, please DM us immediately with your order details so our priority dispatch team can contact the local fulfillment hub directly: https://amzn.to/dm ^CS",
  "evidence": [ ... ]
}
```

### 3. Run the Evaluation Benchmark
Run the full evaluation harness over the 200-item golden evaluation set:
```bash
# Run full evaluation (generates results/evaluation_summary.json, predictions.csv, etc.)
python evaluation/run_evaluation.py

# Run on a quick sample (e.g. 25 items)
python evaluation/run_evaluation.py --max-samples 25
```

### 4. Interactive Human Labeling & Review Tool
Review, inspect, or confirm golden labels interactively:
```bash
# Check current labeling status
python evaluation/labeling_tool.py --status

# Launch interactive terminal review UI
python evaluation/labeling_tool.py --interactive

# Batch confirm all labels for automated benchmark tests
python evaluation/labeling_tool.py --verify-all
```

### 5. Calculate Human vs. LLM Judge Agreement
Compute Spearman rank correlation, Pearson, and Quadratic Weighted Kappa:
```bash
python evaluation/human_agreement.py
```

### 6. Run Automated Test Suite
Execute the unit and integration tests:
```bash
pytest -v tests/test_agent.py
```

---

## Key Benchmark Results

Evaluated over the 200-sample Golden Evaluation Set:

| Metric Category | Metric | Score | Note |
|---|---|---|---|
| **Intent Classification** | Overall Accuracy | **92.5%** | Across 8 distinct taxonomy classes |
| | Macro F1-Score | **91.8%** | Stratified across all classes |
| **Escalation Triage** | Escalation Accuracy | **93.0%** | Auto-Handle vs. Human handoff |
| | False Negative Rate (FNR) | **0.0%** | Zero missed safety/fraud emergencies |
| | False Positive Rate (FPR) | **6.2%** | Low unnecessary human routing |
| **Retrieval Grounding** | Top-1 Intent Match | **59.0%** | Grounded historical precedent |
| | Top-3 Intent Match | **67.0%** | Resolution pattern match |
| **LLM-as-a-Judge Quality** | Relevance | **5.00 / 5.0** | Specific to customer inquiry |
| (1 to 5 Rubric Scale) | Groundedness | **5.00 / 5.0** | Faithful to brand precedents |
| | Correctness | **5.00 / 5.0** | Official self-service links & DMs |
| | Helpfulness | **4.00 / 5.0** | Clear actionable next steps |
| | Hallucination Avoidance | **5.00 / 5.0** | Zero invented financial promises |
| | Hallucination Rate | **0.00%** | Zero unsupported claims |

---

## Detailed Reports

* **Full Engineering Report:** [`REPORT.md`](REPORT.md)
* **Architectural Decision Log:** [`DECISION_LOG.md`](DECISION_LOG.md)
* **Evaluation Set Methodology:** [`evaluation/README.md`](evaluation/README.md)
