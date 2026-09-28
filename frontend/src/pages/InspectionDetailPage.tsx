import {
  AlertCircle,
  AlertTriangle,
  ArrowLeft,
  CheckCircle2,
  Download,
  ImageOff,
  LoaderCircle,
  RefreshCw,
  Trash2,
} from 'lucide-react'
import {
  useEffect,
  useState,
} from 'react'
import {
  useNavigate,
  useParams,
} from 'react-router-dom'
import {
  deleteInspection,
  getInspectionDetail,
  resolveResultImageUrl,
} from '../services/inspectionApi'
import type {
  InspectionHistoryItem,
  ResultStatus,
} from '../types/vision'

export default function InspectionDetailPage() {
  const { inspectionId } = useParams()
  const navigate = useNavigate()

  const [record, setRecord] =
    useState<InspectionHistoryItem | null>(
      null,
    )

  const [isLoading, setIsLoading] =
    useState(true)

  const [loadError, setLoadError] =
    useState('')

  const [retryKey, setRetryKey] =
    useState(0)

  const [
    isDownloading,
    setIsDownloading,
  ] = useState(false)

    const [
    isDeleting,
    setIsDeleting,
  ] = useState(false)

  useEffect(() => {
    const controller = new AbortController()

    async function loadDetail() {
      if (!inspectionId) {
        setLoadError(
          '검사 번호가 지정되지 않았습니다.',
        )
        setIsLoading(false)
        return
      }

      setIsLoading(true)
      setLoadError('')

      try {
        const result =
          await getInspectionDetail(
            inspectionId,
            controller.signal,
          )

        if (!controller.signal.aborted) {
          setRecord(result)
        }
      } catch (error) {
        if (controller.signal.aborted) {
          return
        }

        setRecord(null)
        setLoadError(
          error instanceof Error
            ? error.message
            : '검사 상세 정보를 불러오지 못했습니다.',
        )
      } finally {
        if (!controller.signal.aborted) {
          setIsLoading(false)
        }
      }
    }

    void loadDetail()

    return () => {
      controller.abort()
    }
  }, [inspectionId, retryKey])

    async function deleteCurrentInspection() {
    if (!record || isDeleting) {
      return
    }

    const confirmed = window.confirm(
      `검사 #${formatInspectionId(record.id)} 기록을 삭제하시겠습니까?\n저장된 결과 이미지도 함께 삭제되며 복구할 수 없습니다.`,
    )

    if (!confirmed) {
      return
    }

    setIsDeleting(true)

    try {
      await deleteInspection(record.id)

      window.alert(
        '검사 기록이 삭제되었습니다.',
      )

      navigate('/history', {
        replace: true,
      })
    } catch (error) {
      window.alert(
        error instanceof Error
          ? error.message
          : '검사 기록을 삭제하지 못했습니다.',
      )
    } finally {
      setIsDeleting(false)
    }
  }

  async function downloadEvidenceImage() {
    if (
      !record?.defectImageUrl ||
      isDownloading
    ) {
      return
    }

    setIsDownloading(true)

    try {
      const imageUrl =
        resolveResultImageUrl(
          record.defectImageUrl,
        )

      const response = await fetch(imageUrl)

      if (!response.ok) {
        throw new Error(
          `이미지 다운로드 실패: HTTP ${response.status}`,
        )
      }

      const blob = await response.blob()
      const objectUrl =
        URL.createObjectURL(blob)

      const link =
        document.createElement('a')

      link.href = objectUrl
      link.download =
        `inspection-${record.id}-result.jpg`

      document.body.appendChild(link)
      link.click()
      link.remove()

      URL.revokeObjectURL(objectUrl)
    } catch (error) {
      window.alert(
        error instanceof Error
          ? error.message
          : '이미지를 다운로드하지 못했습니다.',
      )
    } finally {
      setIsDownloading(false)
    }
  }

  if (isLoading) {
    return (
      <PageMessage>
        <LoaderCircle
          size={42}
          className="mx-auto animate-spin text-[#0075c9]"
        />

        <h1 className="mt-5 text-2xl font-bold">
          검사 기록을 불러오는 중입니다.
        </h1>
      </PageMessage>
    )
  }

  if (loadError || !record) {
    return (
      <div className="p-5 sm:p-7 lg:p-9">
        <button
          type="button"
          onClick={() =>
            navigate('/history')
          }
          className="flex items-center gap-2 text-[#0075c9]"
        >
          <ArrowLeft size={18} />
          검사 이력으로 돌아가기
        </button>

        <div className="mt-8 rounded-xl border border-red-200 bg-white p-12 text-center">
          <AlertCircle
            size={42}
            className="mx-auto text-red-500"
          />

          <h1 className="mt-5 text-2xl font-bold">
            검사 기록을 불러오지
            못했습니다.
          </h1>

          <p className="mt-3 text-[#697d90]">
            {loadError}
          </p>

          <button
            type="button"
            onClick={() =>
              setRetryKey(
                (current) => current + 1,
              )
            }
            className="mx-auto mt-6 flex items-center gap-2 rounded-lg bg-[#0075c9] px-5 py-3 font-semibold text-white"
          >
            <RefreshCw size={18} />
            다시 시도
          </button>
        </div>
      </div>
    )
  }

  const resultPresentation =
    getResultPresentation(
      record.overallResult,
    )

  const imageUrl =
    record.defectImageUrl
      ? resolveResultImageUrl(
          record.defectImageUrl,
        )
      : null

  const detectedCounts =
    Object.entries(
      record.metrics.detectedCounts ??
        {},
    )

  const assemblyReasons =
    getAssemblyReasons(record)

  return (
    <div className="p-5 sm:p-7 lg:p-9">
      <header className="flex flex-col justify-between gap-5 xl:flex-row xl:items-start">
        <div>
          <button
            type="button"
            onClick={() =>
              navigate('/history')
            }
            className="flex items-center gap-2 text-sm text-[#697d90] hover:text-[#0075c9]"
          >
            <ArrowLeft size={17} />
            검사 이력 / #
            {formatInspectionId(record.id)}
          </button>

          <h1 className="mt-3 text-3xl font-bold text-[#172a3a]">
            검사 상세
          </h1>

          <p className="mt-2 text-[#697d90]">
            {formatDateTime(
              record.inspectionTime,
            )}
          </p>
        </div>

        <div className="flex flex-wrap gap-3">
                    <button
            type="button"
            onClick={() =>
              void deleteCurrentInspection()
            }
            disabled={isDeleting}
            className="flex items-center gap-2 rounded-lg border border-red-200 bg-white px-5 py-3 font-semibold text-red-600 hover:bg-red-50 disabled:cursor-not-allowed disabled:opacity-50"
          >
            {isDeleting ? (
              <LoaderCircle
                size={18}
                className="animate-spin"
              />
            ) : (
              <Trash2 size={18} />
            )}

            {isDeleting
              ? '삭제 중'
              : '검사 기록 삭제'}
          </button>

          <button
            type="button"
            onClick={() =>
              void downloadEvidenceImage()
            }
            disabled={
              !imageUrl || isDownloading
            }
            className="flex items-center gap-2 rounded-lg border border-[#d9e4ee] bg-white px-5 py-3 font-semibold hover:bg-[#f3f7fb] disabled:cursor-not-allowed disabled:opacity-40"
          >
            {isDownloading ? (
              <LoaderCircle
                size={18}
                className="animate-spin"
              />
            ) : (
              <Download size={18} />
            )}

            결과 이미지 저장
          </button>

          <button
            type="button"
            onClick={() =>
              navigate('/history')
            }
            className="rounded-lg bg-[#0075c9] px-5 py-3 font-semibold text-white hover:bg-[#0065ad]"
          >
            목록으로
          </button>
        </div>
      </header>

      <div className="mt-7 grid gap-6 xl:grid-cols-[minmax(0,1fr)_420px]">
        <section className="rounded-xl border border-[#d9e4ee] bg-white p-5">
          <div>
            <h2 className="text-xl font-bold">
              검사 증거 이미지
            </h2>

            <p className="mt-1 text-sm text-[#697d90]">
              백엔드에서 저장한 분석 완료
              프레임입니다.
            </p>
          </div>

          <div className="mt-5 flex min-h-[520px] items-center justify-center overflow-hidden rounded-xl border border-[#bfd0df] bg-[#0b1f33]">
            {imageUrl ? (
              <img
                src={imageUrl}
                alt={`검사 #${record.id} 결과`}
                className="max-h-[720px] w-full object-contain"
              />
            ) : (
              <div className="px-6 text-center text-slate-300">
                <ImageOff
                  size={46}
                  className="mx-auto"
                />

                <p className="mt-4 font-semibold">
                  저장된 증거 이미지가
                  없습니다.
                </p>

                <p className="mt-2 text-sm text-slate-400">
                  이미지가 저장되지 않은
                  기록이거나 저장 작업 이전의
                  기록입니다.
                </p>
              </div>
            )}
          </div>
        </section>

        <aside className="rounded-xl border border-[#d9e4ee] bg-white p-5">
          <h2 className="text-xl font-bold">
            판정 요약
          </h2>

          <div
            className={[
              'mt-5 rounded-xl border p-5',
              resultPresentation.panelClass,
            ].join(' ')}
          >
            <p className="text-sm text-[#697d90]">
              최종 판정
            </p>

            <div className="mt-2 flex items-center gap-3">
              {record.overallResult ===
              'NORMAL' ? (
                <CheckCircle2
                  size={34}
                  className="text-[#168b5b]"
                />
              ) : (
                <AlertTriangle
                  size={34}
                  className={
                    resultPresentation.iconClass
                  }
                />
              )}

              <strong
                className={[
                  'text-4xl',
                  resultPresentation.textClass,
                ].join(' ')}
              >
                {
                  resultPresentation.shortLabel
                }
              </strong>
            </div>

            <p
              className={[
                'mt-2 text-sm font-semibold',
                resultPresentation.textClass,
              ].join(' ')}
            >
              {resultPresentation.label}
            </p>
          </div>

          <h3 className="mt-7 font-bold">
            검사 항목
          </h3>

          <ResultRow
            label="조립 순서"
            result={
              record.assemblySequenceResult
            }
          />

          <ResultRow
            label="부품 누락"
            result={
              record.missingComponentResult
            }
          />

          <ResultRow
            label="부품 정렬"
            result={record.alignmentResult}
          />

          <ResultRow
            label="체결 상태"
            result={record.fasteningResult}
          />

          <h3 className="mt-7 font-bold">
            판정 사유
          </h3>

          <div
            className={[
              'mt-3 rounded-lg border p-4 text-sm',
              resultPresentation.reasonClass,
            ].join(' ')}
          >
            {getDefectReason(record)}
          </div>
        </aside>
      </div>

      <div className="mt-6 grid gap-6 xl:grid-cols-[1fr_1.1fr]">
        <section className="rounded-xl border border-[#d9e4ee] bg-white p-5">
          <h2 className="text-xl font-bold">
            측정값
          </h2>

          <div className="mt-5 grid gap-4 sm:grid-cols-2 xl:grid-cols-4">
            <MeasurementCard
              label="나사산 측정 길이"
              value={formatCentimeter(
                record.metrics
                  .measuredThreadCm,
              )}
            />

            <MeasurementCard
              label="나사산 기준값"
              value={formatCentimeter(
                record.metrics
                  .threadThresholdCm,
              )}
            />

            <MeasurementCard
              label="검출 객체 수"
              value={`${getDetectionCount(
                record,
              )}개`}
            />

            <MeasurementCard
              label="추론 시간"
              value={formatInferenceTime(
                record,
              )}
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
              value={`#${formatInspectionId(
                record.id,
              )}`}
            />

            <InformationRow
              label="검사 시각"
              value={formatDateTime(
                record.inspectionTime,
              )}
            />

            <InformationRow
              label="모델"
              value={
                record.modelName ??
                record.metrics.modelType ??
                '-'
              }
            />

            <InformationRow
              label="저장 시각"
              value={formatDateTime(
                record.createdAt,
              )}
            />

            <InformationRow
              label="증거 이미지"
              value={
                imageUrl
                  ? '저장됨'
                  : '없음'
              }
            />

            <InformationRow
              label="픽셀당 길이"
              value={formatScale(
                record.metrics
                  .scaleCmPerPx,
              )}
            />
          </div>
        </section>
      </div>

      <div className="mt-6 grid gap-6 xl:grid-cols-2">
        <section className="rounded-xl border border-[#d9e4ee] bg-white p-5">
          <h2 className="text-xl font-bold">
            검출 객체 구성
          </h2>

          {detectedCounts.length > 0 ? (
            <div className="mt-5 grid gap-3 sm:grid-cols-2">
              {detectedCounts.map(
                ([name, count]) => (
                  <div
                    key={name}
                    className="flex items-center justify-between rounded-lg border border-[#dce6ef] bg-[#f3f7fb] px-4 py-3"
                  >
                    <span className="text-sm text-[#697d90]">
                      {getClassLabel(name)}
                    </span>

                    <strong>
                      {count}개
                    </strong>
                  </div>
                ),
              )}
            </div>
          ) : (
            <EmptyInformation>
              저장된 객체별 검출 수가
              없습니다.
            </EmptyInformation>
          )}
        </section>

        <section className="rounded-xl border border-[#d9e4ee] bg-white p-5">
          <h2 className="text-xl font-bold">
            조립 판정 상세
          </h2>

          {assemblyReasons.length > 0 ? (
            <ul className="mt-5 space-y-3">
              {assemblyReasons.map(
                (reason, index) => (
                  <li
                    key={`${reason}-${index}`}
                    className="flex items-start gap-3 rounded-lg border border-red-100 bg-red-50 p-4 text-sm text-red-700"
                  >
                    <AlertTriangle
                      size={18}
                      className="mt-0.5 shrink-0"
                    />

                    {getReasonLabel(reason)}
                  </li>
                ),
              )}
            </ul>
          ) : (
            <EmptyInformation>
              저장된 세부 판정 사유가
              없습니다.
            </EmptyInformation>
          )}
        </section>
      </div>
    </div>
  )
}

