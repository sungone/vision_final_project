import type {
  InspectionApiError,
  InspectionResponse,
  InspectionResult,
} from '../types/inspection'

const API_BASE_URL =
  import.meta.env.VITE_API_BASE_URL ?? ''

const USE_MOCK_API =
  String(import.meta.env.VITE_USE_MOCK_API)
    .toLowerCase() === 'true'

type BackendCheckResult =
  | 'PASS'
  | 'FAIL'
  | 'SKIPPED'

type BackendInspectionResponse = {
  overallResult: 'PASS' | 'FAIL'
  componentCheck: {
    result: BackendCheckResult
  }
  orderCheck: {
    result: BackendCheckResult
  }
  fasteningCheck: {
    result: BackendCheckResult
  }
  images: {
    originalUrl: string
    processedUrl: string
  }
}

export async function inspectImage(
  image: File,
): Promise<InspectionResponse> {
  if (USE_MOCK_API) {
    return createMockInspection(image)
  }

  return requestRealInspection(image)
}

async function requestRealInspection(
  image: File,
): Promise<InspectionResponse> {
  const formData = new FormData()
  formData.append('image', image)

  const response = await fetch(
    `${API_BASE_URL}/api/inspections`,
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

  const result =
    (await response.json()) as BackendInspectionResponse

  const assemblySequenceResult: InspectionResult =
    result.componentCheck.result === 'PASS' &&
    result.orderCheck.result === 'PASS'
      ? 'NORMAL'
      : 'DEFECT'

  const fasteningQualityResult: InspectionResult =
    result.fasteningCheck.result === 'PASS'
      ? 'NORMAL'
      : 'DEFECT'

  return {
    resultImageUrl: result.images.processedUrl,
    assemblySequenceResult,
    fasteningQualityResult,
  }
}

async function createMockInspection(
  image: File,
): Promise<InspectionResponse> {
  await delay(900)

  const hash = createStableHash(
    `${image.name}:${image.size}:${image.lastModified}`,
  )

  const defect = determineMockDefect(image.name, hash)

  let assemblySequenceResult: InspectionResult =
    'NORMAL'

  let fasteningQualityResult: InspectionResult =
    'NORMAL'

  if (defect) {
    const defectType = hash % 3

    if (defectType === 0) {
      assemblySequenceResult = 'DEFECT'
    } else if (defectType === 1) {
      fasteningQualityResult = 'DEFECT'
    } else {
      assemblySequenceResult = 'DEFECT'
      fasteningQualityResult = 'DEFECT'
    }
  }

  const resultImageUrl =
    await createMockResultImage(
      image,
      assemblySequenceResult,
      fasteningQualityResult,
    )

  return {
    resultImageUrl,
    assemblySequenceResult,
    fasteningQualityResult,
  }
}

function determineMockDefect(
  fileName: string,
  hash: number,
) {
  const configuredMode = String(
    import.meta.env.VITE_MOCK_RESULT_MODE ??
      'mixed',
  ).toLowerCase()

  if (configuredMode === 'normal') {
    return false
  }

  if (configuredMode === 'defect') {
    return true
  }

  const normalizedName = fileName
    .normalize('NFC')
    .toLowerCase()
    .replace(/\.[^.]+$/, '')

  const normalPattern =
    /(^|[._\-\s])(ok|normal|pass)(?=[._\-\s]|$)/i

  const defectPattern =
    /(^|[._\-\s])(ng|defect|fail)(?=[._\-\s]|$)/i

  if (
    normalizedName.includes('정상') ||
    normalPattern.test(normalizedName)
  ) {
    return false
  }

  if (
    normalizedName.includes('불량') ||
    defectPattern.test(normalizedName)
  ) {
    return true
  }

  // 파일명이 특별히 지정되지 않으면 약 25%를 불량 처리합니다.
  return hash % 4 === 0
}

async function createMockResultImage(
  image: File,
  assemblyResult: InspectionResult,
  fasteningResult: InspectionResult,
) {
  try {
    const bitmap = await createImageBitmap(image)

    try {
      const maxDimension = 1400
      const scale = Math.min(
        1,
        maxDimension /
          Math.max(bitmap.width, bitmap.height),
      )

      const canvas =
        document.createElement('canvas')

      canvas.width = Math.max(
        1,
        Math.round(bitmap.width * scale),
      )

      canvas.height = Math.max(
        1,
        Math.round(bitmap.height * scale),
      )

      const context = canvas.getContext('2d')

      if (!context) {
        return readFileAsDataUrl(image)
      }

      context.drawImage(
        bitmap,
        0,
        0,
        canvas.width,
        canvas.height,
      )

      const finalResult =
        assemblyResult === 'NORMAL' &&
        fasteningResult === 'NORMAL'
          ? 'NORMAL'
          : 'DEFECT'

      drawStatusHeader(
        context,
        canvas.width,
        canvas.height,
        finalResult,
      )

      const mockBoxes = [
        {
          label: 'BOLT',
          x: 0.18,
          y: 0.27,
          width: 0.22,
          height: 0.46,
          defect: assemblyResult === 'DEFECT',
        },
        {
          label: 'WASHER',
          x: 0.40,
          y: 0.32,
          width: 0.20,
          height: 0.36,
          defect: assemblyResult === 'DEFECT',
        },
        {
          label: 'NUT',
          x: 0.61,
          y: 0.27,
          width: 0.21,
          height: 0.46,
          defect: fasteningResult === 'DEFECT',
        },
      ]

      mockBoxes.forEach((box) => {
        drawMockBox(
          context,
          canvas.width,
          canvas.height,
          box,
        )
      })

      return canvas.toDataURL(
        'image/jpeg',
        0.88,
      )
    } finally {
      bitmap.close()
    }
  } catch {
    return readFileAsDataUrl(image)
  }
}

function drawStatusHeader(
  context: CanvasRenderingContext2D,
  width: number,
  height: number,
  result: InspectionResult,
) {
  const normal = result === 'NORMAL'
  const headerHeight = Math.max(
    48,
    Math.round(height * 0.09),
  )

  context.fillStyle = normal
    ? 'rgba(22, 139, 91, 0.90)'
    : 'rgba(217, 75, 75, 0.90)'

  context.fillRect(
    0,
    0,
    width,
    headerHeight,
  )

  context.fillStyle = '#ffffff'
  context.font = `bold ${Math.max(
    17,
    Math.round(width * 0.023),
  )}px Arial, sans-serif`

  context.textBaseline = 'middle'

  context.fillText(
    `MOCK TEST ONLY · ${
      normal ? 'OK' : 'NG'
    }`,
    Math.max(16, width * 0.025),
    headerHeight / 2,
  )
}

function drawMockBox(
  context: CanvasRenderingContext2D,
  imageWidth: number,
  imageHeight: number,
  box: {
    label: string
    x: number
    y: number
    width: number
    height: number
    defect: boolean
  },
) {
  const x = imageWidth * box.x
  const y = imageHeight * box.y
  const width = imageWidth * box.width
  const height = imageHeight * box.height

  const color = box.defect
    ? '#ef4444'
    : '#22c55e'

  const fontSize = Math.max(
    14,
    Math.round(imageWidth * 0.018),
  )

  context.strokeStyle = color
  context.lineWidth = Math.max(
    3,
    Math.round(imageWidth * 0.004),
  )

  context.strokeRect(x, y, width, height)

  context.font =
    `bold ${fontSize}px Arial, sans-serif`

  const label = `${box.label} ${
    box.defect ? 'NG' : 'OK'
  }`

  const padding = 7
  const labelWidth =
    context.measureText(label).width +
    padding * 2

  const labelHeight = fontSize + padding * 2

  context.fillStyle = color
  context.fillRect(
    x,
    Math.max(0, y - labelHeight),
    labelWidth,
    labelHeight,
  )

  context.fillStyle = '#ffffff'
  context.textBaseline = 'middle'

  context.fillText(
    label,
    x + padding,
    Math.max(
      labelHeight / 2,
      y - labelHeight / 2,
    ),
  )
}

function readFileAsDataUrl(file: File) {
  return new Promise<string>(
    (resolve, reject) => {
      const reader = new FileReader()

      reader.onload = () => {
        if (typeof reader.result === 'string') {
          resolve(reader.result)
        } else {
          reject(
            new Error(
              '이미지 미리보기를 생성할 수 없습니다.',
            ),
          )
        }
      }

      reader.onerror = () => {
        reject(
          new Error(
            '이미지 파일을 읽을 수 없습니다.',
          ),
        )
      }

      reader.readAsDataURL(file)
    },
  )
}

function createStableHash(value: string) {
  let hash = 2166136261

  for (let index = 0; index < value.length; index += 1) {
    hash ^= value.charCodeAt(index)
    hash = Math.imul(hash, 16777619)
  }

  return hash >>> 0
}

function delay(milliseconds: number) {
  return new Promise<void>((resolve) => {
    window.setTimeout(resolve, milliseconds)
  })
}

export function resolveResultImageUrl(
  path: string,
) {
  if (
    /^(https?:\/\/|data:|blob:)/i.test(path)
  ) {
    return path
  }

  return `${API_BASE_URL}${path}`
}