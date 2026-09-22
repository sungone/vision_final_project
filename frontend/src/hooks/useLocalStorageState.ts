import {
  useEffect,
  useState,
} from 'react'

export function useLocalStorageState<T>(
  key: string,
  initialValue: T,
) {
  const [value, setValue] = useState<T>(() => {
    try {
      const savedValue =
        window.localStorage.getItem(key)

      return savedValue === null
        ? initialValue
        : (JSON.parse(savedValue) as T)
    } catch {
      return initialValue
    }
  })

  useEffect(() => {
    try {
      window.localStorage.setItem(
        key,
        JSON.stringify(value),
      )
    } catch {
      // 저장 공간 사용 불가 시 현재 화면 상태만 유지
    }
  }, [key, value])

  return [value, setValue] as const
}