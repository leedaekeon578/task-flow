export type Status = 'TODO' | 'IN_PROGRESS' | 'DONE'

export type Priority = 'LOW' | 'NORMAL' | 'HIGH'

export const PRIORITIES: { value: Priority; label: string }[] = [
  { value: 'LOW', label: '낮음' },
  { value: 'NORMAL', label: '보통' },
  { value: 'HIGH', label: '높음' },
]

export const DEFAULT_PRIORITY: Priority = 'NORMAL'

export function priorityLabel(priority: Priority): string {
  return PRIORITIES.find((p) => p.value === priority)?.label ?? priority
}

export interface Task {
  id: number
  title: string
  description: string
  status: Status
  priority: Priority
  due_date: string | null // YYYY-MM-DD
  overdue: boolean // 서버가 계산해서 준다. 화면은 다시 계산하지 않는다.
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

// POST /api/tasks/suggest 의 응답. 제안만이고 저장하지 않는다. (D-020)
export interface Suggestion {
  priority: Priority
  due_date: string | null // YYYY-MM-DD
  reason: string
}

export interface AuthUser {
  id: number
  email: string
}

export const PASSWORD_MIN_LENGTH = 8

// API 와 같은 규칙으로 미리 안내만 한다. 최종 검증은 API 가 한다. (D-004)
export function credentialsError(
  email: string,
  password: string,
  signup: boolean,
): string | null {
  if (!email.trim()) return '이메일을 입력하세요.'
  if (!password) return '비밀번호를 입력하세요.'
  if (signup && password.length < PASSWORD_MIN_LENGTH)
    return `비밀번호는 ${PASSWORD_MIN_LENGTH}자 이상이어야 합니다.`
  return null
}

// 등록 · 수정 입력값. dueDate 가 빈 문자열이면 마감일 없음(API 에는 null 로 보낸다).
export interface Draft {
  title: string
  description: string
  priority: Priority
  dueDate: string
}
