"""
Escalation Triage Evaluator.
Determines whether an inbound inquiry should be auto-handled or escalated to a human agent.
Enforces deterministic safety overrides and calibrated confidence thresholds.
"""

import os
import sys
import re
import logging
from typing import Dict, Any, Optional

PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

from src.llm.groq_client import GroqClient

logger = logging.getLogger("Escalation")
DEFAULT_PROMPT_PATH = os.path.join(PROJECT_ROOT, "prompts", "escalation.txt")

SAFETY_OVERRIDE_PATTERNS = [
    r'\b(?:hacked|hacker|unauthorized|stolen card|identity theft|fraud)\b',
    r'(?<!fire\s)(?<!fire\shd\s)\b(?:caught fire|burst into flames|smoke|smoking|exploded|explosion|electric shock|poison|choking|infant|nebulizer|insulin)\b',
    r'\b(?:lawyer|attorney|sue|lawsuit|police|attorney general|bbb complaint)\b',
    r'\b(?:3rd time|third time|4th time|fourth time|multiple times|never resolved|incompetent)\b'
]

class EscalationEvaluator:
    def __init__(
        self,
        llm_client: Optional[GroqClient] = None,
        prompt_path: Optional[str] = None,
        brand: str = "AmazonHelp",
        confidence_threshold: float = 0.65
    ):
        self.llm = llm_client or GroqClient()
        self.prompt_path = prompt_path or DEFAULT_PROMPT_PATH
        self.brand = brand
        self.confidence_threshold = confidence_threshold
        self.prompt_template = self._load_prompt_template()

    def _load_prompt_template(self) -> str:
        if not os.path.exists(self.prompt_path):
            raise FileNotFoundError(f"Escalation prompt not found at: {self.prompt_path}")
        with open(self.prompt_path, "r", encoding="utf-8") as f:
            return f.read()

    def _check_safety_overrides(self, customer_message: str) -> Optional[Dict[str, Any]]:
        """Fast-path deterministic rule engine for high-liability triggers."""
        msg_lower = customer_message.lower()
        for pattern in SAFETY_OVERRIDE_PATTERNS:
            match = re.search(pattern, msg_lower)
            if match:
                matched_term = match.group(0)
                logger.info(f"Triggered safety override rule: '{matched_term}'")
                return {
                    "decision": "ESCALATE_TO_HUMAN",
                    "escalation_reason": f"Deterministic safety rule triggered by risk indicator: '{matched_term}'.",
                    "risk_level": "CRITICAL",
                    "trigger_factor": "SAFETY_OR_LEGAL_OVERRIDE"
                }
        return None

    def evaluate(
        self,
        customer_message: str,
        intent: str,
        confidence: float,
        evidence_summary: str,
        drafted_reply: Optional[str] = "",
        context: Optional[str] = None
    ) -> Dict[str, Any]:
        """Evaluates whether to AUTO_HANDLE or ESCALATE_TO_HUMAN."""
        # 1. Deterministic safety check
        override = self._check_safety_overrides(customer_message)
        if override:
            return override

        # 2. Confidence threshold fallback
        if confidence < self.confidence_threshold:
            return {
                "decision": "ESCALATE_TO_HUMAN",
                "escalation_reason": f"Intent classification confidence ({confidence:.2f}) below calibrated threshold ({self.confidence_threshold:.2f}).",
                "risk_level": "MEDIUM",
                "trigger_factor": "LOW_CONFIDENCE"
            }

        # 3. LLM-based nuanced policy assessment
        prompt = self.prompt_template.format(
            brand=self.brand,
            customer_message=customer_message,
            context=context or "Twitter direct interaction.",
            intent=intent,
            intent_confidence=f"{confidence:.2f}",
            drafted_reply=drafted_reply or "Awaiting triage decision before final reply rendering.",
            evidence_text=evidence_summary
        )

        fallback = {
            "decision": "ESCALATE_TO_HUMAN",
            "escalation_reason": "Fallback escalation due to policy evaluation ambiguity.",
            "risk_level": "MEDIUM",
            "trigger_factor": "UNCERTAINTY"
        }

        result = self.llm.generate_json(
            prompt=prompt,
            system_prompt="You are an expert customer support triage officer assessing escalation risk. Output JSON only.",
            temperature=0.1,
            fallback_default=fallback
        )

        decision = str(result.get("decision", "AUTO_HANDLE")).upper().strip()
        if "ESCALAT" in decision or "HUMAN" in decision:
            result["decision"] = "ESCALATE_TO_HUMAN"
        else:
            result["decision"] = "AUTO_HANDLE"

        if "escalation_reason" not in result or not result["escalation_reason"]:
            result["escalation_reason"] = "Standard self-service resolution path." if result["decision"] == "AUTO_HANDLE" else "Customer requires human agent intervention."

        return result
