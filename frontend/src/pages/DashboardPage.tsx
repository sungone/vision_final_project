import {
  AlertCircle,
  ArrowRight,
  RefreshCw,
  ScanLine,
} from 'lucide-react'
import {
  useEffect,
  useMemo,
  useState,
} from 'react'
import { useNavigate } from 'react-router-dom'
import { useLocalStorageState } from '../hooks/useLocalStorageState'
import {
  getInspectionHistory,
  getLatestInspection,
  resolveResultImageUrl,
} from '../services/inspectionApi'
import type {
  InspectionHistoryItem,
  LatestInspectionResponse,
  ResultStatus,
} from '../types/vision'

type RangeHours = 1 | 3 | 5

type TimeData = {
  time: string
  timestamp: number
  value: number
}

type DefectType = {
  name: string
  value: number
  color: string
}

export default function DashboardPage() {
  const navigate = useNavigate()

  const [rangeHours, setRangeHours] =
    useLocalStorageState<RangeHours>(
      'smart-bolt-dashboard-range',
      5,
    )

  const [latestInspection, setLatestInspection] =
    useState<LatestInspectionResponse | null>(null)

  const [history, setHistory] = useState<
    InspectionHistoryItem[]
  >([])

  const [latestError, setLatestError] = useState('')
  const [historyError, setHistoryError] = useState('')
  const [refreshToken, setRefreshToken] = useState(0)
  const [historyUpdatedAt, setHistoryUpdatedAt] =
    useState<Date | null>(null)

  useEffect(() => {
    let disposed = false
    let requestInFlight = false
    const controller = new AbortController()

    async function refreshLatest() {
      if (requestInFlight) {
        return
      }

      requestInFlight = true

      try {
        const result = await getLatestInspection(
          controller.signal,
        )

        if (!disposed) {
          setLatestInspection(result)
          setLatestError('')
        }
      } catch (error) {
        if (!disposed && !controller.signal.aborted) {
          setLatestError(
            error instanceof Error
              ? error.message
              : '현재 검사 결과를 불러오지 못했습니다.',
          )
        }
      } finally {
        requestInFlight = false
      }
    }

    void refreshLatest()

    const timer = window.setInterval(() => {
      void refreshLatest()
    }, 1000)

    return () => {
      disposed = true
      window.clearInterval(timer)
      controller.abort()
    }
  }, [refreshToken])

  useEffect(() => {
    let disposed = false
    let requestInFlight = false
    const controller = new AbortController()

    async function refreshHistory() {
      if (requestInFlight) {
        return
      }

      requestInFlight = true

      try {
        const result = await getInspectionHistory(
          0,
          100,
          controller.signal,
        )

        if (!disposed) {
          setHistory(result.content)
          setHistoryUpdatedAt(new Date())
          setHistoryError('')
        }
      } catch (error) {
        if (!disposed && !controller.signal.aborted) {
          setHistoryError(
            error instanceof Error
              ? error.message
              : '검사 이력을 불러오지 못했습니다.',
          )
        }
      } finally {
        requestInFlight = false
      }
    }

    void refreshHistory()

    const timer = window.setInterval(() => {
      void refreshHistory()
    }, 10000)

    return () => {
      disposed = true
      window.clearInterval(timer)
      controller.abort()
    }
  }, [refreshToken])

  const filteredHistory = useMemo(() => {
    const referenceTime =
      historyUpdatedAt?.getTime() ?? 0

    const cutoff =
      referenceTime -
      rangeHours * 60 * 60 * 1000

    return history.filter((item) => {
      const time = new Date(
        item.inspectionTime,
      ).getTime()

      return (
        Number.isFinite(time) &&
        time >= cutoff &&
        time <= referenceTime
      )
    })
  }, [history, historyUpdatedAt, rangeHours])

  const timeData = useMemo(
    () =>
      createTimeData(
        rangeHours,
        filteredHistory,
        historyUpdatedAt ?? new Date(),
      ),
    [
      rangeHours,
      filteredHistory,
      historyUpdatedAt,
    ],
  )

  const totalInspections = filteredHistory.length

  const normalCount = filteredHistory.filter(
    (item) => item.overallResult === 'NORMAL',
  ).length

  const defectItems = filteredHistory.filter(
    (item) => item.overallResult === 'DEFECT',
  )

  const defectCount = defectItems.length

  const normalRate =
    totalInspections === 0
      ? 0
      : (normalCount / totalInspections) * 100

  const defectRate =
    totalInspections === 0
      ? 0
      : (defectCount / totalInspections) * 100

  const averageInferenceTime = useMemo(() => {
    const values = filteredHistory
      .map(getInferenceTime)
      .filter(
        (value): value is number =>
          typeof value === 'number' &&
          Number.isFinite(value),
      )

    if (values.length === 0) {
      return null
    }

    return (
      values.reduce(
        (total, value) => total + value,
        0,
      ) / values.length
    )
  }, [filteredHistory])

  const defectTypes = useMemo(
    () => createDefectTypes(defectItems),
    [defectItems],
  )

  const recentDefects = useMemo(
    () =>
      history
        .filter(
          (item) =>
            item.overallResult === 'DEFECT',
        )
        .slice(0, 3),
    [history],
  )

  const metrics = [
    {
      label: '전체 검사',
      value: totalInspections.toLocaleString(),
      detail: `최근 ${rangeHours}시간 · 최대 100건 기준`,
      color: 'text-[#172a3a]',
    },
    {
      label: '정상률',
      value: `${normalRate.toFixed(1)}%`,
      detail: `OK ${normalCount.toLocaleString()}건`,
      color: 'text-[#168b5b]',
    },
    {
      label: '불량률',
      value: `${defectRate.toFixed(1)}%`,
      detail: `NG ${defectCount.toLocaleString()}건`,
      color: 'text-[#d94b4b]',
    },
    {
      label: '평균 추론 시간',
      value:
        averageInferenceTime == null
          ? '-'
          : `${averageInferenceTime.toFixed(1)} ms`,
      detail: '서버 모델 추론 기준',
      color: 'text-[#172a3a]',
    },
  ]

  const latestCounts =
    latestInspection?.metrics.detectedCounts ?? {}

  const currentError =
    latestError || historyError

  return (
    <div className="p-5 sm:p-7 lg:p-9">
      <header className="flex flex-col justify-between gap-4 sm:flex-row sm:items-start">
        <div>
          <div className="flex flex-wrap items-center gap-3">
            <h1 className="text-3xl font-bold text-[#172a3a]">
              품질 현황 대시보드
            </h1>

            <LatestStatusBadge
              result={
                latestInspection?.overallResult ??
                null
              }
            />
          </div>

          <p className="mt-2 text-[#697d90]">
            실제 검사 이력을 10분 단위로
            집계합니다.
          </p>

          <p className="mt-1 text-xs text-[#8a9bab]">
            마지막 이력 갱신:{' '}
            {historyUpdatedAt
              ? historyUpdatedAt.toLocaleString(
                  'ko-KR',
                  {
                    hour12: false,
                  },
                )
              : '대기 중'}
          </p>
        </div>

        <div className="flex flex-wrap gap-3">
          <select
            value={rangeHours}
            onChange={(event) =>
              setRangeHours(
                Number(
                  event.target.value,
                ) as RangeHours,
              )
            }
            className="rounded-lg border border-[#d9e4ee] bg-white px-5 py-3 text-sm font-semibold outline-none focus:border-[#0075c9]"
          >
            <option value={1}>최근 1시간</option>
            <option value={3}>최근 3시간</option>
            <option value={5}>최근 5시간</option>
          </select>

          <button
            type="button"
            onClick={() =>
              setRefreshToken(
                (current) => current + 1,
              )
            }
            className="flex items-center gap-2 rounded-lg border border-[#bfd0df] bg-white px-4 py-3 text-sm font-semibold text-[#0075c9] hover:bg-blue-50"
          >
            <RefreshCw size={17} />
            새로고침
          </button>

          <button
            type="button"
            onClick={() => navigate('/realtime')}
            className="flex items-center gap-2 rounded-lg bg-[#0075c9] px-5 py-3 font-semibold text-white hover:bg-[#0065ad]"
          >
            <ScanLine size={18} />
            실시간 검사
          </button>
        </div>
      </header>

      {currentError && (
        <div className="mt-5 flex items-start gap-2 rounded-lg border border-red-200 bg-red-50 px-4 py-3 text-sm text-red-700">
          <AlertCircle
            size={18}
            className="mt-0.5 shrink-0"
          />
          {currentError}
        </div>
      )}

      <section className="mt-8 grid gap-4 sm:grid-cols-2 xl:grid-cols-4">
        {metrics.map((metric) => (
          <article
            key={metric.label}
            className="rounded-xl border border-[#d9e4ee] bg-white p-6"
          >
            <p className="text-sm text-[#697d90]">
              {metric.label}
            </p>

            <p
              className={`mt-3 text-3xl font-bold ${metric.color}`}
            >
              {metric.value}
            </p>

            <p className="mt-2 text-sm text-[#697d90]">
              {metric.detail}
            </p>
          </article>
        ))}
      </section>

      <section className="mt-6 grid gap-6 xl:grid-cols-[1.7fr_1fr]">
        <InspectionChart
          timeData={timeData}
          rangeHours={rangeHours}
        />

        <DefectChart
          defectCount={defectCount}
          defectTypes={defectTypes}
        />
      </section>

      <section className="mt-6 grid gap-6 xl:grid-cols-[1.7fr_1fr]">
        <article className="rounded-xl border border-[#d9e4ee] bg-white p-6">
          <div className="flex items-center justify-between">
            <div>
              <h2 className="text-xl font-bold">
                현재 프레임 측정값
              </h2>

              <p className="mt-1 text-sm text-[#697d90]">
                실시간 분석 결과에서 가져온
                최신 값입니다.
              </p>
            </div>
          </div>

          <div className="mt-5 grid gap-4 sm:grid-cols-3">
            <MeasurementCard
              label="나사산 노출 길이"
              value={formatCentimeter(
                latestInspection?.metrics
                  .measuredThreadCm,
              )}
            />

            <MeasurementCard
              label="체결 판정 기준"
              value={formatCentimeter(
                latestInspection?.metrics
                  .threadThresholdCm,
              )}
            />

            <MeasurementCard
              label="현재 검출 객체"
              value={
                latestInspection
                  ? `${latestInspection.metrics.detectedInstanceCount}개`
                  : '-'
              }
            />
          </div>

          <div className="mt-5 grid gap-3 sm:grid-cols-3">
            <DetectionCount
              label="볼트"
              value={latestCounts.bolt ?? 0}
            />

            <DetectionCount
              label="와셔"
              value={latestCounts.washer ?? 0}
            />

            <DetectionCount
              label="나사산"
              value={latestCounts.thread ?? 0}
            />
          </div>
        </article>

        <article className="rounded-xl border border-[#d9e4ee] bg-white p-6">
          <div className="flex items-center justify-between">
            <h2 className="text-xl font-bold">
              최근 불량
            </h2>

            <button
              type="button"
              onClick={() => navigate('/history')}
              className="flex items-center gap-1 text-sm font-semibold text-[#0075c9]"
            >
              전체 보기
              <ArrowRight size={15} />
            </button>
          </div>

          {recentDefects.length === 0 ? (
            <div className="mt-4 flex min-h-44 items-center justify-center rounded-lg border border-dashed border-[#d9e4ee] bg-[#f7fafc] p-5 text-center text-sm text-[#697d90]">
              저장된 불량 검사 이력이 없습니다.
            </div>
          ) : (
            <div className="mt-4 divide-y divide-[#e1e9f0]">
              {recentDefects.map((defect) => (
                <button
                  key={defect.id}
                  type="button"
                  onClick={() =>
                    navigate(
                      `/history/${defect.id}`,
                    )
                  }
                  className="flex w-full items-center gap-4 py-3 text-left hover:bg-[#f7fafc]"
                >
                  <DefectThumbnail
                    item={defect}
                  />

                  <div className="min-w-0">
                    <p className="truncate font-semibold">
                      검사 #{defect.id}
                    </p>

                    <p className="mt-1 truncate text-sm text-[#697d90]">
                      {getDefectReason(defect)}
                      {' · '}
                      {formatDateTime(
                        defect.inspectionTime,
                      )}
                    </p>
                  </div>
                </button>
              ))}
            </div>
          )}
        </article>
      </section>
    </div>
  )
}

