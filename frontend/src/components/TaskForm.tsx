import { useState, type FormEvent } from 'react'
import { ApiError, createTask } from '../api'
import { SuggestButton, SuggestReason } from './Suggest'
import { useSuggest } from './useSuggest'
import {
  DEFAULT_PRIORITY,
  PRIORITIES,
  titleError,
  type Priority,
  type Task,
} from '../types'

export function TaskForm({ onCreated }: { onCreated: (task: Task) => void }) {
  const [title, setTitle] = useState('')
  const [description, setDescription] = useState('')
  const [priority, setPriority] = useState<Priority>(DEFAULT_PRIORITY)
  const [dueDate, setDueDate] = useState('')
  const [error, setError] = useState<string | null>(null)
  const [saving, setSaving] = useState(false)
  const suggest = useSuggest()

  // 제안은 입력칸만 채운다. 저장은 사용자가 등록 버튼으로 한다.
  // 제안 마감일이 없으면 사용자가 적어 둔 마감일을 지우지 않는다.
  function handleSuggest() {
    suggest.run(title, description, (s) => {
      setPriority(s.priority)
      if (s.due_date) setDueDate(s.due_date)
    })
  }

  async function handleSubmit(e: FormEvent) {
    e.preventDefault()
    const invalid = titleError(title)
    if (invalid) {
      setError(invalid)
      return
    }
    setSaving(true)
    setError(null)
    try {
      const created = await createTask({ title, description, priority, dueDate })
      // 저장이 성공한 뒤에만 보드에 반영하고 입력 칸을 비운다. (D-005)
      onCreated(created)
      setTitle('')
      setDescription('')
      setPriority(DEFAULT_PRIORITY)
      setDueDate('')
      suggest.reset()
    } catch (err) {
      // 실패하면 입력한 내용을 남긴다.
      setError(err instanceof ApiError ? err.message : '요청을 처리하지 못했습니다.')
    } finally {
      setSaving(false)
    }
  }

  return (
    <form className="task-form" onSubmit={handleSubmit}>
      <input
        aria-label="제목"
        placeholder="제목"
        value={title}
        onChange={(e) => setTitle(e.target.value)}
      />
      <textarea
        aria-label="설명"
        placeholder="설명 (선택)"
        rows={2}
        value={description}
        onChange={(e) => setDescription(e.target.value)}
      />
      <SuggestButton suggest={suggest} onClick={handleSuggest} />
      <div className="field-row">
        <label>
          우선순위
          <select
            value={priority}
            onChange={(e) => setPriority(e.target.value as Priority)}
          >
            {PRIORITIES.map(({ value, label }) => (
              <option key={value} value={value}>
                {label}
              </option>
            ))}
          </select>
        </label>
        <label>
          마감일 (선택)
          <input
            type="date"
            max="9999-12-31"
            value={dueDate}
            onChange={(e) => setDueDate(e.target.value)}
          />
        </label>
      </div>
      <SuggestReason suggest={suggest} />
      <button type="submit" disabled={saving}>
        등록
      </button>
      {error && (
        <p className="form-error" role="alert">
          {error}
        </p>
      )}
    </form>
  )
}
