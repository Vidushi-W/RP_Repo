export interface TrainingPreview {
  dataset_id: number
  dataset_name: string
  provenance: string
  dataset_version: string
  train_count: number
  val_count: number
  test_count: number
  vocabulary_size: number
  schema_compatible: boolean
  warnings: string[]
  estimated_params: number
}

export interface TrainingJob {
  id: number
  name: string
  status: string
  dataset_id: number | null
  model_id: number | null
  training_mode: string
  current_epoch: number
  total_epochs: number
  train_loss: number | null
  val_loss: number | null
  val_wer: number | null
  message: string
  pid: number | null
  started_at: string | null
  completed_at: string | null
  created_at: string
  config: Record<string, unknown>
}

export interface ModelRecord {
  id: number
  name: string
  version: string
  status: string
  architecture: string
  dataset_id: number | null
  dataset_version: string | null
  provenance: string
  training_job_id: number | null
  validation_metrics: Record<string, unknown>
  vocabulary: string[]
  emotion_available: boolean
  is_archived: boolean
  created_at: string
  notes: string
}

export interface StartTrainingPayload {
  dataset_id: number
  name?: string
  training_mode?: string
  source_model_id?: number
  epochs?: number
  batch_size?: number
  learning_rate?: number
  cnn_channels?: number
  hidden_size?: number
  model_name?: string
}
