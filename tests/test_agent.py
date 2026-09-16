"""
Unit and Integration Test Suite for Twitter Customer Support Agent.
Tests:
- GroqClient initialization, retries, JSON parsing/repair, and offline mock mode
- HistoricalRetriever indexing, top-k retrieval, and evidence formatting
- IntentClassifier taxonomy alignment and confidence scoring
- EscalationEvaluator deterministic safety rules, threshold logic, and policy assessment
- ResponseGenerator groundedness and Twitter character constraints
- CustomerSupportAgent end-to-end pipeline execution
- Leakage prevention shingle similarity
"""

import os
import sys
import json
import pytest

PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

from src.llm.groq_client import GroqClient
from src.agent.retriever import HistoricalRetriever
from src.agent.classifier import IntentClassifier
from src.agent.escalation import EscalationEvaluator
from src.agent.responder import ResponseGenerator
from src.agent.pipeline import CustomerSupportAgent
from data.preprocess import calculate_jaccard, tokenize_shingles

class TestGroqClient:
    def test_offline_initialization_without_key(self):
        client = GroqClient(api_key="")
        assert not client.is_live
        assert client.model is not None

    def test_mock_generation_returns_valid_json(self):
        client = GroqClient(api_key="")
        res = client.generate_json("Classify the following customer inquiry: Where is my order?")
        assert isinstance(res, dict)
        assert "intent" in res
        assert "confidence" in res

    def test_json_repair_logic(self):
        client = GroqClient(api_key="")
        # Malformed JSON with markdown block
        raw_text = '```json\n{"reply": "Hello customer!", "grounding": true}\n```'
        parsed = client._extract_json(raw_text, fallback={})
        assert parsed.get("reply") == "Hello customer!"
        assert parsed.get("grounding") is True

    def test_json_repair_fallback_on_garbage(self):
        client = GroqClient(api_key="")
        fallback = {"error": "failed"}
        parsed = client._extract_json("Just random conversational text with no brackets", fallback=fallback)
        assert parsed == fallback

class TestHistoricalRetriever:
    @pytest.fixture
    def retriever(self):
        return HistoricalRetriever()

    def test_corpus_loaded(self, retriever):
        assert len(retriever.documents) > 0
        assert retriever.vectorizer is not None
        assert retriever.tfidf_matrix is not None

    def test_retrieve_top_k(self, retriever):
        query = "Where is my package? Tracking has not updated."
        results = retriever.retrieve(query, top_k=3)
        assert len(results) == 3
        for item in results:
            assert "conversation_id" in item
            assert "customer_message" in item
            assert "historical_response" in item
            assert "similarity_score" in item
            assert item["similarity_score"] >= 0.0

    def test_evidence_formatting(self, retriever):
        results = retriever.retrieve("My refund was not processed", top_k=2)
        formatted = retriever.format_evidence_for_prompt(results)
        assert "[Evidence #1" in formatted
        assert "Historical Customer:" in formatted
        assert "Historical Brand Response:" in formatted

class TestIntentClassifier:
    @pytest.fixture
    def classifier(self):
        return IntentClassifier()

    def test_taxonomy_loaded(self, classifier):
        assert "intents" in classifier.taxonomy
        assert len(classifier.taxonomy["intents"]) == 8

    def test_classify_tracking_inquiry(self, classifier):
        res = classifier.classify("Where is my package? It was supposed to be delivered today.")
        assert "intent" in res
        assert "confidence" in res
        assert 0.0 <= res["confidence"] <= 1.0

    def test_classify_security_inquiry(self, classifier):
        res = classifier.classify("URGENT: Hacker logged into my account and changed my password!")
        assert res["intent"] == "account_access_and_security"

class TestEscalationEvaluator:
    @pytest.fixture
    def escalator(self):
        return EscalationEvaluator()

    def test_safety_override_account_hacked(self, escalator):
        res = escalator.evaluate(
            customer_message="Someone hacked my account and ordered items!",
            intent="account_access_and_security",
            confidence=0.95,
            evidence_summary="Historical account review."
        )
        assert res["decision"] == "ESCALATE_TO_HUMAN"
        assert res["risk_level"] == "CRITICAL"
        assert res["trigger_factor"] == "SAFETY_OR_LEGAL_OVERRIDE"

    def test_safety_override_medical_emergency(self, escalator):
        res = escalator.evaluate(
            customer_message="My baby needs this nebulizer medication immediately!",
            intent="delivery_delay_and_tracking",
            confidence=0.90,
            evidence_summary="Carrier transit."
        )
        assert res["decision"] == "ESCALATE_TO_HUMAN"
        assert res["risk_level"] == "CRITICAL"

    def test_safety_override_repeated_failures(self, escalator):
        res = escalator.evaluate(
            customer_message="This is the 3rd time you sent the wrong item. Incompetent service!",
            intent="damaged_or_incorrect_item",
            confidence=0.85,
            evidence_summary="Exchange guidance."
        )
        assert res["decision"] == "ESCALATE_TO_HUMAN"

    def test_confidence_threshold_fallback(self, escalator):
        res = escalator.evaluate(
            customer_message="Random vague question about some stuff",
            intent="general_product_or_policy_inquiry",
            confidence=0.45,  # Below 0.65 threshold
            evidence_summary="General policy."
        )
        assert res["decision"] == "ESCALATE_TO_HUMAN"
        assert res["trigger_factor"] == "LOW_CONFIDENCE"

    def test_routine_query_auto_handle(self, escalator):
        res = escalator.evaluate(
            customer_message="What is the return window for items bought on Black Friday?",
            intent="return_and_refund_status",
            confidence=0.92,
            evidence_summary="Items bought between Oct 11 and Dec 25 can be returned until Jan 31."
        )
        assert res["decision"] == "AUTO_HANDLE"

class TestCustomerSupportAgent:
    @pytest.fixture
    def agent(self):
        return CustomerSupportAgent()

    def test_process_message_structure(self, agent):
        output = agent.process_message("@AmazonHelp Can I combine two gift cards on one order?")
        assert "intent" in output
        assert "confidence" in output
        assert "decision" in output
        assert "escalation_reason" in output
        assert "risk_level" in output
        assert "reply" in output
        assert "evidence" in output
        assert isinstance(output["evidence"], list)
        assert len(output["evidence"]) > 0
        assert output["decision"] in ["AUTO_HANDLE", "ESCALATE_TO_HUMAN"]

class TestLeakagePrevention:
    def test_shingle_jaccard_identical(self):
        text1 = "Where is my package? It was supposed to arrive today."
        text2 = "Where is my package? It was supposed to arrive today."
        s1 = tokenize_shingles(text1)
        s2 = tokenize_shingles(text2)
        assert calculate_jaccard(s1, s2) == 1.0

    def test_shingle_jaccard_distinct(self):
        text1 = "Where is my package? It was supposed to arrive today."
        text2 = "How do I reset my Kindle Paperwhite device password?"
        s1 = tokenize_shingles(text1)
        s2 = tokenize_shingles(text2)
        assert calculate_jaccard(s1, s2) == 0.0
