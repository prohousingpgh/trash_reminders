import { useEffect, useState } from 'react'
import { Link, useParams, useSearchParams } from 'react-router-dom'
import { unsubscribe } from '../api'

export function UnsubscribePage() {
  const { token = '' } = useParams()
  const [params] = useSearchParams()
  const channel = params.get('channel') as 'email' | 'sms' | null
  const [message, setMessage] = useState<string | null>(null)
  const [error, setError] = useState<string | null>(null)

  useEffect(() => {
    if (!token) {
      setError('Invalid unsubscribe link.')
      return
    }
    unsubscribe(token, channel ?? undefined)
      .then((result) => {
        const label = result.channel === 'all' ? 'all reminders' : `${result.channel} reminders`
        setMessage(`You have been unsubscribed from ${label}.`)
      })
      .catch((err) => setError(err instanceof Error ? err.message : 'Unsubscribe failed'))
  }, [token, channel])

  return (
    <section className="card">
      <h2>Unsubscribe</h2>
      {message && <div className="success">{message}</div>}
      {error && <div className="error">{error}</div>}
      <p>
        <Link to="/">Back to home</Link>
      </p>
    </section>
  )
}
