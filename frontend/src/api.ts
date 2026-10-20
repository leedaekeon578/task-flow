import type { Task } from './types'

export class ApiError extends Error {}

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
    throw new ApiError(messageFrom(body, '요청을 처리하지 못했습니다.'))
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
