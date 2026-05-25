import type { LocateResponse, ServiceAlert, Subscription, AddressSuggestion } from './types'

async function apiFetch<T>(path: string, init?: RequestInit): Promise<T> {
  const response = await fetch(path, {
    headers: { 'Content-Type': 'application/json', ...init?.headers },
    ...init,
  })
  const data = await response.json().catch(() => ({}))
  if (!response.ok) {
    const detail = (data as { detail?: string }).detail ?? 'Request failed'
    throw new Error(typeof detail === 'string' ? detail : 'Request failed')
  }
  return data as T
}

export async function autocompleteAddress(query: string): Promise<AddressSuggestion[]> {
  const params = new URLSearchParams({ q: query })
  const data = await apiFetch<{ suggestions: AddressSuggestion[] }>(`/api/autocomplete?${params}`)
  return data.suggestions
}

export async function locateByParts(
  house: string,
  street: string,
  zip: string
): Promise<LocateResponse> {
  const params = new URLSearchParams()
  if (zip) params.set('zip', zip)
  const qs = params.toString()
  return apiFetch<LocateResponse>(
    `/api/locate/${encodeURIComponent(house)}/${encodeURIComponent(street)}${qs ? `?${qs}` : ''}`
  )
}

export async function locateAddress(address: string, zip: string): Promise<LocateResponse> {
  const params = new URLSearchParams({ address })
  if (zip) params.set('zip', zip)
  return apiFetch<LocateResponse>(`/api/locate?${params}`)
}

export type SubscriptionInput = {
  house_number: string
  street: string
  zip: string
  hood?: string | null
  division?: string | null
  regular_trash_pickup_day?: number | null
  email?: string
  phone?: string
  email_enabled: boolean
  sms_enabled: boolean
  holiday_only: boolean
  prohousing_newsletter?: boolean
}

export async function createSubscription(
  input: SubscriptionInput
): Promise<{ subscription: Subscription; message: string }> {
  return apiFetch('/api/subscriptions', {
    method: 'POST',
    body: JSON.stringify(input),
  })
}

export async function verifyEmail(token: string): Promise<{ subscription: Subscription; message: string }> {
  return apiFetch(`/api/subscriptions/verify/${token}`)
}

export async function confirmSms(subId: string): Promise<{ subscription: Subscription; message: string }> {
  return apiFetch(`/api/subscriptions/${subId}/confirm-sms`, { method: 'POST' })
}

export async function unsubscribe(
  token: string,
  channel?: 'email' | 'sms'
): Promise<{ status: string; channel: string }> {
  const params = channel ? `?channel=${channel}` : ''
  return apiFetch(`/api/unsubscribe/${token}${params}`)
}

export async function listAlerts(adminPassword: string): Promise<ServiceAlert[]> {
  const data = await apiFetch<{ alerts: ServiceAlert[] }>('/api/admin/alerts', {
    headers: { 'X-Admin-Password': adminPassword },
  })
  return data.alerts
}

export async function createAlert(
  adminPassword: string,
  message: string,
  division?: string
): Promise<ServiceAlert> {
  const data = await apiFetch<{ alert: ServiceAlert }>('/api/admin/alerts', {
    method: 'POST',
    headers: { 'X-Admin-Password': adminPassword },
    body: JSON.stringify({ message, division: division || null }),
  })
  return data.alert
}

export async function deleteAlert(adminPassword: string, alertId: string): Promise<void> {
  await apiFetch(`/api/admin/alerts/${alertId}`, {
    method: 'DELETE',
    headers: { 'X-Admin-Password': adminPassword },
  })
}
