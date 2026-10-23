import { useEffect, useState } from 'react'
import { ApiError, CONNECTION_ERROR, fetchMe, logout } from './api'
import { AuthForm } from './components/AuthForm'
import { Board } from './components/Board'
import type { AuthUser } from './types'

type AuthState =
  | { kind: 'checking' }
  | { kind: 'error'; message: string }
  | { kind: 'out' }
  | { kind: 'in'; user: AuthUser }

function App() {
  const [auth, setAuth] = useState<AuthState>({ kind: 'checking' })
  const [logoutError, setLogoutError] = useState<string | null>(null)

  // 처음 열 때 로그인 상태를 확인한다. 401 이면 로그인 화면, 연결 실패면 다시 시도 안내.
  function loadMe() {
    fetchMe()
      .then((user) => setAuth({ kind: 'in', user }))
      .catch((err) => {
        if (err instanceof ApiError && err.status === 401) {
          setAuth({ kind: 'out' })
        } else {
          setAuth({
            kind: 'error',
            message: err instanceof ApiError ? err.message : CONNECTION_ERROR,
          })
        }
      })
  }

  function retryCheck() {
    setAuth({ kind: 'checking' })
    loadMe()
  }

  useEffect(() => {
    // 처음 상태가 이미 '확인 중'이라 상태를 다시 바꾸지 않고 요청만 보낸다.
    loadMe()
  }, [])

  async function handleLogout() {
    setLogoutError(null)
    try {
      await logout()
      setAuth({ kind: 'out' })
    } catch (err) {
      // 이미 만료된 세션(401)이면 로그아웃된 것과 같다. 그 밖의 실패는 로그인 상태를 유지하고 알린다.
      if (err instanceof ApiError && err.status === 401) {
        setAuth({ kind: 'out' })
        return
      }
      setLogoutError(err instanceof ApiError ? err.message : CONNECTION_ERROR)
    }
  }

  if (auth.kind === 'checking') {
    return (
      <main>
        <p className="notice">불러오는 중…</p>
      </main>
    )
  }

  if (auth.kind === 'error') {
    return (
      <main>
        <div className="notice error" role="alert">
          <p>{auth.message}</p>
          <button type="button" onClick={retryCheck}>
            다시 시도
          </button>
        </div>
      </main>
    )
  }

  if (auth.kind === 'out') {
    return <AuthForm onAuthenticated={(user) => setAuth({ kind: 'in', user })} />
  }

  return (
    <>
      <header className="user-bar">
        <span>{auth.user.email}</span>
        <button type="button" onClick={handleLogout}>
          로그아웃
        </button>
        {logoutError && (
          <span className="form-error" role="alert">
            {logoutError}
          </span>
        )}
      </header>
      <Board />
    </>
  )
}

export default App
