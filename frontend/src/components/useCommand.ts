import { useCallback, useEffect, useRef, useState } from 'react'
import { ApiError, changeStatus, commandTasks, createTask, updateTask } from '../api'
import { commandError, type CommandAction, type Task } from '../types'

const COMMAND_UNAVAILABLE = '지금은 시킬 수 없습니다'
const COMMAND_FAILED = '알아듣지 못했습니다'
const APPLY_FAILED = '요청을 처리하지 못했습니다.'
export const TASK_MISSING = '카드를 찾을 수 없습니다.'

function errorMessage(err: unknown): string {
  if (err instanceof ApiError) {
    if (err.status === 503) return COMMAND_UNAVAILABLE
    if (err.status === 502) return COMMAND_FAILED
    return err.message
  }
  return APPLY_FAILED
}

// 확인 카드 한 줄. 적용에 실패하면 error 를 달고 남는다.
export interface CommandItem {
  key: number
  action: CommandAction
  error?: string
}

// 한 문장으로 시키기의 상태. [시키기] 는 변경안만 받고, 저장은 [적용] 을 눌러야 한다.
// [적용] 은 Claude 를 부르지 않고 기존 API 를 카드마다 한 번씩 부른다.
export function useCommand() {
  const [pending, setPending] = useState(false)
  const [error, setError] = useState<string | null>(null)
  const [ask, setAsk] = useState<string | null>(null)
  const [items, setItems] = useState<CommandItem[] | null>(null)
  const [applying, setApplying] = useState(false)
  const [summary, setSummary] = useState<string | null>(null)
  // 요청 번호. 취소하거나 다시 눌렀을 때 늦게 온 응답을 버린다.
  const seq = useRef(0)

  useEffect(
    () => () => {
      seq.current += 1
    },
    [],
  )

  const reset = useCallback(() => {
    setError(null)
    setAsk(null)
    setItems(null)
    setSummary(null)
  }, [])

  // 성공하면 true. 입력란을 비울지는 부르는 쪽이 정한다.
  const run = useCallback(
    async (text: string): Promise<boolean> => {
      const invalid = commandError(text)
      if (invalid) {
        reset()
        setError(invalid)
        return false
      }
      seq.current += 1
      const id = seq.current
      setPending(true)
      reset()
      try {
        const result = await commandTasks(text)
        if (id !== seq.current) return false
        if (result.actions.length === 0) {
          setAsk(result.ask ?? COMMAND_FAILED)
        } else {
          setItems(result.actions.map((action, key) => ({ key, action })))
        }
        return true
      } catch (err) {
        if (id !== seq.current) return false
        setError(errorMessage(err))
        return false
      } finally {
        if (id === seq.current) setPending(false)
      }
    },
    [reset],
  )

  const cancel = useCallback(() => {
    seq.current += 1
    setPending(false)
    reset()
  }, [reset])

  // 한 줄씩 기존 API 로 적용한다. 하나가 실패해도 나머지를 멈추지 않고, 실패한 줄만 남긴다.
  // 끝나면 목록을 다시 받는다(onApplied). 모두 성공하면 true.
  const apply = useCallback(
    async (tasks: Task[], onApplied: () => void | Promise<void>): Promise<boolean> => {
      if (!items) return false
      setApplying(true)
      setSummary(null)
      const failed: CommandItem[] = []
      for (const item of items) {
        const { action } = item
        try {
          if (action.kind === 'add') {
            await createTask({
              title: action.title,
              description: '',
              priority: action.priority ?? 'NORMAL',
              dueDate: action.due_date ?? '',
            })
            continue
          }
          const task = tasks.find((t) => t.id === action.id)
          if (!task || action.id === null) throw new ApiError(TASK_MISSING, 404)
          if (action.kind === 'done') {
            await changeStatus(action.id, 'DONE')
          } else {
            // 수정 API 는 네 값을 함께 받는다. 마감일 말고는 지금 값 그대로 보낸다.
            await updateTask(action.id, {
              title: task.title,
              description: task.description,
              priority: task.priority,
              dueDate: action.due_date ?? '',
            })
          }
        } catch (err) {
          failed.push({ ...item, error: errorMessage(err) })
        }
      }
      await onApplied()
      setItems(failed.length ? failed : null)
      setSummary(
        failed.length
          ? `${items.length}개 중 ${failed.length}개를 적용하지 못했습니다.`
          : null,
      )
      setApplying(false)
      return failed.length === 0
    },
    [items],
  )

  return { pending, error, ask, items, applying, summary, run, cancel, apply }
}

export type CommandState = ReturnType<typeof useCommand>
