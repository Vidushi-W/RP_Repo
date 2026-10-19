export interface HealthResponse {
  status: string
  service: string
}

export interface ModelSummary {
  id: number
  name: string
  version: string
  status: string
}

export interface TrainingJobSummary {
  id: number
  name: string
  status: string
  message: string
  updated_at?: string | null
}

export interface EvaluationSummary {
  id: number
  name: string
  status: string
  summary: string
  sequence_accuracy?: number | null
  created_at?: string | null
}

export interface ActivityItem {
  id: number
  event_type: string
  message: string
  created_at: string
}

export interface SystemStatus {
  backend_healthy: boolean
  database_ready: boolean
  dataset_count: number
  model_count: number
  active_model: ModelSummary | null
  latest_training_job: TrainingJobSummary | null
  latest_evaluation: EvaluationSummary | null
  recent_activity: ActivityItem[]
  setup_complete: boolean
  hardware_gloves_connected: boolean
  features: Record<string, string>
}
