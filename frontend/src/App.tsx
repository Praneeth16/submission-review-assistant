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
import {
  ClaimList,
  EmptyState,
  InfoBlock,
  MetricDelta,
  RunColumn,
  WinList,
} from './components/primitives'
import { AdhocForm } from './components/AdhocForm'
import type { AdhocReviewBody } from './lib/api'

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
  const [adhocActive, setAdhocActive] = useState(false)
  const [adhocTarget, setAdhocTarget] = useState<AdhocReviewBody | null>(null)
  const [view, setView] = useState<'review' | 'lab'>('review')
  const [traceExpanded, setTraceExpanded] = useState(false)
  const [claimsExpanded, setClaimsExpanded] = useState(false)

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
    if (adhocActive) {
      return
    }
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
  }, [selected, adhocActive])

  useEffect(() => {
    if (adhocActive) {
      return
    }
    if (!selected) {
      setReview(null)
      return
    }

    setLoadingReview(true)
    fetchReviewPreview(selected.student_id, selected.session, reviewMode)
      .then(setReview)
      .catch((err: Error) => setError(err.message))
      .finally(() => setLoadingReview(false))
  }, [selected, reviewMode, adhocActive])

  function handleAdhocResult(result: ReviewPreview, target: AdhocReviewBody) {
    setAdhocActive(true)
    setAdhocTarget(target)
    setSelected(null)
    setDetail(null)
    setReview(result)
  }

  function exitAdhocMode() {
    setAdhocActive(false)
    setAdhocTarget(null)
    setReview(null)
  }

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
      <header className="app-header app-header-compact">
        <div className="brand-block">
          <p className="eyebrow">Submission Review Assistant</p>
          <h1>{view === 'review' ? 'Score a submission' : 'Evaluation lab'}</h1>
        </div>

        <nav className="top-nav segmented">
          <button
            type="button"
            className={view === 'review' ? 'active' : ''}
            onClick={() => setView('review')}
          >
            Review
          </button>
          <button
            type="button"
            className={view === 'lab' ? 'active' : ''}
            onClick={() => setView('lab')}
          >
            Eval lab
          </button>
        </nav>

        <div className="header-actions">
          <span className="dataset-chip-compact">{datasetLine}</span>
          <button
            type="button"
            className="theme-toggle"
            onClick={() => setTheme((current) => (current === 'dark' ? 'light' : 'dark'))}
            aria-label="Toggle theme"
          >
            {theme === 'dark' ? '☀' : '☾'}
          </button>
        </div>
      </header>

      {view === 'review' && (
      <main className="product-stage">
        <aside className="panel inbox-panel">
          <div className="section-head">
            <div>
              <span className="panel-kicker">Review inbox</span>
              <h2>Choose a submission</h2>
            </div>
            <span className="chip subtle">{loadingList ? 'loading' : `${submissions.length} loaded`}</span>
          </div>

          <div className="inbox-mode-switch segmented">
            <button
              type="button"
              className={!adhocActive ? 'active' : ''}
              onClick={exitAdhocMode}
            >
              Historical dataset
            </button>
            <button
              type="button"
              className={adhocActive ? 'active' : ''}
              onClick={() => {
                setAdhocActive(true)
                setSelected(null)
                setDetail(null)
                setReview(null)
              }}
            >
              Ad-hoc review
            </button>
          </div>

          {adhocActive ? (
            <AdhocForm
              onResult={handleAdhocResult}
              onError={(message) => setError(message)}
              knownSessions={summary?.sessions ?? []}
            />
          ) : (
          <>
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
          </>
          )}
        </aside>

        <section className="panel scoring-panel">
          <div className="section-head">
            <div>
              <span className="panel-kicker">Scoring sheet</span>
              <h2>
                {adhocActive
                  ? adhocTarget?.title ?? 'Run an ad-hoc review'
                  : selected?.primary_title ?? 'Choose a submission'}
              </h2>
              <p>
                {adhocActive
                  ? adhocTarget
                    ? `${adhocTarget.author} · ${adhocTarget.session} · ad-hoc ${adhocTarget.platform} artifact`
                    : 'Fill in the ad-hoc form to review a new submission.'
                  : selected
                  ? `${selected.author} · ${selected.session} · primary artifact on ${selected.primary_platform}`
                  : 'Pick a submission from the inbox to open the scoring sheet.'}
              </p>
            </div>

            {adhocActive && adhocTarget ? (
              <div className="section-actions">
                <a
                  href={adhocTarget.video_url}
                  target="_blank"
                  rel="noreferrer"
                  className="action-link"
                >
                  open artifact
                </a>
                <span className="chip subtle">ad-hoc</span>
              </div>
            ) : (
              selected && (
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
              )
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
                  <span
                    className={`chip ${review.source === 'fallback' ? 'tone-low' : 'tone-high'}`}
                    title={
                      review.source === 'fallback'
                        ? 'No Gemini evidence was collected. This is a band-anchored placeholder.'
                        : 'Evidence collected via Gemini.'
                    }
                  >
                    source: {review.source}
                  </span>
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

          {adhocActive && adhocTarget ? (
            <div className="detail-grid">
              <InfoBlock label="Primary platform" value={adhocTarget.platform} />
              <InfoBlock label="Session" value={adhocTarget.session} />
              <InfoBlock label="Author" value={adhocTarget.author} />
              <InfoBlock label="Mode" value={adhocTarget.mode} />
            </div>
          ) : detail?.submission ? (
            <>
              <div className="detail-grid">
                <InfoBlock label="Primary platform" value={detail.submission.primary_platform} />
                <InfoBlock label="Historical score" value={String(detail.submission.score ?? '—')} />
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
              <details className="collapsible" open={claimsExpanded} onToggle={(event) => setClaimsExpanded((event.target as HTMLDetailsElement).open)}>
                <summary>
                  <span className="panel-kicker">Claim ledger</span>
                  <span className="claim-counts">
                    <span className="tone-high">{review.claim_verification.confirmed_claims.length} confirmed</span>
                    <span className="tone-medium">{review.claim_verification.weak_claims.length} weak</span>
                    <span className="tone-low">{review.claim_verification.unsupported_claims.length} unsupported</span>
                    <span className="subtle">{review.claim_verification.open_questions.length} open</span>
                  </span>
                </summary>
                <div className="claim-grid">
                  <ClaimList title="Confirmed" items={review.claim_verification.confirmed_claims} />
                  <ClaimList title="Weak" items={review.claim_verification.weak_claims} />
                  <ClaimList title="Unsupported" items={review.claim_verification.unsupported_claims} />
                  <ClaimList title="Open questions" items={review.claim_verification.open_questions} />
                </div>
              </details>

              <details className="collapsible" open={traceExpanded} onToggle={(event) => setTraceExpanded((event.target as HTMLDetailsElement).open)}>
                <summary>
                  <span className="panel-kicker">Trace</span>
                  <span className="subtle">{review.trace.length} steps</span>
                </summary>
                <ol className="trace-list">
                  {review.trace.map((step) => (
                    <li key={step.step} className="trace-card">
                      <div className="trace-step">Step {step.step} · {step.selected_tool}</div>
                      <h3>{step.current_question}</h3>
                      <p>{step.tool_result_summary}</p>
                      <p className="subtle">
                        <strong>Belief:</strong> {step.belief_update}
                      </p>
                    </li>
                  ))}
                </ol>
              </details>
            </>
          ) : (
            <EmptyState message="Evidence notes will fill in after the review runs." />
          )}
        </aside>
      </main>
      )}

      {view === 'lab' && (
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
      )}

      {error && (
        <div className="error-banner">
          <span>{error}</span>
          <button type="button" onClick={() => setError(null)} aria-label="Dismiss error">
            ×
          </button>
        </div>
      )}
    </div>
  )
}

export default App
