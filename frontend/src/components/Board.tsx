import { useCallback, useEffect, useState } from 'react'
import { ApiError, changeStatus, listTasks } from '../api'
import { COLUMNS, type Status, type Task } from '../types'
import { Column } from './Column'
import { TaskForm } from './TaskForm'

export function Board() {
  const [tasks, setTasks] = useState<Task[]>([])

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

  // 저장이 성공한 뒤에만 카드를 새 열로 옮긴다. 열 안 순서는 id 순서 그대로다. (D-005)
  async function handleChangeStatus(task: Task, status: Status) {
    try {
      const updated = await changeStatus(task.id, status)
      setTasks((prev) => prev.map((t) => (t.id === updated.id ? updated : t)))
    } catch (err) {
      // 없는 카드면 보드를 다시 불러와 저장 내용에 맞춘다. (S-07)
      if (err instanceof ApiError && err.status === 404) await reload()
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
            onChangeStatus={handleChangeStatus}
          />
        ))}
      </div>
    </main>
  )
}
