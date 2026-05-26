export function PrivacyPage() {
  return (
    <section className="card">
      <h2>Privacy</h2>
      <p>
        Pittsburgh Trash Reminders uses your email address and/or phone number only to send trash,
        recycling, and yard waste pickup reminders for the address you register.
      </p>
      <p>
        We do not sell or share your contact information for pickup reminders, and you will not
        receive advertisements from the reminder service itself.
      </p>
      <p>
        If you opt in at signup, your email address is also sent to Pro-Housing Pittsburgh&apos;s
        separate Mailchimp newsletter list. That list has its own privacy practices and unsubscribe
        links in those emails.
      </p>
      <p>
        Schedule data comes from public City of Pittsburgh collection information.
      </p>
      <h3>Unsubscribe</h3>
      <ul>
        <li>Email: use the unsubscribe link in any reminder email.</li>
        <li>SMS: reply STOP to any reminder text. Reply START to resume.</li>
        <li>
          Manage all addresses: use <a href="/account">My reminders</a> to sign in with a one-time email
          link.
        </li>
      </ul>
    </section>
  )
}