function PageMessage({
  children,
}: {
  children: React.ReactNode
}) {
  return (
    <div className="p-5 sm:p-7 lg:p-9">
      <div className="rounded-xl border border-[#d9e4ee] bg-white p-12 text-center">
        {children}
      </div>
    </div>
  )
}

function ResultRow({
  label,
  result,
}: {
  label: string
  result: ResultStatus
}) {
  const presentation =
    getResultPresentation(result)

  return (
    <div className="flex items-center justify-between border-b border-[#e1e9f0] py-4">
      <span>{label}</span>

      <strong
        className={
          presentation.textClass
        }
      >
        {presentation.label}
      </strong>
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
    <article className="rounded-lg border border-[#dce6ef] bg-[#f3f7fb] p-4">
      <p className="text-sm text-[#697d90]">
        {label}
      </p>

      <p className="mt-2 text-xl font-bold text-[#172a3a]">
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

      <strong
        className="truncate text-sm"
        title={value}
      >
        {value}
      </strong>
    </div>
  )
}

function EmptyInformation({
  children,
}: {
  children: React.ReactNode
}) {
  return (
    <div className="mt-5 rounded-lg border border-dashed border-[#bfd0df] bg-[#f8fafc] p-8 text-center text-sm text-[#697d90]">
      {children}
    </div>
  )
}

