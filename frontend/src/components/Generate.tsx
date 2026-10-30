import { priorityLabel, type Task } from '../types'
import type { GenerateState } from './useGenerate'

const GENERATE_PENDING = '제안을 받는 중...'

// [AI 제안] 옆에 놓는 버튼. 기다리는 동안 이 버튼만 잠근다.
export function GenerateButton({
  generate,
  onClick,
}: {
  generate: GenerateState
  onClick: () => void
}) {
  return (
    <>
      <button
        type="button"
        disabled={generate.pending || generate.saving}
        onClick={onClick}
      >
        AI로 할 일 만들기
      </button>
      {generate.pending && (
        <span className="suggest-status" role="status">
          {GENERATE_PENDING}
        </span>
      )}
      {generate.error && (
        <span className="form-error" role="alert">
          {generate.error}
        </span>
      )}
    </>
  )
}

// 제안 미리 보기. 이 단계에서는 저장하지 않고, [모두 등록] 을 눌러야 저장한다.
export function GeneratePreview({
  generate,
  onCreated,
}: {
  generate: GenerateState
  onCreated: (task: Task) => void
}) {
  const { items, summary, saving } = generate
  if (!items) return null
  return (
    <section className="generate-preview" aria-label="AI가 만든 할 일">
      <h2>AI가 만든 할 일 {items.length}개</h2>
      {summary && (
        <p className="form-error" role="alert">
          {summary}
        </p>
      )}
      <ul>
        {items.map(({ key, task, error }) => (
          <li key={key}>
            <span className="generate-title">{task.title}</span>
            <span className="generate-meta">
              우선순위 {priorityLabel(task.priority)} · 마감일{' '}
              {task.due_date ?? '없음'}
            </span>
            {error && <span className="form-error">등록 못 함: {error}</span>}
          </li>
        ))}
      </ul>
      <div className="generate-actions">
        <button
          type="button"
          disabled={saving}
          onClick={() => generate.saveAll(onCreated)}
        >
          모두 등록
        </button>
        <button type="button" disabled={saving} onClick={generate.cancel}>
          취소
        </button>
      </div>
    </section>
  )
}
