import { ArrowRight, ScanLine } from 'lucide-react'

const metrics = [
  {
    label: '전체 검사',
    value: '1,248',
    detail: '어제 대비 +8.2%',
    color: 'text-[#172a3a]',
  },
  {
    label: '정상률',
    value: '94.6%',
    detail: 'OK 1,181건',
    color: 'text-[#168b5b]',
  },
  {
    label: '불량률',
    value: '5.4%',
    detail: 'NG 67건',
    color: 'text-[#d94b4b]',
  },
  {
    label: '평균 검사 시간',
    value: '1.8초',
    detail: '이미지 1장 기준',
    color: 'text-[#172a3a]',
  },
]

const defectTypes = [
  { name: '와셔 누락', value: 24, color: '#d94b4b' },
  { name: '너트 기울어짐', value: 18, color: '#d68a18' },
  { name: '순서 오류', value: 12, color: '#7b61c9' },
  { name: '기타', value: 13, color: '#56a6b8' },
]

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
  return (
    <div className="p-5 sm:p-7 lg:p-9">
      <div className="flex flex-col justify-between gap-4 sm:flex-row sm:items-start">
        <div>
          <h1 className="text-3xl font-bold text-[#172a3a]">
            품질 현황 대시보드
          </h1>

          <p className="mt-2 text-[#697d90]">
            오늘의 볼트 체결 검사 현황을 확인합니다.
          </p>
        </div>

        <div className="flex gap-3">
          <select className="rounded-lg border border-[#d9e4ee] bg-white px-5 py-3 text-sm">
            <option>오늘</option>
            <option>최근 7일</option>
            <option>최근 30일</option>
          </select>

          <button
            type="button"
            className="flex items-center gap-2 rounded-lg bg-[#0075c9] px-5 py-3 font-semibold text-white hover:bg-[#0065ad]"
          >
            <ScanLine size={18} />
            검사
          </button>
        </div>
      </div>

      <section className="mt-8 grid gap-4 sm:grid-cols-2 xl:grid-cols-4">
        {metrics.map((metric) => (
          <article
            key={metric.label}
            className="rounded-xl border border-[#d9e4ee] bg-white p-6"
          >
            <p className="text-sm text-[#697d90]">{metric.label}</p>

            <p className={`mt-3 text-3xl font-bold ${metric.color}`}>
              {metric.value}
            </p>

            <p className="mt-2 text-sm text-[#697d90]">
              {metric.detail}
            </p>
          </article>
        ))}
      </section>

      <section className="mt-6 grid gap-6 xl:grid-cols-[1.7fr_1fr]">
        <article className="rounded-xl border border-[#d9e4ee] bg-white p-6">
          <div className="flex items-center justify-between">
            <h2 className="text-xl font-bold">시간대별 검사량</h2>
            <p className="text-sm text-[#697d90]">전체 · OK · NG</p>
          </div>

          <div className="mt-6 overflow-hidden">
            <svg
              viewBox="0 0 760 230"
              role="img"
              aria-label="시간대별 검사량 그래프"
              className="h-[230px] w-full"
            >
              {[40, 85, 130, 175].map((y) => (
                <line
                  key={y}
                  x1="45"
                  y1={y}
                  x2="730"
                  y2={y}
                  stroke="#e1e9f0"
                />
              ))}

              <line
                x1="45"
                y1="200"
                x2="730"
                y2="200"
                stroke="#9cafbf"
              />

              <polyline
                points="45,180 140,156 235,170 330,111 425,131 520,77 615,101 700,57 730,69"
                fill="none"
                stroke="#0075c9"
                strokeWidth="5"
                strokeLinecap="round"
                strokeLinejoin="round"
              />

              {['09', '10', '11', '12', '13', '14', '15', '16'].map(
                (hour, index) => (
                  <text
                    key={hour}
                    x={40 + index * 94}
                    y="224"
                    fontSize="13"
                    fill="#697d90"
                  >
                    {hour}
                  </text>
                ),
              )}
            </svg>
          </div>
        </article>

        <article className="rounded-xl border border-[#d9e4ee] bg-white p-6">
          <h2 className="text-xl font-bold">불량 유형</h2>

          <div className="mt-7 flex flex-col items-center gap-8 sm:flex-row sm:justify-center">
            <div
              className="flex h-40 w-40 items-center justify-center rounded-full"
              style={{
                background:
                  'conic-gradient(#d94b4b 0 36%, #d68a18 36% 63%, #7b61c9 63% 81%, #56a6b8 81% 100%)',
              }}
            >
              <div className="flex h-24 w-24 items-center justify-center rounded-full bg-white text-2xl font-bold">
                67
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
                    style={{ backgroundColor: item.color }}
                  />

                  <span>{item.name}</span>
                  <strong>{item.value}</strong>
                </div>
              ))}
            </div>
          </div>
        </article>
      </section>

      <section className="mt-6 grid gap-6 xl:grid-cols-[1.7fr_1fr]">
        <article className="rounded-xl border border-[#d9e4ee] bg-white p-6">
          <h2 className="text-xl font-bold">평균 측정값</h2>

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
            <h2 className="text-xl font-bold">최근 불량</h2>

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
                  <p className="font-semibold">{defect.fileName}</p>
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

function MeasurementCard({
  label,
  value,
}: {
  label: string
  value: string
}) {
  return (
    <div className="rounded-lg border border-[#dce6ef] bg-[#f3f7fb] p-4">
      <p className="text-sm text-[#697d90]">{label}</p>
      <p className="mt-2 text-xl font-bold">{value}</p>
    </div>
  )
}