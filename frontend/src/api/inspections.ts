/** Backend-only browser adapter. Configure baseUrl to the Spring Boot origin. */
export type Result = 'PASS' | 'FAIL';
export type CheckResult = Result | 'SKIPPED';
export interface RuleSettings {
  confidenceThreshold: number;
  fasteningGapThreshold: number;
  axisDirection: 'X_POSITIVE' | 'X_NEGATIVE' | 'Y_POSITIVE' | 'Y_NEGATIVE';
  expectedOrder: ('bolt' | 'washer' | 'nut')[];
  alignmentTolerance: number;
  ruleVersion: string;
}
export interface Metadata {
  equipmentId?: string | null;
  productCode?: string | null;
  lotNumber?: string | null;
  operatorId?: string | null;
}
export interface Detection {
  className: string;
  confidence: number;
  bbox: { x1: number; y1: number; x2: number; y2: number };
  segmentation: [number, number][];
}
export interface Inspection {
  inspectionId: string;
  inspectionTime: string;
  overallResult: Result;
  componentCheck: { result: CheckResult; boltDetected: boolean; nutDetected: boolean; washerDetected: boolean; detail: string };
  orderCheck: { result: CheckResult; actualOrder: string[]; expectedOrder: string[]; axisDirection: string; detail: string };
  fasteningCheck: { result: CheckResult; gap: number | null; threshold: number; unit: 'px'; lateralOffset: number | null; alignmentTolerance: number; detail: string };
  measurements: { boltConfidence: number | null; nutConfidence: number | null; washerConfidence: number | null };
  defectCodes: string[];
  images: { originalUrl: string; processedUrl: string };
  modelVersion: string;
  ruleVersion: string;
  ruleSnapshot: RuleSettings;
  metadata: Metadata;
  imageSha256: string;
  detections: Detection[];
}
export interface HistoryPage {
  content: { inspectionId: string; inspectionTime: string; overallResult: Result; thumbnailUrl: string }[];
  page: number; size: number; totalElements: number; totalPages: number;
}
export interface DashboardSummary {
  totalInspections: number; passCount: number; failCount: number; passRate: number; failRate: number;
  defects: { component: number; order: number; fastening: number };
  averages: { boltConfidence: number | null; nutConfidence: number | null; washerConfidence: number | null; fasteningGap: number | null };
}
export interface Filters {
  result?: Result; startDate?: string; endDate?: string; productCode?: string; equipmentId?: string; lotNumber?: string;
  page?: number; size?: number;
}
export interface ApiErrorBody { timestamp: string; status: number; code: string; message: string }
export class InspectionApiError extends Error {
  constructor(public readonly response: ApiErrorBody) { super(response.message); this.name = 'InspectionApiError'; }
}
export function createInspectionApi(baseUrl = '') {
  const base = baseUrl.replace(/\/$/, '');
  async function request<T>(path: string, init?: RequestInit): Promise<T> {
    const response = await fetch(base + path, init);
    if (!response.ok) {
      const body = await response.json().catch(() => ({ timestamp: new Date().toISOString(), status: response.status, code: 'HTTP_ERROR', message: '서버 요청에 실패했습니다.' }));
      throw new InspectionApiError(body);
    }
    return response.json() as Promise<T>;
  }
  function query(filters: Filters) {
    const params = new URLSearchParams();
    for (const [key, value] of Object.entries(filters)) if (value != null) params.set(key, String(value));
    return params.toString();
  }
  return {
    async inspect(image: File, metadata: Metadata = {}, signal?: AbortSignal) {
      const body = new FormData(); body.append('image', image);
      for (const [key, value] of Object.entries(metadata)) if (value != null) body.append(key, value);
      // Browser sets the multipart boundary. Aborting the request does not cancel server-side inspection.
      return request<Inspection>('/api/inspections', { method: 'POST', body, signal });
    },
    history: (filters: Filters = {}) => request<HistoryPage>('/api/inspections?' + query(filters)),
    detail: (id: string) => request<Inspection>('/api/inspections/' + encodeURIComponent(id)),
    summary: (filters: Omit<Filters, 'page' | 'size' | 'result'> = {}) => request<DashboardSummary>('/api/dashboard/summary?' + query(filters)),
    recent: (limit = 8) => request<{ inspectionId: string; inspectionTime: string; result: Result; thumbnailUrl: string }[]>('/api/dashboard/recent-inspections?limit=' + limit),
    settings: () => request<RuleSettings>('/api/settings/inspection-rules'),
    updateSettings: (settings: RuleSettings, key: string) => request<RuleSettings>('/api/settings/inspection-rules', { method: 'PUT', headers: { 'Content-Type': 'application/json', 'X-Settings-Key': key }, body: JSON.stringify(settings) }),
    imageUrl: (relativeUrl: string) => base + relativeUrl,
  };
}
