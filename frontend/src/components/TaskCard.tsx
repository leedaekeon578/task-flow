import { useState } from 'react'
import { ApiError } from '../api'
import { COLUMNS, type Status, type Task } from '../types'

interface Props {
  task: Task
  onChangeStatus: (task: Task, status: Status) => Promise<void>
}

export function TaskCard({ task, onChangeStatus }: Props) {
  const [pending, setPending] = useState(false)
  const [error, setError] = useState<string | null>(null)

  async function handleClick(status: Status) {
    if (status === task.status || pending) return
    setPending(true)
    setError(null)
    try {
      await onChangeStatus(task, status)
    } catch (err) {
      // 실패하면 카드는 그대로 두고 안내만 보인다. (D-005)
      setError(err instanceof ApiError ? err.message : '요청을 처리하지 못했습니다.')
    } finally {
      setPending(false)
    }
  }

  return (
    <article className="card">
      <h3>{task.title}</h3>
      {task.description && <p className="card-desc">{task.description}</p>}
      <div className="card-actions" role="group" aria-label="상태 변경">
        {COLUMNS.map(({ status, label }) => (
          <button
            key={status}
            type="button"
            className={status === task.status ? 'current' : undefined}
            aria-pressed={status === task.status}
            disabled={pending}
            onClick={() => handleClick(status)}
          >
            {label}
          </button>
        ))}
      </div>
      {error && (
        <p className="form-error" role="alert">
          {error}
        </p>
      )}
    </article>
  )
}