function LatestStatusBadge({
  result,
}: {
  result: ResultStatus | null
}) {
  if (result == null) {
    return (
      <span className="rounded-full bg-slate-100 px-3 py-1 text-xs font-bold text-slate-500">
        분석 대기
      </span>
    )
  }

  if (result === 'NORMAL') {
    return (
      <span className="rounded-full bg-emerald-100 px-3 py-1 text-xs font-bold text-emerald-700">
        현재 정상
      </span>
    )
  }

  if (result === 'NOT_EVALUATED') {
    return (
      <span className="rounded-full bg-slate-100 px-3 py-1 text-xs font-bold text-slate-600">
        현재 미평가
      </span>
    )
  }

  return (
    <span className="rounded-full bg-red-100 px-3 py-1 text-xs font-bold text-red-700">
      현재 불량
    </span>
  )
}

function InspectionChart({
  timeData,
  rangeHours,
}: {
  timeData: TimeData[]
  rangeHours: RangeHours
}) {
  const chartLeft = 50
  const chartRight = 730
  const chartTop = 35
  const chartBottom = 190

  const chartWidth = chartRight - chartLeft
  const chartHeight = chartBottom - chartTop

  const maximumValue = Math.max(
    ...timeData.map((item) => item.value),
    1,
  )

  const points = timeData
    .map((item, index) => {
      const x =
        timeData.length === 1
          ? chartLeft
          : chartLeft +
            (index /
              (timeData.length - 1)) *
              chartWidth

      const y =
        chartBottom -
        (item.value / maximumValue) *
          chartHeight

      return `${x},${y}`
    })
    .join(' ')

  const labelInterval =
    rangeHours === 1 ? 1 : 3

  return (
    <article className="rounded-xl border border-[#d9e4ee] bg-white p-6">
      <div className="flex flex-col justify-between gap-2 sm:flex-row sm:items-center">
        <div>
          <h2 className="text-xl font-bold">
            10분 단위 검사량
          </h2>

          <p className="mt-1 text-sm text-[#697d90]">
            최근 {rangeHours}시간 실제 저장 건수
          </p>
        </div>

        <span className="rounded-full bg-blue-50 px-3 py-1 text-xs font-semibold text-[#0075c9]">
          집계 간격 10분
        </span>
      </div>

      <div className="mt-5 overflow-x-auto">
        <svg
          viewBox="0 0 760 240"
          role="img"
          aria-label={`최근 ${rangeHours}시간 10분 단위 검사량`}
          className="h-[250px] min-w-[700px] w-full"
        >
          {[0, 0.25, 0.5, 0.75, 1].map(
            (ratio) => {
              const y =
                chartBottom -
                ratio * chartHeight

              const value = Math.round(
                maximumValue * ratio,
              )

              return (
                <g key={ratio}>
                  <line
                    x1={chartLeft}
                    y1={y}
                    x2={chartRight}
                    y2={y}
                    stroke="#e1e9f0"
                  />

                  <text
                    x="8"
                    y={y + 4}
                    fontSize="11"
                    fill="#697d90"
                  >
                    {value}
                  </text>
                </g>
              )
            },
          )}

          <polyline
            points={points}
            fill="none"
            stroke="#0075c9"
            strokeWidth="4"
            strokeLinecap="round"
            strokeLinejoin="round"
          />

          {timeData.map((item, index) => {
            const x =
              timeData.length === 1
                ? chartLeft
                : chartLeft +
                  (index /
                    (timeData.length - 1)) *
                    chartWidth

            const y =
              chartBottom -
              (item.value /
                maximumValue) *
                chartHeight

            const showLabel =
              index % labelInterval === 0 ||
              index === timeData.length - 1

            return (
              <g key={item.timestamp}>
                <circle
                  cx={x}
                  cy={y}
                  r="4"
                  fill="#0075c9"
                  stroke="white"
                  strokeWidth="2"
                >
                  <title>
                    {item.time} · {item.value}건
                  </title>
                </circle>

                {showLabel && (
                  <text
                    x={x}
                    y="220"
                    textAnchor="middle"
                    fontSize="11"
                    fill="#697d90"
                  >
                    {item.time}
                  </text>
                )}
              </g>
            )
          })}
        </svg>
      </div>
    </article>
  )
}

