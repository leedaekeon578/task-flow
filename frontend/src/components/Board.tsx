import { useCallback, useEffect, useState } from 'react'
import { ApiError, changeStatus, deleteTask, listTasks, updateTask } from '../api'
import { COLUMNS, type Draft, type Status, type Task } from '../types'
import { Column } from './Column'
import { TaskForm } from './TaskForm'

function without<T>(record: Record<number, T>, id: number): Record<number, T> {
  const { [id]: _removed, ...rest } = record
  return rest
}

export function Board() {
  const [tasks, setTasks] = useState<Task[]>([])
  // 수정 중인 카드의 입력값. 카드가 다른 열로 옮겨져도 남도록 보드가 들고 있다.
  const [drafts, setDrafts] = useState<Record<number, Draft>>({})

  const reload = useCallback(
    () =>
      // 불러오는 중 · 실패 화면은 이슈 #4 에서 만든다.
      listTasks()
        .then(setTasks)
        .catch(() => {}),
    [],
  )

  useEffect(() => {
    reload()
  }, [reload])

  function replace(updated: Task) {
    setTasks((prev) => prev.map((t) => (t.id === updated.id ? updated : t)))
  }

  // 없는 카드(404)면 보드를 다시 불러와 저장 내용에 맞춘다. (S-07)
  async function reloadIfMissing(err: unknown, id: number) {
    if (err instanceof ApiError && err.status === 404) {
      setDrafts((prev) => without(prev, id))
      await reload()
    }
  }

  // 저장이 성공한 뒤에만 화면을 바꾼다. 열 안 순서는 id 순서 그대로다. (D-005)
  async function handleChangeStatus(task: Task, status: Status) {
    try {
      replace(await changeStatus(task.id, status))
    } catch (err) {
      await reloadIfMissing(err, task.id)
      throw err
    }
  }

  async function handleSave(task: Task, draft: Draft) {
    try {
      replace(await updateTask(task.id, draft.title, draft.description))
      setDrafts((prev) => without(prev, task.id))
    } catch (err) {
      await reloadIfMissing(err, task.id)
      throw err
    }
  }

  async function handleDelete(task: Task) {
    try {
      await deleteTask(task.id)
      setTasks((prev) => prev.filter((t) => t.id !== task.id))
      setDrafts((prev) => without(prev, task.id))
    } catch (err) {
      // 이미 지워진 카드면 보드만 다시 불러오고 오류는 보이지 않는다.
      if (err instanceof ApiError && err.status === 404) {
        await reloadIfMissing(err, task.id)
        return
      }
      throw err
    }
  }

  return (
    <main>
      <h1>Task Flow</h1>
      <TaskForm onCreated={(task) => setTasks((prev) => [...prev, task])} />
      <div className="columns">
        {COLUMNS.map(({ status, label }) => (
          <Column
            key={status}
            label={label}
            tasks={tasks.filter((t) => t.status === status)}
            drafts={drafts}
            onChangeStatus={handleChangeStatus}
            onStartEdit={(t) =>
              setDrafts((prev) => ({
                ...prev,
                [t.id]: { title: t.title, description: t.description },
              }))
            }
            onEditChange={(t, d) => setDrafts((prev) => ({ ...prev, [t.id]: d }))}
            onCancelEdit={(t) => setDrafts((prev) => without(prev, t.id))}
            onSave={handleSave}
            onDelete={handleDelete}
          />
        ))}
      </div>
    </main>
  )
}
