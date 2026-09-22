import {
  AlertCircle,
  ChevronLeft,
  ChevronRight,
  FileImage,
  LoaderCircle,
  ScanLine,
  Trash2,
} from 'lucide-react'
import {
  useEffect,
  useMemo,
  useRef,
  useState,
} from 'react'
import FileImportControls, {
  type FileImportControlsHandle,
} from '../components/FileImportControls'
import {
  inspectImage,
  resolveResultImageUrl,
} from '../services/inspectionApi'
import type {
  InspectionResponse,
  InspectionResult,
} from '../types/inspection'

type ItemState =
  | 'READY'
  | 'INSPECTING'
  | 'DONE'
  | 'ERROR'

type InspectionItem = {
  id: string
  file: File
  previewUrl: string
  state: ItemState
  response?: InspectionResponse
  error?: string
}

const MAX_FILE_SIZE = 10 * 1024 * 1024
const SUPPORTED_TYPES = ['image/jpeg', 'image/png']

export default function InspectionPage() {
  const [items, setItems] = useState<InspectionItem[]>([])
  const [selectedIndex, setSelectedIndex] = useState(0)
  const [uploadError, setUploadError] = useState('')
  const fileImportRef = useRef<FileImportControlsHandle>(null)
  const previewUrlsRef = useRef<string[]>([])
  const selectedItem = items[selectedIndex]

  useEffect(() => {
    return () => {
      previewUrlsRef.current.forEach((url) => {
        URL.revokeObjectURL(url)
      })
    }
  }, [])

  const finalResult = useMemo<InspectionResult | null>(() => {
    return getFinalResult(selectedItem?.response)
  }, [selectedItem])

  function addFiles(files: File[]) {
  const errors: string[] = []
  const validFiles: File[] = []

  files.forEach((file) => {
    if (!SUPPORTED_TYPES.includes(file.type)) {
      errors.push(
        `${file.name}: 지원하지 않는 형식`,
      )
      return
    }

    if (file.size > MAX_FILE_SIZE) {
      errors.push(`${file.name}: 10MB 초과`)
      return
    }

    validFiles.push(file)
  })

  const existingKeys = new Set(
    items.map((item) =>
      createFileKey(item.file),
    ),
  )

  const uniqueFiles: File[] = []
  let duplicateCount = 0

  validFiles.forEach((file) => {
    const fileKey = createFileKey(file)

    if (existingKeys.has(fileKey)) {
      duplicateCount += 1
      return
    }

    existingKeys.add(fileKey)
    uniqueFiles.push(file)
  })

  if (duplicateCount > 0) {
    errors.push(
      `${duplicateCount}개의 중복 파일을 제외했습니다.`,
    )
  }

  setUploadError(errors.join(' / '))

  if (uniqueFiles.length === 0) {
    return
  }

  const newItems: InspectionItem[] =
    uniqueFiles.map((file) => {
      const previewUrl =
        URL.createObjectURL(file)

      previewUrlsRef.current.push(previewUrl)

      return {
        id: crypto.randomUUID(),
        file,
        previewUrl,
        state: 'READY',
      }
    })

  setItems((currentItems) => [
    ...currentItems,
    ...newItems,
  ])

  if (items.length === 0) {
    setSelectedIndex(0)
  }
}

  async function handleInspection() {
    if (
      !selectedItem ||
      selectedItem.state === 'INSPECTING'
    ) {
      return
    }

    updateItem(selectedItem.id, {
      state: 'INSPECTING',
      response: undefined,
      error: undefined,
    })

    try {
      const response = await inspectImage(
        selectedItem.file,
      )

      updateItem(selectedItem.id, {
        state: 'DONE',
        response,
        error: undefined,
      })
    } catch (error) {
      updateItem(selectedItem.id, {
        state: 'ERROR',
        error:
          error instanceof Error
            ? error.message
            : '검사 중 알 수 없는 오류가 발생했습니다.',
      })
    }
  }

  function updateItem(
    id: string,
    changes: Partial<InspectionItem>,
  ) {
    setItems((currentItems) =>
      currentItems.map((item) =>
        item.id === id
          ? {
              ...item,
              ...changes,
            }
          : item,
      ),
    )
  }

  function movePrevious() {
    setSelectedIndex((currentIndex) =>
      Math.max(0, currentIndex - 1),
    )
  }

  function moveNext() {
    setSelectedIndex((currentIndex) =>
      Math.min(items.length - 1, currentIndex + 1),
    )
  }

  function removeSelected() {
    if (!selectedItem) {
      return
    }

    URL.revokeObjectURL(selectedItem.previewUrl)

    setItems((currentItems) =>
      currentItems.filter(
        (item) => item.id !== selectedItem.id,
      ),
    )

    setSelectedIndex((currentIndex) =>
      Math.max(
        0,
        Math.min(currentIndex, items.length - 2),
      ),
    )
  }

  function clearAllItems() {
      if (items.length === 0) {
        return
      }

      const confirmed = window.confirm(
        `선택한 이미지 ${items.length}개를 모두 삭제하시겠습니까?`,
      )

      if (!confirmed) {
        return
      }

      items.forEach((item) => {
        URL.revokeObjectURL(item.previewUrl)
        previewUrlsRef.current =
        previewUrlsRef.current.filter(
          (url) => url !== selectedItem.previewUrl,
        )
      })

      previewUrlsRef.current = []
      setItems([])
      setSelectedIndex(0)
      setUploadError('')
    }

  const resultImageUrl =
    selectedItem?.response?.resultImageUrl
      ? resolveResultImageUrl(
          selectedItem.response.resultImageUrl,
        )
      : null

  return (
    <div className="p-5 sm:p-7 lg:p-9">
      <header className="flex flex-col justify-between gap-4 sm:flex-row sm:items-start">
        <div>
          <h1 className="text-3xl font-bold text-[#172a3a]">
            이미지 검사
          </h1>

          <p className="mt-2 text-[#697d90]">
            사진을 촬영하거나 파일을 업로드하여 체결
            상태를 검사합니다.
          </p>
        </div>

        <FileImportControls
          ref={fileImportRef}
          onFiles={addFiles}
          onError={setUploadError}
        />  
      </header>

      {uploadError && (
        <div className="mt-5 flex items-center gap-2 rounded-lg border border-red-200 bg-red-50 px-4 py-3 text-sm text-red-700">
          <AlertCircle size={18} />
          {uploadError}
        </div>
      )}

      <div className="mt-7 grid gap-6 xl:grid-cols-[minmax(0,1fr)_376px]">
        <section className="rounded-xl border border-[#d9e4ee] bg-white p-5">
          <div className="flex items-center justify-between">
            <h2 className="text-xl font-bold">
              검사 이미지
            </h2>

            <span className="text-sm text-[#697d90]">
              {items.length === 0
                ? '0 / 0 이미지'
                : `${selectedIndex + 1} / ${items.length} 이미지`}
            </span>
          </div>

          {!selectedItem ? (
            <EmptyImageState
              onUpload={() =>
                fileImportRef.current?.openImagePicker()
              }
            />
          ) : (
            <>
              <div className="mt-5 grid gap-5 md:grid-cols-2">
                <ImagePanel
                  title="원본"
                  imageUrl={selectedItem.previewUrl}
                />

                <ResultImagePanel
                  item={selectedItem}
                  resultImageUrl={resultImageUrl}
                />
              </div>

              <div className="mt-5 flex items-center gap-4 rounded-lg border border-[#dce6ef] bg-[#f3f7fb] p-3">
                <button
                  type="button"
                  aria-label="이전 이미지"
                  disabled={selectedIndex === 0}
                  onClick={movePrevious}
                  className="rounded-md bg-white p-2 disabled:cursor-not-allowed disabled:opacity-40"
                >
                  <ChevronLeft />
                </button>

                <div className="min-w-0 flex-1">
                  <p className="truncate font-bold">
                    {selectedItem.file.name}
                  </p>

                  <p className="mt-1 text-sm text-[#697d90]">
                    {formatBytes(selectedItem.file.size)}
                    {' · '}
                    {getStateLabel(selectedItem.state)}
                  </p>
                </div>

                <button
                  type="button"
                  aria-label="현재 이미지 삭제"
                  onClick={removeSelected}
                  className="rounded-md p-2 text-red-600 hover:bg-red-50"
                >
                  <Trash2 size={19} />
                </button>

                <button
                  type="button"
                  aria-label="다음 이미지"
                  disabled={
                    selectedIndex >= items.length - 1
                  }
                  onClick={moveNext}
                  className="rounded-md bg-white p-2 disabled:cursor-not-allowed disabled:opacity-40"
                >
                  <ChevronRight />
                </button>
              </div>

              <FileGrid
                items={items}
                selectedIndex={selectedIndex}
                onSelect={setSelectedIndex}
                onClearAll={clearAllItems}
              />
            </>
          )}
        </section>

        <ResultPanel
          item={selectedItem}
          finalResult={finalResult}
          onInspect={handleInspection}
        />
      </div>
    </div>
  )
}

