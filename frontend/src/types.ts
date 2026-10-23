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

// 카드를 수정하는 동안의 입력값
export interface Draft {
  title: string
  description: string
}
