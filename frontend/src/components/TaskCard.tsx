import { useState } from 'react'
import { ApiError } from '../api'
import {
  COLUMNS,
  PRIORITIES,
  priorityLabel,
  titleError,
  type Draft,
  type Priority,
  type Status,
  type Task,
} from '../types'

interface Props {
  task: Task
  draft?: Draft // 있으면 수정 중이다.
  onChangeStatus: (task: Task, status: Status) => Promise<void>
  onStartEdit: (task: Task) => void
  onEditChange: (task: Task, draft: Draft) => void
  onCancelEdit: (task: Task) => void
  onSave: (task: Task, draft: Draft) => Promise<void>
  onDelete: (task: Task) => Promise<void>
}

export function TaskCard({
  task,
  draft,
  onChangeStatus,
  onStartEdit,
  onEditChange,
  onCancelEdit,
  onSave,
  onDelete,
}: Props) {
  const [pending, setPending] = useState(false)
  const [error, setError] = useState<string | null>(null)

  // 요청 하나를 보내고, 실패하면 카드는 그대로 둔 채 안내만 보인다. (D-005)
  async function run(action: () => Promise<void>) {
    if (pending) return
    setPending(true)
    setError(null)
    try {
      await action()
    } catch (err) {
      setError(err instanceof ApiError ? err.message : '요청을 처리하지 못했습니다.')
    } finally {
      setPending(false)
    }
  }

  function handleStatus(status: Status) {
    if (status === task.status) return
    run(() => onChangeStatus(task, status))
  }

  function handleSave() {
    if (!draft) return
    const invalid = titleError(draft.title)
    if (invalid) {
      setError(invalid)
      return
    }
    run(() => onSave(task, draft))
  }

  function handleDelete() {
    if (!window.confirm('이 카드를 삭제할까요?')) return
    run(() => onDelete(task))
  }

  return (
    <article className={task.overdue ? 'card overdue' : 'card'}>
      {draft ? (
        <div className="card-edit">
          <input
            aria-label="제목"
            value={draft.title}
            onChange={(e) => onEditChange(task, { ...draft, title: e.target.value })}
          />
          <textarea
            aria-label="설명"
            rows={3}
            value={draft.description}
            onChange={(e) =>
              onEditChange(task, { ...draft, description: e.target.value })
            }
          />
          <div className="field-row">
            <label>
              우선순위
              <select
                value={draft.priority}
                onChange={(e) =>
                  onEditChange(task, { ...draft, priority: e.target.value as Priority })
                }
              >
                {PRIORITIES.map(({ value, label }) => (
                  <option key={value} value={value}>
                    {label}
                  </option>
                ))}
              </select>
            </label>
            <label>
              마감일
              <input
                type="date"
                max="9999-12-31"
                value={draft.dueDate}
                onChange={(e) => onEditChange(task, { ...draft, dueDate: e.target.value })}
              />
            </label>
            <button
              type="button"
              disabled={pending || !draft.dueDate}
              onClick={() => onEditChange(task, { ...draft, dueDate: '' })}
            >
              마감일 비우기
            </button>
          </div>
          <div className="card-actions">
            <button type="button" disabled={pending} onClick={handleSave}>
              저장
            </button>
            <button type="button" disabled={pending} onClick={() => onCancelEdit(task)}>
              취소
            </button>
          </div>
        </div>
      ) : (
        <>
          <h3>{task.title}</h3>
          {task.description && <p className="card-desc">{task.description}</p>}
          <div className="card-meta">
            <span className={`badge priority-${task.priority.toLowerCase()}`}>
              우선순위 {priorityLabel(task.priority)}
            </span>
            {task.due_date && <span className="due-date">마감 {task.due_date}</span>}
            {task.overdue && <span className="badge badge-overdue">기한 초과</span>}
          </div>
        </>
      )}
      <div className="card-actions" role="group" aria-label="상태 변경">
        {COLUMNS.map(({ status, label }) => (
          <button
            key={status}
            type="button"
            className={status === task.status ? 'current' : undefined}
            aria-pressed={status === task.status}
            disabled={pending}
            onClick={() => handleStatus(status)}
          >
            {label}
          </button>
        ))}
      </div>
      <div className="card-actions">
        {!draft && (
          <button type="button" disabled={pending} onClick={() => onStartEdit(task)}>
            수정
          </button>
        )}
        <button type="button" disabled={pending} onClick={handleDelete}>
          삭제
        </button>
      </div>
      {error && (
        <p className="form-error" role="alert">
          {error}
        </p>
      )}
    </article>
  )
}
