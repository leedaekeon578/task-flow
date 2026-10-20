import type { Task } from '../types'

export function TaskCard({ task }: { task: Task }) {
  return (
    <article className="card">
      <h3>{task.title}</h3>
      {task.description && <p className="card-desc">{task.description}</p>}
    </article>
  )
}
