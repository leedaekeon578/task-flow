import type { SuggestState } from './useSuggest'

const SUGGEST_PENDING = '제안을 받는 중...'

// 제목 · 설명 아래에 놓는 버튼 줄. 기다리는 동안 버튼만 잠근다.
export function SuggestButton({
  suggest,
  onClick,
}: {
  suggest: SuggestState
  onClick: () => void
}) {
  return (
    <div className="suggest-row">
      <button type="button" disabled={suggest.pending} onClick={onClick}>
        AI 제안
      </button>
      {suggest.pending && (
        <span className="suggest-status" role="status">
          {SUGGEST_PENDING}
        </span>
      )}
      {suggest.error && (
        <span className="form-error" role="alert">
          {suggest.error}
        </span>
      )}
    </div>
  )
}

// 우선순위 · 마감일 칸 아래에 놓는 reason 한 줄.
export function SuggestReason({ suggest }: { suggest: SuggestState }) {
  if (!suggest.reason) return null
  return <p className="suggest-reason">{suggest.reason}</p>
}