function DefectChart({
  defectCount,
  defectTypes,
}: {
  defectCount: number
  defectTypes: DefectType[]
}) {
  return (
    <article className="rounded-xl border border-[#d9e4ee] bg-white p-6">
      <h2 className="text-xl font-bold">
        불량 유형
      </h2>

      <div className="mt-7 flex flex-col items-center gap-8 sm:flex-row sm:justify-center">
        <div
          className="flex h-40 w-40 shrink-0 items-center justify-center rounded-full"
          style={{
            background: createConicGradient(
              defectTypes,
              defectCount,
            ),
          }}
        >
          <div className="flex h-24 w-24 items-center justify-center rounded-full bg-white text-2xl font-bold">
            {defectCount}
          </div>
        </div>

        <div className="space-y-3">
          {defectTypes.map((item) => (
            <div
              key={item.name}
              className="flex items-center gap-3 text-sm"
            >
              <span
                className="h-3 w-3 rounded-sm"
                style={{
                  backgroundColor: item.color,
                }}
              />

              <span>{item.name}</span>
              <strong>{item.value}</strong>
            </div>
          ))}
        </div>
      </div>
    </article>
  )
}

function MeasurementCard({
  label,
  value,
}: {
  label: string
  value: string
}) {
  return (
    <div className="rounded-lg border border-[#dce6ef] bg-[#f3f7fb] p-4">
      <p className="text-sm text-[#697d90]">
        {label}
      </p>

      <p className="mt-2 text-xl font-bold">
        {value}
      </p>
    </div>
  )
}

