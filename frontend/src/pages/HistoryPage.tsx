import {
  Download,
  RotateCcw,
  Search,
  Trash2,
} from 'lucide-react'
import { useMemo, useState } from 'react'
import type { InspectionResult } from '../types/inspection'
import { useNavigate } from 'react-router-dom'

type InspectionRecord = {
  id: string
  inspectedAt: string
  fileName: string
  assemblySequenceResult: InspectionResult
  fasteningQualityResult: InspectionResult
  exposedLength: number
  tiltAngle: number
  defectReason: string
}

type ResultFilter = 'ALL' | InspectionResult

const initialRecords: InspectionRecord[] = [
  {
    id: '001248',
    inspectedAt: '2026-09-22 10:42',
    fileName: 'IMG_0142.jpg',
    assemblySequenceResult: 'DEFECT',
    fasteningQualityResult: 'NORMAL',
    exposedLength: 12.8,
    tiltAngle: 1.4,
    defectReason: '와셔 누락',
  },
  {
    id: '001247',
    inspectedAt: '2026-09-22 10:40',
    fileName: 'IMG_0141.jpg',
    assemblySequenceResult: 'NORMAL',
    fasteningQualityResult: 'NORMAL',
    exposedLength: 12.1,
    tiltAngle: 0.8,
    defectReason: '-',
  },
  {
    id: '001246',
    inspectedAt: '2026-09-22 10:38',
    fileName: 'IMG_0140.jpg',
    assemblySequenceResult: 'NORMAL',
    fasteningQualityResult: 'DEFECT',
    exposedLength: 16.9,
    tiltAngle: 4.6,
    defectReason: '너트 기울어짐',
  },
  {
    id: '001245',
    inspectedAt: '2026-09-22 10:36',
    fileName: 'IMG_0139.jpg',
    assemblySequenceResult: 'NORMAL',
    fasteningQualityResult: 'NORMAL',
    exposedLength: 11.9,
    tiltAngle: 1,
    defectReason: '-',
  },
  {
    id: '001244',
    inspectedAt: '2026-09-22 10:34',
    fileName: 'IMG_0138.jpg',
    assemblySequenceResult: 'NORMAL',
    fasteningQualityResult: 'NORMAL',
    exposedLength: 12.3,
    tiltAngle: 0.9,
    defectReason: '-',
  },
  {
    id: '001243',
    inspectedAt: '2026-09-22 10:31',
    fileName: 'IMG_0135.jpg',
    assemblySequenceResult: 'NORMAL',
    fasteningQualityResult: 'DEFECT',
    exposedLength: 15.7,
    tiltAngle: 5.1,
    defectReason: '체결 위치 오류',
  },
  {
    id: '001242',
    inspectedAt: '2026-09-22 10:28',
    fileName: 'IMG_0132.jpg',
    assemblySequenceResult: 'NORMAL',
    fasteningQualityResult: 'NORMAL',
    exposedLength: 12.5,
    tiltAngle: 1.1,
    defectReason: '-',
  },
]

