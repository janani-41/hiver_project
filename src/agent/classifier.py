"""
Customer Support Intent Classifier.
Loads intent taxonomy from config/intents.json, formats few-shot definitions,
and leverages Groq LLM to accurately categorize customer queries with confidence estimates.
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
DEFAULT_INTENTS_PATH = os.path.join(PROJECT_ROOT, "config", "intents.json")
DEFAULT_PROMPT_PATH = os.path.join(PROJECT_ROOT, "prompts", "classification.txt")

class IntentClassifier:
    def __init__(
        self,
        llm_client: Optional[GroqClient] = None,
        intents_path: Optional[str] = None,
        prompt_path: Optional[str] = None
    ):
        self.llm = llm_client or GroqClient()
        self.intents_path = intents_path or DEFAULT_INTENTS_PATH
        self.prompt_path = prompt_path or DEFAULT_PROMPT_PATH
        self.taxonomy = self._load_taxonomy()
        self.prompt_template = self._load_prompt_template()

    def _load_taxonomy(self) -> Dict[str, Any]:
        if not os.path.exists(self.intents_path):
            raise FileNotFoundError(f"Intents taxonomy config not found at: {self.intents_path}")
        with open(self.intents_path, "r", encoding="utf-8") as f:
            return json.load(f)

    def _load_prompt_template(self) -> str:
        if not os.path.exists(self.prompt_path):
            raise FileNotFoundError(f"Classification prompt not found at: {self.prompt_path}")
        with open(self.prompt_path, "r", encoding="utf-8") as f:
            return f.read()

    def _format_taxonomy_definitions(self) -> str:
        blocks = []
        for item in self.taxonomy.get("intents", []):
            name = item.get("intent")
            desc = item.get("definition")
            examples = item.get("examples", [])
            ex_str = " | ".join([f'"{e}"' for e in examples[:3]])
            blocks.append(f"- Intent: {name}\n  Definition: {desc}\n  Examples: {ex_str}")
        return "\n\n".join(blocks)

    def classify(self, customer_message: str, context: Optional[str] = None) -> Dict[str, Any]:
        """Classifies incoming message into one of the brand's validated intents."""
        ctx = context or "Initial customer support inquiry on Twitter."
        definitions = self._format_taxonomy_definitions()
        brand = self.taxonomy.get("brand", "AmazonHelp")

        prompt = self.prompt_template.format(
            brand=brand,
            intent_definitions=definitions,
            context=ctx,
            customer_message=customer_message
        )

        fallback = {
            "intent": "general_product_or_policy_inquiry",
            "confidence": 0.5,
            "reasoning": "Default classification fallback."
        }

        result = self.llm.generate_json(
            prompt=prompt,
            system_prompt="You are a strict, objective customer support intent classifier outputting JSON only.",
            temperature=0.1,
            fallback_default=fallback
        )

        # Validate that intent exists in taxonomy
        valid_intent_names = [i["intent"] for i in self.taxonomy.get("intents", [])]
        intent = result.get("intent")
        if intent not in valid_intent_names:
            logger.warning(f"Classified intent '{intent}' not in known taxonomy. Mapping to closest match.")
            # Map by substring match or default
            matched = False
            for valid in valid_intent_names:
                if valid in str(intent) or str(intent) in valid:
                    result["intent"] = valid
                    matched = True
                    break
            if not matched:
                result["intent"] = "general_product_or_policy_inquiry"
                result["confidence"] = min(result.get("confidence", 0.5), 0.5)

        # Ensure confidence is float between 0.0 and 1.0
        try:
            conf = float(result.get("confidence", 0.75))
            result["confidence"] = max(0.0, min(1.0, conf))
        except (ValueError, TypeError):
            result["confidence"] = 0.70

        return result
