import type {
  ComparisonDetail,
  ComparisonListResponse,
  DatasetSummary,
  EvalRunDetail,
  EvalRunListResponse,
  ReviewPreview,
  SubmissionDetailResponse,
  SubmissionListResponse,
} from '../types/api'

const API_BASE = import.meta.env.VITE_API_BASE_URL ?? 'http://localhost:8000'

async function request<T>(path: string): Promise<T> {
  const response = await fetch(`${API_BASE}${path}`)
  if (!response.ok) {
    throw new Error(`Request failed: ${response.status}`)
  }
  return response.json() as Promise<T>
}

export function fetchDatasetSummary() {
  return request<DatasetSummary>('/api/datasets/summary')
}

export function fetchSubmissions(params: {
  split: 'train' | 'test'
  session: 'S1' | 'S2' | 'ALL'
  query: string
}) {
  const search = new URLSearchParams()
  search.set('split', params.split)
  if (params.session !== 'ALL') {
    search.set('session', params.session)
  }
  if (params.query.trim()) {
    search.set('query', params.query.trim())
  }
  search.set('limit', '80')
  return request<SubmissionListResponse>(`/api/submissions?${search.toString()}`)
}

export function fetchSubmissionDetail(studentId: string, session: string) {
  return request<SubmissionDetailResponse>(`/api/submissions/${studentId}/${session}`)
}

export function fetchReviewPreview(
  studentId: string,
  session: string,
  mode: 'baseline' | 'agent',
) {
  return request<ReviewPreview>(
    `/api/submissions/${studentId}/${session}/review-preview?mode=${mode}`,
  )
}

export function fetchEvalRuns(mode: 'baseline' | 'agent') {
  return request<EvalRunListResponse>(`/api/eval/runs?mode=${mode}`)
}

export function fetchEvalRunDetail(mode: 'baseline' | 'agent', runName: string) {
  return request<EvalRunDetail>(`/api/eval/runs/${mode}/${runName}`)
}

export function fetchComparisons() {
  return request<ComparisonListResponse>('/api/eval/comparisons')
}

export interface AdhocReviewBody {
  title: string
  video_url: string
  platform: string
  author: string
  session: 'S1' | 'S2'
  student_id: string
  mode: 'baseline' | 'agent'
  thumbnail_url?: string
}

export function submitAdhocReview(body: AdhocReviewBody) {
  const response = fetch(`${API_BASE}/api/submissions/review-adhoc`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(body),
  })
  return response.then(async (res) => {
    if (!res.ok) {
      const detail = await res.text()
      throw new Error(`Ad-hoc review failed (${res.status}): ${detail}`)
    }
    return (await res.json()) as ReviewPreview
  })
}

export function fetchComparisonDetail(comparisonName: string) {
  return request<ComparisonDetail>(`/api/eval/comparisons/${comparisonName}`)
}
