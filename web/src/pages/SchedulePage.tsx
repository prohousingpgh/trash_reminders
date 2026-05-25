import { useEffect, useState, type FormEvent } from 'react'
import { Link, useSearchParams } from 'react-router-dom'
import { confirmSms, createSubscription, locateAddress, locateByParts } from '../api'
import type { LocateResult } from '../types'

const SMS_SIGNUP_AVAILABLE = false

function PickupCards({ schedule }: { schedule: LocateResult }) {
  return (
    <div className="pickup-grid">
      <div className="pickup-card trash">
        <h3>Trash</h3>
        <div className="date">{schedule.next_pickup_date_long}</div>
      </div>
      <div className="pickup-card recycle">
        <h3>Recycling</h3>
        <div className="date">{schedule.next_recycling_date_long}</div>
      </div>
      <div className="pickup-card yard">
        <h3>Yard waste</h3>
        <div className="date">{schedule.next_yard_date_long}</div>
      </div>
    </div>
  )
}

function SubscribeForm({ schedule }: { schedule: LocateResult }) {
  const [emailEnabled, setEmailEnabled] = useState(true)
  const [prohousingNewsletter, setProhousingNewsletter] = useState(true)
  const [smsEnabled, setSmsEnabled] = useState(false)
  const [holidayOnly, setHolidayOnly] = useState(false)
  const [email, setEmail] = useState('')
  const [phone, setPhone] = useState('')
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState<string | null>(null)
  const [message, setMessage] = useState<string | null>(null)
  const [subId, setSubId] = useState<string | null>(null)

  async function onSubmit(e: FormEvent) {
    e.preventDefault()
    setLoading(true)
    setError(null)
    setMessage(null)
    try {
      const result = await createSubscription({
        house_number: schedule.number,
        street: schedule.street,
        zip: String(schedule.zip),
        hood: schedule.hood,
        division: schedule.division,
        regular_trash_pickup_day: schedule.regular_trash_pickup_day,
        email: emailEnabled ? email : undefined,
        phone: smsEnabled ? phone : undefined,
        email_enabled: emailEnabled,
        sms_enabled: smsEnabled,
        holiday_only: holidayOnly,
        prohousing_newsletter: emailEnabled && prohousingNewsletter,
      })
      setMessage(result.message)
      setSubId(result.subscription.id)
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Signup failed')
    } finally {
      setLoading(false)
    }
  }

  async function onConfirmSms() {
    if (!subId) return
    setLoading(true)
    setError(null)
    try {
      const result = await confirmSms(subId)
      setMessage(result.message)
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Confirmation failed')
    } finally {
      setLoading(false)
    }
  }

  return (
    <section className="card subscribe-form">
      <h2>Sign up for reminders</h2>
      <p className="page-meta">Free reminders sent around 6 PM the evening before pickup.</p>
      {error && <div className="error">{error}</div>}
      {message && (
        <div className="success">
          {message}
          {subId && smsEnabled && !message.includes('confirmed') && (
            <p style={{ margin: '0.5rem 0 0' }}>
              <button type="button" className="btn btn-secondary" onClick={onConfirmSms} disabled={loading}>
                I replied YES — confirm SMS
              </button>
            </p>
          )}
        </div>
      )}
      {!message && (
        <form onSubmit={onSubmit}>
          <label className="checkbox">
            <input type="checkbox" checked={emailEnabled} onChange={(e) => setEmailEnabled(e.target.checked)} />
            Email reminders
          </label>
          {emailEnabled && (
            <>
              <label className="field" htmlFor="email">
                Email address
              </label>
              <input
                id="email"
                type="email"
                value={email}
                onChange={(e) => setEmail(e.target.value)}
                required={emailEnabled}
                placeholder="you@example.com"
              />
              <label className="checkbox newsletter-opt-in">
                <input
                  type="checkbox"
                  checked={prohousingNewsletter}
                  onChange={(e) => setProhousingNewsletter(e.target.checked)}
                />
                Also subscribe me to{' '}
                <a href="https://prohousingpgh.org" target="_blank" rel="noopener noreferrer">
                  Pro-Housing Pittsburgh
                </a>{' '}
                email updates (optional)
              </label>
            </>
          )}
          <label className={`checkbox${SMS_SIGNUP_AVAILABLE ? '' : ' checkbox-disabled'}`}>
            <input
              type="checkbox"
              checked={smsEnabled}
              disabled={!SMS_SIGNUP_AVAILABLE}
              onChange={(e) => setSmsEnabled(e.target.checked)}
            />
            <span>
              Text message reminders
              {!SMS_SIGNUP_AVAILABLE && <span className="coming-soon-label">Coming soon</span>}
            </span>
          </label>
          {SMS_SIGNUP_AVAILABLE && smsEnabled && (
            <>
              <label className="field" htmlFor="phone">
                Mobile phone
              </label>
              <input
                id="phone"
                type="tel"
                value={phone}
                onChange={(e) => setPhone(e.target.value)}
                required={smsEnabled}
                placeholder="4125551234"
              />
            </>
          )}
          <label className="checkbox">
            <input type="checkbox" checked={holidayOnly} onChange={(e) => setHolidayOnly(e.target.checked)} />
            Only notify me about holiday or weather delays
          </label>
          <button
            type="submit"
            disabled={
              loading ||
              (SMS_SIGNUP_AVAILABLE ? !emailEnabled && !smsEnabled : !emailEnabled)
            }
          >
            {loading ? 'Signing up…' : 'Sign up for reminders'}
          </button>
        </form>
      )}
    </section>
  )
}