function DetectionCount({
  label,
  value,
}: {
  label: string
  value: number
}) {
  return (
    <div className="flex items-center justify-between rounded-lg border border-[#dce6ef] px-4 py-3">
      <span className="text-sm text-[#697d90]">
        {label}
      </span>

      <strong>{value}개</strong>
    </div>
  )
}

function DefectThumbnail({
  item,
}: {
  item: InspectionHistoryItem
}) {
  if (!item.defectImageUrl) {
    return (
      <div className="h-12 w-16 shrink-0 rounded-md border border-[#d9e4ee] bg-[#f3f7fb]" />
    )
  }

  return (
    <img
      src={resolveResultImageUrl(
        item.defectImageUrl,
      )}
      alt={`검사 ${item.id} 불량 이미지`}
      className="h-12 w-16 shrink-0 rounded-md border border-[#d9e4ee] object-cover"
    />
  )
}

function createTimeData(
  rangeHours: RangeHours,
  items: InspectionHistoryItem[],
  referenceTime: Date,
): TimeData[] {
  const pointCount = rangeHours * 6

  const currentBucket = new Date(
    referenceTime,
  )

  currentBucket.setSeconds(0, 0)
  currentBucket.setMinutes(
    Math.floor(
      currentBucket.getMinutes() / 10,
    ) * 10,
  )

  const buckets = Array.from(
    { length: pointCount },
    (_, index) => {
      const timestamp =
        currentBucket.getTime() -
        (pointCount - 1 - index) *
          10 *
          60 *
          1000

      return {
        time: formatTime(
          new Date(timestamp),
        ),
        timestamp,
        value: 0,
      }
    },
  )

  const bucketMap = new Map(
    buckets.map((bucket) => [
      bucket.timestamp,
      bucket,
    ]),
  )

  items.forEach((item) => {
    const date = new Date(
      item.inspectionTime,
    )

    if (
      Number.isNaN(date.getTime())
    ) {
      return
    }

    date.setSeconds(0, 0)
    date.setMinutes(
      Math.floor(date.getMinutes() / 10) *
        10,
    )

    const bucket = bucketMap.get(
      date.getTime(),
    )

    if (bucket) {
      bucket.value += 1
    }
  })

  return buckets
}

