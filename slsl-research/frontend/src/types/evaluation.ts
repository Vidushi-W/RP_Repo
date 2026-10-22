export interface EvalCompatibility {
  model_id: number
  model_name: string
  model_version: string
  model_provenance: string
  training_dataset_id: number | null
  training_dataset_version: string | null
  dataset_id: number
  dataset_name: string
  dataset_version: string
  dataset_provenance: string
  split: string
  split_counts: Record<string, number>
  recommended_split: string
  compatible: boolean
  schema_compatible: boolean
  vocabulary_warnings: string[]
  signer_analysis: {
    training_signer_count: number
    evaluation_signer_count: number
    unseen_signers: string[]
    supports_unseen_signer_eval: boolean
    note: string
  }
  warnings: string[]
}

export interface EvaluationRun {
  id: number
  name: string
  status: string
  model_id: number | null
  dataset_id: number | null
  dataset_version: string | null
  split_used: string
  provenance: string
  summary: string
  message: string
  sequence_accuracy: number | null
  word_error_rate: number | null
  metrics: Record<string, unknown>
  config: Record<string, unknown>
  created_at: string
  completed_at: string | null
}

export interface AlignmentStep {
  op: 'match' | 'substitution' | 'insertion' | 'deletion'
  ref: string | null
  pred: string | null
}

export interface PredictionRow {
  recording_id: string
  signer_id: string
  provenance: string
  split: string
  reference_signs: string[]
  predicted_signs: string[]
  reference_english: string | null
  generated_english: string
  reference_emotion: string | null
  predicted_emotion: string | null
  emotion_confidence: number | null
  decoder_score: number
  decoder_score_label: string
  high_uncertainty: boolean
  emotion_mismatch: boolean
  inference_ms: number
  exact_match: boolean
  word_error_rate: number
  insertions: number
  deletions: number
  substitutions: number
  alignment: AlignmentStep[]
}

export interface EvaluationResults {
  run: EvaluationRun
  aggregate: Record<string, number>
  emotion: Record<string, unknown>
  predictions: PredictionRow[]
  limitations: string[]
}

export interface StartEvaluationPayload {
  model_id: number
  dataset_id: number
  split?: string
  name?: string
  uncertainty_threshold?: number
}
