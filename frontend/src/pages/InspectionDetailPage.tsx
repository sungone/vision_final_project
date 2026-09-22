import {
  AlertTriangle,
  ArrowLeft,
  CheckCircle2,
  ChevronLeft,
  ChevronRight,
  Download,
  Trash2,
} from 'lucide-react'
import {
  useNavigate,
  useParams,
} from 'react-router-dom'
import type { InspectionResult } from '../types/inspection'

type DetailRecord = {
  id: string
  fileName: string
  inspectedAt: string
  assemblySequenceResult: InspectionResult
  fasteningQualityResult: InspectionResult
  defectReason: string
  washerNutGap: number | null
  exposedLength: number
  tiltAngle: number
  processingTime: number
  modelName: string
}

const detailRecords: DetailRecord[] = [
  {
    id: '001248',
    fileName: 'IMG_0142.jpg',
    inspectedAt: '2026-09-22 10:42:16',
    assemblySequenceResult: 'DEFECT',
    fasteningQualityResult: 'NORMAL',
    defectReason:
      '와셔 객체가 기준 신뢰도 이상으로 검출되지 않음',
    washerNutGap: null,
    exposedLength: 12.8,
    tiltAngle: 1.4,
    processingTime: 1.82,
    modelName: 'bolt-seg-v1.0',
  },
  {
    id: '001247',
    fileName: 'IMG_0141.jpg',
    inspectedAt: '2026-09-22 10:40:08',
    assemblySequenceResult: 'NORMAL',
    fasteningQualityResult: 'NORMAL',
    defectReason: '-',
    washerNutGap: 1.5,
    exposedLength: 12.1,
    tiltAngle: 0.8,
    processingTime: 1.76,
    modelName: 'bolt-seg-v1.0',
  },
  {
    id: '001246',
    fileName: 'IMG_0140.jpg',
    inspectedAt: '2026-09-22 10:38:42',
    assemblySequenceResult: 'NORMAL',
    fasteningQualityResult: 'DEFECT',
    defectReason: '너트 기울기가 허용 기준을 초과함',
    washerNutGap: 2.8,
    exposedLength: 16.9,
    tiltAngle: 4.6,
    processingTime: 1.91,
    modelName: 'bolt-seg-v1.0',
  },
  {
    id: '001245',
    fileName: 'IMG_0139.jpg',
    inspectedAt: '2026-09-22 10:36:11',
    assemblySequenceResult: 'NORMAL',
    fasteningQualityResult: 'NORMAL',
    defectReason: '-',
    washerNutGap: 1.4,
    exposedLength: 11.9,
    tiltAngle: 1,
    processingTime: 1.69,
    modelName: 'bolt-seg-v1.0',
  },
  {
    id: '001244',
    fileName: 'IMG_0138.jpg',
    inspectedAt: '2026-09-22 10:34:27',
    assemblySequenceResult: 'NORMAL',
    fasteningQualityResult: 'NORMAL',
    defectReason: '-',
    washerNutGap: 1.6,
    exposedLength: 12.3,
    tiltAngle: 0.9,
    processingTime: 1.74,
    modelName: 'bolt-seg-v1.0',
  },
]

