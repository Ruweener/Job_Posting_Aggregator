import type { PostingSummary } from './api'
import { urlWithPosting } from './useOpenPosting'

// "2026-11-06T18:41:27Z" -> "Nov 6"
const dateFmt = new Intl.DateTimeFormat('en-CA', { month: 'short', day: 'numeric' })

function scoreClass(score: number | null): string {
  if (score === null) return 'score'
  if (score >= 7) return 'score high'
  if (score >= 4) return 'score mid'
  return 'score low'
}

export function PostingCard({ posting: p, onOpen }: { posting: PostingSummary; onOpen: (id: number) => void }) {
  const posted = p.posted_at ?? p.first_seen_at
  return (
    <li className="card">
      <div className={scoreClass(p.fit_score)} title="Fit score (0–10) from skills.yaml">
        {p.fit_score ?? '–'}
      </div>
      <div className="card-body">
        <h2 className="card-title">
          {/* A real link (so middle-click / "open in new tab" work), but a normal click opens the
              detail panel in place instead of loading a new page */}
          <a
            href={urlWithPosting(p.id)}
            onClick={(e) => {
              if (e.button !== 0 || e.ctrlKey || e.metaKey || e.shiftKey) return
              e.preventDefault()
              onOpen(p.id)
            }}
          >
            {p.title}
          </a>
        </h2>
        <p className="card-meta">
          <strong>{p.company}</strong>
          {p.location && <> · {p.location}</>}
          {p.remote && <> · Remote</>}
          {' · '}
          <time dateTime={posted}>{dateFmt.format(new Date(posted))}</time>
        </p>
        <div className="tags">
          {p.term !== 'Unknown' && <span className="tag term">{p.term}</span>}
          {p.in_target_area && <span className="tag area">In my area</span>}
          {p.coop_required && (
            <span className="tag warn" title="The description says a co-op program is required. Read before skipping: some also have a regular internship track.">
              Co-op required
            </span>
          )}
          {p.matched_skills?.map((s) => <span key={s} className="tag skill">{s}</span>)}
        </div>
      </div>
      {/* rel="noreferrer" stops the job board's page from being able to control this tab */}
      <a className="card-apply" href={p.url} target="_blank" rel="noreferrer" title="Open the posting on the job board">
        Apply ↗
      </a>
    </li>
  )
}
