import type {
  InspectionApiError,
  InspectionResponse,
} from '../types/inspection'
import type {
  InspectionHistoryPage,
  LatestInspectionResponse,
  SystemStatus,
} from '../types/vision'

const API_BASE_URL =
  import.meta.env.VITE_API_BASE_URL ?? ''

export function getVisionStreamUrl(cacheKey?: number) {
  const url = `${API_BASE_URL}/api/v1/stream`

  return cacheKey == null
    ? url
    : `${url}?v=${cacheKey}`
}

export async function getLatestInspection(
  signal?: AbortSignal,
): Promise<LatestInspectionResponse | null> {
  const response = await fetch(
    `${API_BASE_URL}/api/v1/inspection/latest`,
    {
      method: 'GET',
      signal,
    },
  )

  if (response.status === 204) {
    return null
  }

  if (!response.ok) {
    throw new Error(
      `실시간 검사 결과 조회 실패: HTTP ${response.status}`,
    )
  }

  return response.json() as Promise<LatestInspectionResponse>
}

export async function getInspectionHistory(
  page = 0,
  size = 100,
  signal?: AbortSignal,
): Promise<InspectionHistoryPage> {
  const query = new URLSearchParams({
    page: String(page),
    size: String(size),
  })

  const response = await fetch(
    `${API_BASE_URL}/api/v1/inspections?${query.toString()}`,
    {
      method: 'GET',
      signal,
    },
  )

  if (!response.ok) {
    throw new Error(
      `검사 이력 조회 실패: HTTP ${response.status}`,
    )
  }

  return response.json() as Promise<InspectionHistoryPage>
}

export async function getSystemStatus(
  signal?: AbortSignal,
): Promise<SystemStatus> {
  const response = await fetch(
    `${API_BASE_URL}/api/v1/system/status`,
    {
      method: 'GET',
      signal,
    },
  )

  if (!response.ok) {
    throw new Error(
      `시스템 상태 조회 실패: HTTP ${response.status}`,
    )
  }

  return response.json() as Promise<SystemStatus>
}

// 백엔드 POST 엔드포인트가 구현될 때까지
// 이미지 검사 화면에서는 호출하지 않습니다.
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