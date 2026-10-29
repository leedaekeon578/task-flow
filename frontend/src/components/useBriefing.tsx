import { useCallback, useEffect, useRef, useState } from 'react'
import { ApiError, CONNECTION_ERROR } from '../api'

// POST /api/tasks/briefing 의 응답. 읽기만 하고 저장하지 않는다.
export type Briefing = {
  top3: { id: number; reason: string }[]
  later: number[]
  cheer: string
}

const BRIEFING_UNAVAILABLE = '지금은 브리핑을 쓸 수 없습니다'
const BRIEFING_FAILED = '브리핑을 받지 못했습니다'

// 새 파일만 고치기로 해서 api.ts 의 request() 를 쓰지 않고 같은 방식으로 직접 부른다.
async function requestBriefing(): Promise<Briefing> {
  let res: Response
  try {
    res = await fetch('/api/tasks/briefing', { method: 'POST' })
  } catch {
    throw new ApiError(CONNECTION_ERROR)
  }
  const body = await res.json().catch(() => null)
  if (!res.ok) {
    // 본문 없는 5xx 는 개발 서버 프록시가 API 없이 답한 것이다. 연결 실패로 본다.
    if (body === null && res.status >= 500) throw new ApiError(CONNECTION_ERROR)
    const detail = (body as { detail?: unknown } | null)?.detail
    throw new ApiError(
      typeof detail === 'string' ? detail : '요청을 처리하지 못했습니다.',
      res.status,
    )
  }
  return body as Briefing
}

function errorMessage(err: unknown): string {
  if (err instanceof ApiError) {
    if (err.status === 503) return BRIEFING_UNAVAILABLE
    if (err.status === 502) return BRIEFING_FAILED
    return err.message
  }
  return '요청을 처리하지 못했습니다.'
}

// 오늘 브리핑 요청의 상태. 실패해도 보드와 등록 폼에는 영향이 없다.
export function useBriefing() {
  const [pending, setPending] = useState(false)
  const [error, setError] = useState<string | null>(null)
  const [data, setData] = useState<Briefing | null>(null)
  // 요청 번호. 닫거나 다시 눌렀을 때 늦게 온 응답을 버린다.
  const seq = useRef(0)

  useEffect(
    () => () => {
      seq.current += 1
    },
    [],
  )

  const close = useCallback(() => {
    seq.current += 1
    setPending(false)
    setError(null)
    setData(null)
  }, [])

  const run = useCallback(async () => {
    seq.current += 1
    const id = seq.current
    setPending(true)
    setError(null)
    setData(null)
    try {
      const result = await requestBriefing()
      if (id !== seq.current) return
      setData(result)
    } catch (err) {
      if (id !== seq.current) return
      setError(errorMessage(err))
    } finally {
      if (id === seq.current) setPending(false)
    }
  }, [])

  return { pending, error, data, run, close }
}

export type BriefingState = ReturnType<typeof useBriefing>
