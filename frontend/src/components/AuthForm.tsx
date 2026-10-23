import { useState, type FormEvent } from 'react'
import { ApiError, login, signup } from '../api'
import { credentialsError, type AuthUser } from '../types'

export function AuthForm({ onAuthenticated }: { onAuthenticated: (user: AuthUser) => void }) {
  const [mode, setMode] = useState<'login' | 'signup'>('login')
  const [email, setEmail] = useState('')
  const [password, setPassword] = useState('')
  const [error, setError] = useState<string | null>(null)
  const [submitting, setSubmitting] = useState(false)

  const isSignup = mode === 'signup'

  function switchMode() {
    setMode(isSignup ? 'login' : 'signup')
    setPassword('')
    setError(null)
  }

  async function handleSubmit(e: FormEvent) {
    e.preventDefault()
    const invalid = credentialsError(email, password, isSignup)
    if (invalid) {
      setError(invalid)
      return
    }
    setSubmitting(true)
    setError(null)
    try {
      const user = await (isSignup ? signup : login)(email, password)
      // 성공한 뒤에만 보드로 넘어간다. (D-005)
      onAuthenticated(user)
    } catch (err) {
      // 실패하면 이메일은 남기고 비밀번호만 비운다.
      setPassword('')
      setError(err instanceof ApiError ? err.message : '요청을 처리하지 못했습니다.')
    } finally {
      setSubmitting(false)
    }
  }

  return (
    <main className="auth">
      <h1>Task Flow</h1>
      <form className="auth-form" onSubmit={handleSubmit}>
        <input
          type="email"
          aria-label="이메일"
          placeholder="이메일"
          autoComplete="email"
          value={email}
          onChange={(e) => setEmail(e.target.value)}
        />
        <input
          type="password"
          aria-label="비밀번호"
          placeholder="비밀번호"
          autoComplete={isSignup ? 'new-password' : 'current-password'}
          value={password}
          onChange={(e) => setPassword(e.target.value)}
        />
        <button type="submit" disabled={submitting}>
          {isSignup ? '가입' : '로그인'}
        </button>
        {error && (
          <p className="form-error" role="alert">
            {error}
          </p>
        )}
        <button type="button" className="link" onClick={switchMode}>
          {isSignup ? '이미 계정이 있으면 로그인' : '계정이 없으면 가입'}
        </button>
      </form>
    </main>
  )
}