export function SchedulePage() {
  const [params, setParams] = useSearchParams()
  const house = params.get('house') ?? ''
  const street = params.get('street') ?? ''
  const zip = params.get('zip') ?? ''
  const legacyAddress = params.get('address') ?? ''
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)
  const [results, setResults] = useState<LocateResult[]>([])
  const [selected, setSelected] = useState<LocateResult | null>(null)

  useEffect(() => {
    const hasStructured = house.trim() && street.trim()
    if (!hasStructured && !legacyAddress.trim()) {
      setLoading(false)
      setError('Select an address on the home page.')
      return
    }

    setLoading(true)
    setError(null)
    setSelected(null)

    const lookup = hasStructured
      ? locateByParts(house.trim(), street.trim(), zip)
      : locateAddress(legacyAddress.trim(), zip)

    lookup
      .then((data) => {
        setResults(data.results)
        if (data.results.length === 1) {
          setSelected(data.results[0])
        }
      })
      .catch((err) => {
        setResults([])
        setError(err instanceof Error ? err.message : 'Lookup failed')
      })
      .finally(() => setLoading(false))
  }, [house, street, zip, legacyAddress])

  function selectResult(result: LocateResult) {
    setSelected(result)
    const next = new URLSearchParams()
    next.set('house', result.number)
    next.set('street', result.street)
    next.set('zip', String(result.zip))
    setParams(next, { replace: true })
  }

  if (loading) {
    return <p className="page-meta">Looking up schedule…</p>
  }

  if (error) {
    return (
      <>
        <div className="error">{error}</div>
        <p>
          <Link to="/">Try another address</Link>
        </p>
      </>
    )
  }

  if (!selected && results.length > 1) {
    return (
      <section className="card">
        <h2>Multiple matches — choose your address</h2>
        <ul className="disambiguation-list">
          {results.map((r) => (
            <li key={`${r.number}-${r.street}-${r.zip}`}>
              <button type="button" onClick={() => selectResult(r)}>
                {r.number} {r.street}, Pittsburgh PA {r.zip}
                {r.hood ? ` (${r.hood})` : ''}
              </button>
            </li>
          ))}
        </ul>
      </section>
    )
  }

  if (!selected) {
    return (
      <p>
        <Link to="/">Search again</Link>
      </p>
    )
  }

  return (
    <>
      <p>
        <Link to="/">← Search again</Link>
      </p>
      {selected.holiday_cancellation && (
        <div className="alert-banner">
          <strong>Schedule note:</strong> Upcoming pickups may be affected by a holiday. Check the
          city&apos;s DPW page for details.
        </div>
      )}
      <section className="card">
        <h2>
          {selected.number} {selected.street}
        </h2>
        <p className="page-meta">
          {selected.hood} · {selected.division} division · ZIP {selected.zip}
        </p>
        {selected.next_recycling && <p>{selected.next_recycling}</p>}
        <PickupCards schedule={selected} />
      </section>
      <SubscribeForm schedule={selected} />
    </>
  )
}