function getResultPresentation(
  result: ResultStatus,
) {
  if (result === 'NORMAL') {
    return {
      label: '정상',
      shortLabel: 'OK',
      textClass: 'text-[#168b5b]',
      iconClass: 'text-[#168b5b]',
      panelClass:
        'border-emerald-200 bg-emerald-50',
      reasonClass:
        'border-emerald-100 bg-emerald-50 text-emerald-700',
    }
  }

  if (result === 'DEFECT') {
    return {
      label: '불량',
      shortLabel: 'NG',
      textClass: 'text-[#d94b4b]',
      iconClass: 'text-[#d94b4b]',
      panelClass:
        'border-red-200 bg-red-50',
      reasonClass:
        'border-red-100 bg-red-50 text-red-700',
    }
  }

  return {
    label: '판정 전',
    shortLabel: '대기',
    textClass: 'text-[#697d90]',
    iconClass: 'text-amber-500',
    panelClass:
      'border-amber-200 bg-amber-50',
    reasonClass:
      'border-amber-100 bg-amber-50 text-amber-700',
  }
}

function getAssemblyReasons(
  record: InspectionHistoryItem,
): string[] {
  const reasons =
    record.metrics.assemblyReasons

  if (!Array.isArray(reasons)) {
    return []
  }

  return reasons.filter(
    (reason): reason is string =>
      typeof reason === 'string',
  )
}

