"""
Unified Customer Support Agent Pipeline.
Coordinates:
1. Intent Classification (with confidence scoring & reasoning)
2. Historical Evidence Retrieval (TF-IDF vector matching against brand corpus)
3. Escalation Triage (safety overrides + confidence thresholding + policy evaluation)
4. Response Generation (strictly grounded in evidence, Twitter-length formatted)
"""

import os
import sys
import json
import logging
from typing import Dict, Any, List, Optional

PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

from src.llm.groq_client import GroqClient
from src.agent.classifier import IntentClassifier
from src.agent.retriever import HistoricalRetriever
from src.agent.escalation import EscalationEvaluator
from src.agent.responder import ResponseGenerator

logger = logging.getLogger("Pipeline")

class CustomerSupportAgent:
    def __init__(
        self,
        api_key: Optional[str] = None,
        model: Optional[str] = None,
        brand: str = "AmazonHelp",
        confidence_threshold: float = 0.65
    ):
        self.brand = brand
        self.llm = GroqClient(api_key=api_key, model=model)
        self.retriever = HistoricalRetriever()
        self.classifier = IntentClassifier(llm_client=self.llm)
        self.escalator = EscalationEvaluator(llm_client=self.llm, confidence_threshold=confidence_threshold)
        self.responder = ResponseGenerator(llm_client=self.llm, brand=brand)
        logger.info(f"Initialized CustomerSupportAgent for brand @{brand}")

    def process_message(
        self,
        customer_message: str,
        conversation_context: Optional[str] = None
    ) -> Dict[str, Any]:
        """Processes an inbound customer support tweet and returns structured triage and reply."""
        clean_msg = customer_message.strip()
        ctx = conversation_context or f"Customer contacted @{self.brand} on Twitter."

        # Step 1: Classify intent
        classification = self.classifier.classify(customer_message=clean_msg, context=ctx)
        intent = classification.get("intent", "general_product_or_policy_inquiry")
        confidence = classification.get("confidence", 0.70)
        reasoning = classification.get("reasoning", "")

        # Step 2: Retrieve historical evidence
        evidence_items = self.retriever.retrieve(query=clean_msg, intent=intent, top_k=3)
        evidence_text = self.retriever.format_evidence_for_prompt(evidence_items)

        # Step 3: Evaluate escalation triage
        escalation_eval = self.escalator.evaluate(
            customer_message=clean_msg,
            intent=intent,
            confidence=confidence,
            evidence_summary=evidence_text,
            context=ctx
        )
        decision = escalation_eval.get("decision", "AUTO_HANDLE")
        escalation_reason = escalation_eval.get("escalation_reason", "")
        risk_level = escalation_eval.get("risk_level", "LOW")
        trigger_factor = escalation_eval.get("trigger_factor", "NONE")

        # Step 4: Generate grounded response
        resp_result = self.responder.generate_response(
            customer_message=clean_msg,
            intent=intent,
            decision=decision,
            escalation_reason=escalation_reason,
            evidence_text=evidence_text,
            context=ctx
        )
        reply = resp_result.get("reply", "")

        # Step 5: Format standardized structured output
        output = {
            "intent": intent,
            "confidence": round(float(confidence), 4),
            "intent_reasoning": reasoning,
            "decision": decision,
            "escalation_reason": escalation_reason,
            "risk_level": risk_level,
            "trigger_factor": trigger_factor,
            "reply": reply,
            "evidence": evidence_items
        }

        return output

# Convenient CLI interface for interactive query testing
if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser(description="Run Twitter Customer Support Agent Pipeline.")
    parser.add_argument("--message", type=str, required=True, help="Customer message / tweet")
    parser.add_argument("--context", type=str, default="Initial customer inquiry", help="Conversation context")
    args = parser.parse_args()

    agent = CustomerSupportAgent()
    res = agent.process_message(args.message, args.context)
    print(json.dumps(res, indent=2))
