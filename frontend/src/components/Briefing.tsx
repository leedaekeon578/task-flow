import type { Task } from '../types'
import './briefing.css'
import { BriefingCard } from './BriefingCard'
import { useBriefing } from './useBriefing'

const BRIEFING_PENDING = '만드는 중…'
const BRIEFING_EMPTY = '오늘은 비어 있어요'

// 보드 바로 위 · 등록 폼 아래에 놓는 [오늘 브리핑] 버튼과 결과 카드.
export function Briefing({ tasks }: { tasks: Task[] }) {
  const { pending, error, data, run, close } = useBriefing()
  const empty = data !== null && data.top3.length === 0 && data.later.length === 0

  return (
    <div className="briefing">
      <button type="button" disabled={pending} onClick={run}>
        {pending ? BRIEFING_PENDING : '오늘 브리핑'}
      </button>
      {error && (
        <p className="form-error" role="alert">
          {error}
        </p>
      )}
      {empty && (
        <p className="briefing-empty" role="status">
          {BRIEFING_EMPTY}
        </p>
      )}
      {data && !empty && <BriefingCard data={data} tasks={tasks} onClose={close} />}
    </div>
  )
}
