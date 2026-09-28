export type InspectionResult =
  | 'NORMAL'
  | 'DEFECT'
  | 'NOT_EVALUATED'

export type FinalInspectionResult =
  | 'NORMAL'
  | 'DEFECT'

export type InspectionResponse = {
  inspectionId: number
  inspectionTime: string
  overallResult: FinalInspectionResult
  resultImageUrl: string
  assemblySequenceResult: InspectionResult
  fasteningQualityResult: InspectionResult
  missingComponentResult: InspectionResult
  alignmentResult: InspectionResult
  fasteningResult: InspectionResult
  metrics: Record<string, unknown>
}

export type InspectionApiError = {
  error?: string
  code?: string
  message?: string
}
