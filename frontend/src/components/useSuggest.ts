import { useCallback, useEffect, useRef, useState } from 'react'
import { ApiError, suggestTask } from '../api'
import { titleError, type Suggestion } from '../types'

const SUGGEST_UNAVAILABLE = '지금은 AI 제안을 쓸 수 없습니다. 직접 입력을 주세요.'
const SUGGEST_FAILED = '제안을 못 받았습니다. 다시 제안 버튼을 눌러 보세요.'

function errorMessage(err: unknown): string {
  if (err instanceof ApiError) {
    if (err.status === 503) return SUGGEST_UNAVAILABLE
    if (err.status === 502) return SUGGEST_FAILED
    return err.message
  }
  return '요청을 처리하지 못했습니다.'
}

// AI 제안 요청의 상태. 입력칸을 채우는 일은 부르는 쪽(onSuggested)이 한다.
// 실패해도 입력칸은 건드리지 않고, 등록 · 저장 버튼에는 영향이 없다.
export function useSuggest() {
  const [pending, setPending] = useState(false)
  const [error, setError] = useState<string | null>(null)
  const [reason, setReason] = useState<string | null>(null)
  // 요청 번호. 기다리는 중에 등록 · 저장 · 취소로 상황이 바뀌면 늦게 온 응답을 버린다.
  const seq = useRef(0)

  const reset = useCallback(() => {
    seq.current += 1
    setPending(false)
    setError(null)
    setReason(null)
  }, [])

  useEffect(
    () => () => {
      seq.current += 1
    },
    [],
  )

  const run = useCallback(
    async (
      title: string,
      description: string,
      onSuggested: (suggestion: Suggestion) => void,
    ) => {
      const invalid = titleError(title)
      if (invalid) {
        setReason(null)
        setError(invalid)
        return
      }
      seq.current += 1
      const id = seq.current
      setPending(true)
      setError(null)
      setReason(null)
      try {
        const suggestion = await suggestTask(title, description)
        if (id !== seq.current) return
        onSuggested(suggestion)
        setReason(suggestion.reason)
      } catch (err) {
        if (id !== seq.current) return
        setError(errorMessage(err))
      } finally {
        if (id === seq.current) setPending(false)
      }
    },
    [],
  )

  return { pending, error, reason, run, reset }
}

export type SuggestState = ReturnType<typeof useSuggest>
