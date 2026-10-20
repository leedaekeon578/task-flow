import type { Status, Task } from './types'

export class ApiError extends Error {
  status?: number

  constructor(message: string, status?: number) {
    super(message)
    this.status = status
  }
}

// FastAPI 오류 본문(detail)에서 사용자에게 보일 문장을 꺼낸다.
function messageFrom(body: unknown, fallback: string): string {
  const detail = (body as { detail?: unknown } | null)?.detail
  if (typeof detail === 'string') return detail
  if (Array.isArray(detail) && typeof detail[0]?.msg === 'string') {
    return detail[0].msg.replace(/^Value error, /, '')
  }
  return fallback
}

async function request<T>(path: string, init?: RequestInit): Promise<T> {
  let res: Response
  try {
    res = await fetch(path, init)
  } catch {
    throw new ApiError('요청을 보내지 못했습니다.')
  }
  const body = await res.json().catch(() => null)
  if (!res.ok) {
    throw new ApiError(
      messageFrom(body, '요청을 처리하지 못했습니다.'),
      res.status,
    )
  }
  return body as T
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
