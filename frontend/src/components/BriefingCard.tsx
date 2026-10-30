import type { Task } from '../types'
import type { Briefing } from './useBriefing'

const NUMBERS = ['①', '②', '③']

// 오늘 브리핑 카드. 제목은 id 로 찾고, 목록에 없는 id 는 건너뛴다.
export function BriefingCard({
  data,
  tasks,
  onClose,
}: {
  data: Briefing
  tasks: Task[]
  onClose: () => void
}) {
  const titleOf = (id: number) => tasks.find((t) => t.id === id)?.title
  const tops = data.top3.flatMap(({ id, reason }) => {
    const title = titleOf(id)
    return title === undefined ? [] : [{ id, title, reason }]
  })
  const laters = data.later.flatMap((id) => {
    const title = titleOf(id)
    return title === undefined ? [] : [{ id, title }]
  })

  return (
    <section className="briefing-card" aria-label="오늘 브리핑">
      <h2>먼저 할 일</h2>
      <ol>
        {tops.map((t, i) => (
          <li key={t.id}>
            <span className="briefing-number">{NUMBERS[i]}</span>
            <span>
              {t.title} — {t.reason}
            </span>
          </li>
        ))}
      </ol>
      {laters.length > 0 && (
        <>
          <h2>미뤄도 되는 일</h2>
          <ul>
            {laters.map((t) => (
              <li key={t.id}>{t.title}</li>
            ))}
          </ul>
        </>
      )}
      <p className="briefing-cheer">{data.cheer}</p>
      <div className="briefing-actions">
        <button type="button" onClick={onClose}>
          닫기
        </button>
      </div>
    </section>
  )
}
