import type { Status, Task } from '../types'
import { TaskCard } from './TaskCard'

interface Props {
  label: string
  tasks: Task[]
  onChangeStatus: (task: Task, status: Status) => Promise<void>
}

export function Column({ label, tasks, onChangeStatus }: Props) {
  return (
    <section className="column">
      <h2>{label}</h2>
      {tasks.map((task) => (
        <TaskCard key={task.id} task={task} onChangeStatus={onChangeStatus} />
      ))}
    </section>
  )
}
