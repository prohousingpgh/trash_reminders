import { useEffect, useState } from 'react'
import { Link, useNavigate, useSearchParams } from 'react-router-dom'
import { verifyAccountLogin } from '../api'

export function AccountVerifyPage() {
  const [params] = useSearchParams()
  const navigate = useNavigate()
  const token = params.get('token') ?? ''
  const [error, setError] = useState<string | null>(null)

  useEffect(() => {
    if (!token) {
      setError('Missing sign-in token.')
      return
    }
    verifyAccountLogin(token)
      .then(() => navigate('/account', { replace: true }))
      .catch((err) => setError(err instanceof Error ? err.message : 'Sign-in failed'))
  }, [token, navigate])

  return (
    <section className="card">
      <h2>Signing you in…</h2>
      {error && (
        <>
          <div className="error">{error}</div>
          <p>
            <Link to="/account/login">Request a new sign-in link</Link>
          </p>
        </>
      )}
      {!error && <p className="page-meta">Please wait.</p>}
    </section>
  )
}
