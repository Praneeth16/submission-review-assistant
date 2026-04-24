import { useEffect, useMemo, useState } from 'react'

import {
  fetchComparisonDetail,
  fetchComparisons,
  fetchDatasetSummary,
  fetchEvalRunDetail,
  fetchEvalRuns,
  fetchReviewPreview,
  fetchSubmissionDetail,
  fetchSubmissions,
} from './lib/api'
import type {
  ComparisonDetail,
  ComparisonSummary,
  ConfidenceLevel,
  DatasetSummary,
  EvalRunDetail,
  EvalRunSummary,
  ReviewPreview,
  SubmissionDetailResponse,
  SubmissionRecord,
} from './types/api'

type SplitMode = 'train' | 'test'
type SessionMode = 'ALL' | 'S1' | 'S2'
type ReviewMode = 'baseline' | 'agent'
type ThemeMode = 'dark' | 'light'

const confidenceTone: Record<ConfidenceLevel, string> = {
  high: 'tone-high',
  medium: 'tone-medium',
  low: 'tone-low',
}

function App() {
  const [theme, setTheme] = useState<ThemeMode>(() => {
    if (typeof window === 'undefined') {
      return 'dark'
    }
    const stored = window.localStorage.getItem('submission-review-theme')
    if (stored === 'dark' || stored === 'light') {
      return stored
    }
    return window.matchMedia('(prefers-color-scheme: light)').matches ? 'light' : 'dark'
  })

  const [summary, setSummary] = useState<DatasetSummary | null>(null)
  const [submissions, setSubmissions] = useState<SubmissionRecord[]>([])
  const [selected, setSelected] = useState<SubmissionRecord | null>(null)
  const [detail, setDetail] = useState<SubmissionDetailResponse | null>(null)
  const [review, setReview] = useState<ReviewPreview | null>(null)
  const [split, setSplit] = useState<SplitMode>('test')
  const [session, setSession] = useState<SessionMode>('ALL')
  const [reviewMode, setReviewMode] = useState<ReviewMode>('agent')
  const [query, setQuery] = useState('')
  const [loadingList, setLoadingList] = useState(false)
  const [loadingDetail, setLoadingDetail] = useState(false)
  const [loadingReview, setLoadingReview] = useState(false)
  const [baselineRuns, setBaselineRuns] = useState<EvalRunSummary[]>([])
  const [agentRuns, setAgentRuns] = useState<EvalRunSummary[]>([])
  const [comparisonRuns, setComparisonRuns] = useState<ComparisonSummary[]>([])
  const [selectedBaselineRun, setSelectedBaselineRun] = useState<string | null>(null)
  const [selectedAgentRun, setSelectedAgentRun] = useState<string | null>(null)
  const [selectedComparisonRun, setSelectedComparisonRun] = useState<string | null>(null)
  const [baselineRunDetail, setBaselineRunDetail] = useState<EvalRunDetail | null>(null)
  const [agentRunDetail, setAgentRunDetail] = useState<EvalRunDetail | null>(null)
  const [comparisonDetail, setComparisonDetail] = useState<ComparisonDetail | null>(null)
  const [loadingEval, setLoadingEval] = useState(false)
  const [error, setError] = useState<string | null>(null)

  useEffect(() => {
    document.documentElement.dataset.theme = theme
    window.localStorage.setItem('submission-review-theme', theme)
  }, [theme])

  useEffect(() => {
    fetchDatasetSummary().then(setSummary).catch(() => setSummary(null))
  }, [])

  useEffect(() => {
    setLoadingEval(true)
    Promise.all([fetchEvalRuns('baseline'), fetchEvalRuns('agent'), fetchComparisons()])
      .then(([baselineResponse, agentResponse, comparisonResponse]) => {
        setBaselineRuns(baselineResponse.items)
        setAgentRuns(agentResponse.items)
        setComparisonRuns(comparisonResponse.items)
        setSelectedBaselineRun((current) => current ?? baselineResponse.items[0]?.run_name ?? null)
        setSelectedAgentRun((current) => current ?? agentResponse.items[0]?.run_name ?? null)
        setSelectedComparisonRun(
          (current) => current ?? comparisonResponse.items[0]?.comparison_name ?? null,
        )
      })
      .catch((err: Error) => setError(err.message))
      .finally(() => setLoadingEval(false))
  }, [])

  useEffect(() => {
    setLoadingList(true)
    fetchSubmissions({ split, session, query })
      .then((response) => {
        setSubmissions(response.items)
        setSelected((current) => {
          if (!current) {
            return response.items[0] ?? null
          }
          const stillPresent = response.items.find(
            (item) => item.student_id === current.student_id && item.session === current.session,
          )
          return stillPresent ?? response.items[0] ?? null
        })
      })
      .catch((err: Error) => setError(err.message))
      .finally(() => setLoadingList(false))
  }, [split, session, query])

  useEffect(() => {
    if (!selected) {
      setDetail(null)
      setReview(null)
      return
    }

    setLoadingDetail(true)
    fetchSubmissionDetail(selected.student_id, selected.session)
      .then(setDetail)
      .catch((err: Error) => setError(err.message))
      .finally(() => setLoadingDetail(false))
  }, [selected])

  useEffect(() => {
    if (!selected) {
      setReview(null)
      return
    }

    setLoadingReview(true)
    fetchReviewPreview(selected.student_id, selected.session, reviewMode)
      .then(setReview)
      .catch((err: Error) => setError(err.message))
      .finally(() => setLoadingReview(false))
  }, [selected, reviewMode])

  useEffect(() => {
    if (!selectedBaselineRun) {
      setBaselineRunDetail(null)
      return
    }
    fetchEvalRunDetail('baseline', selectedBaselineRun)
      .then(setBaselineRunDetail)
      .catch((err: Error) => setError(err.message))
  }, [selectedBaselineRun])

  useEffect(() => {
    if (!selectedAgentRun) {
      setAgentRunDetail(null)
      return
    }
    fetchEvalRunDetail('agent', selectedAgentRun)
      .then(setAgentRunDetail)
      .catch((err: Error) => setError(err.message))
  }, [selectedAgentRun])

  useEffect(() => {
    if (!selectedComparisonRun) {
      setComparisonDetail(null)
      return
    }
    fetchComparisonDetail(selectedComparisonRun)
      .then(setComparisonDetail)
      .catch((err: Error) => setError(err.message))
  }, [selectedComparisonRun])

  const datasetLine = useMemo(() => {
    if (!summary) {
      return 'Loading dataset'
    }
    return `${summary.train_rows} train rows, ${summary.test_rows} test rows, ${summary.students} students`
  }, [summary])

  return (
    <div className="app-shell">
      <header className="app-header">
        <div className="brand-block">
          <p className="eyebrow">Submission Review Copilot</p>
          <h1>Instructor scoring workspace</h1>
          <p className="lede">
            Score one submission at a time, defend the decision with evidence, and keep the
            rationale close enough to challenge it before you move on.
          </p>
        </div>

        <div className="header-actions">
          <div className="dataset-chip">
            <span className="label">Dataset</span>
            <strong>{datasetLine}</strong>
          </div>
          <button
            type="button"
            className="theme-toggle"
            onClick={() => setTheme((current) => (current === 'dark' ? 'light' : 'dark'))}
          >
            {theme === 'dark' ? 'Switch to light' : 'Switch to dark'}
          </button>
        </div>
      </header>

      <main className="product-stage">
        <aside className="panel inbox-panel">
          <div className="section-head">
            <div>
              <span className="panel-kicker">Review inbox</span>
              <h2>Choose a submission</h2>
            </div>
            <span className="chip subtle">{loadingList ? 'loading' : `${submissions.length} loaded`}</span>
          </div>

          <div className="filter-stack">
            <label className="field">
              <span>Split</span>
              <select value={split} onChange={(event) => setSplit(event.target.value as SplitMode)}>
                <option value="test">Test</option>
                <option value="train">Train</option>
              </select>
            </label>

            <label className="field">
              <span>Assignment</span>
              <div className="segmented segmented-compact">
                {(['ALL', 'S1', 'S2'] as SessionMode[]).map((option) => (
                  <button
                    key={option}
                    type="button"
                    className={option === session ? 'active' : ''}
                    onClick={() => setSession(option)}
                  >
                    {option}
                  </button>
                ))}
              </div>
            </label>

            <label className="field">
              <span>Scoring path</span>
              <div className="segmented segmented-compact">
                {(['agent', 'baseline'] as ReviewMode[]).map((option) => (
                  <button
                    key={option}
                    type="button"
                    className={option === reviewMode ? 'active' : ''}
                    onClick={() => setReviewMode(option)}
                  >
                    {option}
                  </button>
                ))}
              </div>
            </label>

            <label className="field">
              <span>Search</span>
              <input
                value={query}
                onChange={(event) => setQuery(event.target.value)}
                placeholder="author, title, or student id"
              />
            </label>
          </div>

          <div className="submission-list">
            {submissions.map((item) => {
              const active =
                selected?.student_id === item.student_id && selected.session === item.session

              return (
                <button
                  key={`${item.student_id}-${item.session}`}
                  type="button"
                  className={`submission-card ${active ? 'active' : ''}`}
                  onClick={() => setSelected(item)}
                >
                  <div className="submission-meta">
                    <span>
                      {item.session} #{item.student_id}
                    </span>
                    <strong>{item.score}</strong>
                  </div>
                  <h3>{item.primary_title}</h3>
                  <p>{item.author}</p>
                  <small>{item.primary_platform}</small>
                </button>
              )
            })}
          </div>
        </aside>

        <section className="panel scoring-panel">
          <div className="section-head">
            <div>
              <span className="panel-kicker">Scoring sheet</span>
              <h2>{selected?.primary_title ?? 'Choose a submission'}</h2>
              <p>
                {selected
                  ? `${selected.author} · ${selected.session} · primary artifact on ${selected.primary_platform}`
                  : 'Pick a submission from the inbox to open the scoring sheet.'}
              </p>
            </div>

            {selected && (
              <div className="section-actions">
                <a
                  href={selected.primary_video_url}
                  target="_blank"
                  rel="noreferrer"
                  className="action-link"
                >
                  open artifact
                </a>
                <span className="chip">historical score {selected.score}</span>
              </div>
            )}
          </div>

          <div className="score-layout">
            <div className="score-card">
              <span className="label">Predicted score</span>
              <strong>{review?.predicted_score ?? '—'}</strong>
              <p>{reviewMode === 'agent' ? 'Agent scoring path' : 'Baseline scoring path'}</p>
              {review && (
                <div className="score-flags">
                  <span className={`chip ${confidenceTone[review.confidence]}`}>{review.confidence}</span>
                  {review.needs_human_review && <span className="chip subtle">needs human review</span>}
                  <span className="chip subtle">{review.model}</span>
                </div>
              )}
            </div>

            <div className="summary-card">
              <div className="section-head section-head-inline">
                <div>
                  <span className="panel-kicker">Why this score</span>
                  <h3>Instructor explanation</h3>
                </div>
              </div>

              {loadingReview ? (
                <EmptyState message="Building scoring explanation..." />
              ) : review ? (
                <>
                  <p className="review-summary">{review.summary}</p>
                  <div className="criteria-list">
                    {review.criterion_evidence.map((criterion) => (
                      <article key={criterion.criterion} className="criterion-card">
                        <div className="criterion-topline">
                          <h3>{criterion.criterion}</h3>
                          <span className={`chip ${confidenceTone[criterion.confidence]}`}>
                            {criterion.confidence}
                          </span>
                        </div>
                        <p>{criterion.finding}</p>
                        <div className="criterion-meta">
                          <span>{criterion.evidence_source}</span>
                          <span>{criterion.provisional_score_band}</span>
                        </div>
                      </article>
                    ))}
                  </div>
                </>
              ) : (
                <EmptyState message="The score explanation will appear here." />
              )}
            </div>
          </div>
        </section>

        <aside className="panel notebook-panel">
          <div className="section-head">
            <div>
              <span className="panel-kicker">Evidence notebook</span>
              <h2>Context, proof, and doubts</h2>
            </div>
            {loadingDetail && <span className="chip subtle">loading</span>}
          </div>

          {detail?.submission ? (
            <>
              <div className="detail-grid">
                <InfoBlock label="Primary platform" value={detail.submission.primary_platform} />
                <InfoBlock label="Historical score" value={String(detail.submission.score)} />
                <InfoBlock
                  label="Selection notes"
                  value={detail.submission.selection_notes.join(', ')}
                />
                <InfoBlock label="Candidate artifacts" value={String(detail.submission.candidate_count)} />
              </div>

              <div className="alt-section">
                <h3>Alternate artifacts</h3>
                <ul>
                  {detail.submission.all_titles.map((title, index) => (
                    <li key={`${title}-${index}`}>
                      <span>{title}</span>
                      <a href={detail.submission.all_video_urls[index]} target="_blank" rel="noreferrer">
                        open
                      </a>
                    </li>
                  ))}
                </ul>
              </div>

              {detail.progression && (
                <div className="progression-strip">
                  <div>
                    <span className="label">Session 1</span>
                    <strong>{detail.progression.s1_score || '—'}</strong>
                    <p>{detail.progression.s1_primary_title || 'No Session 1 row'}</p>
                  </div>
                  <div className="progression-divider" />
                  <div>
                    <span className="label">Session 2</span>
                    <strong>{detail.progression.s2_score || '—'}</strong>
                    <p>{detail.progression.s2_primary_title || 'No Session 2 row'}</p>
                  </div>
                </div>
              )}
            </>
          ) : (
            <EmptyState message="Submission context appears here." />
          )}

          {review ? (
            <>
              <div className="claim-grid">
                <ClaimList title="Confirmed" items={review.claim_verification.confirmed_claims} />
                <ClaimList title="Weak" items={review.claim_verification.weak_claims} />
                <ClaimList title="Unsupported" items={review.claim_verification.unsupported_claims} />
                <ClaimList title="Open questions" items={review.claim_verification.open_questions} />
              </div>

              <div className="trace-wrap">
                <div className="section-head section-head-inline">
                  <div>
                    <span className="panel-kicker">Trace</span>
                    <h3>How the score was formed</h3>
                  </div>
                </div>

                <ol className="trace-list">
                  {review.trace.map((step) => (
                    <li key={step.step} className="trace-card">
                      <div className="trace-step">Step {step.step}</div>
                      <h3>{step.current_question}</h3>
                      <p>
                        <strong>Tool:</strong> {step.selected_tool}
                      </p>
                      <p>{step.tool_result_summary}</p>
                      <p>
                        <strong>Belief update:</strong> {step.belief_update}
                      </p>
                      <p>
                        <strong>Next:</strong> {step.next_step}
                      </p>
                    </li>
                  ))}
                </ol>
              </div>
            </>
          ) : (
            <EmptyState message="Evidence notes will fill in after the review runs." />
          )}
        </aside>
      </main>

      <section className="evaluation-lab">
        <div className="section-head lab-head">
          <div>
            <span className="panel-kicker">Evaluation lab</span>
            <h2>Benchmark the reviewer</h2>
            <p>Saved runs live here so you can check whether the scoring path earns its keep.</p>
          </div>
          {loadingEval && <span className="chip subtle">loading</span>}
        </div>

        <div className="lab-grid">
          <section className="panel eval-panel">
            <div className="section-head section-head-inline">
              <div>
                <span className="panel-kicker">Persisted runs</span>
                <h3>Baseline vs agent</h3>
              </div>
            </div>

            <div className="eval-grid">
              <RunColumn
                title="Baseline"
                runs={baselineRuns}
                selectedRun={selectedBaselineRun}
                onSelect={setSelectedBaselineRun}
                detail={baselineRunDetail}
              />
              <RunColumn
                title="Agent"
                runs={agentRuns}
                selectedRun={selectedAgentRun}
                onSelect={setSelectedAgentRun}
                detail={agentRunDetail}
              />
            </div>
          </section>

          <section className="panel compare-panel">
            <div className="section-head section-head-inline">
              <div>
                <span className="panel-kicker">Comparison</span>
                <h3>Run deltas</h3>
              </div>
            </div>

            <div className="comparison-shell">
              <div className="comparison-list">
                {comparisonRuns.map((run) => (
                  <button
                    key={run.comparison_name}
                    type="button"
                    className={`comparison-card ${
                      selectedComparisonRun === run.comparison_name ? 'active' : ''
                    }`}
                    onClick={() => setSelectedComparisonRun(run.comparison_name)}
                  >
                    <span className="label">{run.created_at}</span>
                    <strong>
                      {run.label_a} vs {run.label_b}
                    </strong>
                    <p>{run.shared_count} shared rows</p>
                  </button>
                ))}
              </div>

              {comparisonDetail ? (
                <div className="comparison-detail">
                  <div className="compare-metrics">
                    <MetricDelta
                      label="Exact accuracy delta"
                      value={comparisonDetail.metric_deltas.exact_score_accuracy}
                    />
                    <MetricDelta
                      label="Within-250 delta"
                      value={comparisonDetail.metric_deltas.within_250_accuracy}
                    />
                    <MetricDelta
                      label="Band accuracy delta"
                      value={comparisonDetail.metric_deltas.score_band_accuracy}
                    />
                    <MetricDelta
                      label="MAE delta"
                      value={comparisonDetail.metric_deltas.mean_absolute_error}
                      invert
                    />
                  </div>

                  <div className="comparison-columns">
                    <WinList
                      title={`${comparisonDetail.label_b} best wins`}
                      rows={comparisonDetail.run_b_best_wins}
                    />
                    <WinList
                      title={`${comparisonDetail.label_a} best wins`}
                      rows={comparisonDetail.run_a_best_wins}
                    />
                  </div>
                </div>
              ) : (
                <EmptyState message="Select a saved comparison to see its deltas." />
              )}
            </div>
          </section>
        </div>
      </section>

      {error && <div className="error-banner">{error}</div>}
    </div>
  )
}

