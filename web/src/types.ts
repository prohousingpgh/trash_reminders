export type AddressSuggestion = {
  label: string
  house_number: string
  street: string
  zip: string
}

export type LocateResult = {
  division: string
  next_yard_date: string
  next_recycling_date_long: string
  regular_trash_pickup_day: number
  zip: number
  next_yard_date_long: string
  division_sched: number
  number: string
  next_pickup_date: string
  holiday_cancellation: boolean
  street: string
  hood: string
  other_cancellation: boolean
  next_pickup_date_long: string
  next_recycling_date: string
  next_recycling?: string
}

export type LocateResponse = {
  query: { house_number: string; street: string; zip: string | null }
  results: LocateResult[]
  disambiguation_required: boolean
}

export type Subscription = {
  id: string
  house_number: string
  street: string
  zip: string
  hood: string | null
  email_enabled: boolean
  sms_enabled: boolean
  email_verified: boolean
  sms_verified: boolean
  holiday_only: boolean
  active: boolean
  created_at: string
}

export type ServiceAlert = {
  id: string
  message: string
  division: string | null
  active: number
  created_at: string
}

export type AccountSession = {
  authenticated: boolean
  email?: string
}
