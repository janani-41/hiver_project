"""
Historical Support Interaction Retriever.
Uses TF-IDF vectorization with sublinear scaling, n-gram features (1, 2),
and cosine similarity to retrieve grounded historical evidence from the target brand's corpus.
"""

import os
import json
import logging
from typing import List, Dict, Any, Optional
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity

logger = logging.getLogger("Retriever")

DEFAULT_CORPUS_PATH = os.path.join(
    os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..")),
    "data", "processed", "train_corpus.json"
)

class HistoricalRetriever:
    def __init__(self, corpus_path: Optional[str] = None, top_k: int = 3):
        self.corpus_path = corpus_path or DEFAULT_CORPUS_PATH
        self.top_k = top_k
        self.documents: List[Dict[str, Any]] = []
        self.vectorizer: Optional[TfidfVectorizer] = None
        self.tfidf_matrix = None
        self._initialize_corpus()

    def _initialize_corpus(self):
        if not os.path.exists(self.corpus_path):
            logger.warning(f"Corpus not found at '{self.corpus_path}'. Initializing empty retriever.")
            return

        with open(self.corpus_path, "r", encoding="utf-8") as f:
            self.documents = json.load(f)

        logger.info(f"Loaded {len(self.documents):,} historical support interactions from corpus.")
        if not self.documents:
            return

        # Prepare text representation for retrieval
        corpus_texts = [
            f"{doc.get('customer_message', '')} {doc.get('conversation_context', '')}"
            for doc in self.documents
        ]

        self.vectorizer = TfidfVectorizer(
            ngram_range=(1, 2),
            sublinear_tf=True,
            stop_words="english",
            max_features=15000
        )
        self.tfidf_matrix = self.vectorizer.fit_transform(corpus_texts)
        logger.info(f"Fitted TF-IDF index across {self.tfidf_matrix.shape[1]:,} features.")

    def retrieve(
        self,
        query: str,
        intent: Optional[str] = None,
        top_k: Optional[int] = None
    ) -> List[Dict[str, Any]]:
        """Retrieves top-k historical interactions most similar to incoming inquiry."""
        k = top_k or self.top_k
        if not self.vectorizer or self.tfidf_matrix is None or not self.documents:
            return []

        query_vec = self.vectorizer.transform([query])
        scores = cosine_similarity(query_vec, self.tfidf_matrix).flatten()

        # Sort indices by score descending
        ranked_indices = scores.argsort()[::-1]

        results = []
        seen_texts = set()

        for idx in ranked_indices:
            score = float(scores[idx])
            doc = self.documents[idx]
            
            # Optional intent matching boost or filter
            if intent and doc.get("intent") != intent:
                # Downweight if intent differs
                score *= 0.85
                
            resp_snippet = doc.get("historical_response", "").strip()
            if resp_snippet in seen_texts:
                continue
            seen_texts.add(resp_snippet)

            evidence_item = {
                "conversation_id": doc.get("id") or doc.get("conversation_id", f"hist_{idx}"),
                "customer_message": doc.get("customer_message", ""),
                "historical_response": doc.get("historical_response", ""),
                "intent": doc.get("intent", "unknown"),
                "similarity_score": round(score, 4)
            }
            results.append(evidence_item)
            if len(results) >= k:
                break

        return results

    def format_evidence_for_prompt(self, evidence_list: List[Dict[str, Any]]) -> str:
        """Formats retrieved historical items into clean markdown for Groq prompt context."""
        if not evidence_list:
            return "No close historical evidence retrieved. Exercise high caution and acknowledge uncertainty."

        formatted_blocks = []
        for i, ev in enumerate(evidence_list, 1):
            block = (
                f"[Evidence #{i} | Similarity: {ev.get('similarity_score', 0.0):.2f}]\n"
                f"Historical Customer: \"{ev.get('customer_message')}\"\n"
                f"Historical Brand Response: \"{ev.get('historical_response')}\""
            )
            formatted_blocks.append(block)

        return "\n\n".join(formatted_blocks)