function Metric({ label, value }: { label: string; value: string }) {
  return (
    <div className="metric">
      <span className="label">{label}</span>
      <strong>{value}</strong>
    </div>
  )
}

function InfoBlock({ label, value }: { label: string; value: string }) {
  return (
    <div className="info-block">
      <span className="label">{label}</span>
      <p>{value}</p>
    </div>
  )
}

function RunColumn({
  title,
  runs,
  selectedRun,
  onSelect,
  detail,
}: {
  title: string
  runs: EvalRunSummary[]
  selectedRun: string | null
  onSelect: (runName: string) => void
  detail: EvalRunDetail | null
}) {
  const exact = getMetricValue(detail?.metrics, 'exact_score_accuracy')
  const within = getMetricValue(detail?.metrics, 'within_250_accuracy')
  const band = getMetricValue(detail?.metrics, 'score_band_accuracy')
  const mae = getMetricValue(detail?.metrics, 'mean_absolute_error')
  const confidenceCounts = getCountMap(detail?.metrics, 'confidence_counts')
  const reviewCounts = getCountMap(detail?.metrics, 'needs_human_review_counts')

  return (
    <div className="run-column">
      <div className="run-list">
        {runs.map((run) => (
          <button
            key={run.run_name}
            type="button"
            className={`run-card ${selectedRun === run.run_name ? 'active' : ''}`}
            onClick={() => onSelect(run.run_name)}
          >
            <span className="label">{run.run_name}</span>
            <strong>{formatPercent(run.exact_score_accuracy)}</strong>
            <p>MAE {formatNumber(run.mean_absolute_error)}</p>
          </button>
        ))}
      </div>

      {detail ? (
        <div className="run-detail">
          <div className="run-meta-strip">
            <span className="chip subtle">{String(detail.config.count ?? '—')} rows</span>
            <span className="chip subtle">
              Gemini {detail.config.gemini_configured ? 'enabled' : 'fallback'}
            </span>
          </div>

          <div className="run-metric-grid">
            <Metric label="Exact" value={formatPercent(exact)} />
            <Metric label="Within 250" value={formatPercent(within)} />
            <Metric label="Band" value={formatPercent(band)} />
            <Metric label="MAE" value={formatNumber(mae)} />
          </div>

          <div className="chart-stack">
            <MetricBar label="Exact score accuracy" value={exact} />
            <MetricBar label="Within 250 accuracy" value={within} />
            <MetricBar label="Score band accuracy" value={band} />
            <MetricBar label="Error efficiency" value={mae == null ? null : Math.max(0, 1 - mae / 1000)} />
          </div>

          <div className="distribution-grid">
            <CountBreakdown
              title="Confidence mix"
              items={[
                { label: 'High', value: confidenceCounts.high ?? 0 },
                { label: 'Medium', value: confidenceCounts.medium ?? 0 },
                { label: 'Low', value: confidenceCounts.low ?? 0 },
              ]}
            />
            <CountBreakdown
              title="Review flags"
              items={[
                { label: 'Needs review', value: reviewCounts.yes ?? 0 },
                { label: 'Cleared', value: reviewCounts.no ?? 0 },
              ]}
            />
          </div>

          <div className="run-row-preview">
            {detail.rows.slice(0, 3).map((row) => (
              <article key={`${row.student_id}-${row.session}`} className="mini-row-card">
                <span className="label">
                  {row.session} #{row.student_id}
                </span>
                <strong>{row.title}</strong>
                <p>
                  GT {row.ground_truth_score} / Pred {row.predicted_score} / {row.confidence}
                </p>
              </article>
            ))}
          </div>
        </div>
      ) : (
        <EmptyState message={`No ${title.toLowerCase()} run selected.`} />
      )}
    </div>
  )
}

