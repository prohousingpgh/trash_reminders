import { Link, Outlet } from 'react-router-dom'

export function Layout() {
  return (
    <div className="layout">
      <header className="site-header">
        <h1>
          <Link to="/" style={{ color: 'inherit', textDecoration: 'none' }}>
            PGH Pickup Reminders
          </Link>
        </h1>
        <p>Trash, recycling, and yard waste schedules for Pittsburgh — with email &amp; text reminders.</p>
        <nav className="site-nav">
          <Link to="/">Look up schedule</Link>
          <Link to="/privacy">Privacy</Link>
        </nav>
      </header>
      <main>
        <Outlet />
      </main>
    </div>
  )
}
