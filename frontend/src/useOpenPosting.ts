import { useCallback, useEffect, useState } from 'react'

// Which posting's detail panel is open, kept in the URL as ?posting=196. That makes a posting
// linkable, and the browser's back button closes the panel. It's separate from the filters on
// purpose: opening a posting must not reload the list.
const PARAM = 'posting'

function read(): number | null {
  const id = Number(new URLSearchParams(window.location.search).get(PARAM))
  return Number.isInteger(id) && id > 0 ? id : null
}

/** URL for the current page with the posting set (or removed when id is null). */
export function urlWithPosting(id: number | null): string {
  const params = new URLSearchParams(window.location.search)
  if (id === null) params.delete(PARAM)
  else params.set(PARAM, String(id))
  const qs = params.toString()
  return qs ? `?${qs}` : window.location.pathname
}

export function useOpenPosting(): [number | null, (id: number | null) => void] {
  const [openId, setOpenId] = useState<number | null>(read)

  const setOpen = useCallback((id: number | null) => {
    if (id !== null) {
      // Remember in the history entry that we opened it, so closing can undo it with "back"
      window.history.pushState({ openedPosting: id }, '', urlWithPosting(id))
      setOpenId(id)
    } else if (window.history.state?.openedPosting) {
      // We pushed this entry: go back to the list entry. popstate then sets openId to null.
      // Pushing a new entry instead would make the back button reopen the posting.
      window.history.back()
    } else {
      // Opened from a shared link (no list entry behind it): just remove ?posting from the URL
      window.history.replaceState(null, '', urlWithPosting(null))
      setOpenId(null)
    }
  }, [])

  useEffect(() => {
    const onPop = () => setOpenId(read())
    window.addEventListener('popstate', onPop)
    return () => window.removeEventListener('popstate', onPop)
  }, [])

  return [openId, setOpen]
}
