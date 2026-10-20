import { useCallback, useEffect, useState } from 'react'
import { ApiError, CONNECTION_ERROR, changeStatus, deleteTask, listTasks, updateTask } from '../api'
import { COLUMNS, type Draft, type Status, type Task } from '../types'
import { Column } from './Column'
import { TaskForm } from './TaskForm'

type LoadState = 'loading' | 'ready' | 'error'

function without<T>(record: Record<number, T>, id: number): Record<number, T> {
  const { [id]: _removed, ...rest } = record
  return rest
}

export function Board() {
  const [tasks, setTasks] = useState<Task[]>([])
  // 수정 중인 카드의 입력값. 카드가 다른 열로 옮겨져도 남도록 보드가 들고 있다.
  const [drafts, setDrafts] = useState<Record<number, Draft>>({})

  const [loadState, setLoadState] = useState<LoadState>('loading')
  const [loadError, setLoadError] = useState<string | null>(null)

  // 불러오기에 실패하면 처음이면 실패 화면으로, 이미 보드가 있으면 이전 카드를 둔 채 안내만 보인다.
  const reload = useCallback(async () => {
    try {
      setTasks(await listTasks())
      setLoadState('ready')
      setLoadError(null)
    } catch (err) {
      setLoadError(err instanceof ApiError ? err.message : CONNECTION_ERROR)
      setLoadState((prev) => (prev === 'ready' ? 'ready' : 'error'))
    }
  }, [])

  useEffect(() => {
    // 첫 불러오기. 이 시점의 상태는 항상 '불러오는 중'이라 실패하면 실패 화면이 된다.
    listTasks()
      .then((loaded) => {
        setTasks(loaded)
        setLoadState('ready')
      })
      .catch((err) => {
        setLoadError(err instanceof ApiError ? err.message : CONNECTION_ERROR)
        setLoadState('error')
      })
  }, [])

  function retryInitialLoad() {
    setLoadState('loading')
    setLoadError(null)
    reload()
  }

  function replace(updated: Task) {
    setTasks((prev) => prev.map((t) => (t.id === updated.id ? updated : t)))
  }

  // 없는 카드(404)면 보드를 다시 불러와 저장 내용에 맞춘다. (S-07)
  async function reloadIfMissing(err: unknown, id: number) {
    if (err instanceof ApiError && err.status === 404) {
      setDrafts((prev) => without(prev, id))
      await reload()
    }
  }

  // 저장이 성공한 뒤에만 화면을 바꾼다. 열 안 순서는 id 순서 그대로다. (D-005)
  async function handleChangeStatus(task: Task, status: Status) {
    try {
      replace(await changeStatus(task.id, status))
    } catch (err) {
      await reloadIfMissing(err, task.id)
      throw err
    }
  }

  async function handleSave(task: Task, draft: Draft) {
    try {
      replace(await updateTask(task.id, draft.title, draft.description))
      setDrafts((prev) => without(prev, task.id))
    } catch (err) {
      await reloadIfMissing(err, task.id)
      throw err
    }
  }

  async function handleDelete(task: Task) {
    try {
      await deleteTask(task.id)
      setTasks((prev) => prev.filter((t) => t.id !== task.id))
      setDrafts((prev) => without(prev, task.id))
    } catch (err) {
      // 이미 지워진 카드면 보드만 다시 불러오고 오류는 보이지 않는다.
      if (err instanceof ApiError && err.status === 404) {
        await reloadIfMissing(err, task.id)
        return
      }
      throw err
    }
  }

  const columns = (
    <div className="columns">
      {COLUMNS.map(({ status, label }) => (
        <Column
          key={status}
          label={label}
          tasks={tasks.filter((t) => t.status === status)}
          drafts={drafts}
          onChangeStatus={handleChangeStatus}
          onStartEdit={(t) =>
            setDrafts((prev) => ({
              ...prev,
              [t.id]: { title: t.title, description: t.description },
            }))
          }
          onEditChange={(t, d) => setDrafts((prev) => ({ ...prev, [t.id]: d }))}
          onCancelEdit={(t) => setDrafts((prev) => without(prev, t.id))}
          onSave={handleSave}
          onDelete={handleDelete}
        />
      ))}
    </div>
  )

  return (
    <main>
      <h1>Task Flow</h1>
      <TaskForm
        onCreated={(task) => {
          // 보드가 아직 없으면(불러오는 중 · 처음 불러오기 실패) 서버 내용을 다시 불러온다.
          if (loadState === 'ready') setTasks((prev) => [...prev, task])
          else reload()
        }}
      />
      {loadState === 'loading' && <p className="notice">불러오는 중…</p>}
      {loadState === 'error' && (
        <div className="notice error" role="alert">
          <p>{loadError}</p>
          <button type="button" onClick={retryInitialLoad}>
            다시 불러오기
          </button>
        </div>
      )}
      {loadState === 'ready' && (
        <>
          {loadError && (
            <div className="notice error" role="alert">
              <p>{loadError}</p>
              <button type="button" onClick={reload}>
                다시 불러오기
              </button>
            </div>
          )}
          {tasks.length === 0 && (
            <p className="notice">카드가 없습니다. 위에서 새 Task를 등록하세요.</p>
          )}
          {columns}
        </>
      )}
    </main>
  )
}
