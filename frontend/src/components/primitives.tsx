import type { EvalRunDetail, EvalRunSummary } from '../types/api'
import { formatNumber, formatPercent, formatDelta, getCountMap, getMetricValue } from '../lib/format'

export function Metric({ label, value }: { label: string; value: string }) {
  return (
    <div className="metric">
      <span className="label">{label}</span>
      <strong>{value}</strong>
    </div>
  )
}

export function InfoBlock({ label, value }: { label: string; value: string }) {
  return (
    <div className="info-block">
      <span className="label">{label}</span>
      <p>{value}</p>
    </div>
  )
}

export function EmptyState({ message }: { message: string }) {
  return <div className="empty-state">{message}</div>
}

export function ClaimList({ title, items }: { title: string; items: string[] }) {
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

export function MetricBar({ label, value }: { label: string; value: number | null }) {
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

export function CountBreakdown({
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

export function MetricDelta({
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

export function WinList({
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

export function RunColumn({
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
  const sourceCounts = getCountMap(detail?.metrics, 'source_counts')

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
            {sourceCounts.fallback ? (
              <span className="chip tone-low">
                {sourceCounts.fallback} fallback rows
              </span>
            ) : null}
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