function MetricDelta({
  label,
  value,
  invert = false,
}: {
  label: string
  value: number | undefined
  invert?: boolean
}) {
  const numeric = value ?? 0
  const positive = invert ? numeric < 0 : numeric > 0
  return (
    <div className={`metric-delta ${positive ? 'positive' : numeric < 0 ? 'negative' : 'neutral'}`}>
      <span className="label">{label}</span>
      <strong>{formatDelta(numeric)}</strong>
    </div>
  )
}

function MetricBar({ label, value }: { label: string; value: number | null }) {
  const percent = value == null ? 0 : Math.max(0, Math.min(100, Math.round(value * 100)))
  return (
    <div className="metric-bar">
      <div className="metric-bar-top">
        <span>{label}</span>
        <strong>{value == null ? '—' : `${percent}%`}</strong>
      </div>
      <div className="metric-bar-track">
        <div className="metric-bar-fill" style={{ width: `${percent}%` }} />
      </div>
    </div>
  )
}

function CountBreakdown({
  title,
  items,
}: {
  title: string
  items: Array<{ label: string; value: number }>
}) {
  const total = items.reduce((sum, item) => sum + item.value, 0)
  return (
    <article className="count-breakdown">
      <h3>{title}</h3>
      <ul>
        {items.map((item) => {
          const width = total === 0 ? 0 : Math.round((item.value / total) * 100)
          return (
            <li key={item.label}>
              <div className="count-row">
                <span>{item.label}</span>
                <strong>{item.value}</strong>
              </div>
              <div className="count-track">
                <div className="count-fill" style={{ width: `${width}%` }} />
              </div>
            </li>
          )
        })}
      </ul>
    </article>
  )
}

