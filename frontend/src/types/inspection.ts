export type InspectionResult = 'NORMAL' | 'DEFECT'

export type InspectionResponse = {
  resultImageUrl: string
  assemblySequenceResult: InspectionResult
  fasteningQualityResult: InspectionResult
}

export type InspectionApiError = {
  code?: string
  message?: string
}