export default function HistoryPage() {
    const navigate = useNavigate()

  const [records, setRecords] =
    useState<InspectionRecord[]>(initialRecords)

  const [dateFilter, setDateFilter] =
    useState('2026-09-22')

  const [resultFilter, setResultFilter] =
    useState<ResultFilter>('ALL')

  const [searchText, setSearchText] = useState('')

  const [selectedIds, setSelectedIds] = useState<
    Set<string>
  >(new Set())

  const filteredRecords = useMemo(() => {
    const normalizedSearch = searchText
      .trim()
      .toLowerCase()

    return records.filter((record) => {
      const matchesDate =
        !dateFilter ||
        record.inspectedAt.startsWith(dateFilter)

      const finalResult = getFinalResult(record)

      const matchesResult =
        resultFilter === 'ALL' ||
        finalResult === resultFilter

      const matchesSearch =
        !normalizedSearch ||
        record.fileName
          .toLowerCase()
          .includes(normalizedSearch) ||
        record.id.includes(normalizedSearch) ||
        record.defectReason
          .toLowerCase()
          .includes(normalizedSearch)

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
      getFinalResult(record) === 'NORMAL',
  ).length

  const defectCount =
    filteredRecords.length - normalCount

  const allFilteredSelected =
    filteredRecords.length > 0 &&
    filteredRecords.every((record) =>
      selectedIds.has(record.id),
    )

  function resetFilters() {
    setDateFilter('2026-09-22')
    setResultFilter('ALL')
    setSearchText('')
  }

  function toggleRecord(id: string) {
    setSelectedIds((currentIds) => {
      const nextIds = new Set(currentIds)

      if (nextIds.has(id)) {
        nextIds.delete(id)
      } else {
        nextIds.add(id)
      }

      return nextIds
    })
  }

  function toggleAllFiltered() {
    setSelectedIds((currentIds) => {
      const nextIds = new Set(currentIds)

      if (allFilteredSelected) {
        filteredRecords.forEach((record) => {
          nextIds.delete(record.id)
        })
      } else {
        filteredRecords.forEach((record) => {
          nextIds.add(record.id)
        })
      }

      return nextIds
    })
  }

  function deleteSelected() {
    if (selectedIds.size === 0) {
      return
    }

    const confirmed = window.confirm(
      `선택한 ${selectedIds.size}개의 검사 기록을 삭제하시겠습니까?`,
    )

    if (!confirmed) {
      return
    }

    setRecords((currentRecords) =>
      currentRecords.filter(
        (record) => !selectedIds.has(record.id),
      ),
    )

    setSelectedIds(new Set())
  }

  function downloadCsv() {
    if (filteredRecords.length === 0) {
      window.alert('다운로드할 검사 기록이 없습니다.')
      return
    }

    const headers = [
      '검사 번호',
      '검사 시각',
      '파일명',
      '조립 순서',
      '체결 상태',
      '노출 길이(mm)',
      '기울기(도)',
      '최종 판정',
      '불량 사유',
    ]

    const rows = filteredRecords.map((record) => [
      record.id,
      record.inspectedAt,
      record.fileName,
      record.assemblySequenceResult,
      record.fasteningQualityResult,
      record.exposedLength,
      record.tiltAngle,
      getFinalResult(record),
      record.defectReason,
    ])

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
    const link = document.createElement('a')

    link.href = url
    link.download = `inspection-history-${dateFilter || 'all'}.csv`

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
            저장된 검사 결과를 조회하고 필요한 기록을
            관리합니다.
          </p>
        </div>

        <button
          type="button"
          onClick={downloadCsv}
          className="flex w-fit items-center gap-2 rounded-lg border border-[#d9e4ee] bg-white px-5 py-3 font-semibold hover:bg-[#f3f7fb]"
        >
          <Download size={18} />
          CSV 다운로드
        </button>
      </header>

      <section className="mt-7 rounded-xl border border-[#d9e4ee] bg-white p-5">
        <div className="grid gap-4 md:grid-cols-2 xl:grid-cols-[200px_160px_minmax(260px,1fr)_110px_100px]">
          <FilterField label="검사 날짜">
            <input
              type="date"
              value={dateFilter}
              onChange={(event) =>
                setDateFilter(event.target.value)
              }
              className="h-11 w-full rounded-lg border border-[#d9e4ee] bg-[#f8fafc] px-3 outline-none focus:border-[#0075c9]"
            />
          </FilterField>

          <FilterField label="최종 판정">
            <select
              value={resultFilter}
              onChange={(event) =>
                setResultFilter(
                  event.target.value as ResultFilter,
                )
              }
              className="h-11 w-full rounded-lg border border-[#d9e4ee] bg-[#f8fafc] px-3 outline-none focus:border-[#0075c9]"
            >
              <option value="ALL">전체</option>
              <option value="NORMAL">정상</option>
              <option value="DEFECT">불량</option>
            </select>
          </FilterField>

          <FilterField label="파일명·검사번호·불량 사유">
            <div className="relative">
              <Search
                size={18}
                className="absolute left-3 top-1/2 -translate-y-1/2 text-[#697d90]"
              />

              <input
                type="search"
                value={searchText}
                onChange={(event) =>
                  setSearchText(event.target.value)
                }
                placeholder="검색어를 입력하세요"
                className="h-11 w-full rounded-lg border border-[#d9e4ee] bg-[#f8fafc] pl-10 pr-3 outline-none focus:border-[#0075c9]"
              />
            </div>
          </FilterField>

          <div className="flex items-end">
            <button
              type="button"
              className="h-11 w-full rounded-lg bg-[#0075c9] px-4 font-semibold text-white hover:bg-[#0065ad]"
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

      <section className="mt-5 grid gap-4 sm:grid-cols-3">
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
      </section>

      <section className="mt-5 overflow-hidden rounded-xl border border-[#d9e4ee] bg-white">
        <div className="flex flex-col justify-between gap-3 border-b border-[#e1e9f0] p-4 sm:flex-row sm:items-center">
          <p className="text-sm text-[#697d90]">
            선택한 기록: {selectedIds.size}개
          </p>

          <button
            type="button"
            disabled={selectedIds.size === 0}
            onClick={deleteSelected}
            className="flex w-fit items-center gap-2 rounded-lg border border-red-200 px-4 py-2 text-sm font-semibold text-red-600 hover:bg-red-50 disabled:cursor-not-allowed disabled:opacity-40"
          >
            <Trash2 size={16} />
            선택 삭제
          </button>
        </div>

        <div className="overflow-x-auto">
          <table className="min-w-[1150px] w-full border-collapse text-left">
            <thead className="bg-[#e8f0f7] text-sm text-[#3c5368]">
              <tr>
                <th className="w-14 px-5 py-4">
                  <input
                    type="checkbox"
                    checked={allFilteredSelected}
                    onChange={toggleAllFiltered}
                    aria-label="전체 선택"
                    className="h-4 w-4 accent-[#0075c9]"
                  />
                </th>

                <th className="px-4 py-4">
                  검사 번호
                </th>
                <th className="px-4 py-4">
                  검사 시각
                </th>
                <th className="px-4 py-4">
                  파일명
                </th>
                <th className="px-4 py-4">
                  조립 순서
                </th>
                <th className="px-4 py-4">
                  체결 상태
                </th>
                <th className="px-4 py-4">
                  노출 길이
                </th>
                <th className="px-4 py-4">
                  기울기
                </th>
                <th className="px-4 py-4">
                  최종 판정
                </th>
                <th className="px-4 py-4">
                  관리
                </th>
              </tr>
            </thead>

            <tbody className="divide-y divide-[#e1e9f0] text-sm">
              {filteredRecords.map((record) => {
                const finalResult =
                  getFinalResult(record)

                return (
                  <tr
                    key={record.id}
                    className="hover:bg-[#f8fafc]"
                  >
                    <td className="px-5 py-4">
                      <input
                        type="checkbox"
                        checked={selectedIds.has(
                          record.id,
                        )}
                        onChange={() =>
                          toggleRecord(record.id)
                        }
                        aria-label={`${record.id} 선택`}
                        className="h-4 w-4 accent-[#0075c9]"
                      />
                    </td>

                    <td className="px-4 py-4 font-semibold">
                      #{record.id}
                    </td>

                    <td className="px-4 py-4 text-[#697d90]">
                      {record.inspectedAt}
                    </td>

                    <td className="px-4 py-4 font-medium">
                      {record.fileName}
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
                      {record.exposedLength.toFixed(1)} mm
                    </td>

                    <td className="px-4 py-4">
                      {record.tiltAngle.toFixed(1)}°
                    </td>

                    <td className="px-4 py-4">
                      <ResultBadge
                        result={finalResult}
                      />
                    </td>

                    <td className="px-4 py-4">
                      <button
                        type="button"
                        onClick={() =>
                            navigate(`/history/${record.id}`)
                        }
                        className="font-semibold text-[#0075c9] hover:underline"
                        >
                        상세 ›
                        </button>
                    </td>
                  </tr>
                )
              })}

              {filteredRecords.length === 0 && (
                <tr>
                  <td
                    colSpan={10}
                    className="px-5 py-16 text-center text-[#697d90]"
                  >
                    조건에 맞는 검사 기록이 없습니다.
                  </td>
                </tr>
              )}
            </tbody>
          </table>
        </div>

        <div className="flex items-center justify-between border-t border-[#e1e9f0] px-5 py-4 text-sm text-[#697d90]">
          <span>
            총 {filteredRecords.length}건
          </span>

          <span>1 / 1 페이지</span>
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
  children: React.ReactNode
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
  result: InspectionResult
}) {
  const normal = result === 'NORMAL'

  return (
    <span
      className={
        normal
          ? 'font-semibold text-[#168b5b]'
          : 'font-semibold text-[#d94b4b]'
      }
    >
      {normal ? 'NORMAL' : 'DEFECT'}
    </span>
  )
}

function ResultBadge({
  result,
}: {
  result: InspectionResult
}) {
  const normal = result === 'NORMAL'

  return (
    <span
      className={[
        'inline-flex rounded-full px-3 py-1 text-xs font-bold',
        normal
          ? 'bg-emerald-100 text-emerald-700'
          : 'bg-red-100 text-red-700',
      ].join(' ')}
    >
      {normal ? 'OK' : 'NG'}
    </span>
  )
}

function getFinalResult(
  record: InspectionRecord,
): InspectionResult {
  return record.assemblySequenceResult === 'NORMAL' &&
    record.fasteningQualityResult === 'NORMAL'
    ? 'NORMAL'
    : 'DEFECT'
}

function escapeCsv(value: unknown) {
  return `"${String(value).replaceAll('"', '""')}"`
}