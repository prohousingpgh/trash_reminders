import { BrowserRouter, Navigate, Route, Routes } from 'react-router-dom'
import { Layout } from './components/Layout'
import { AccountLoginPage } from './pages/AccountLoginPage'
import { AccountPage } from './pages/AccountPage'
import { AccountVerifyPage } from './pages/AccountVerifyPage'
import { AdminAlertsPage } from './pages/AdminAlertsPage'
import { HomePage } from './pages/HomePage'
import { PrivacyPage } from './pages/PrivacyPage'
import { SchedulePage } from './pages/SchedulePage'
import { UnsubscribePage } from './pages/UnsubscribePage'
import { VerifyEmailPage } from './pages/VerifyEmailPage'

function App() {
  return (
    <BrowserRouter>
      <Routes>
        <Route element={<Layout />}>
          <Route index element={<HomePage />} />
          <Route path="schedule" element={<SchedulePage />} />
          <Route path="account/login" element={<AccountLoginPage />} />
          <Route path="account/verify" element={<AccountVerifyPage />} />
          <Route path="account" element={<AccountPage />} />
          <Route path="verify/email" element={<VerifyEmailPage />} />
          <Route path="unsubscribe/:token" element={<UnsubscribePage />} />
          <Route path="privacy" element={<PrivacyPage />} />
          <Route path="admin/alerts" element={<AdminAlertsPage />} />
          <Route path="*" element={<Navigate to="/" replace />} />
        </Route>
      </Routes>
    </BrowserRouter>
  )
}

export default App
