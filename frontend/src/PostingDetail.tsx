import { useEffect, useRef, useState } from 'react'
import { fetchPosting, type PostingDetail as Detail } from './api'

const dateFmt = new Intl.DateTimeFormat('en-CA', { year: 'numeric', month: 'short', day: 'numeric' })

// The ingest stores descriptions as plain text (app/fetchers/html_text.py): one line per
// paragraph or list item. Split into blocks, and show short lines that look like headings
// ("WHO WE ARE", "What you'll do:") in bold.
function Description({ text }: { text: string }) {
  const blocks = text.split(/\n+/).map((b) => b.trim()).filter(Boolean)
  return (
    <div className="description">
      {blocks.map((b, i) => {
        const isHeading = b.length < 60 && (b === b.toUpperCase() || b.endsWith(':')) && /[a-z]/i.test(b)
        return isHeading ? <h3 key={i}>{b}</h3> : <p key={i}>{b}</p>
      })}
    </div>
  )
}

interface Props {
  id: number
  onClose: () => void
}

export function PostingDetail({ id, onClose }: Props) {
  const dialogRef = useRef<HTMLDialogElement>(null)
  // Same pattern as the list: each result is tagged with the id it's for, so
  // "loading" is just "the result isn't for this id yet".
  const [result, setResult] = useState<{ id: number; posting?: Detail; error?: string } | null>(null)
  const loading = result?.id !== id
  const posting = loading ? null : result?.posting
  const error = loading ? null : result?.error

  useEffect(() => {
    const ctrl = new AbortController()
    fetchPosting(id, ctrl.signal)
      .then((posting) => setResult({ id, posting }))
      .catch((e: unknown) => {
        if (!ctrl.signal.aborted) setResult({ id, error: e instanceof Error ? e.message : String(e) })
      })
    return () => ctrl.abort()
  }, [id])

  // <dialog> + showModal() gives a real modal: it traps keyboard focus inside, closes on Escape,
  // and hides the page behind it from screen readers. No library needed.
  useEffect(() => {
    const dialog = dialogRef.current
    if (dialog && !dialog.open) dialog.showModal()
  }, [])

  return (
    <dialog
      ref={dialogRef}
      className="detail"
      aria-labelledby="detail-title"
      onClose={onClose} // fires on Escape as well as on the close button
      onClick={(e) => {
        // A click on the dialog element itself (not its contents) is a click on the backdrop
        if (e.target === dialogRef.current) dialogRef.current.close()
      }}
    >
      <div className="detail-inner">
        <button className="detail-close" onClick={() => dialogRef.current?.close()} aria-label="Close">
          ×
        </button>

        {loading && <p className="detail-status">Loading…</p>}
        {error && <p className="detail-status error">Couldn't load this posting: {error}</p>}

        {posting && (
          <>
            <p className="detail-company">{posting.company}</p>
            <h2 id="detail-title" className="detail-title">{posting.title}</h2>
            <p className="detail-meta">
              {posting.location ?? 'Location not listed'}
              {posting.remote && ' · Remote'}
              {posting.term !== 'Unknown' && ` · ${posting.term}`}
            </p>

            <div className="detail-actions">
              <a className="apply" href={posting.url} target="_blank" rel="noreferrer">
                Apply on {posting.source[0].toUpperCase() + posting.source.slice(1)} ↗
              </a>
              {!posting.is_open && <span className="tag warn">No longer listed</span>}
            </div>

            <dl className="facts">
              <div>
                <dt>Fit score</dt>
                <dd>{posting.fit_score ?? '–'} / 10</dd>
              </div>
              <div>
                <dt>Matched skills</dt>
                <dd>{posting.matched_skills?.length ? posting.matched_skills.join(', ') : 'None'}</dd>
              </div>
              <div>
                <dt>Posted</dt>
                <dd>{posting.posted_at ? dateFmt.format(new Date(posting.posted_at)) : 'Unknown'}</dd>
              </div>
              <div>
                <dt>First seen</dt>
                <dd>{dateFmt.format(new Date(posting.first_seen_at))}</dd>
              </div>
            </dl>

            {posting.coop_required && (
              <p className="notice">
                The description says applicants must be enrolled in a co-op program. Some companies also
                have a regular internship track, so read it before ruling this out.
              </p>
            )}

            {posting.description_text ? (
              <Description text={posting.description_text} />
            ) : (
              <p className="detail-status">No description provided. Open the posting for details.</p>
            )}
          </>
        )}
      </div>
    </dialog>
  )
}
