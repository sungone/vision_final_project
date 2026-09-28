import {
  AlertCircle,
  Download,
  LoaderCircle,
  RefreshCw,
  RotateCcw,
  Search,
  Trash2,
} from 'lucide-react'
import {
  useEffect,
  useMemo,
  useState,
} from 'react'
import type { ReactNode } from 'react'
import { useNavigate } from 'react-router-dom'
import {
  deleteInspection,
  getInspectionHistory,
} from '../services/inspectionApi'
import type {
  InspectionHistoryItem,
  ResultStatus,
} from '../types/vision'

type ResultFilter = 'ALL' | ResultStatus

export default function HistoryPage() {
  const navigate = useNavigate()

  const [records, setRecords] = useState<
    InspectionHistoryItem[]
  >([])

  const [totalElements, setTotalElements] =
    useState(0)

  const [dateFilter, setDateFilter] =
    useState('')

  const [resultFilter, setResultFilter] =
    useState<ResultFilter>('ALL')

  const [searchText, setSearchText] =
    useState('')

  const [isLoading, setIsLoading] =
    useState(true)

  const [loadError, setLoadError] =
    useState('')

  const [refreshKey, setRefreshKey] =
    useState(0)

  const [lastLoadedAt, setLastLoadedAt] =
    useState<Date | null>(null)

  const [selectedIds, setSelectedIds] =
    useState<Set<number>>(
      () => new Set(),
  )

  const [
    isDeletingSelected,
    setIsDeletingSelected,
  ] = useState(false)

  useEffect(() => {
    const controller = new AbortController()

    async function loadHistory() {
      setIsLoading(true)
      setLoadError('')

      try {
        const response =
          await getInspectionHistory(
            0,
            100,
            controller.signal,
          )

        if (controller.signal.aborted) {
          return
        }

        setRecords(response.content)
        setTotalElements(response.totalElements)
        setSelectedIds(new Set())
        setLastLoadedAt(new Date())
      } catch (error) {
        if (controller.signal.aborted) {
          return
        }

        setLoadError(
          error instanceof Error
            ? error.message
            : '검사 이력을 불러오지 못했습니다.',
        )
      } finally {
        if (!controller.signal.aborted) {
          setIsLoading(false)
        }
      }
    }

    void loadHistory()

    return () => {
      controller.abort()
    }
  }, [refreshKey])

  const filteredRecords = useMemo(() => {
    const normalizedSearch = searchText
      .trim()
      .toLowerCase()

    return records.filter((record) => {
      const matchesDate =
        !dateFilter ||
        getDateInputValue(
          record.inspectionTime,
        ) === dateFilter

      const matchesResult =
        resultFilter === 'ALL' ||
        record.overallResult === resultFilter

      const reason =
        getDefectReason(record).toLowerCase()

      const matchesSearch =
        !normalizedSearch ||
        String(record.id).includes(
          normalizedSearch,
        ) ||
        (record.modelName ?? '')
          .toLowerCase()
          .includes(normalizedSearch) ||
        reason.includes(normalizedSearch)

      return (
        matchesDate &&
        matchesResult &&
        matchesSearch
      )
    })
  }, [
    records,
    dateFilter,
    resultFilter,
    searchText,
  ])

  const normalCount = filteredRecords.filter(
    (record) =>
      record.overallResult === 'NORMAL',
  ).length

  const defectCount = filteredRecords.filter(
    (record) =>
      record.overallResult === 'DEFECT',
  ).length

  const notEvaluatedCount =
    filteredRecords.filter(
      (record) =>
        record.overallResult ===
        'NOT_EVALUATED',
    ).length

    const visibleIds = filteredRecords.map(
    (record) => record.id,
  )

  const selectedVisibleCount =
    visibleIds.filter((id) =>
      selectedIds.has(id),
    ).length

  const allVisibleSelected =
    visibleIds.length > 0 &&
    selectedVisibleCount ===
      visibleIds.length

  function resetFilters() {
    setDateFilter('')
    setResultFilter('ALL')
    setSearchText('')
  }

  function refreshHistory() {
    setRefreshKey((current) => current + 1)
  }

    function toggleVisibleRecords() {
    setSelectedIds((current) => {
      const next = new Set(current)

      if (allVisibleSelected) {
        visibleIds.forEach((id) =>
          next.delete(id),
        )
      } else {
        visibleIds.forEach((id) =>
          next.add(id),
        )
      }

      return next
    })
  }

  function toggleRecordSelection(
    inspectionId: number,
  ) {
    setSelectedIds((current) => {
      const next = new Set(current)

      if (next.has(inspectionId)) {
        next.delete(inspectionId)
      } else {
        next.add(inspectionId)
      }

      return next
    })
  }

  async function deleteSelectedRecords() {
    const inspectionIds =
      Array.from(selectedIds)

    if (
      inspectionIds.length === 0 ||
      isDeletingSelected
    ) {
      return
    }

    const confirmed = window.confirm(
      `선택한 검사 기록 ${inspectionIds.length}건을 삭제하시겠습니까?\n저장된 결과 이미지도 함께 삭제되며 복구할 수 없습니다.`,
    )

    if (!confirmed) {
      return
    }

    setIsDeletingSelected(true)

    const deletedIds: number[] = []

    try {
      for (const inspectionId of inspectionIds) {
        try {
          await deleteInspection(inspectionId)
          deletedIds.push(inspectionId)
        } catch {
          // 실패한 기록은 목록에 그대로 유지
        }
      }

      if (deletedIds.length > 0) {
        const deletedIdSet =
          new Set(deletedIds)

        setRecords((current) =>
          current.filter(
            (record) =>
              !deletedIdSet.has(record.id),
          ),
        )

        setTotalElements((current) =>
          Math.max(
            0,
            current - deletedIds.length,
          ),
        )

        setSelectedIds((current) => {
          const next = new Set(current)

          deletedIds.forEach((id) =>
            next.delete(id),
          )

          return next
        })
      }

      const failedCount =
        inspectionIds.length -
        deletedIds.length

      if (failedCount > 0) {
        window.alert(
          `${deletedIds.length}건을 삭제했습니다.\n${failedCount}건은 삭제하지 못했습니다.`,
        )
      } else {
        window.alert(
          `${deletedIds.length}건을 삭제했습니다.`,
        )
      }
    } finally {
      setIsDeletingSelected(false)
    }
  }

  function downloadCsv() {
    if (filteredRecords.length === 0) {
      window.alert(
        '다운로드할 검사 기록이 없습니다.',
      )
      return
    }

    const headers = [
      '검사 번호',
      '검사 시각',
      '모델',
      '검출 객체 수',
      '조립 순서',
      '체결 상태',
      '최종 판정',
      '불량 사유',
      '추론 시간(ms)',
    ]

    const rows = filteredRecords.map(
      (record) => [
        record.id,
        formatDateTime(
          record.inspectionTime,
        ),
        record.modelName ?? '-',
        getDetectionCount(record),
        getResultLabel(
          record.assemblySequenceResult,
        ),
        getResultLabel(
          record.fasteningQualityResult,
        ),
        getResultLabel(
          record.overallResult,
        ),
        getDefectReason(record),
        record.inferenceTimeMs ?? '-',
      ],
    )

    const csv = [headers, ...rows]
      .map((row) =>
        row
          .map((value) => escapeCsv(value))
          .join(','),
      )
      .join('\n')

    const blob = new Blob(
      [`\uFEFF${csv}`],
      {
        type: 'text/csv;charset=utf-8',
      },
    )

    const url = URL.createObjectURL(blob)
    const link =
      document.createElement('a')

    link.href = url
    link.download =
      `inspection-history-${dateFilter || 'all'}.csv`

    document.body.appendChild(link)
    link.click()
    link.remove()

    URL.revokeObjectURL(url)
  }

  return (
    <div className="p-5 sm:p-7 lg:p-9">
      <header className="flex flex-col justify-between gap-4 sm:flex-row sm:items-start">
        <div>
          <h1 className="text-3xl font-bold text-[#172a3a]">
            검사 이력
          </h1>

          <p className="mt-2 text-[#697d90]">
            PostgreSQL에 저장된 검사 결과를
            조회합니다.
          </p>

          {lastLoadedAt && (
            <p className="mt-2 text-xs text-[#8a9aaa]">
              마지막 갱신:{' '}
              {lastLoadedAt.toLocaleTimeString(
                'ko-KR',
              )}
            </p>
          )}
        </div>

        <div className="flex flex-wrap gap-3">
                    <button
            type="button"
            onClick={() =>
              void deleteSelectedRecords()
            }
            disabled={
              selectedIds.size === 0 ||
              isLoading ||
              isDeletingSelected
            }
            className="flex items-center gap-2 rounded-lg border border-red-200 bg-white px-5 py-3 font-semibold text-red-600 hover:bg-red-50 disabled:cursor-not-allowed disabled:opacity-40"
          >
            {isDeletingSelected ? (
              <LoaderCircle
                size={18}
                className="animate-spin"
              />
            ) : (
              <Trash2 size={18} />
            )}

            {isDeletingSelected
              ? '삭제 중'
              : `선택 삭제 (${selectedIds.size})`}
          </button>

          <button
            type="button"
            onClick={refreshHistory}
            disabled={isLoading}
            className="flex items-center gap-2 rounded-lg border border-[#d9e4ee] bg-white px-5 py-3 font-semibold hover:bg-[#f3f7fb] disabled:cursor-not-allowed disabled:opacity-50"
          >
            <RefreshCw
              size={18}
              className={
                isLoading
                  ? 'animate-spin'
                  : ''
              }
            />
            새로고침
          </button>

          <button
            type="button"
            onClick={downloadCsv}
            disabled={
              isLoading ||
              filteredRecords.length === 0
            }
            className="flex items-center gap-2 rounded-lg border border-[#d9e4ee] bg-white px-5 py-3 font-semibold hover:bg-[#f3f7fb] disabled:cursor-not-allowed disabled:opacity-50"
          >
            <Download size={18} />
            CSV 다운로드
          </button>
        </div>
      </header>

      {loadError && (
        <div className="mt-6 flex flex-col gap-4 rounded-xl border border-red-200 bg-red-50 p-5 text-red-700 sm:flex-row sm:items-center sm:justify-between">
          <div className="flex items-start gap-3">
            <AlertCircle
              size={21}
              className="mt-0.5 shrink-0"
            />

            <div>
              <p className="font-bold">
                검사 이력을 불러오지
                못했습니다.
              </p>

              <p className="mt-1 text-sm">
                {loadError}
              </p>

              <p className="mt-1 text-sm">
                Flask 서버와 PostgreSQL 연결
                상태를 확인해주세요.
              </p>
            </div>
          </div>

          <button
            type="button"
            onClick={refreshHistory}
            className="shrink-0 rounded-lg border border-red-300 bg-white px-4 py-2 font-semibold"
          >
            다시 시도
          </button>
        </div>
      )}

      <section className="mt-7 rounded-xl border border-[#d9e4ee] bg-white p-5">
        <div className="grid gap-4 md:grid-cols-2 xl:grid-cols-[200px_180px_minmax(260px,1fr)_110px_100px]">
          <FilterField label="검사 날짜">
            <input
              type="date"
              value={dateFilter}
              onChange={(event) =>
                setDateFilter(
                  event.target.value,
                )
              }
              className="h-11 w-full rounded-lg border border-[#d9e4ee] bg-[#f8fafc] px-3 outline-none focus:border-[#0075c9]"
            />
          </FilterField>

          <FilterField label="최종 판정">
            <select
              value={resultFilter}
              onChange={(event) =>
                setResultFilter(
                  event.target
                    .value as ResultFilter,
                )
              }
              className="h-11 w-full rounded-lg border border-[#d9e4ee] bg-[#f8fafc] px-3 outline-none focus:border-[#0075c9]"
            >
              <option value="ALL">
                전체
              </option>

              <option value="NORMAL">
                정상
              </option>

              <option value="DEFECT">
                불량
              </option>

              <option value="NOT_EVALUATED">
                판정 전
              </option>
            </select>
          </FilterField>

          <FilterField label="검사번호·모델·불량 사유">
            <div className="relative">
              <Search
                size={18}
                className="absolute left-3 top-1/2 -translate-y-1/2 text-[#697d90]"
              />

              <input
                type="search"
                value={searchText}
                onChange={(event) =>
                  setSearchText(
                    event.target.value,
                  )
                }
                placeholder="검색어를 입력하세요"
                className="h-11 w-full rounded-lg border border-[#d9e4ee] bg-[#f8fafc] pl-10 pr-3 outline-none focus:border-[#0075c9]"
              />
            </div>
          </FilterField>

          <div className="flex items-end">
            <button
              type="button"
              onClick={refreshHistory}
              disabled={isLoading}
              className="h-11 w-full rounded-lg bg-[#0075c9] px-4 font-semibold text-white hover:bg-[#0065ad] disabled:cursor-not-allowed disabled:opacity-50"
            >
              조회
            </button>
          </div>

          <div className="flex items-end">
            <button
              type="button"
              onClick={resetFilters}
              className="flex h-11 w-full items-center justify-center gap-2 rounded-lg text-sm text-[#697d90] hover:bg-[#f3f7fb]"
            >
              <RotateCcw size={16} />
              초기화
            </button>
          </div>
        </div>
      </section>

      <section className="mt-5 grid gap-4 sm:grid-cols-2 xl:grid-cols-4">
        <SummaryCard
          label="조회 결과"
          value={`${filteredRecords.length}건`}
          color="text-[#172a3a]"
        />

        <SummaryCard
          label="정상"
          value={`${normalCount}건`}
          color="text-[#168b5b]"
        />

        <SummaryCard
          label="불량"
          value={`${defectCount}건`}
          color="text-[#d94b4b]"
        />

        <SummaryCard
          label="판정 전"
          value={`${notEvaluatedCount}건`}
          color="text-[#697d90]"
        />
      </section>

      <section className="mt-5 overflow-hidden rounded-xl border border-[#d9e4ee] bg-white">
        <div className="flex flex-col justify-between gap-2 border-b border-[#e1e9f0] p-4 text-sm text-[#697d90] sm:flex-row sm:items-center">
          <span>
            DB 전체 기록: {totalElements}건
          </span>

          <span>
            현재 최근 {records.length}건을
            표시하고 있습니다.
          </span>
        </div>

        <div className="overflow-x-auto">
          <table className="w-full min-w-[1180px] border-collapse text-left">
            <thead className="bg-[#e8f0f7] text-sm text-[#3c5368]">
              <tr>
                <th className="w-14 px-4 py-4 text-center">
                  <input
                    type="checkbox"
                    checked={allVisibleSelected}
                    onChange={
                      toggleVisibleRecords
                    }
                    disabled={
                      isLoading ||
                      filteredRecords.length ===
                        0
                    }
                    aria-label="현재 조회 결과 전체 선택"
                    className="h-4 w-4 accent-[#0075c9]"
                  />
                </th>

                <th className="px-5 py-4">
                  검사 번호
                </th>

                <th className="px-4 py-4">
                  검사 시각
                </th>

                <th className="px-4 py-4">
                  모델
                </th>

                <th className="px-4 py-4">
                  검출 수
                </th>

                <th className="px-4 py-4">
                  조립 순서
                </th>

                <th className="px-4 py-4">
                  체결 상태
                </th>

                <th className="px-4 py-4">
                  최종 판정
                </th>

                <th className="px-4 py-4">
                  불량 사유
                </th>

                <th className="px-4 py-4">
                  관리
                </th>
              </tr>
            </thead>

                        <tbody className="divide-y divide-[#e1e9f0] text-sm">
              {isLoading && (
                <tr>
                  <td
                    colSpan={10}
                    className="px-5 py-16 text-center"
                  >
                    <LoaderCircle
                      size={30}
                      className="mx-auto animate-spin text-[#0075c9]"
                    />

                    <p className="mt-3 text-[#697d90]">
                      검사 이력을 불러오는
                      중입니다.
                    </p>
                  </td>
                </tr>
              )}

              {!isLoading &&
                !loadError &&
                filteredRecords.map(
                  (record) => (
                    <tr
                      key={record.id}
                      className="hover:bg-[#f8fafc]"
                    >
                      <td className="px-4 py-4 text-center">
                        <input
                          type="checkbox"
                          checked={selectedIds.has(
                            record.id,
                          )}
                          onChange={() =>
                            toggleRecordSelection(
                              record.id,
                            )
                          }
                          aria-label={`검사 #${formatInspectionId(record.id)} 선택`}
                          className="h-4 w-4 accent-[#0075c9]"
                        />
                      </td>

                      <td className="px-5 py-4 font-semibold">
                        #{formatInspectionId(
                          record.id,
                        )}
                      </td>

                      <td className="px-4 py-4 text-[#697d90]">
                        {formatDateTime(
                          record.inspectionTime,
                        )}
                      </td>

                      <td className="px-4 py-4">
                        {record.modelName ??
                          record.metrics
                            .modelType ??
                          '-'}
                      </td>

                      <td className="px-4 py-4">
                        {getDetectionCount(
                          record,
                        )}
                      </td>

                      <td className="px-4 py-4">
                        <ResultText
                          result={
                            record.assemblySequenceResult
                          }
                        />
                      </td>

                      <td className="px-4 py-4">
                        <ResultText
                          result={
                            record.fasteningQualityResult
                          }
                        />
                      </td>

                      <td className="px-4 py-4">
                        <ResultBadge
                          result={
                            record.overallResult
                          }
                        />
                      </td>

                      <td className="max-w-[260px] px-4 py-4">
                        <span
                          className="block truncate"
                          title={getDefectReason(
                            record,
                          )}
                        >
                          {getDefectReason(
                            record,
                          )}
                        </span>
                      </td>

                      <td className="px-4 py-4">
                        <button
                          type="button"
                          onClick={() =>
                            navigate(
                              `/history/${record.id}`,
                            )
                          }
                          className="font-semibold text-[#0075c9] hover:underline"
                        >
                          상세 ›
                        </button>
                      </td>
                    </tr>
                  ),
                )}

              {!isLoading &&
                !loadError &&
                filteredRecords.length ===
                  0 && (
                  <tr>
                    <td
                      colSpan={10}
                      className="px-5 py-16 text-center text-[#697d90]"
                    >
                      조건에 맞는 검사 기록이
                      없습니다.
                    </td>
                  </tr>
                )}
            </tbody>
          </table>
        </div>

        <div className="flex items-center justify-between border-t border-[#e1e9f0] px-5 py-4 text-sm text-[#697d90]">
          <span>
            필터 결과{' '}
            {filteredRecords.length}건
          </span>

          {totalElements > records.length && (
            <span className="text-amber-600">
              전체 {totalElements}건 중 최근{' '}
              {records.length}건 표시
            </span>
          )}
        </div>
      </section>
    </div>
  )
}

