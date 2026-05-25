import { useState, type FormEvent } from 'react'
import { createAlert, deleteAlert, listAlerts } from '../api'
import type { ServiceAlert } from '../types'

export function AdminAlertsPage() {
  const [password, setPassword] = useState('')
  const [authenticated, setAuthenticated] = useState(false)
  const [alerts, setAlerts] = useState<ServiceAlert[]>([])
  const [message, setMessage] = useState('')
  const [division, setDivision] = useState('')
  const [alertMessage, setAlertMessage] = useState('')
  const [error, setError] = useState<string | null>(null)
  const [loading, setLoading] = useState(false)

  async function loadAlerts(pwd: string) {
    setLoading(true)
    setError(null)
    try {
      const data = await listAlerts(pwd)
      setAlerts(data)
      setAuthenticated(true)
      setPassword(pwd)
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Could not load alerts')
      setAuthenticated(false)
    } finally {
      setLoading(false)
    }
  }

  function onLogin(e: FormEvent) {
    e.preventDefault()
    loadAlerts(password)
  }

  async function onCreate(e: FormEvent) {
    e.preventDefault()
    setLoading(true)
    setError(null)
    try {
      await createAlert(password, alertMessage.trim(), division.trim() || undefined)
      setAlertMessage('')
      setDivision('')
      setMessage('Alert posted.')
      setAlerts(await listAlerts(password))
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Could not create alert')
    } finally {
      setLoading(false)
    }
  }

  async function onDelete(alertId: string) {
    setLoading(true)
    setError(null)
    try {
      await deleteAlert(password, alertId)
      setAlerts(await listAlerts(password))
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Could not delete alert')
    } finally {
      setLoading(false)
    }
  }

  if (!authenticated) {
    return (
      <section className="card">
        <h2>Admin — service alerts</h2>
        <p className="page-meta">Post weather or holiday delay notices shown in reminders.</p>
        {error && <div className="error">{error}</div>}
        <form onSubmit={onLogin}>
          <label htmlFor="admin-password">Admin password</label>
          <input
            id="admin-password"
            type="password"
            value={password}
            onChange={(e) => setPassword(e.target.value)}
            required
          />
          <button type="submit" disabled={loading}>
            Sign in
          </button>
        </form>
      </section>
    )
  }

  return (
    <>
      <section className="card">
        <h2>Post alert</h2>
        {message && <div className="success">{message}</div>}
        {error && <div className="error">{error}</div>}
        <form onSubmit={onCreate}>
          <label htmlFor="alert-message">Message</label>
          <input
            id="alert-message"
            value={alertMessage}
            onChange={(e) => setAlertMessage(e.target.value)}
            required
            placeholder="Friday collections delayed to Monday due to weather"
          />
          <label htmlFor="alert-division">Division (optional)</label>
          <input
            id="alert-division"
            value={division}
            onChange={(e) => setDivision(e.target.value)}
            placeholder="EASTERN, CENTRAL, etc."
          />
          <button type="submit" disabled={loading}>
            Post alert
          </button>
        </form>
      </section>

      <section className="card">
        <h2>Active alerts</h2>
        {alerts.length === 0 ? (
          <p className="page-meta">No active alerts.</p>
        ) : (
          <ul className="admin-list">
            {alerts.map((alert) => (
              <li key={alert.id}>
                <div>
                  <strong>{alert.message}</strong>
                  {alert.division && <div className="page-meta">Division: {alert.division}</div>}
                </div>
                <button type="button" className="btn btn-danger" onClick={() => onDelete(alert.id)} disabled={loading}>
                  Remove
                </button>
              </li>
            ))}
          </ul>
        )}
      </section>
    </>
  )
}
