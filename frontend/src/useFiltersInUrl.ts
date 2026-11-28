import { useCallback, useEffect, useState } from 'react'
import type { PostingFilters } from './api'

const DEFAULTS: PostingFilters = {
  q: '',
  term: '',
  min_score: 0,
  in_target_area: false,
  hide_coop_required: false,
  sort: 'newest',
  offset: 0,
}

// URL query string -> filters. Anything missing or invalid falls back to the default.
function read(): PostingFilters {
  const p = new URLSearchParams(window.location.search)
  const score = Number(p.get('min_score'))
  const offset = Number(p.get('offset'))
  return {
    q: p.get('q') ?? DEFAULTS.q,
    term: p.get('term') ?? DEFAULTS.term,
    min_score: Number.isInteger(score) && score >= 0 && score <= 10 ? score : 0,
    in_target_area: p.get('in_target_area') === 'true',
    hide_coop_required: p.get('hide_coop_required') === 'true',
    sort: p.get('sort') === 'score' ? 'score' : 'newest',
    offset: Number.isInteger(offset) && offset > 0 ? offset : 0,
  }
}

// Filters -> URL query string. Defaults are left out to keep the URL short.
function write(f: PostingFilters): string {
  const p = new URLSearchParams()
  for (const key of Object.keys(DEFAULTS) as (keyof PostingFilters)[]) {
    if (f[key] !== DEFAULTS[key]) p.set(key, String(f[key]))
  }
  const qs = p.toString()
  return qs ? `?${qs}` : window.location.pathname
}

/** Like useState, but the value is stored in the page URL. */
export function useFiltersInUrl(): [PostingFilters, (f: PostingFilters) => void] {
  const [filters, setState] = useState<PostingFilters>(read)

  const setFilters = useCallback((f: PostingFilters) => {
    window.history.pushState(null, '', write(f)) // adds a history entry without reloading the page
    setState(f)
  }, [])

  // Back/forward buttons change the URL without calling setFilters, so re-read it then
  useEffect(() => {
    const onPop = () => setState(read())
    window.addEventListener('popstate', onPop)
    return () => window.removeEventListener('popstate', onPop)
  }, [])

  return [filters, setFilters]
}
