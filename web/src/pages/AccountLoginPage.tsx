import { useState, type FormEvent } from 'react'
import { Link } from 'react-router-dom'
import { requestAccountLogin } from '../api'

export function AccountLoginPage() {
  const [email, setEmail] = useState('')
  const [loading, setLoading] = useState(false)
  const [message, setMessage] = useState<string | null>(null)
  const [error, setError] = useState<string | null>(null)

  async function onSubmit(e: FormEvent) {
    e.preventDefault()
    setLoading(true)
    setError(null)
    setMessage(null)
    try {
      const result = await requestAccountLogin(email.trim())
      setMessage(result.message)
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Request failed')
    } finally {
      setLoading(false)
    }
  }

  return (
    <section className="card">
      <h2>My reminders</h2>
      <p className="page-meta">
        Enter the email you used to sign up. We&apos;ll send a one-time sign-in link — no password needed.
      </p>
      {error && <div className="error">{error}</div>}
      {message ? (
        <div className="success">{message}</div>
      ) : (
        <form onSubmit={onSubmit}>
          <label className="field" htmlFor="login-email">
            Email address
          </label>
          <input
            id="login-email"
            type="email"
            value={email}
            onChange={(e) => setEmail(e.target.value)}
            required
            placeholder="you@example.com"
            autoComplete="email"
          />
          <button type="submit" disabled={loading}>
            {loading ? 'Sending…' : 'Email me a sign-in link'}
          </button>
        </form>
      )}
      <p style={{ marginTop: '1rem' }}>
        <Link to="/">← Back to schedule lookup</Link>
      </p>
    </section>
  )
}