export default function InspectionDetailPage() {
  const { inspectionId } = useParams()
  const navigate = useNavigate()

  const recordIndex = detailRecords.findIndex(
    (item) => item.id === inspectionId,
  )

  if (recordIndex === -1) {
    return (
      <div className="p-5 sm:p-7 lg:p-9">
        <button
          type="button"
          onClick={() => navigate('/history')}
          className="flex items-center gap-2 text-[#0075c9]"
        >
          <ArrowLeft size={18} />
          검사 이력으로 돌아가기
        </button>

        <div className="mt-8 rounded-xl border border-[#d9e4ee] bg-white p-12 text-center">
          <AlertTriangle
            size={40}
            className="mx-auto text-amber-500"
          />

          <h1 className="mt-4 text-2xl font-bold">
            검사 기록을 찾을 수 없습니다.
          </h1>
        </div>
      </div>
    )
  }

  const record = detailRecords[recordIndex]

  const previousRecord =
    detailRecords[recordIndex + 1]

  const nextRecord =
    detailRecords[recordIndex - 1]

  const finalResult = getFinalResult(record)
  const isNormal = finalResult === 'NORMAL'

  function deleteRecord() {
    const confirmed = window.confirm(
      `검사 #${record.id} 기록을 삭제하시겠습니까?`,
    )

    if (confirmed) {
      navigate('/history')
    }
  }

  return (
    <div className="p-5 sm:p-7 lg:p-9">
      <header className="flex flex-col justify-between gap-5 xl:flex-row xl:items-start">
        <div>
          <button
            type="button"
            onClick={() => navigate('/history')}
            className="flex items-center gap-2 text-sm text-[#697d90] hover:text-[#0075c9]"
          >
            <ArrowLeft size={17} />
            검사 이력 / #{record.id}
          </button>

          <h1 className="mt-3 text-3xl font-bold text-[#172a3a]">
            검사 상세
          </h1>

          <p className="mt-2 text-[#697d90]">
            {record.fileName} · {record.inspectedAt}
          </p>
        </div>

        <div className="flex flex-wrap gap-3">
          <button
            type="button"
            onClick={() =>
              window.alert(
                '실제 결과 이미지 연결 후 다운로드됩니다.',
              )
            }
            className="flex items-center gap-2 rounded-lg border border-[#d9e4ee] bg-white px-5 py-3 font-semibold hover:bg-[#f3f7fb]"
          >
            <Download size={18} />
            결과 저장
          </button>

          <button
            type="button"
            onClick={deleteRecord}
            className="flex items-center gap-2 rounded-lg border border-red-200 bg-red-50 px-5 py-3 font-semibold text-red-600 hover:bg-red-100"
          >
            <Trash2 size={18} />
            삭제
          </button>

          <button
            type="button"
            onClick={() => navigate('/history')}
            className="rounded-lg bg-[#0075c9] px-5 py-3 font-semibold text-white hover:bg-[#0065ad]"
          >
            목록으로
          </button>
        </div>
      </header>

      <div className="mt-7 grid gap-6 xl:grid-cols-[minmax(0,1fr)_400px]">
        <section className="rounded-xl border border-[#d9e4ee] bg-white p-5">
          <h2 className="text-xl font-bold">
            이미지 비교
          </h2>

          <div className="mt-5 grid gap-5 md:grid-cols-2">
            <ImageCard title="원본">
              <MockInspectionImage
                analyzed={false}
                isDefect={!isNormal}
              />
            </ImageCard>

            <ImageCard title="분석 결과">
              <MockInspectionImage
                analyzed
                isDefect={!isNormal}
              />
            </ImageCard>
          </div>

          <div className="mt-5 flex items-center justify-between gap-4 border-t border-[#e1e9f0] pt-4">
            <button
              type="button"
              disabled={!previousRecord}
              onClick={() =>
                previousRecord &&
                navigate(
                  `/history/${previousRecord.id}`,
                )
              }
              className="flex items-center gap-2 rounded-lg border border-[#d9e4ee] px-4 py-2 text-sm disabled:cursor-not-allowed disabled:opacity-40"
            >
              <ChevronLeft size={17} />
              이전 검사
            </button>

            <button
              type="button"
              disabled={!nextRecord}
              onClick={() =>
                nextRecord &&
                navigate(`/history/${nextRecord.id}`)
              }
              className="flex items-center gap-2 rounded-lg border border-[#d9e4ee] px-4 py-2 text-sm disabled:cursor-not-allowed disabled:opacity-40"
            >
              다음 검사
              <ChevronRight size={17} />
            </button>
          </div>
        </section>

        <aside className="rounded-xl border border-[#d9e4ee] bg-white p-5">
          <h2 className="text-xl font-bold">
            판정 요약
          </h2>

          <div
            className={[
              'mt-5 rounded-xl border p-5',
              isNormal
                ? 'border-emerald-200 bg-emerald-50'
                : 'border-red-200 bg-red-50',
            ].join(' ')}
          >
            <p className="text-sm text-[#697d90]">
              최종 판정
            </p>

            <div className="mt-2 flex items-center gap-3">
              {isNormal ? (
                <CheckCircle2
                  size={34}
                  className="text-[#168b5b]"
                />
              ) : (
                <AlertTriangle
                  size={34}
                  className="text-[#d94b4b]"
                />
              )}

              <strong
                className={[
                  'text-4xl',
                  isNormal
                    ? 'text-[#168b5b]'
                    : 'text-[#d94b4b]',
                ].join(' ')}
              >
                {isNormal ? 'OK' : 'NG'}
              </strong>
            </div>
          </div>

          <h3 className="mt-7 font-bold">
            검사 항목
          </h3>

          <ResultRow
            label="조립 순서"
            result={record.assemblySequenceResult}
          />

          <ResultRow
            label="체결 상태"
            result={record.fasteningQualityResult}
          />

          <h3 className="mt-7 font-bold">
            불량 사유
          </h3>

          <div
            className={[
              'mt-3 rounded-lg border p-4 text-sm',
              isNormal
                ? 'border-emerald-100 bg-emerald-50 text-emerald-700'
                : 'border-red-100 bg-red-50 text-red-700',
            ].join(' ')}
          >
            {isNormal
              ? '검출된 불량이 없습니다.'
              : record.defectReason}
          </div>
        </aside>
      </div>

      <div className="mt-6 grid gap-6 xl:grid-cols-[1fr_1.1fr]">
        <section className="rounded-xl border border-[#d9e4ee] bg-white p-5">
          <h2 className="text-xl font-bold">측정값</h2>

          <div className="mt-5 grid gap-4 sm:grid-cols-3">
            <MeasurementCard
              label="와셔-너트 간격"
              value={
                record.washerNutGap === null
                  ? '측정 불가'
                  : `${record.washerNutGap.toFixed(1)} mm`
              }
              warning={record.washerNutGap === null}
            />

            <MeasurementCard
              label="나사산 노출 길이"
              value={`${record.exposedLength.toFixed(1)} mm`}
            />

            <MeasurementCard
              label="너트 기울기"
              value={`${record.tiltAngle.toFixed(1)}°`}
              warning={record.tiltAngle > 3}
            />
          </div>
        </section>

        <section className="rounded-xl border border-[#d9e4ee] bg-white p-5">
          <h2 className="text-xl font-bold">
            검사 정보
          </h2>

          <div className="mt-5 grid gap-x-8 gap-y-4 sm:grid-cols-2">
            <InformationRow
              label="검사 번호"
              value={`#${record.id}`}
            />

            <InformationRow
              label="검사 시각"
              value={record.inspectedAt}
            />

            <InformationRow
              label="모델"
              value={record.modelName}
            />

            <InformationRow
              label="처리 시간"
              value={`${record.processingTime.toFixed(2)}초`}
            />

            <InformationRow
              label="원본 이미지"
              value={record.fileName}
            />

            <InformationRow
              label="결과 이미지"
              value={`RESULT_${record.fileName}`}
            />
          </div>
        </section>
      </div>
    </div>
  )
}

