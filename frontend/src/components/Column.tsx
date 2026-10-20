import type { Task } from '../types'
import { TaskCard } from './TaskCard'

export function Column({ label, tasks }: { label: string; tasks: Task[] }) {
  return (
    <section className="column">
      <h2>{label}</h2>
      {tasks.map((task) => (
        <TaskCard key={task.id} task={task} />
      ))}
    </section>
  )
}
