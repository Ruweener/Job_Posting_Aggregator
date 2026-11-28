import { useEffect, useState } from 'react'
import { fetchPostings, fetchStats, PAGE_SIZE, type PostingFilters, type PostingPage } from './api'
import { PostingCard } from './PostingCard'
import { PostingDetail } from './PostingDetail'
import { useOpenPosting } from './useOpenPosting'
import { useFiltersInUrl } from './useFiltersInUrl'
import './App.css'

export default function App() {
  // Filters live in the URL (?term=Winter+2027&sort=score), so a filtered view can be bookmarked
  // or shared, and the browser's back button works.
  const [filters, setFilters] = useFiltersInUrl()
  const [openId, setOpen] = useOpenPosting() // detail panel, ?posting=<id>
  const [search, setSearch] = useState(filters.q) // what's typed, before the debounce
  const [terms, setTerms] = useState<string[]>([])

  // The last response, tagged with the filters it was for. "Loading" isn't stored separately:
  // it's true whenever the latest response is for different filters than the current ones.
  const key = JSON.stringify(filters)
  const [result, setResult] = useState<{ key: string; page?: PostingPage; error?: string } | null>(null)
  const loading = result?.key !== key
  const page = result?.page ?? null
  const error = loading ? null : (result?.error ?? null)

  // If the URL changes the search (back button), show it in the box. Adjusting state while
  // rendering, when a value changes, is React's recommended alternative to an effect here.
  const [prevQ, setPrevQ] = useState(filters.q)
  if (filters.q !== prevQ) {
    setPrevQ(filters.q)
    setSearch(filters.q)
  }

  // Terms for the dropdown come from /stats, so new terms appear without code changes
  useEffect(() => {
    const ctrl = new AbortController()
    fetchStats(ctrl.signal)
      .then((s) => setTerms(s.by_term.map((t) => t.term).filter((t) => t !== 'Unknown')))
      .catch(() => {}) // the dropdown is optional; the list still works without it
    return () => ctrl.abort()
  }, [])

  // Debounce: wait until typing pauses for 300 ms before searching, instead of one request per key
  useEffect(() => {
    if (search === filters.q) return
    const t = setTimeout(() => setFilters({ ...filters, q: search, offset: 0 }), 300)
    return () => clearTimeout(t)
  }, [search, filters, setFilters])

  // Load postings whenever the filters change. AbortController cancels the previous request,
  // so a slow old response can't overwrite a newer one.
  useEffect(() => {
    const ctrl = new AbortController()
    fetchPostings(filters, ctrl.signal)
      .then((page) => setResult({ key, page }))
      .catch((e: unknown) => {
        // Keep the previous page on screen and show the error above it
        if (!ctrl.signal.aborted) {
          setResult((prev) => ({ key, page: prev?.page, error: e instanceof Error ? e.message : String(e) }))
        }
      })
    return () => ctrl.abort()
  }, [filters, key])

  // Any filter change goes back to the first page
  const update = (patch: Partial<PostingFilters>) => setFilters({ ...filters, ...patch, offset: 0 })

  const total = page?.total ?? 0
  const from = total === 0 ? 0 : filters.offset + 1
  const to = Math.min(filters.offset + PAGE_SIZE, total)

  return (
    <div className="app">
      <header className="header">
        <h1>Internship postings</h1>
        <p className="subtitle">Greenhouse, Lever and Ashby boards, scored against my skills. Updated daily.</p>
      </header>

      <section className="filters" aria-label="Filters">
        <input
          type="search"
          className="search"
          placeholder="Search title or description (e.g. python, react, QA)"
          value={search}
          onChange={(e) => setSearch(e.target.value)}
        />
        <label>
          Term
          <select value={filters.term} onChange={(e) => update({ term: e.target.value })}>
            <option value="">Any</option>
            {terms.map((t) => (
              <option key={t} value={t}>{t}</option>
            ))}
          </select>
        </label>
        <label>
          Min. fit
          <select value={filters.min_score} onChange={(e) => update({ min_score: Number(e.target.value) })}>
            {[0, 2, 4, 6, 8, 10].map((n) => (
              <option key={n} value={n}>{n === 0 ? 'Any' : `${n}+`}</option>
            ))}
          </select>
        </label>
        <label>
          Sort
          <select value={filters.sort} onChange={(e) => update({ sort: e.target.value as PostingFilters['sort'] })}>
            <option value="newest">Newest</option>
            <option value="score">Best fit</option>
          </select>
        </label>
        <label className="check">
          <input
            type="checkbox"
            checked={filters.in_target_area}
            onChange={(e) => update({ in_target_area: e.target.checked })}
          />
          Ontario / remote Canada
        </label>
        <label className="check">
          <input
            type="checkbox"
            checked={filters.hide_coop_required}
            onChange={(e) => update({ hide_coop_required: e.target.checked })}
          />
          Hide co-op required
        </label>
      </section>

      <div className="status" aria-live="polite">
        {error ? (
          <span className="error">Couldn't load postings: {error}</span>
        ) : (
          <span>{loading && !page ? 'Loading…' : `${from}–${to} of ${total} postings`}</span>
        )}
      </div>

      <ul className={`list ${loading ? 'is-loading' : ''}`}>
        {page?.items.map((p) => <PostingCard key={p.id} posting={p} onOpen={setOpen} />)}
      </ul>

      {page && total === 0 && !loading && <p className="empty">No postings match these filters.</p>}

      {total > PAGE_SIZE && (
        <nav className="pager" aria-label="Pages">
          <button
            disabled={filters.offset === 0}
            onClick={() => setFilters({ ...filters, offset: Math.max(0, filters.offset - PAGE_SIZE) })}
          >
            ← Previous
          </button>
          <button
            disabled={to >= total}
            onClick={() => setFilters({ ...filters, offset: filters.offset + PAGE_SIZE })}
          >
            Next →
          </button>
        </nav>
      )}

      {openId !== null && <PostingDetail id={openId} onClose={() => setOpen(null)} />}
    </div>
  )
}
