import type { Draft, Status, Task } from '../types'
import { TaskCard } from './TaskCard'

interface Props {
  label: string
  tasks: Task[]
  drafts: Record<number, Draft>
  onChangeStatus: (task: Task, status: Status) => Promise<void>
  onStartEdit: (task: Task) => void
  onEditChange: (task: Task, draft: Draft) => void
  onCancelEdit: (task: Task) => void
  onSave: (task: Task, draft: Draft) => Promise<void>
  onDelete: (task: Task) => Promise<void>
}

export function Column({ label, tasks, drafts, ...handlers }: Props) {
  return (
    <section className="column">
      <h2>{label}</h2>
      {tasks.map((task) => (
        <TaskCard key={task.id} task={task} draft={drafts[task.id]} {...handlers} />
      ))}
    </section>
  )
}