function EmptyImageState({
  onUpload,
}: {
  onUpload: () => void
}) {
  return (
    <div className="mt-5 flex min-h-[510px] flex-col items-center justify-center rounded-xl border-2 border-dashed border-[#bfd0df] bg-[#f7fafc] p-8 text-center">
      <div className="flex h-16 w-16 items-center justify-center rounded-full bg-blue-100 text-[#0075c9]">
        <FileImage size={30} />
      </div>

      <p className="mt-5 text-lg font-bold">
        검사할 이미지를 선택하세요
      </p>

      <p className="mt-2 text-sm text-[#697d90]">
        JPG, JPEG, PNG · 이미지당 최대 10MB
      </p>

      <button
        type="button"
        onClick={onUpload}
        className="mt-6 rounded-lg bg-[#0075c9] px-6 py-3 font-semibold text-white hover:bg-[#0065ad]"
      >
        이미지 선택
      </button>
    </div>
  )
}

function ImagePanel({
  title,
  imageUrl,
}: {
  title: string
  imageUrl: string
}) {
  return (
    <div className="rounded-lg border border-[#dce6ef] bg-[#f3f7fb] p-4">
      <p className="font-bold">{title}</p>

      <div className="mt-4 flex h-[360px] items-center justify-center overflow-hidden rounded-lg border border-[#bfd0df] bg-[#eaf1f6]">
        <img
          src={imageUrl}
          alt={title}
          className="h-full w-full object-contain"
        />
      </div>
    </div>
  )
}

