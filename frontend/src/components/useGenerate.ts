import { useCallback, useEffect, useRef, useState } from 'react'
import { ApiError, createTask, generateTasks } from '../api'
import { titleError, type GeneratedTask, type Task } from '../types'

const GENERATE_UNAVAILABLE = '지금은 AI 제안을 쓸 수 없습니다. - 직접 입력해 주세요.'
const GENERATE_FAILED = '제안을 못 받았습니다. 다시 눌러 보세요.'
const SAVE_FAILED = '요청을 처리하지 못했습니다.'

function errorMessage(err: unknown): string {
  if (err instanceof ApiError) {
    if (err.status === 503) return GENERATE_UNAVAILABLE
    if (err.status === 502) return GENERATE_FAILED
    return err.message
  }
  return SAVE_FAILED
}

// 미리 보기 한 줄. 저장에 실패하면 error 를 달고 남는다.
export interface PreviewItem {
  key: number
  task: GeneratedTask
  error?: string
}

// AI 로 할 일 만들기의 상태. 제안을 받는 일과 [모두 등록] 만 한다.
// 입력칸과 기존 등록 · AI 제안에는 손대지 않고, 저장은 [모두 등록] 을 눌러야 한다.
export function useGenerate() {
  const [pending, setPending] = useState(false)
  const [error, setError] = useState<string | null>(null)
  const [items, setItems] = useState<PreviewItem[] | null>(null)
  const [saving, setSaving] = useState(false)
  const [summary, setSummary] = useState<string | null>(null)
  // 요청 번호. 기다리는 중에 등록 · 취소로 상황이 바뀌면 늦게 온 응답을 버린다.
  const seq = useRef(0)

  useEffect(
    () => () => {
      seq.current += 1
    },
    [],
  )

  const run = useCallback(async (topic: string) => {
    const invalid = titleError(topic)
    if (invalid) {
      setError(invalid)
      return
    }
    seq.current += 1
    const id = seq.current
    setPending(true)
    setError(null)
    try {
      const tasks = await generateTasks(topic)
      if (id !== seq.current) return
      setItems(tasks.map((task, key) => ({ key, task })))
      setSummary(null)
    } catch (err) {
      if (id !== seq.current) return
      setError(errorMessage(err))
    } finally {
      if (id === seq.current) setPending(false)
    }
  }, [])

  // 기존 [등록] 이 성공했을 때: 기다리는 중인 요청의 응답만 버린다. 이미 보이는 미리 보기는 둔다.
  const discardPending = useCallback(() => {
    seq.current += 1
    setPending(false)
    setError(null)
  }, [])

  const cancel = useCallback(() => {
    seq.current += 1
    setPending(false)
    setError(null)
    setItems(null)
    setSummary(null)
  }, [])

  // 한 개씩 저장한다. 하나가 실패해도 나머지를 멈추지 않고, 실패한 것만 남긴다.
  // 보드 반영(onCreated)은 모두 저장한 뒤에 부른다. 그래야 마지막 다시 불러오기에 전부 담긴다.
  const saveAll = useCallback(
    async (onCreated: (task: Task) => void) => {
      if (!items) return
      setSaving(true)
      setSummary(null)
      const created: Task[] = []
      const failed: PreviewItem[] = []
      for (const item of items) {
        try {
          created.push(
            await createTask({
              title: item.task.title,
              description: '',
              priority: item.task.priority,
              dueDate: item.task.due_date ?? '',
            }),
          )
        } catch (err) {
          failed.push({ ...item, error: errorMessage(err) })
        }
      }
      created.forEach(onCreated)
      setItems(failed.length ? failed : null)
      setSummary(
        failed.length
          ? `${items.length}개 중 ${failed.length}개를 등록하지 못했습니다.`
          : null,
      )
      setSaving(false)
    },
    [items],
  )

  return { pending, error, items, saving, summary, run, discardPending, cancel, saveAll }
}

export type GenerateState = ReturnType<typeof useGenerate>
