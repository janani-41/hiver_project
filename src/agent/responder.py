"""
Response Generator.
Drafts empathetic, brand-aligned Twitter customer support replies strictly grounded
in retrieved historical evidence and triage decisions.
"""

import os
import sys
import re
import logging
from typing import Dict, Any, List, Optional

PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

from src.llm.groq_client import GroqClient

logger = logging.getLogger("Responder")
DEFAULT_PROMPT_PATH = os.path.join(PROJECT_ROOT, "prompts", "response_generation.txt")

class ResponseGenerator:
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
            raise FileNotFoundError(f"Response prompt not found at: {self.prompt_path}")
        with open(self.prompt_path, "r", encoding="utf-8") as f:
            return f.read()

    def generate_response(
        self,
        customer_message: str,
        intent: str,
        evidence_text: str,
        decision: Optional[str] = "AUTO_HANDLE",
        escalation_reason: Optional[str] = "",
        context: Optional[str] = None
    ) -> Dict[str, Any]:
        """Generates grounded Twitter support reply."""
        prompt = self.prompt_template.format(
            brand=self.brand,
            customer_message=customer_message,
            context=context or f"Direct Twitter tweet to @{self.brand}.",
            intent=intent,
            evidence_text=evidence_text
        )

        fallback_reply = (
            f"We're sorry for the trouble! Please send us a direct message with your order details "
            f"so our team can look into this for you: https://amzn.to/dm ^AH"
            if decision == "ESCALATE_TO_HUMAN"
            else f"Hello! Please check your order tracking and self-service options at https://amzn.to/your-orders. "
                 f"Let us know if you need anything else! ^AH"
        )

        fallback = {
            "reply": fallback_reply,
            "grounding_summary": "Generated using verified brand support protocol fallback.",
            "requires_human_review": decision == "ESCALATE_TO_HUMAN"
        }

        result = self.llm.generate_json(
            prompt=prompt,
            system_prompt=(
                f"You are a professional customer support representative for @{self.brand} on Twitter. "
                f"Be empathetic, grounded, concise (<280 chars preferred), and output valid JSON."
            ),
            temperature=0.2,
            fallback_default=fallback
        )

        reply_text = result.get("reply", fallback_reply).strip()
        
        # Ensure agent initials signature (^AB style) exists to mimic authentic Twitter support
        if not re.search(r'\^[A-Z]{2}$', reply_text):
            reply_text = f"{reply_text} ^CS"
            
        result["reply"] = reply_text
        return result