function FilterField({
  label,
  children,
}: {
  label: string
  children: ReactNode
}) {
  return (
    <label>
      <span className="mb-2 block text-sm text-[#697d90]">
        {label}
      </span>

      {children}
    </label>
  )
}

function SummaryCard({
  label,
  value,
  color,
}: {
  label: string
  value: string
  color: string
}) {
  return (
    <article className="rounded-xl border border-[#d9e4ee] bg-white p-5">
      <p className="text-sm text-[#697d90]">
        {label}
      </p>

      <p
        className={`mt-2 text-3xl font-bold ${color}`}
      >
        {value}
      </p>
    </article>
  )
}

function ResultText({
  result,
}: {
  result: ResultStatus
}) {
  const presentation =
    getResultPresentation(result)

  return (
    <span
      className={`font-semibold ${presentation.textClass}`}
    >
      {presentation.label}
    </span>
  )
}

function ResultBadge({
  result,
}: {
  result: ResultStatus
}) {
  const presentation =
    getResultPresentation(result)

  return (
    <span
      className={[
        'inline-flex rounded-full px-3 py-1 text-xs font-bold',
        presentation.badgeClass,
      ].join(' ')}
    >
      {presentation.shortLabel}
    </span>
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
      badgeClass:
        'bg-emerald-100 text-emerald-700',
    }
  }

  if (result === 'DEFECT') {
    return {
      label: '불량',
      shortLabel: 'NG',
      textClass: 'text-[#d94b4b]',
      badgeClass:
        'bg-red-100 text-red-700',
    }
  }

  return {
    label: '판정 전',
    shortLabel: '대기',
    textClass: 'text-[#697d90]',
    badgeClass:
      'bg-slate-100 text-slate-600',
  }
}

function getResultLabel(
  result: ResultStatus,
) {
  return getResultPresentation(result).label
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
    return '-'
  }

  if (
    record.overallResult ===
    'NOT_EVALUATED'
  ) {
    return '판정 대기'
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
    return '체결 상태 불량'
  }

  if (
    record.alignmentResult === 'DEFECT'
  ) {
    return '부품 정렬 불량'
  }

  if (
    record.missingComponentResult ===
    'DEFECT'
  ) {
    return '필수 부품 누락'
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

function getDateInputValue(value: string) {
  const date = new Date(value)

  if (Number.isNaN(date.getTime())) {
    return ''
  }

  const year = date.getFullYear()
  const month = String(
    date.getMonth() + 1,
  ).padStart(2, '0')

  const day = String(
    date.getDate(),
  ).padStart(2, '0')

  return `${year}-${month}-${day}`
}

function escapeCsv(value: unknown) {
  return `"${String(value).replaceAll(
    '"',
    '""',
  )}"`
}