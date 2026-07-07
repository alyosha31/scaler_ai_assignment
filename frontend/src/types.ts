export type GenerationStatus =
  | 'CREATED'
  | 'VALIDATING'
  | 'GENERATING_OUTLINE'
  | 'GENERATING_SEGMENTS'
  | 'EVALUATING'
  | 'REPAIRING'
  | 'READY_FOR_REVIEW'
  | 'NEEDS_REVISION'
  | 'FAILED'

export type ReviewStatus = 'DRAFT' | 'UNDER_REVIEW' | 'CHANGES_REQUESTED' | 'APPROVED'

export type InstructorBrief = {
  topic: string
  agenda: string[]
  beginner_percentage: number
  advanced_percentage: number
  duration_minutes: number
  content_percentage: number
  code_percentage: number
  topics_already_covered: string[]
}

export type ValidationWarning = {
  code: string
  message: string
  suggested_resolution: string
}

export type BriefValidationResult = {
  is_valid: boolean
  warnings: ValidationWarning[]
  errors: { code: string; message: string }[]
  normalized_brief: InstructorBrief | null
}

export type SegmentOutline = {
  id: string
  order: number
  agenda_item: string
  title: string
  duration_minutes: number
  content_minutes: number
  code_minutes: number
  learning_objective: string
  concepts_introduced: string[]
  concepts_assumed: string[]
  concepts_reinforced: string[]
  teaching_strategy: string
  example_plan: string
  activity_plan: string[]
  transition_in: string
  transition_out: string
  rationale: string
}

export type ClassOutline = {
  id: string
  topic: string
  total_duration_minutes: number
  audience_calibration: string
  target_content_minutes: number
  target_code_minutes: number
  segments: SegmentOutline[]
  recap_plan: string
  next_steps_plan: string
  global_assumptions: string[]
  design_rationale: string[]
  warnings: ValidationWarning[]
}

export type SegmentDraft = {
  id: string
  outline_id: string
  duration_minutes: number
  content_minutes: number
  code_minutes: number
  instructor_narration: string
  live_code_steps: Array<{
    order: number
    instruction: string
    code: string
    explanation: string
    expected_output: string
  }>
  worked_examples: Array<{ setup: string; walkthrough: string; takeaway: string }>
  checks: Array<{ question: string; expected_answer: string; instructor_guidance: string }>
  activities: Array<{
    type: string
    prompt: string
    expected_response: string
    facilitation_notes: string
  }>
  reviewer_rationale: string
  status: string
  version: number
}

export type EvaluationReport = {
  id: string
  structural: {
    all_agenda_items_present: boolean
    timing_sums_correctly: boolean
    content_code_ratio_within_tolerance: boolean
    prior_topics_not_reteaught: boolean
    segment_ids_stable: boolean
    failures: string[]
  }
  model_judge: null | {
    coverage_score: number
    level_fit_score: number
    pedagogy_score: number
    tone_score: number
    factuality_score: number
    pacing_score: number
    judge_rationale: string
  }
  passed_gate: boolean
  recommendations: string[]
}

export type ReviewEvent = {
  id: string
  segment_id: string | null
  type: string
  instructor_feedback: string
  version_before: number | null
  version_after: number | null
  created_at: string
}

export type ScriptProject = {
  id: string
  brief: InstructorBrief
  validation: BriefValidationResult | null
  outline: ClassOutline | null
  segments: SegmentDraft[]
  latest_evaluation: EvaluationReport | null
  review_events: ReviewEvent[]
  sign_off: null | {
    instructor_name: string
    approved: boolean
    final_notes: string
    approved_at: string
  }
  review_status: ReviewStatus
  generation_status: GenerationStatus
  generation_message: string
  generation_progress: number
  generation_error: string | null
}