function ResultImagePanel({
  item,
  resultImageUrl,
}: {
  item: InspectionItem
  resultImageUrl: string | null
}) {
  return (
    <div className="rounded-lg border border-[#dce6ef] bg-[#f3f7fb] p-4">
      <p className="font-bold">분석 결과</p>

      <div className="relative mt-4 flex h-[360px] items-center justify-center overflow-hidden rounded-lg border border-[#bfd0df] bg-[#eaf1f6]">
        {resultImageUrl ? (
          <img
            src={resultImageUrl}
            alt="분석 결과"
            className="h-full w-full object-contain"
          />
        ) : (
          <>
            <img
              src={item.previewUrl}
              alt=""
              className="h-full w-full object-contain opacity-30"
            />

            <div className="absolute inset-0 flex items-center justify-center">
              {item.state === 'INSPECTING' ? (
                <div className="flex items-center gap-2 rounded-lg bg-white px-5 py-3 font-semibold shadow">
                  <LoaderCircle
                    size={20}
                    className="animate-spin text-[#0075c9]"
                  />
                  검사 중
                </div>
              ) : (
                <span className="rounded-lg bg-white px-5 py-3 text-sm font-semibold shadow">
                  검사 결과 대기
                </span>
              )}
            </div>
          </>
        )}
      </div>
    </div>
  )
}

