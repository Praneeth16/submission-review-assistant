export type ScoreBand =
  | 'early_below_750'
  | 'mid_750_999'
  | 'strong_1000_1499'
  | 'elite_1500_plus'

export type ConfidenceLevel = 'high' | 'medium' | 'low'

export interface DatasetSummary {
  train_rows: number
  test_rows: number
  students: number
  sessions: string[]
  score_bands: Record<string, number>
}

export interface SubmissionRecord {
  student_id: string
  session: string
  author: string
  score: number
  primary_title: string
  primary_platform: string
  primary_video_url: string
  primary_thumbnail_url: string
  candidate_count: number
  all_titles: string[]
  all_video_urls: string[]
  all_platforms: string[]
  selection_notes: string[]
  split: string
  row_score_band: ScoreBand
}

export interface SubmissionListResponse {
  items: SubmissionRecord[]
  total: number
  split: string
  session: string | null
  query: string | null
}

export interface ProgressionRecord {
  student_id: string
  author: string
  has_s1: 'yes' | 'no'
  has_s2: 'yes' | 'no'
  s1_score: string
  s2_score: string
  s1_primary_title: string
  s2_primary_title: string
  s1_primary_video_url: string
  s2_primary_video_url: string
  s1_candidate_count: string
  s2_candidate_count: string
}

export interface SubmissionDetailResponse {
  submission: SubmissionRecord
  progression: ProgressionRecord | null
}

export interface ReviewCriterion {
  criterion: string
  finding: string
  evidence_source: string
  confidence: ConfidenceLevel
  provisional_score_band: 'low' | 'medium' | 'high'
}

export interface ClaimVerification {
  confirmed_claims: string[]
  weak_claims: string[]
  unsupported_claims: string[]
  open_questions: string[]
}

export interface TraceStep {
  step: number
  current_question: string
  selected_tool: string
  tool_result_summary: string
  belief_update: string
  next_step: string
}

export interface ReviewPreview {
  student_id: string
  session: string
  mode: 'baseline' | 'agent'
  model: string
  predicted_score: number
  predicted_score_band: ScoreBand
  confidence: ConfidenceLevel
  needs_human_review: boolean
  summary: string
  criterion_evidence: ReviewCriterion[]
  claim_verification: ClaimVerification
  trace: TraceStep[]
}

export interface EvalRunSummary {
  mode: 'baseline' | 'agent'
  run_name: string
  created_at: string
  count: number
  exact_score_accuracy: number | null
  within_250_accuracy: number | null
  score_band_accuracy: number | null
  mean_absolute_error: number | null
  gemini_configured: boolean
}

export interface EvalRunListResponse {
  items: EvalRunSummary[]
  mode: 'baseline' | 'agent'
}

export interface EvalRunDetailRow {
  student_id: string
  session: string
  author: string
  title: string
  ground_truth_score: string
  ground_truth_band: ScoreBand
  predicted_score: string
  predicted_score_band: ScoreBand
  confidence: ConfidenceLevel
  needs_human_review: boolean | string
  model: string
  summary: string
}

export interface EvalRunDetail {
  mode: 'baseline' | 'agent'
  run_name: string
  metrics: Record<string, unknown>
  config: Record<string, unknown>
  rows: EvalRunDetailRow[]
}

export interface ComparisonSummary {
  comparison_name: string
  created_at: string
  label_a: string
  label_b: string
  shared_count: number
  metric_deltas: Record<string, number>
}

export interface ComparisonListResponse {
  items: ComparisonSummary[]
}

export interface ComparisonDetail {
  comparison_name: string
  label_a: string
  label_b: string
  run_a_path: string
  run_b_path: string
  shared_count: number
  run_a_metrics: Record<string, number>
  run_b_metrics: Record<string, number>
  metric_deltas: Record<string, number>
  run_b_best_wins: Array<Record<string, string | number>>
  run_a_best_wins: Array<Record<string, string | number>>
}
