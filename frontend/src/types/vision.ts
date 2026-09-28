export type ResultStatus =
  | 'NORMAL'
  | 'DEFECT'
  | 'NOT_EVALUATED'

export interface Detection {
  classId: number
  className: string
  confidence: number
  bbox: [number, number, number, number]
  center: [number, number]
  areaPx: number
}

export interface InspectionMetrics {
  modelType: string
  detectedInstanceCount: number
  inferenceTimeMs: number
  detectedCounts: Record<string, number>
  detections: Detection[]
  assemblyReasons: string[]
  fasteningEvaluated: boolean
  measuredThreadCm?: number
  threadThresholdCm?: number
  scaleCmPerPx?: number
}

export interface LatestInspectionResponse {
  inspectionTime: string
  overallResult: ResultStatus
  assemblySequenceResult: ResultStatus
  fasteningQualityResult: ResultStatus
  missingComponentResult: ResultStatus
  alignmentResult: ResultStatus
  fasteningResult: ResultStatus
  metrics: InspectionMetrics
}

export interface InspectionHistoryItem {
  id: number
  inspectionTime: string
  overallResult: ResultStatus
  assemblySequenceResult: ResultStatus
  fasteningQualityResult: ResultStatus
  missingComponentResult: ResultStatus
  alignmentResult: ResultStatus
  fasteningResult: ResultStatus
  detectedInstanceCount: number | null
  inferenceTimeMs: number | null
  modelName: string | null
  metrics: Partial<InspectionMetrics> &
    Record<string, unknown>
  defectImageUrl: string | null
  createdAt: string
}

export interface InspectionHistoryPage {
  content: InspectionHistoryItem[]
  page: number
  size: number
  totalElements: number
  totalPages: number
}

export interface SystemStatus {
  cameraConnected: boolean
  visionWorkerRunning: boolean
  persistenceWorkerRunning: boolean
  pendingPersistenceEvents: number
  modelLoaded: boolean
  modelType: string | null
  visionDevice: string | null
  databaseConnected: boolean
  eventState: string
  lastCapturedAt: string | null
  lastProcessedAt: string | null
  lastInferenceTimeMs: number | null
  lastDetectionCount: number | null
  cameraError: string | null
  visionError: string | null
  modelError: string | null
  databaseError: string | null
}