function FileGrid({
  items,
  selectedIndex,
  onSelect,
  onClearAll,
  }: {
    items: InspectionItem[]
    selectedIndex: number
    onSelect: (index: number) => void
    onClearAll: () => void
  }) {
  return (
    <div className="mt-6">
      <div className="flex items-center justify-between gap-4">
        <div className="flex items-center gap-3">
          <h3 className="font-bold">파일 목록</h3>

          <span className="text-sm text-[#697d90]">
            총 {items.length}개
          </span>
        </div>

        <button
          type="button"
          onClick={onClearAll}
          className="rounded-lg px-3 py-2 text-sm font-semibold text-red-600 hover:bg-red-50"
        >
          전체 삭제
        </button>
      </div>

      <div className="mt-3 grid grid-cols-2 gap-3 sm:grid-cols-3 lg:grid-cols-4 2xl:grid-cols-5">
        {items.map((item, index) => {
          const status = getItemStatus(item)
          const isSelected = index === selectedIndex

          return (
            <button
              key={item.id}
              type="button"
              onClick={() => onSelect(index)}
              className={[
                'group overflow-hidden rounded-xl border bg-white text-left transition',
                isSelected
                  ? 'border-[#0075c9] ring-2 ring-[#0075c9]/25'
                  : 'border-[#d9e4ee] hover:border-[#8dbbdd] hover:shadow-md',
              ].join(' ')}
            >
              <div className="relative aspect-[4/3] overflow-hidden bg-[#eaf1f6]">
                <img
                  src={item.previewUrl}
                  alt={item.file.name}
                  className="h-full w-full object-cover transition duration-200 group-hover:scale-[1.03]"
                />

                <span
                  className={[
                    'absolute right-2 top-2 rounded-full px-2.5 py-1 text-[11px] font-bold shadow-sm',
                    status.className,
                  ].join(' ')}
                >
                  {status.label}
                </span>

                <span className="absolute bottom-2 left-2 rounded-md bg-black/60 px-2 py-1 text-[11px] text-white">
                  {index + 1}
                </span>

                {item.state === 'INSPECTING' && (
                  <div className="absolute inset-0 flex items-center justify-center bg-black/30">
                    <LoaderCircle
                      size={28}
                      className="animate-spin text-white"
                    />
                  </div>
                )}
              </div>

              <div className="p-3">
                <p
                  title={item.file.name}
                  className="truncate text-sm font-bold text-[#172a3a]"
                >
                  {item.file.name}
                </p>

                <p className="mt-1 text-xs text-[#697d90]">
                  {formatBytes(item.file.size)}
                </p>
              </div>
            </button>
          )
        })}
      </div>
    </div>
  )
}