function createDefectTypes(
  items: InspectionHistoryItem[],
): DefectType[] {
  const counts = {
    washer: 0,
    thread: 0,
    fastening: 0,
    other: 0,
  }

  items.forEach((item) => {
    const reasons = getAssemblyReasons(item)

    if (
      reasons.some((reason) =>
        reason.includes('washer'),
      )
    ) {
      counts.washer += 1
      return
    }

    if (
      reasons.some((reason) =>
        reason.includes('thread'),
      )
    ) {
      counts.thread += 1
      return
    }

    if (item.fasteningResult === 'DEFECT') {
      counts.fastening += 1
      return
    }

    counts.other += 1
  })

  return [
    {
      name: '와셔 이상',
      value: counts.washer,
      color: '#d94b4b',
    },
    {
      name: '나사산 이상',
      value: counts.thread,
      color: '#d68a18',
    },
    {
      name: '체결 불량',
      value: counts.fastening,
      color: '#7b61c9',
    },
    {
      name: '기타',
      value: counts.other,
      color: '#56a6b8',
    },
  ]
}

function createConicGradient(
  defectTypes: DefectType[],
  total: number,
) {
  if (total === 0) {
    return '#e8eff5'
  }

  let start = 0

  const segments = defectTypes
    .filter((item) => item.value > 0)
    .map((item) => {
      const end =
        start + (item.value / total) * 100

      const segment =
        `${item.color} ${start}% ${end}%`

      start = end
      return segment
    })

  return `conic-gradient(${segments.join(', ')})`
}

