import type {
  InspectionApiError,
  InspectionResponse,
} from '../types/inspection'
import type {
  InspectionHistoryItem,
  InspectionHistoryPage,
  LatestInspectionResponse,
  SystemStatus,
} from '../types/vision'

const API_BASE_URL =
  import.meta.env.VITE_API_BASE_URL ?? ''

export function getVisionStreamUrl(
  cacheKey?: number,
) {
  const url =
    `${API_BASE_URL}/api/v1/stream`

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

export async function getInspectionDetail(
  inspectionId: number | string,
  signal?: AbortSignal,
): Promise<InspectionHistoryItem> {
  const encodedId = encodeURIComponent(
    String(inspectionId),
  )

  const response = await fetch(
    `${API_BASE_URL}/api/v1/inspections/${encodedId}`,
    {
      method: 'GET',
      signal,
    },
  )

  if (response.status === 404) {
    throw new Error(
      '요청한 검사 기록을 찾을 수 없습니다.',
    )
  }

  if (!response.ok) {
    throw new Error(
      `검사 상세 조회 실패: HTTP ${response.status}`,
    )
  }

  return response.json() as Promise<InspectionHistoryItem>
}

export type DeleteInspectionResponse = {
  deleted: boolean
  inspectionId: number
  imageDeleted: boolean
}

export async function deleteInspection(
  inspectionId: number | string,
): Promise<DeleteInspectionResponse> {
  const encodedId = encodeURIComponent(
    String(inspectionId),
  )

  const response = await fetch(
    `${API_BASE_URL}/api/v1/inspections/${encodedId}`,
    {
      method: 'DELETE',
    },
  )

  if (response.status === 404) {
    throw new Error(
      '삭제할 검사 기록을 찾을 수 없습니다.',
    )
  }

  if (!response.ok) {
    throw new Error(
      `검사 기록 삭제 실패: HTTP ${response.status}`,
    )
  }

  return response.json() as Promise<DeleteInspectionResponse>
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

export function resolveResultImageUrl(
  path: string,
) {
  if (/^https?:\/\//i.test(path)) {
    return path
  }

  return `${API_BASE_URL}${path}`
}