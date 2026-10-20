import { useEffect, useState } from 'react'
import { listTasks } from '../api'
import { COLUMNS, type Task } from '../types'
import { Column } from './Column'
import { TaskForm } from './TaskForm'

export function Board() {
  const [tasks, setTasks] = useState<Task[]>([])

  useEffect(() => {
    // 불러오는 중 · 실패 화면은 이슈 #4 에서 만든다.
    listTasks()
      .then(setTasks)
      .catch(() => {})
  }, [])

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
          />
        ))}
      </div>
    </main>
  )
}
