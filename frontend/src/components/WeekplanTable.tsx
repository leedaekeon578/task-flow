import type { Task } from '../types'
import type { Weekplan } from './useWeekplan'

const WEEKDAYS = ['일', '월', '화', '수', '목', '금', '토']

// "YYYY-MM-DD" 를 시간대 이동 없이 읽어 "10/28 (수)" 로 보인다. 읽을 수 없으면 받은 글자 그대로 둔다.
function dateLabel(date: string): string {
  const m = /^(\d{4})-(\d{2})-(\d{2})$/.exec(date)
  if (!m) return date
  const [y, mo, d] = [Number(m[1]), Number(m[2]), Number(m[3])]
  const weekday = WEEKDAYS[new Date(y, mo - 1, d).getDay()]
  return `${mo}/${d} (${weekday})`
}

// 이번 주 계획 표. 제목은 id 로 찾고, 목록에 없는 id 는 건너뛴다. 저장하지 않는다.
export function WeekplanTable({
  data,
  tasks,
  onClose,
}: {
  data: Weekplan
  tasks: Task[]
  onClose: () => void
}) {
  const titleOf = (id: number) => tasks.find((t) => t.id === id)?.title

  return (
    <section className="weekplan-card" aria-label="이번 주 계획">
      <table className="weekplan-table">
        <tbody>
          {data.days.map((day) => {
            const titles = day.ids.flatMap((id) => {
              const title = titleOf(id)
              return title === undefined ? [] : [{ id, title }]
            })
            return (
              <tr key={day.date}>
                <th scope="row">{dateLabel(day.date)}</th>
                <td>
                  {titles.length > 0 && (
                    <ul>
                      {titles.map((t) => (
                        <li key={t.id}>{t.title}</li>
                      ))}
                    </ul>
                  )}
                  <p className="weekplan-note">{day.note}</p>
                </td>
              </tr>
            )
          })}
        </tbody>
      </table>
      <div className="weekplan-actions">
        <button type="button" onClick={onClose}>
          닫기
        </button>
      </div>
    </section>
  )
}
