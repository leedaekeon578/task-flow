import { useEffect, useState } from 'react'

type ApiState = 'checking' | 'ok' | 'down'

function App() {
  const [api, setApi] = useState<ApiState>('checking')

  useEffect(() => {
    fetch('/api/health')
      .then((res) => res.json())
      .then((body) => setApi(body.status === 'ok' ? 'ok' : 'down'))
      .catch(() => setApi('down'))
  }, [])

  return (
    <main>
      <h1>Task Flow</h1>
      <p>
        API 연결:{' '}
        {api === 'checking' ? '확인 중' : api === 'ok' ? '정상' : '연결 실패'}
      </p>
    </main>
  )
}

export default App
