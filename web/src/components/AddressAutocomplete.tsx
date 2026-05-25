import { useEffect, useId, useRef, useState, type KeyboardEvent } from 'react'
import { autocompleteAddress } from '../api'
import type { AddressSuggestion } from '../types'

type Props = {
  onSelect: (suggestion: AddressSuggestion) => void
  autoFocus?: boolean
}

export function AddressAutocomplete({ onSelect, autoFocus }: Props) {
  const listId = useId()
  const rootRef = useRef<HTMLDivElement>(null)
  const [query, setQuery] = useState('')
  const [suggestions, setSuggestions] = useState<AddressSuggestion[]>([])
  const [open, setOpen] = useState(false)
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState<string | null>(null)
  const [activeIndex, setActiveIndex] = useState(-1)

  useEffect(() => {
    if (query.trim().length < 3) {
      setSuggestions([])
      setOpen(false)
      setError(null)
      return
    }

    const handle = window.setTimeout(async () => {
      setLoading(true)
      setError(null)
      try {
        const results = await autocompleteAddress(query.trim())
        setSuggestions(results)
        setOpen(results.length > 0)
        setActiveIndex(-1)
      } catch (e) {
        setSuggestions([])
        setOpen(false)
        setError(e instanceof Error ? e.message : 'Search failed')
      } finally {
        setLoading(false)
      }
    }, 300)

    return () => window.clearTimeout(handle)
  }, [query])

  useEffect(() => {
    function onClickOutside(event: MouseEvent) {
      if (rootRef.current && !rootRef.current.contains(event.target as Node)) {
        setOpen(false)
      }
    }
    document.addEventListener('mousedown', onClickOutside)
    return () => document.removeEventListener('mousedown', onClickOutside)
  }, [])

  function pick(suggestion: AddressSuggestion) {
    setQuery(suggestion.label)
    setOpen(false)
    setSuggestions([])
    onSelect(suggestion)
  }

  function onKeyDown(e: KeyboardEvent<HTMLInputElement>) {
    if (!open || suggestions.length === 0) return

    if (e.key === 'ArrowDown') {
      e.preventDefault()
      setActiveIndex((i) => (i + 1) % suggestions.length)
    } else if (e.key === 'ArrowUp') {
      e.preventDefault()
      setActiveIndex((i) => (i <= 0 ? suggestions.length - 1 : i - 1))
    } else if (e.key === 'Enter' && activeIndex >= 0) {
      e.preventDefault()
      pick(suggestions[activeIndex])
    } else if (e.key === 'Escape') {
      setOpen(false)
    }
  }

  return (
    <div ref={rootRef} className="autocomplete">
      <label htmlFor="address-autocomplete">Street address</label>
      <input
        id="address-autocomplete"
        type="text"
        role="combobox"
        aria-expanded={open}
        aria-controls={listId}
        aria-autocomplete="list"
        autoComplete="off"
        autoFocus={autoFocus}
        placeholder="Start typing your address…"
        value={query}
        onChange={(e) => setQuery(e.target.value)}
        onFocus={() => suggestions.length > 0 && setOpen(true)}
        onKeyDown={onKeyDown}
      />
      {loading && <p className="autocomplete-meta">Searching…</p>}
      {error && <p className="autocomplete-error">{error}</p>}
      {open && suggestions.length > 0 && (
        <ul id={listId} className="autocomplete-list" role="listbox">
          {suggestions.map((s, index) => (
            <li key={`${s.house_number}-${s.street}-${s.zip}-${index}`} role="option" aria-selected={index === activeIndex}>
              <button
                type="button"
                className={index === activeIndex ? 'active' : undefined}
                onMouseDown={(e) => e.preventDefault()}
                onClick={() => pick(s)}
              >
                {s.label}
              </button>
            </li>
          ))}
        </ul>
      )}
      {open && !loading && suggestions.length === 0 && query.trim().length >= 3 && !error && (
        <p className="autocomplete-meta">No Pittsburgh addresses found. Try including your house number.</p>
      )}
    </div>
  )
}
