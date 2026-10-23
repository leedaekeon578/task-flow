import type { AuthUser, Status, Task } from './types'

export class ApiError extends Error {
  status?: number

  constructor(message: string, status?: number) {
    super(message)
    this.status = status
  }
}

export const CONNECTION_ERROR = '서버에 연결하지 못했습니다.'
const CHECK_INPUT = '입력한 내용을 확인하세요.'

// FastAPI 오류 본문(detail)에서 사용자에게 보일 문장을 꺼낸다.
// 검증 오류(배열)는 한글 문구만 그대로 보이고, 영어 문구는 일반 안내로 바꾼다.
function messageFrom(body: unknown, fallback: string): string {
  const detail = (body as { detail?: unknown } | null)?.detail
  if (typeof detail === 'string') return detail
  if (Array.isArray(detail)) {
    const msg = detail[0]?.msg
    if (typeof msg === 'string' && /[가-힣]/.test(msg)) {
      return msg.replace(/^Value error, /, '')
    }
    return CHECK_INPUT
  }
  return fallback
}

async function request<T>(path: string, init?: RequestInit): Promise<T> {
  let res: Response
  try {
    res = await fetch(path, init)
  } catch {
    throw new ApiError(CONNECTION_ERROR)
  }
  const body = await res.json().catch(() => null)
  if (!res.ok) {
    // 개발 서버 프록시는 API 가 꺼져 있으면 본문 없는 5xx 로 답한다. 연결 실패로 본다.
    if (body === null && res.status >= 500) throw new ApiError(CONNECTION_ERROR)
    throw new ApiError(
      messageFrom(body, '요청을 처리하지 못했습니다.'),
      res.status,
    )
  }
  return body as T
}

// 로그인 상태는 httponly 쿠키가 들고 있다. 같은 출처(/api 프록시)라 fetch 가 쿠키를 알아서 보낸다.
function sendCredentials(
  path: string,
  email: string,
  password: string,
): Promise<AuthUser> {
  return request<AuthUser>(path, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ email, password }),
  })
}

export function signup(email: string, password: string): Promise<AuthUser> {
  return sendCredentials('/api/auth/signup', email, password)
}

export function login(email: string, password: string): Promise<AuthUser> {
  return sendCredentials('/api/auth/login', email, password)
}

export function logout(): Promise<null> {
  return request<null>('/api/auth/logout', { method: 'POST' })
}

export function fetchMe(): Promise<AuthUser> {
  return request<AuthUser>('/api/auth/me')
}

export function listTasks(): Promise<Task[]> {
  return request<Task[]>('/api/tasks')
}

export function createTask(title: string, description: string): Promise<Task> {
  return request<Task>('/api/tasks', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ title, description }),
  })
}

export function changeStatus(id: number, status: Status): Promise<Task> {
  return request<Task>(`/api/tasks/${id}/status`, {
    method: 'PATCH',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ status }),
  })
}

export function updateTask(
  id: number,
  title: string,
  description: string,
): Promise<Task> {
  return request<Task>(`/api/tasks/${id}`, {
    method: 'PATCH',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ title, description }),
  })
}

export function deleteTask(id: number): Promise<null> {
  return request<null>(`/api/tasks/${id}`, { method: 'DELETE' })
}
