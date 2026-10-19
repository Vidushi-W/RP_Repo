export interface PlaygroundStatus {
  active_model: {
    id: number
    name: string
    version: string
    provenance: string
    emotion_available: boolean
  } | null
  hardware_connected: boolean
  hardware_message: string
}

export interface RecognitionMessage {
  filename: string
  validation: Record<string, unknown>
  english: string
  gloss_sequence: string[]
  emotion: string | null
  emotion_confidence: number | null
  emotion_source: string
  emotion_message: string
  decoder_score: number
  decoder_score_label: string
  uncertain: boolean
  sentence_status: string
  sentence_message: string
  model_id: number
  model_name: string
  model_version: string
  inference_ms: number
  timestamp: number
  feedback: { event_type: string; message: string; simulated: boolean } | null
  no_ground_truth_used: boolean
}

export interface DictionaryEntry {
  gloss: string
  english_concept: string
  supported_patterns: { gloss_sequence: string[]; english: string; supported: boolean }[]
  support_count: number
  provenance: string
  validation_status: string
  example_recordings: {
    recording_id: string
    dataset_id: number
    split: string
    provenance: string
    ordered_sign_labels: string
  }[]
  reliability_note: string
}

export interface DictionaryResponse {
  model_id: number
  model_name: string
  model_version: string
  provenance: string
  entries: DictionaryEntry[]
  sentence_patterns: { gloss_sequence: string[]; english: string; supported: boolean }[]
  disclaimer: string
}

export interface LiveTickResponse {
  session_id: string
  status: string
  source_type: string
  filename: string
  elapsed_ms: number
  buffer_frames: number
  speed: number
  motion: { timestamps_ms: number[]; left: number[]; right: number[] }
  provisional: {
    gloss_sequence: string[]
    english: string
    decoder_score: number
    is_provisional: boolean
    lookahead_note: string
  } | null
  finalized_messages: Record<string, unknown>[]
  auto_finalized?: Record<string, unknown>
}

export interface ChatMessage extends RecognitionMessage {
  id: string
}