function getInferenceTime(
  item: InspectionHistoryItem,
) {
  if (
    typeof item.inferenceTimeMs === 'number'
  ) {
    return item.inferenceTimeMs
  }

  const nestedValue =
    item.metrics.inferenceTimeMs

  return typeof nestedValue === 'number'
    ? nestedValue
    : null
}

function getAssemblyReasons(
  item: InspectionHistoryItem,
): string[] {
  const reasons =
    item.metrics.assemblyReasons

  if (!Array.isArray(reasons)) {
    return []
  }

  return reasons.filter(
    (reason): reason is string =>
      typeof reason === 'string',
  )
}

function getDefectReason(
  item: InspectionHistoryItem,
) {
  const reasons = getAssemblyReasons(item)

  if (reasons.length > 0) {
    return getReasonLabel(reasons[0])
  }

  if (item.fasteningResult === 'DEFECT') {
    return '체결 상태 불량'
  }

  if (
    item.missingComponentResult ===
    'DEFECT'
  ) {
    return '구성품 또는 조립 상태 불량'
  }

  return '검사 기준 불량'
}

function getReasonLabel(reason: string) {
  if (reason === 'no_thread') {
    return '나사산 미검출'
  }

  if (reason === 'no_bolt') {
    return '볼트 미검출'
  }

  if (reason === 'no_nut') {
    return '너트 미검출'
  }

  if (reason.startsWith('dup_thread')) {
    return '나사산 중복 검출'
  }

  if (reason.startsWith('extra_bolt')) {
    return '볼트 수량 이상'
  }

  if (reason.startsWith('washer_low')) {
    return '와셔 수량 부족'
  }

  if (reason.startsWith('washer_high')) {
    return '와셔 수량 초과'
  }

  return reason
}

function formatCentimeter(value?: number) {
  if (value == null) {
    return '-'
  }

  return `${value.toFixed(2)} cm`
}

function formatDateTime(value: string) {
  const date = new Date(value)

  if (Number.isNaN(date.getTime())) {
    return '-'
  }

  return date.toLocaleString('ko-KR', {
    month: '2-digit',
    day: '2-digit',
    hour: '2-digit',
    minute: '2-digit',
    hour12: false,
  })
}

function formatTime(date: Date) {
  const hours = String(
    date.getHours(),
  ).padStart(2, '0')

  const minutes = String(
    date.getMinutes(),
  ).padStart(2, '0')

  return `${hours}:${minutes}`
}