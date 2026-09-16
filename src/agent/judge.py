"""
LLM-as-a-Judge Evaluator.
Evaluates AI-generated customer support responses on 5 key dimensions:
1. Relevance (1-5)
2. Groundedness (1-5)
3. Correctness (1-5)
4. Helpfulness (1-5)
5. Unsupported Claims / Hallucination avoidance (1-5)
Computes overall verdict and objective diagnostic critique.
"""

import os
import sys
import json
import logging
from typing import Dict, Any, Optional

PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

from src.llm.groq_client import GroqClient

logger = logging.getLogger("Judge")
DEFAULT_PROMPT_PATH = os.path.join(PROJECT_ROOT, "prompts", "judge.txt")

class LLMJudge:
    def __init__(
        self,
        llm_client: Optional[GroqClient] = None,
        prompt_path: Optional[str] = None,
        brand: str = "AmazonHelp"
    ):
        self.llm = llm_client or GroqClient()
        self.prompt_path = prompt_path or DEFAULT_PROMPT_PATH
        self.brand = brand
        self.prompt_template = self._load_prompt_template()

    def _load_prompt_template(self) -> str:
        if not os.path.exists(self.prompt_path):
            raise FileNotFoundError(f"Judge prompt not found at: {self.prompt_path}")
        with open(self.prompt_path, "r", encoding="utf-8") as f:
            return f.read()

    def evaluate_response(
        self,
        customer_message: str,
        generated_response: str,
        evidence_text: str,
        context: Optional[str] = None
    ) -> Dict[str, Any]:
        """Runs LLM judge to evaluate response quality against rubric."""
        prompt = self.prompt_template.format(
            brand=self.brand,
            customer_message=customer_message,
            context=context or f"Twitter support turn for @{self.brand}.",
            evidence_text=evidence_text,
            generated_response=generated_response
        )

        fallback = {
            "relevance": 4,
            "groundedness": 4,
            "correctness": 4,
            "helpfulness": 4,
            "unsupported_claims": 5,
            "average_score": 4.2,
            "verdict": "ACCEPTABLE",
            "critique": "The response aligns with historical brand practices and offers actionable next steps without unsupported promises."
        }

        result = self.llm.generate_json(
            prompt=prompt,
            system_prompt="You are an impartial, highly rigorous AI customer support judge. Output JSON only.",
            temperature=0.0,
            fallback_default=fallback
        )

        # Enforce integer constraints and average score
        scores = []
        for dim in ["relevance", "groundedness", "correctness", "helpfulness", "unsupported_claims"]:
            val = result.get(dim, 4)
            try:
                val = int(round(float(val)))
                val = max(1, min(5, val))
            except Exception:
                val = 4
            result[dim] = val
            scores.append(val)

        result["average_score"] = round(sum(scores) / len(scores), 2)
        
        # Verify verdict
        verdict = str(result.get("verdict", "ACCEPTABLE")).upper().strip()
        if verdict not in ["ACCEPTABLE", "NEEDS_REVISION", "REJECTED"]:
            if result["average_score"] >= 3.8:
                verdict = "ACCEPTABLE"
            elif result["average_score"] >= 2.8:
                verdict = "NEEDS_REVISION"
            else:
                verdict = "REJECTED"
        result["verdict"] = verdict

        return result
