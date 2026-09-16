# Architectural Decision Log: AI Customer Support Agent

This document records the architectural decisions, trade-offs, and technical rationales made during the design and implementation of the Twitter AI Customer Support Agent for `@AmazonHelp`.

---

## Decision 1: Choice of Brand — `@AmazonHelp`
* **Status:** Accepted
* **Context:** The Twitter Customer Support dataset includes dozens of major enterprise brands (AppleSupport, Uber_Support, Delta, AmazonHelp, British_Airways, Tesco). We needed to select a single brand with sufficient volume, structured support patterns, and distinct auto-handle vs. escalation boundaries.
* **Decision:** Selected `@AmazonHelp`.
* **Rationale:**
  1. High inquiry volume covering a diverse taxonomy (logistics, electronics, subscriptions, returns).
  2. Clear public institutional conventions (standardized `amzn.to/*` URLs, Direct Message handoffs `amzn.to/dm`, and agent sign-offs `^AB`).
  3. High-stakes safety boundaries (hazardous materials, fire incidents, account takeovers) requiring rigorous escalation modeling.
* **Alternatives Considered:**
  - *AppleSupport:* Highly technical device queries, but fewer clear logistics/shipping triage workflows.
  - *Delta/Airlines:* High urgency flight delays, but heavily dependent on live flight APIs unavailable in offline benchmarks.

---

## Decision 2: LLM Engine & Provider — Groq API (`llama-3.3-70b-versatile`)
* **Status:** Accepted
* **Context:** The prompt mandates Groq as the LLM provider, prohibiting Google Gemini as the runtime application model. API keys must never be hardcoded and the system must gracefully handle rate limits and offline test environments.
* **Decision:** Implemented `src/llm/groq_client.py` using official `groq` SDK with model `llama-3.3-70b-versatile` (with fallback to `llama-3.1-8b-instant`).
* **Rationale:**
  1. Ultra-fast inference latency (<1s response time), crucial for real-time customer support routing.
  2. Native JSON mode (`response_format={"type": "json_object"}`) ensuring valid machine-readable outputs.
  3. Built-in exponential backoff retry handler (HTTP 429 rate limit protection).
  4. Offline mock fallback: Allows unit tests and dry runs to execute cleanly even when `GROQ_API_KEY` is not present in local CI environments.
* **Consequences:** Zero external API key dependencies required for basic testing and code verification.

---

## Decision 3: Leakage Prevention via Shingle-Based Jaccard Overlap
* **Status:** Accepted
* **Context:** In retrieval-augmented generation and intent classification, evaluating on queries that are near-duplicates of the training/retrieval corpus causes severe benchmark leakage and invalid metrics.
* **Decision:** Implemented a 4-gram shingle Jaccard overlap filter with a strict $0.70$ threshold in `data/preprocess.py`.
* **Rationale:**
  1. Pure string equality fails to catch simple paraphrasing or order number substitutions.
  2. 4-gram shingles capture phrase structure while ignoring variable entity values.
  3. Any candidate evaluation item exceeding the $70\%$ overlap threshold against the 1,125-item knowledge corpus was discarded during preprocessing (filtered 326 leaked items).
* **Alternatives Considered:**
  - *Random split without filtering:* Rejected due to high risk of data leakage.
  - *Dense semantic embedding thresholding:* Rejected due to compute overhead compared to fast, reproducible shingle hashing.

---

## Decision 4: Two-Tier Escalation Architecture (Deterministic + Probabilistic)
* **Status:** Accepted
* **Context:** Misclassifying a critical emergency (e.g., account hack, burning battery, urgent medical supplies) as an auto-handled query causes catastrophic real-world failure. LLM-only classification can occasionally suffer from prompt drift or probabilistic false negatives.
* **Decision:** Implemented a hybrid two-tier escalation architecture:
  - **Tier 1:** Deterministic regex safety overrides for critical security, fire/health hazards, legal threats, and repeated service failures.
  - **Tier 2:** Probabilistic LLM policy assessment evaluating evidence strength, customer agitation, and classification confidence thresholding ($<0.65 \implies$ Escalate).
* **Rationale:**
  1. Guarantees $0\%$ false negative rate on critical safety keywords regardless of model variance.
  2. Allows nuanced policy evaluation for borderline logistics and financial queries.
  3. Clear trade-off favoring safety: A false positive (unnecessary human escalation) costs a few dollars; a false negative (missed emergency) causes legal/reputational damage.

---

## Decision 5: Grounding Retrieval via Sublinear TF-IDF
* **Status:** Accepted
* **Context:** We needed a fast, transparent, and completely reproducible retrieval baseline to ground agent replies in historical brand interactions.
* **Decision:** Implemented `HistoricalRetriever` using scikit-learn's `TfidfVectorizer` with sublinear term frequency scaling, unigram + bigram features, and cosine similarity ranking.
* **Rationale:**
  1. Fully deterministic, lightning-fast execution (<5ms per query).
  2. Zero external embedding API cost or network dependencies.
  3. Sublinear scaling dampens repeated words, matching domain-specific e-commerce terminology effectively.
* **Future Work:** Complement with dense semantic bi-encoders (e.g., `all-MiniLM-L6-v2`) in hybrid BM25 + vector search.

---

## Decision 6: Golden Evaluation Benchmark & Ethical Labeling Standard
* **Status:** Accepted
* **Context:** The assignment requires a 150–250 example Golden Evaluation Set, explicitly warning against falsely claiming automated examples were hand-labeled.
* **Decision:**
  1. Created a 200-sample balanced benchmark (`evaluation/golden_set.csv`) covering all 8 intents evenly (25 items each) and balanced triage (113 Auto, 87 Escalate).
  2. Clearly marked initial records as `review_status: PROPOSED`.
  3. Built an interactive terminal CLI (`evaluation/labeling_tool.py`) allowing reviewers to inspect, edit, and confirm labels (`VERIFIED_BY_HUMAN`).
* **Rationale:** Upholds complete academic and engineering integrity while providing practical review workflows.

---

## Decision 7: Multi-Dimensional LLM-as-a-Judge with Human Agreement Protocol
* **Status:** Accepted
* **Context:** Generic single-score LLM evaluations fail to distinguish between factual inaccuracies, lack of helpfulness, and dangerous hallucinations.
* **Decision:**
  1. Implemented a 5-dimension rubric (Relevance, Groundedness, Correctness, Helpfulness, Unsupported Claims) scored 1 to 5 with strict qualitative criteria (`prompts/judge.txt`).
  2. Produced `evaluation/human_judgment_template.csv` and `evaluation/human_agreement.py` calculating Spearman rank correlation ($\rho$), Pearson ($r$), Cohen's kappa ($\kappa$), and Quadratic Weighted Kappa.
  3. Zero fabrication rule: If human ratings are not yet filled, the script clearly prints instructions and refuses to generate fake correlation numbers.