function getDefectReason(
  record: InspectionHistoryItem,
) {
  if (record.overallResult === 'NORMAL') {
    return '검출된 불량이 없습니다.'
  }

  if (
    record.overallResult ===
    'NOT_EVALUATED'
  ) {
    return '검사 결과가 아직 평가되지 않았습니다.'
  }

  const reasons =
    getAssemblyReasons(record)

  if (reasons.length > 0) {
    return reasons
      .map(getReasonLabel)
      .join(', ')
  }

  if (
    record.fasteningResult === 'DEFECT'
  ) {
    return '체결 상태가 검사 기준을 충족하지 않습니다.'
  }

  if (
    record.alignmentResult === 'DEFECT'
  ) {
    return '부품 정렬 상태가 검사 기준을 충족하지 않습니다.'
  }

  if (
    record.missingComponentResult ===
    'DEFECT'
  ) {
    return '필수 부품이 누락되었거나 조립 상태가 올바르지 않습니다.'
  }

  return '검사 기준을 충족하지 않습니다.'
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

function getClassLabel(name: string) {
  const labels: Record<string, string> = {
    bolt: '볼트',
    washer: '와셔',
    nut: '너트',
    thread: '나사산',
  }

  return labels[name.toLowerCase()] ?? name
}

function getDetectionCount(
  record: InspectionHistoryItem,
) {
  return (
    record.detectedInstanceCount ??
    record.metrics.detectedInstanceCount ??
    0
  )
}

function formatInferenceTime(
  record: InspectionHistoryItem,
) {
  const value =
    record.inferenceTimeMs ??
    record.metrics.inferenceTimeMs

  if (value == null) {
    return '-'
  }

  return `${value.toFixed(1)} ms`
}

function formatCentimeter(
  value?: number,
) {
  if (value == null) {
    return '-'
  }

  return `${value.toFixed(2)} cm`
}

function formatScale(
  value?: number,
) {
  if (value == null) {
    return '-'
  }

  return `${value.toFixed(5)} cm/px`
}

function formatInspectionId(id: number) {
  return String(id).padStart(6, '0')
}

function formatDateTime(value: string) {
  const date = new Date(value)

  if (Number.isNaN(date.getTime())) {
    return value
  }

  return new Intl.DateTimeFormat(
    'ko-KR',
    {
      year: 'numeric',
      month: '2-digit',
      day: '2-digit',
      hour: '2-digit',
      minute: '2-digit',
      second: '2-digit',
      hour12: false,
    },
  ).format(date)
}