function ImageCard({
  title,
  children,
}: {
  title: string
  children: React.ReactNode
}) {
  return (
    <article className="rounded-xl border border-[#dce6ef] bg-[#f3f7fb] p-4">
      <h3 className="font-bold">{title}</h3>

      <div className="mt-4 flex min-h-[350px] items-center justify-center overflow-hidden rounded-lg border border-[#bfd0df] bg-[#eaf1f6]">
        {children}
      </div>
    </article>
  )
}

function MockInspectionImage({
  analyzed,
  isDefect,
}: {
  analyzed: boolean
  isDefect: boolean
}) {
  return (
    <svg
      viewBox="0 0 500 350"
      role="img"
      aria-label={
        analyzed ? '분석 결과 이미지' : '원본 이미지'
      }
      className="h-full w-full"
    >
      <rect
        width="500"
        height="350"
        fill="#eaf1f6"
      />

      <line
        x1="80"
        y1="180"
        x2="420"
        y2="180"
        stroke="#8199ad"
        strokeWidth="45"
      />

      <circle
        cx="150"
        cy="180"
        r="72"
        fill="#b7cad9"
        stroke="#6f8ba1"
        strokeWidth="5"
      />

      <rect
        x="270"
        y="115"
        width="105"
        height="130"
        fill="#c6d6e2"
        stroke="#6f8ba1"
        strokeWidth="5"
      />

      {analyzed && (
        <>
          <rect
            x="85"
            y="90"
            width="325"
            height="180"
            fill="none"
            stroke={isDefect ? '#d94b4b' : '#168b5b'}
            strokeWidth="5"
            strokeDasharray="12 8"
          />

          <line
            x1="150"
            y1="180"
            x2="375"
            y2="180"
            stroke="#0075c9"
            strokeWidth="4"
          />

          <text
            x="255"
            y="165"
            textAnchor="middle"
            fontSize="15"
            fontWeight="700"
            fill="#172a3a"
          >
            측정축
          </text>

          <rect
            x="94"
            y="99"
            width="82"
            height="30"
            rx="6"
            fill={isDefect ? '#d94b4b' : '#168b5b'}
          />

          <text
            x="135"
            y="120"
            textAnchor="middle"
            fontSize="14"
            fontWeight="700"
            fill="white"
          >
            {isDefect ? 'DEFECT' : 'NORMAL'}
          </text>
        </>
      )}
    </svg>
  )
}

function ResultRow({
  label,
  result,
}: {
  label: string
  result: InspectionResult
}) {
  const normal = result === 'NORMAL'

  return (
    <div className="flex items-center justify-between border-b border-[#e1e9f0] py-4">
      <span>{label}</span>

      <strong
        className={
          normal
            ? 'text-[#168b5b]'
            : 'text-[#d94b4b]'
        }
      >
        {normal ? '정상' : '불량'}
      </strong>
    </div>
  )
}

function MeasurementCard({
  label,
  value,
  warning = false,
}: {
  label: string
  value: string
  warning?: boolean
}) {
  return (
    <article
      className={[
        'rounded-lg border p-4',
        warning
          ? 'border-red-200 bg-red-50'
          : 'border-[#dce6ef] bg-[#f3f7fb]',
      ].join(' ')}
    >
      <p className="text-sm text-[#697d90]">
        {label}
      </p>

      <p
        className={[
          'mt-2 text-xl font-bold',
          warning
            ? 'text-[#d94b4b]'
            : 'text-[#172a3a]',
        ].join(' ')}
      >
        {value}
      </p>
    </article>
  )
}

function InformationRow({
  label,
  value,
}: {
  label: string
  value: string
}) {
  return (
    <div className="flex min-w-0 justify-between gap-4 border-b border-[#e1e9f0] pb-3">
      <span className="shrink-0 text-sm text-[#697d90]">
        {label}
      </span>

      <strong className="truncate text-sm">
        {value}
      </strong>
    </div>
  )
}

function getFinalResult(
  record: DetailRecord,
): InspectionResult {
  return record.assemblySequenceResult === 'NORMAL' &&
    record.fasteningQualityResult === 'NORMAL'
    ? 'NORMAL'
    : 'DEFECT'
}