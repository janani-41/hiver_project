export interface EvidenceItem {
  conversation_id: string;
  customer_message: string;
  historical_response: string;
  similarity_score: number;
  intent: string;
}

export interface AgentResponse {
  intent: string;
  confidence: number;
  reasoning: string;
  decision: "AUTO_HANDLE" | "ESCALATE_TO_HUMAN";
  escalation_reason: string;
  risk_level: "LOW" | "MEDIUM" | "HIGH" | "CRITICAL";
  trigger_factor: string;
  reply: string;
  evidence: EvidenceItem[];
}

export interface EvaluationSummary {
  timestamp: string;
  evaluation_samples: number;
  execution_time_seconds: number;
  intent_classification: {
    accuracy: number;
    macro_precision: number;
    macro_recall: number;
    macro_f1: number;
  };
  escalation_triage: {
    accuracy: number;
    precision: number;
    recall: number;
    f1: number;
    false_positive_rate_unnecessary_escalations: number;
    false_negative_rate_missed_critical_escalations: number;
    true_positives: number;
    false_positives: number;
    true_negatives: number;
    false_negatives: number;
  };
  retrieval_performance: {
    top1_intent_match_accuracy: number;
    top3_intent_match_accuracy: number;
    average_cosine_similarity: number;
  };
  response_generation_quality: {
    mean_relevance: number;
    mean_groundedness: number;
    mean_correctness: number;
    mean_helpfulness: number;
    mean_unsupported_claims: number;
    overall_average_score: number;
    hallucination_rate: number;
    acceptable_pct: number;
  };
}

export interface ConfusionMatrixData {
  labels: string[];
  matrix: number[][];
}

export interface GoldenSample {
  id: string;
  customer_message: string;
  gold_intent: string;
  gold_escalation: string;
  gold_reason: string;
  review_status: string;
  reply?: string;
  pred_intent?: string;
  pred_escalation?: string;
  judge_relevance?: number;
  judge_groundedness?: number;
  judge_correctness?: number;
  judge_helpfulness?: number;
  judge_unsupported_claims?: number;
  judge_average_score?: number;
  judge_verdict?: string;
}

export interface HumanRating {
  relevance: number;
  groundedness: number;
  correctness: number;
  notes?: string;
  updated_at?: string;
}

export type HumanJudgmentsMap = Record<string, HumanRating>;

export interface HumanAgreementStats {
  status: string;
  filled_samples?: number;
  matched_samples?: number;
  total_samples?: number;
  instructions?: string;
  dimensions?: Record<
    string,
    {
      spearman_rho: number;
      spearman_p_val: number;
      pearson_r: number;
      quadratic_weighted_kappa: number;
      human_mean: number;
      judge_mean: number;
    }
  >;
}

export interface TaxonomyIntent {
  name: string;
  description: string;
  typical_customer_phrases: string[];
  auto_handle_criteria: string;
  escalation_triggers: string[];
}
