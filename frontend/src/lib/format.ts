export function formatPercent(value: unknown) {
  if (typeof value !== 'number') {
    return '—'
  }
  return `${Math.round(value * 100)}%`
}

export function formatNumber(value: unknown) {
  if (typeof value !== 'number') {
    return '—'
  }
  return `${Math.round(value)}`
}

export function formatDelta(value: number) {
  const sign = value > 0 ? '+' : ''
  const rounded = Math.abs(value) < 1 ? value.toFixed(2) : Math.round(value).toString()
  return `${sign}${rounded}`
}

export function getMetricValue(
  source: Record<string, unknown> | undefined,
  key: string,
): number | null {
  const value = source?.[key]
  return typeof value === 'number' ? value : null
}

export function getCountMap(
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
