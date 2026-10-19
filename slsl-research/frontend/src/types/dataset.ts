export interface DatasetSummary {
  id: number
  name: string
  description: string
  provenance: string
  status: string
  current_version: string
  recording_count: number
  created_at: string
  updated_at?: string
}

export interface RecordingSummary {
  id: number
  recording_id: string
  signer_id: string
  provenance: string
  ordered_sign_labels: string
  emotion_label: string
  reference_english_sentence: string
  split: string
  duration_ms: number
  frame_count: number
  sample_rate_hz: number
}

export interface ChartSeries {
  timestamps_ms: number[]
  values: number[]
}

export interface RecordingDetail extends RecordingSummary {
  file_path: string
  collection_date?: string | null
  group_id: string
  validation: {
    valid: boolean
    errors: string[]
    warnings: string[]
    frame_count: number
    duration_ms: number
    estimated_sample_rate_hz: number
  }
  visualization: {
    left_motion: ChartSeries
    right_motion: ChartSeries
    left_flex_1: ChartSeries
    right_flex_1: ChartSeries
  }
}

export interface ImportPreviewItem {
  filename: string
  valid: boolean
  errors: string[]
  warnings: string[]
  frame_count: number
  duration_ms: number
}

export interface ImportJob {
  id: number
  dataset_id: number | null
  status: string
  step: string
  source_name: string
  report: Record<string, unknown>
  created_at: string
}

export interface DatasetValidationReport {
  dataset_id: number
  recording_count: number
  valid_recordings: number
  invalid_recordings: number
  split_counts: Record<string, number>
  split_isolation_errors: string[]
  issues: string[]
}
