export type Status = 'TODO' | 'IN_PROGRESS' | 'DONE'

export interface Task {
  id: number
  title: string
  description: string
  status: Status
  created_at: string
  updated_at: string
}

export const COLUMNS: { status: Status; label: string }[] = [
  { status: 'TODO', label: '할 일' },
  { status: 'IN_PROGRESS', label: '진행 중' },
  { status: 'DONE', label: '완료' },
]

export const TITLE_MAX_LENGTH = 100

// API 와 같은 규칙으로 미리 안내만 한다. 최종 검증은 API 가 한다. (D-004)
export function titleError(title: string): string | null {
  if (!title.trim()) return '제목을 입력하세요.'
  if (title.length > TITLE_MAX_LENGTH)
    return `제목은 ${TITLE_MAX_LENGTH}자 이하여야 합니다.`
  return null
}