function WinList({
  title,
  rows,
}: {
  title: string
  rows: Array<Record<string, string | number>>
}) {
  return (
    <article className="win-list">
      <h3>{title}</h3>
      <ul>
        {rows.map((row, index) => (
          <li key={`${title}-${index}`}>
            <strong>{String(row.title)}</strong>
            <span>
              #{String(row.student_id)} {String(row.session)} delta {String(row.error_delta)}
            </span>
          </li>
        ))}
      </ul>
    </article>
  )
}

function ClaimList({ title, items }: { title: string; items: string[] }) {
  return (
    <article className="claim-list">
      <h3>{title}</h3>
      <ul>
        {items.map((item, index) => (
          <li key={`${title}-${index}`}>{item}</li>
        ))}
      </ul>
    </article>
  )
}

function EmptyState({ message }: { message: string }) {
  return <div className="empty-state">{message}</div>
}

function formatPercent(value: unknown) {
  if (typeof value !== 'number') {
    return '—'
  }
  return `${Math.round(value * 100)}%`
}

function formatNumber(value: unknown) {
  if (typeof value !== 'number') {
    return '—'
  }
  return `${Math.round(value)}`
}

function formatDelta(value: number) {
  const sign = value > 0 ? '+' : ''
  const rounded = Math.abs(value) < 1 ? value.toFixed(2) : Math.round(value).toString()
  return `${sign}${rounded}`
}

function getMetricValue(source: Record<string, unknown> | undefined, key: string): number | null {
  const value = source?.[key]
  return typeof value === 'number' ? value : null
}

function getCountMap(
  source: Record<string, unknown> | undefined,
  key: string,
): Record<string, number> {
  const value = source?.[key]
  if (!value || typeof value !== 'object') {
    return {}
  }

  return Object.fromEntries(
    Object.entries(value as Record<string, unknown>).map(([label, count]) => [
      label,
      typeof count === 'number' ? count : 0,
    ]),
  )
}

export default App
