import { useState } from 'react'

import { submitAdhocReview, type AdhocReviewBody } from '../lib/api'
import type { ReviewPreview } from '../types/api'

type Platform = 'YouTube' | 'Loom' | 'Google Drive' | 'GitHub video' | 'Other'

interface Props {
  onResult: (result: ReviewPreview, target: AdhocReviewBody) => void
  onError: (message: string) => void
  knownSessions?: string[]
}

export function AdhocForm({ onResult, onError, knownSessions = [] }: Props) {
  const [title, setTitle] = useState('')
  const [url, setUrl] = useState('')
  const [platform, setPlatform] = useState<Platform>('YouTube')
  const [author, setAuthor] = useState('')
  const [session, setSession] = useState<string>(knownSessions[0] ?? 'S1')
  const [mode, setMode] = useState<'baseline' | 'agent'>('agent')
  const [submitting, setSubmitting] = useState(false)

  async function handleSubmit(event: React.FormEvent<HTMLFormElement>) {
    event.preventDefault()
    const sessionLabel = session.trim()
    if (!title.trim() || !url.trim() || !sessionLabel) {
      onError('Provide title, video URL, and assignment label before running an ad-hoc review.')
      return
    }

    const body: AdhocReviewBody = {
      title: title.trim(),
      video_url: url.trim(),
      platform,
      author: author.trim() || 'unknown',
      session: sessionLabel,
      student_id: 'adhoc',
      mode,
    }

    setSubmitting(true)
    try {
      const preview = await submitAdhocReview(body)
      onResult(preview, body)
    } catch (err) {
      onError((err as Error).message)
    } finally {
      setSubmitting(false)
    }
  }

  return (
    <form className="adhoc-form" onSubmit={handleSubmit}>
      <div className="adhoc-head">
        <span className="panel-kicker">Ad-hoc review</span>
        <h2>Review any new submission</h2>
        <p>Paste a demo link. The agent fetches the transcript, inspects it with Gemini, and returns the same dossier as the historical rows.</p>
      </div>

      <label className="field">
        <span>Title</span>
        <input
          value={title}
          name="adhoc-title"
          onChange={(event) => setTitle(event.target.value)}
          placeholder="e.g. Personal Spends Tracker on Your Voice Tips"
          required
        />
      </label>

      <label className="field">
        <span>Video URL</span>
        <input
          value={url}
          name="adhoc-url"
          type="url"
          onChange={(event) => setUrl(event.target.value)}
          placeholder="https://youtu.be/..."
          required
        />
      </label>

      <div className="adhoc-grid">
        <label className="field">
          <span>Author (optional)</span>
          <input
            value={author}
            name="adhoc-author"
            onChange={(event) => setAuthor(event.target.value)}
            placeholder="Submitter name"
          />
        </label>

        <label className="field">
          <span>Platform</span>
          <select
            value={platform}
            name="adhoc-platform"
            onChange={(event) => setPlatform(event.target.value as Platform)}
          >
            <option>YouTube</option>
            <option>Loom</option>
            <option>Google Drive</option>
            <option>GitHub video</option>
            <option>Other</option>
          </select>
        </label>

        <label className="field">
          <span>Assignment</span>
          <input
            value={session}
            name="adhoc-session"
            list="adhoc-session-options"
            placeholder="e.g. S1, S2, Capstone, Week 4"
            onChange={(event) => setSession(event.target.value)}
            required
          />
          <datalist id="adhoc-session-options">
            {knownSessions.map((option) => (
              <option key={option} value={option} />
            ))}
          </datalist>
        </label>

        <label className="field">
          <span>Mode</span>
          <select
            value={mode}
            name="adhoc-mode"
            onChange={(event) => setMode(event.target.value as 'baseline' | 'agent')}
          >
            <option value="agent">agent</option>
            <option value="baseline">baseline</option>
          </select>
        </label>
      </div>

      <button type="submit" className="adhoc-submit" disabled={submitting}>
        {submitting ? 'Running review…' : 'Run ad-hoc review'}
      </button>
    </form>
  )
}
