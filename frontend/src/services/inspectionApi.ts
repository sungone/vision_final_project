import type {
  InspectionApiError,
  InspectionResponse,
} from '../types/inspection'

const API_BASE_URL = import.meta.env.VITE_API_BASE_URL ?? ''

export async function inspectImage(
  image: File,
): Promise<InspectionResponse> {
  const formData = new FormData()
  formData.append('image', image)

  const response = await fetch(
    `${API_BASE_URL}/api/v1/inspections`,
    {
      method: 'POST',
      body: formData,
    },
  )

  if (!response.ok) {
    let error: InspectionApiError = {}

    try {
      error = await response.json()
    } catch {
      // JSON 형식이 아닌 오류 응답
    }

    throw new Error(
      error.message ??
        `검사 요청에 실패했습니다. HTTP ${response.status}`,
    )
  }

  return response.json() as Promise<InspectionResponse>
}

export function resolveResultImageUrl(path: string) {
  if (/^https?:\/\//i.test(path)) {
    return path
  }

  return `${API_BASE_URL}${path}`
}