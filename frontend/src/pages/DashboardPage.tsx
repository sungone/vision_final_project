import { ArrowRight, ScanLine } from 'lucide-react'
import { useMemo } from 'react'
import { useLocalStorageState } from '../hooks/useLocalStorageState'

type RangeHours = 1 | 3 | 5

type TimeData = {
  time: string
  value: number
}

const recentDefects = [
  {
    fileName: 'IMG_0142.jpg',
    reason: '와셔 누락',
    time: '10:42',
  },
  {
    fileName: 'IMG_0135.jpg',
    reason: '너트 기울어짐',
    time: '10:31',
  },
  {
    fileName: 'IMG_0121.jpg',
    reason: '조립 순서 오류',
    time: '10:08',
  },
]

export default function DashboardPage() {
  const [rangeHours, setRangeHours] =
    useLocalStorageState<RangeHours>(
      'smart-bolt-dashboard-range',
      5,
  )

  const timeData = useMemo(
    () => createTimeData(rangeHours),
    [rangeHours],
  )

  const totalInspections = useMemo(
    () =>
      timeData.reduce(
        (total, current) => total + current.value,
        0,
      ),
    [timeData],
  )

  const normalCount = Math.round(
    totalInspections * 0.946,
  )

  const defectCount = Math.max(
    0,
    totalInspections - normalCount,
  )

  const normalRate =
    totalInspections === 0
      ? 0
      : (normalCount / totalInspections) * 100

  const defectRate =
    totalInspections === 0
      ? 0
      : (defectCount / totalInspections) * 100

  const metrics = [
    {
      label: '전체 검사',
      value: totalInspections.toLocaleString(),
      detail: `최근 ${rangeHours}시간`,
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
      label: '평균 검사 시간',
      value: '1.8초',
      detail: '이미지 1장 기준',
      color: 'text-[#172a3a]',
    },
  ]

  const defectTypes = createDefectTypes(defectCount)

  return (
    <div className="p-5 sm:p-7 lg:p-9">
      <header className="flex flex-col justify-between gap-4 sm:flex-row sm:items-start">
        <div>
          <h1 className="text-3xl font-bold text-[#172a3a]">
            품질 현황 대시보드
          </h1>

          <p className="mt-2 text-[#697d90]">
            최근 검사 현황을 10분 단위로 확인합니다.
          </p>
        </div>

        <div className="flex gap-3">
          <select
            value={rangeHours}
            onChange={(event) =>
              setRangeHours(
                Number(event.target.value) as RangeHours,
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
            className="flex items-center gap-2 rounded-lg bg-[#0075c9] px-5 py-3 font-semibold text-white hover:bg-[#0065ad]"
          >
            <ScanLine size={18} />
            검사
          </button>
        </div>
      </header>

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
          <h2 className="text-xl font-bold">
            평균 측정값
          </h2>

          <div className="mt-5 grid gap-4 sm:grid-cols-3">
            <MeasurementCard
              label="와셔-너트 간격"
              value="1.6 mm"
            />

            <MeasurementCard
              label="나사산 노출 길이"
              value="12.4 mm"
            />

            <MeasurementCard
              label="너트 기울기"
              value="1.2°"
            />
          </div>

          <p className="mt-7 text-sm text-[#697d90]">
            기준 범위 대비 평균 추세
          </p>

          <div className="mt-3 h-3 overflow-hidden rounded-full bg-[#e8eff5]">
            <div className="ml-[24%] h-full w-[48%] bg-[#00a9ce]" />
          </div>
        </article>

        <article className="rounded-xl border border-[#d9e4ee] bg-white p-6">
          <div className="flex items-center justify-between">
            <h2 className="text-xl font-bold">
              최근 불량
            </h2>

            <button
              type="button"
              className="flex items-center gap-1 text-sm text-[#0075c9]"
            >
              전체 보기
              <ArrowRight size={15} />
            </button>
          </div>

          <div className="mt-4 divide-y divide-[#e1e9f0]">
            {recentDefects.map((defect) => (
              <div
                key={defect.fileName}
                className="flex items-center gap-4 py-3"
              >
                <div className="h-12 w-16 rounded-md border border-[#d9e4ee] bg-[#f3f7fb]" />

                <div>
                  <p className="font-semibold">
                    {defect.fileName}
                  </p>

                  <p className="mt-1 text-sm text-[#697d90]">
                    {defect.reason} · {defect.time}
                  </p>
                </div>
              </div>
            ))}
          </div>
        </article>
      </section>
    </div>
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
            (index / (timeData.length - 1)) *
              chartWidth

      const y =
        chartBottom -
        (item.value / maximumValue) * chartHeight

      return `${x},${y}`
    })
    .join(' ')

  const labelInterval = rangeHours === 1 ? 1 : 3

  return (
    <article className="rounded-xl border border-[#d9e4ee] bg-white p-6">
      <div className="flex flex-col justify-between gap-2 sm:flex-row sm:items-center">
        <div>
          <h2 className="text-xl font-bold">
            10분 단위 검사량
          </h2>

          <p className="mt-1 text-sm text-[#697d90]">
            최근 {rangeHours}시간 검사 건수
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
                chartBottom - ratio * chartHeight

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
              (item.value / maximumValue) *
                chartHeight

            const showLabel =
              index % labelInterval === 0 ||
              index === timeData.length - 1

            return (
              <g key={`${item.time}-${index}`}>
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
  defectTypes: {
    name: string
    value: number
    color: string
  }[]
}) {
  return (
    <article className="rounded-xl border border-[#d9e4ee] bg-white p-6">
      <h2 className="text-xl font-bold">불량 유형</h2>

      <div className="mt-7 flex flex-col items-center gap-8 sm:flex-row sm:justify-center">
        <div
          className="flex h-40 w-40 shrink-0 items-center justify-center rounded-full"
          style={{
            background:
              'conic-gradient(#d94b4b 0 36%, #d68a18 36% 63%, #7b61c9 63% 81%, #56a6b8 81% 100%)',
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

function createTimeData(
  rangeHours: RangeHours,
): TimeData[] {
  const pointCount = rangeHours * 6
  const currentTime = new Date()

  currentTime.setSeconds(0, 0)
  currentTime.setMinutes(
    Math.floor(currentTime.getMinutes() / 10) * 10,
  )

  return Array.from(
    { length: pointCount },
    (_, index) => {
      const time = new Date(
        currentTime.getTime() -
          (pointCount - 1 - index) *
            10 *
            60 *
            1000,
      )

      const value =
        24 +
        ((index * 7 + pointCount * 3) % 27)

      return {
        time: formatTime(time),
        value,
      }
    },
  )
}

function createDefectTypes(defectCount: number) {
  const washer = Math.round(defectCount * 0.36)
  const tiltedNut = Math.round(defectCount * 0.27)
  const sequence = Math.round(defectCount * 0.18)

  return [
    {
      name: '와셔 누락',
      value: washer,
      color: '#d94b4b',
    },
    {
      name: '너트 기울어짐',
      value: tiltedNut,
      color: '#d68a18',
    },
    {
      name: '순서 오류',
      value: sequence,
      color: '#7b61c9',
    },
    {
      name: '기타',
      value: Math.max(
        0,
        defectCount -
          washer -
          tiltedNut -
          sequence,
      ),
      color: '#56a6b8',
    },
  ]
}

function formatTime(date: Date) {
  const hours = String(date.getHours()).padStart(
    2,
    '0',
  )

  const minutes = String(date.getMinutes()).padStart(
    2,
    '0',
  )

  return `${hours}:${minutes}`
}