function ResultPanel({
  item,
  finalResult,
  onInspect,
}: {
  item?: InspectionItem
  finalResult: InspectionResult | null
  onInspect: () => void
}) {
  return (
    <aside className="h-fit rounded-xl border border-[#d9e4ee] bg-white p-5">
      <h2 className="text-xl font-bold">검사 결과</h2>

      {!item ? (
        <p className="mt-8 text-sm text-[#697d90]">
          검사할 이미지를 먼저 선택하세요.
        </p>
      ) : item.state === 'ERROR' ? (
        <div className="mt-5 rounded-lg border border-red-200 bg-red-50 p-4 text-red-700">
          <div className="flex items-center gap-2 font-bold">
            <AlertCircle size={19} />
            검사 실패
          </div>

          <p className="mt-2 text-sm">{item.error}</p>
        </div>
      ) : item.response && finalResult ? (
        <div className="mt-5">
          <div
            className={[
              'rounded-lg border p-5',
              finalResult === 'NORMAL'
                ? 'border-emerald-200 bg-emerald-50'
                : 'border-red-200 bg-red-50',
            ].join(' ')}
          >
            <p className="text-sm text-[#697d90]">
              최종 판정
            </p>

            <p
              className={[
                'mt-2 text-4xl font-extrabold',
                finalResult === 'NORMAL'
                  ? 'text-[#168b5b]'
                  : 'text-[#d94b4b]',
              ].join(' ')}
            >
              {finalResult === 'NORMAL' ? 'OK' : 'NG'}
            </p>
          </div>

          <h3 className="mt-7 font-bold">검사 항목</h3>

          <ResultRow
            label="조립 순서"
            result={
              item.response.assemblySequenceResult
            }
          />

          <ResultRow
            label="체결 상태"
            result={
              item.response.fasteningQualityResult
            }
          />
        </div>
      ) : (
        <div className="mt-5 rounded-lg border border-[#dce6ef] bg-[#f3f7fb] p-5">
          <p className="font-bold">
            {item.state === 'INSPECTING'
              ? '검사 중입니다.'
              : '아직 검사하지 않았습니다.'}
          </p>

          <p className="mt-2 text-sm text-[#697d90]">
            선택한 이미지를 검사하려면 아래 버튼을
            누르세요.
          </p>
        </div>
      )}

      <button
        type="button"
        disabled={
          !item || item.state === 'INSPECTING'
        }
        onClick={onInspect}
        className="mt-6 flex w-full items-center justify-center gap-2 rounded-lg bg-[#0075c9] px-5 py-3 font-semibold text-white hover:bg-[#0065ad] disabled:cursor-not-allowed disabled:bg-slate-300"
      >
        {item?.state === 'INSPECTING' ? (
          <LoaderCircle
            size={19}
            className="animate-spin"
          />
        ) : (
          <ScanLine size={19} />
        )}

        {item?.state === 'ERROR'
          ? '다시 검사'
          : '선택 이미지 검사'}
      </button>
    </aside>
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
    <div className="mt-3 flex items-center justify-between border-b border-[#e1e9f0] py-3">
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

function getFinalResult(
  response?: InspectionResponse,
): InspectionResult | null {
  if (!response) {
    return null
  }

  return response.assemblySequenceResult === 'NORMAL' &&
    response.fasteningQualityResult === 'NORMAL'
    ? 'NORMAL'
    : 'DEFECT'
}

function getItemStatus(item: InspectionItem) {
  const result = getFinalResult(item.response)

  if (result === 'NORMAL') {
    return {
      label: 'OK',
      className:
        'bg-emerald-100 text-emerald-700',
    }
  }

  if (result === 'DEFECT') {
    return {
      label: 'NG',
      className: 'bg-red-100 text-red-700',
    }
  }

  if (item.state === 'INSPECTING') {
    return {
      label: '검사 중',
      className: 'bg-blue-100 text-blue-700',
    }
  }

  if (item.state === 'ERROR') {
    return {
      label: '실패',
      className: 'bg-red-100 text-red-700',
    }
  }

  return {
    label: '대기',
    className: 'bg-slate-100 text-slate-600',
  }
}

function getStateLabel(state: ItemState) {
  const labels: Record<ItemState, string> = {
    READY: '검사 전',
    INSPECTING: '검사 중',
    DONE: '검사 완료',
    ERROR: '검사 실패',
  }

  return labels[state]
}

function formatBytes(bytes: number) {
  if (bytes < 1024 * 1024) {
    return `${(bytes / 1024).toFixed(1)} KB`
  }

  return `${(bytes / 1024 / 1024).toFixed(1)} MB`
}

function createFileKey(file: File) {
  return [
    file.name.toLowerCase(),
    file.size,
    file.lastModified,
  ].join('::')
}