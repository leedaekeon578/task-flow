import { useState } from 'react'
import { COMMAND_MAX_LENGTH, priorityLabel, type CommandAction, type Task } from '../types'
import { useCommand } from './useCommand'

const COMMAND_PENDING = '알아듣는 중.....'

function currentDue(task: Task | undefined): string {
  return task?.due_date ? `지금 마감 ${task.due_date}` : '마감 없음'
}

// 확인 카드 한 줄의 글. 지금 마감은 보드가 가진 카드 목록에서 id 로 찾는다.
function lineText(action: CommandAction, tasks: Task[]): string {
  if (action.kind === 'add') {
    const priority = priorityLabel(action.priority ?? 'NORMAL')
    return `새 카드 「${action.title}」 — 우선순위 ${priority} · 마감 ${action.due_date ?? '없음'}`
  }
  const task = tasks.find((t) => t.id === action.id)
  const head = `${action.title}(${currentDue(task)})`
  if (action.kind === 'done') return `${head} — 완료로`
  return `${head} — 마감을 ${action.due_date}으로`
}

// [오늘 브리핑] 아래 · 보드 위에 놓는 입력란 하나 + [시키기] 단추와 확인 카드.
export function Command({
  tasks,
  onApplied,
}: {
  tasks: Task[]
  onApplied: () => void | Promise<void>
}) {
  const [text, setText] = useState('')
  const command = useCommand()
  const { pending, error, ask, items, applying, summary } = command

  async function handleRun() {
    await command.run(text)
  }

  async function handleApply() {
    if (await command.apply(tasks, onApplied)) setText('')
  }

  return (
    <div className="briefing">
      <input
        type="text"
        value={text}
        maxLength={COMMAND_MAX_LENGTH}
        disabled={pending || applying}
        aria-label="한 문장으로 시키기"
        onChange={(e) => setText(e.target.value)}
      />
      <button type="button" disabled={pending || applying} onClick={handleRun}>
        {pending ? COMMAND_PENDING : '시키기'}
      </button>
      {error && (
        <p className="form-error" role="alert">
          {error}
        </p>
      )}
      {ask && (
        <p className="briefing-empty" role="status">
          {ask}
        </p>
      )}
      {items && (
        <section className="briefing-card" aria-label="바꿀 내용 확인">
          <h2>이렇게 바꿀까요? {items.length}개</h2>
          {summary && (
            <p className="form-error" role="alert">
              {summary}
            </p>
          )}
          <ul>
            {items.map(({ key, action, error: lineError }) => (
              <li key={key}>
                <span>{lineText(action, tasks)}</span>
                {lineError && <span className="form-error">적용 못 함: {lineError}</span>}
              </li>
            ))}
          </ul>
          <div className="briefing-actions">
            <button type="button" disabled={applying} onClick={handleApply}>
              적용
            </button>
            <button type="button" disabled={applying} onClick={command.cancel}>
              취소
            </button>
          </div>
        </section>
      )}
    </div>
  )
}
