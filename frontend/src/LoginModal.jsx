import { useEffect, useRef, useState } from 'react'
import { LoaderCircle, LogIn, X } from 'lucide-react'

/**
 * Mentor login dialog. Credentials are validated by the backend (/auth/login).
 * There is intentionally no student login or registration.
 */
export default function LoginModal({ onClose, onLogin }) {
  const [userId, setUserId] = useState('')
  const [password, setPassword] = useState('')
  const [error, setError] = useState('')
  const [submitting, setSubmitting] = useState(false)
  const userRef = useRef(null)

  useEffect(() => {
    userRef.current?.focus()
    const onKey = (e) => { if (e.key === 'Escape') onClose() }
    window.addEventListener('keydown', onKey)
    return () => window.removeEventListener('keydown', onKey)
  }, [onClose])

  async function submit(e) {
    e.preventDefault()
    if (submitting) return
    if (!userId.trim() || !password) {
      setError('Please enter both the mentor user ID and password.')
      return
    }
    setSubmitting(true)
    setError('')
    try {
      await onLogin(userId.trim(), password)
    } catch (err) {
      setError(err.status === 401 ? 'Incorrect mentor user ID or password.' : err.message)
      setPassword('')
      setSubmitting(false)
    }
  }

  return (
    <div className="modal-backdrop" onMouseDown={e => { if (e.target === e.currentTarget) onClose() }}>
      <div className="modal" role="dialog" aria-modal="true" aria-labelledby="login-title">
        <button type="button" className="modal-close" onClick={onClose} aria-label="Close login"><X size={16}/></button>
        <div className="modal-icon"><LogIn size={20}/></div>
        <h2 id="login-title">Mentor login</h2>
        <p className="modal-sub">Mentors can upload and manage the knowledge base. Students can use the chat without logging in.</p>
        <form onSubmit={submit} noValidate>
          <label htmlFor="mentor-user">User ID</label>
          <input id="mentor-user" ref={userRef} type="email" autoComplete="username" value={userId}
            onChange={e => setUserId(e.target.value)} placeholder="name@transflower.in" disabled={submitting}/>
          <label htmlFor="mentor-pass">Password</label>
          <input id="mentor-pass" type="password" autoComplete="current-password" value={password}
            onChange={e => setPassword(e.target.value)} placeholder="Password" disabled={submitting}/>
          {error && <div className="modal-error" role="alert">{error}</div>}
          <div className="modal-actions">
            <button type="button" className="btn-secondary" onClick={onClose} disabled={submitting}>Cancel</button>
            <button type="submit" className="btn-primary" disabled={submitting}>
              {submitting ? <><LoaderCircle className="spin" size={15}/> Signing in…</> : 'Login'}
            </button>
          </div>
        </form>
      </div>
    </div>
  )
}
