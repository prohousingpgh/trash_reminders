import { useCallback, useEffect, useState } from 'react'
import { Link, useNavigate } from 'react-router-dom'
import {
  cancelAccountSubscription,
  fetchAccountSession,
  fetchAccountSubscriptions,
  logoutAccount,
  updateAccountSubscription,
} from '../api'
import type { Subscription } from '../types'

function scheduleUrl(sub: Subscription) {
  const params = new URLSearchParams({
    house: sub.house_number,
    street: sub.street,
    zip: sub.zip,
  })
  return `/schedule?${params}`
}

function SubscriptionCard({
  sub,
  onUpdated,
}: {
  sub: Subscription
  onUpdated: () => void
}) {
  const [holidayOnly, setHolidayOnly] = useState(sub.holiday_only)
  const [emailEnabled, setEmailEnabled] = useState(sub.email_enabled)
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState<string | null>(null)

  async function save() {
    setLoading(true)
    setError(null)
    try {
      await updateAccountSubscription(sub.id, {
        holiday_only: holidayOnly,
        email_enabled: emailEnabled,
      })
      onUpdated()
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Update failed')
    } finally {
      setLoading(false)
    }
  }

  async function cancel() {
    if (!confirm(`Stop all reminders for ${sub.house_number} ${sub.street}?`)) return
    setLoading(true)
    setError(null)
    try {
      await cancelAccountSubscription(sub.id)
      onUpdated()
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Cancel failed')
    } finally {
      setLoading(false)
    }
  }

  return (
    <article className="card account-sub-card">
      <h3>
        {sub.house_number} {sub.street}
      </h3>
      <p className="page-meta">
        {sub.hood ? `${sub.hood} · ` : ''}ZIP {sub.zip}
      </p>
      <p className="page-meta">
        Email: {sub.email_verified ? 'verified' : 'pending verification'}
        {sub.sms_enabled && ` · SMS: ${sub.sms_verified ? 'on' : 'pending'}`}
      </p>
      {error && <div className="error">{error}</div>}
      <label className="checkbox">
        <input
          type="checkbox"
          checked={emailEnabled}
          onChange={(e) => setEmailEnabled(e.target.checked)}
          disabled={loading}
        />
        Email reminders
      </label>
      <label className="checkbox">
        <input
          type="checkbox"
          checked={holidayOnly}
          onChange={(e) => setHolidayOnly(e.target.checked)}
          disabled={loading}
        />
        Holiday / weather delays only
      </label>
      <div className="account-sub-actions">
        <button type="button" onClick={save} disabled={loading}>
          Save changes
        </button>
        <Link to={scheduleUrl(sub)} className="btn btn-secondary">
          View schedule
        </Link>
        <button type="button" className="btn btn-danger" onClick={cancel} disabled={loading}>
          Cancel reminders
        </button>
      </div>
    </article>
  )
}

export function AccountPage() {
  const navigate = useNavigate()
  const [email, setEmail] = useState<string | null>(null)
  const [subs, setSubs] = useState<Subscription[]>([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)

  const load = useCallback(async () => {
    setLoading(true)
    setError(null)
    try {
      const session = await fetchAccountSession()
      if (!session.authenticated) {
        navigate('/account/login', { replace: true })
        return
      }
      setEmail(session.email ?? null)
      const data = await fetchAccountSubscriptions()
      setSubs(data.subscriptions)
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to load reminders')
    } finally {
      setLoading(false)
    }
  }, [navigate])

  useEffect(() => {
    load()
  }, [load])

  async function onLogout() {
    await logoutAccount()
    navigate('/account/login', { replace: true })
  }

  if (loading) {
    return <p className="page-meta">Loading your reminders…</p>
  }

  return (
    <section>
      <div className="account-header">
        <div>
          <h2>My reminders</h2>
          {email && <p className="page-meta">Signed in as {email}</p>}
        </div>
        <button type="button" className="btn btn-secondary" onClick={onLogout}>
          Sign out
        </button>
      </div>
      {error && <div className="error">{error}</div>}
      {subs.length === 0 ? (
        <section className="card">
          <p>No active reminders on this account.</p>
          <p>
            <Link to="/">Look up an address and sign up</Link>
          </p>
        </section>
      ) : (
        subs.map((sub) => (
          <SubscriptionCard key={sub.id} sub={sub} onUpdated={load} />
        ))
      )}
      <p>
        <Link to="/">← Back to home</Link>
      </p>
    </section>
  )
}
