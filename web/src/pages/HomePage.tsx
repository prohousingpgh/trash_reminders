import { useNavigate } from 'react-router-dom'
import { AddressAutocomplete } from '../components/AddressAutocomplete'
import type { AddressSuggestion } from '../types'

export function HomePage() {
  const navigate = useNavigate()

  function onSelect(suggestion: AddressSuggestion) {
    const params = new URLSearchParams({
      house: suggestion.house_number,
      street: suggestion.street,
      zip: suggestion.zip,
    })
    navigate(`/schedule?${params}`)
  }

  return (
    <>
      <section className="card">
        <h2>Find your schedule</h2>
        <p className="page-meta">
          Start typing your home address. Results are limited to Pittsburgh city addresses served
          by the Department of Public Works.
        </p>
        <AddressAutocomplete onSelect={onSelect} autoFocus />
      </section>

      <section className="card">
        <h2>Get reminders</h2>
        <p>
          pgh.st schedule lookup is great, but email and text reminders are currently unavailable
          there. This site adds free evening-before reminders for trash, recycling, and yard waste.
        </p>
      </section>
    </>
  )
}
