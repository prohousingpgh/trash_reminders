import { useEffect, useState } from 'react'
import { Link, useSearchParams } from 'react-router-dom'
import { verifyEmail } from '../api'

export function VerifyEmailPage() {
  const [params] = useSearchParams()
  const token = params.get('token') ?? ''
  const [message, setMessage] = useState<string | null>(null)
  const [error, setError] = useState<string | null>(null)

  useEffect(() => {
    if (!token) {
      setError('Missing verification token.')
      return
    }
    verifyEmail(token)
      .then((result) => setMessage(result.message))
      .catch((err) => setError(err instanceof Error ? err.message : 'Verification failed'))
  }, [token])

  return (
    <section className="card">
      <h2>Email verification</h2>
      {message && <div className="success">{message}</div>}
      {error && <div className="error">{error}</div>}
      <p>
        <Link to="/">Back to home</Link>
      </p>
    </section>
  )
}
