// Types and fetch helpers for the FastAPI backend.
// The types mirror the Pydantic models in app/api/models.py. Keep them in sync: if a field
// changes there, change it here (the /docs page shows the exact JSON shape).

export interface PostingSummary {
  id: number
  source: string
  company: string
  title: string
  location: string | null
  url: string
  remote: boolean
  term: string
  posted_at: string | null // ISO 8601 datetimes arrive as strings in JSON
  first_seen_at: string
  last_seen_at: string
  is_open: boolean
  fit_score: number | null
  matched_skills: string[] | null
  coop_required: boolean
  in_target_area: boolean
}

// GET /postings/{id} adds the full description (left out of list responses to keep them small)
export interface PostingDetail extends PostingSummary {
  source_job_id: string
  description_text: string | null
}

export interface PostingPage {
  total: number
  limit: number
  offset: number
  items: PostingSummary[]
}

export interface Stats {
  total: number
  open: number
  by_company: { company: string; total: number; open: number }[]
  by_week: { week_start: string; posted: number }[]
  by_term: { term: string; open: number }[]
}

// The filters the list page can send. Each one matches a query parameter of GET /postings.
export interface PostingFilters {
  q: string
  term: string
  min_score: number
  in_target_area: boolean
  hide_coop_required: boolean
  sort: 'newest' | 'score'
  offset: number
}

export const PAGE_SIZE = 20

// Every request goes to /api/...; the Vite dev server forwards it to FastAPI (see vite.config.ts)
const API = '/api'

async function getJson<T>(path: string, signal?: AbortSignal): Promise<T> {
  const res = await fetch(`${API}${path}`, { signal })
  if (!res.ok) {
    throw new Error(`${res.status} ${res.statusText} from ${path}`)
  }
  return res.json() as Promise<T>
}

export function fetchPostings(f: PostingFilters, signal?: AbortSignal): Promise<PostingPage> {
  // URLSearchParams builds a correctly encoded query string (spaces, &, etc.)
  const params = new URLSearchParams({ sort: f.sort, limit: String(PAGE_SIZE), offset: String(f.offset) })
  // Only send filters that are set, so the API uses its defaults for the rest
  if (f.q.trim().length >= 2) params.set('q', f.q.trim()) // the API requires at least 2 characters
  if (f.term) params.set('term', f.term)
  if (f.min_score > 0) params.set('min_score', String(f.min_score))
  if (f.in_target_area) params.set('in_target_area', 'true')
  if (f.hide_coop_required) params.set('hide_coop_required', 'true')
  return getJson<PostingPage>(`/postings?${params}`, signal)
}

export function fetchPosting(id: number, signal?: AbortSignal): Promise<PostingDetail> {
  return getJson<PostingDetail>(`/postings/${id}`, signal)
}

export function fetchStats(signal?: AbortSignal): Promise<Stats> {
  return getJson<Stats>('/stats', signal)
}
