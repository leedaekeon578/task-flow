import type { Task } from '../types'
import { useWeekplan } from './useWeekplan'
import { WeekplanTable } from './WeekplanTable'
import './weekplan.css'

const WEEKPLAN_PENDING = '나누는 중…'
const WEEKPLAN_EMPTY = '이번 주는 비어 있어요'

// [오늘 브리핑] 아래에 놓는 [이번 주 계획] 버튼과 결과 표.
export function Weekplan({ tasks }: { tasks: Task[] }) {
  const { pending, error, data, run, close } = useWeekplan()
  const empty = data !== null && data.days.length === 0

  return (
    <div className="weekplan">
      <button type="button" disabled={pending} onClick={run}>
        {pending ? WEEKPLAN_PENDING : '이번 주 계획'}
      </button>
      {error && (
        <p className="form-error" role="alert">
          {error}
        </p>
      )}
      {empty && (
        <p className="weekplan-empty" role="status">
          {WEEKPLAN_EMPTY}
        </p>
      )}
      {data && !empty && <WeekplanTable data={data} tasks={tasks} onClose={close} />}
    </div>
  )
}
