import {
  Activity,
  AlertTriangle,
  CheckCircle2,
  Clock3,
  Database,
  RefreshCw,
  Server,
  Video,
  Wifi,
  WifiOff,
} from 'lucide-react'
import {
  useEffect,
  useMemo,
  useState,
} from 'react'
import {
  getLatestInspection,
  getSystemStatus,
  getVisionStreamUrl,
} from '../services/inspectionApi'
import type {
  LatestInspectionResponse,
  ResultStatus,
  SystemStatus,
} from '../types/vision'

export default function RealtimeInspectionPage() {
  const [latestInspection, setLatestInspection] =
    useState<LatestInspectionResponse | null>(null)
  const [systemStatus, setSystemStatus] =
    useState<SystemStatus | null>(null)
  const [inspectionError, setInspectionError] =
    useState('')
  const [statusError, setStatusError] =
    useState('')
  const [streamError, setStreamError] =
    useState(false)
  const [streamKey, setStreamKey] =
    useState(() => Date.now())

  useEffect(() => {
    let disposed = false
    let requestInFlight = false
    const controller = new AbortController()

    async function refreshLatestInspection() {
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
          setInspectionError('')
        }
      } catch (error) {
        if (!disposed && !controller.signal.aborted) {
          setInspectionError(
            error instanceof Error
              ? error.message
              : '검사 결과를 불러오지 못했습니다.',
          )
        }
      } finally {
        requestInFlight = false
      }
    }

    void refreshLatestInspection()

    const timer = window.setInterval(() => {
      void refreshLatestInspection()
    }, 200)

    return () => {
      disposed = true
      window.clearInterval(timer)
      controller.abort()
    }
  }, [])

  useEffect(() => {
    let disposed = false
    let requestInFlight = false
    const controller = new AbortController()

    async function refreshSystemStatus() {
      if (requestInFlight) {
        return
      }

      requestInFlight = true

      try {
        const result = await getSystemStatus(
          controller.signal,
        )

        if (!disposed) {
          setSystemStatus(result)
          setStatusError('')
        }
      } catch (error) {
        if (!disposed && !controller.signal.aborted) {
          setStatusError(
            error instanceof Error
              ? error.message
              : '시스템 상태를 불러오지 못했습니다.',
          )
        }
      } finally {
        requestInFlight = false
      }
    }

    void refreshSystemStatus()

    const timer = window.setInterval(() => {
      void refreshSystemStatus()
    }, 1000)

    return () => {
      disposed = true
      window.clearInterval(timer)
      controller.abort()
    }
  }, [])

  const isLive = Boolean(
    systemStatus?.cameraConnected &&
      systemStatus?.visionWorkerRunning,
  )

  const persistenceReady = Boolean(
    systemStatus?.databaseConnected &&
      systemStatus?.persistenceWorkerRunning,
  )

  const counts = useMemo(() => {
    const detectedCounts =
      latestInspection?.metrics.detectedCounts ?? {}

    return {
      bolt: detectedCounts.bolt ?? 0,
      washer: detectedCounts.washer ?? 0,
      thread: detectedCounts.thread ?? 0,
      total:
        latestInspection?.metrics
          .detectedInstanceCount ?? 0,
    }
  }, [latestInspection])

  const assemblyReasons =
    latestInspection?.metrics.assemblyReasons ?? []

  function reconnectStream() {
    setStreamError(false)
    setStreamKey(Date.now())
  }

  return (
    <div className="flex min-h-screen flex-col bg-[#f3f6fa] p-4 sm:p-5 lg:p-6">
      <header className="mb-5 flex flex-wrap items-center justify-between gap-3">
        <div>
          <div className="flex items-center gap-3">
            <Video
              size={29}
              className="text-[#003478]"
            />

            <h1 className="text-2xl font-black text-[#172033] sm:text-3xl">
              실시간 영상 검사
            </h1>
          </div>

          <p className="mt-1 text-sm text-[#64748b]">
            영상과 주요 판정 결과를 한 화면에서
            즉시 확인합니다.
          </p>
        </div>

        <div className="flex flex-wrap items-center gap-2">
          <div className="flex items-center gap-2 rounded-xl border border-[#d8e0eb] bg-white px-4 py-2.5 text-sm font-bold text-[#172033] shadow-sm">
            <span
              className={[
                'h-2.5 w-2.5 rounded-full',
                isLive
                  ? 'animate-pulse bg-[#42d6af]'
                  : 'bg-slate-400',
              ].join(' ')}
            />
            {isLive ? '분석 중 · 10 FPS' : '연결 대기'}
          </div>

          <button
            type="button"
            onClick={reconnectStream}
            className="flex items-center gap-2 rounded-xl bg-[#003478] px-4 py-2.5 text-sm font-bold text-white shadow-sm transition hover:bg-[#002b63]"
          >
            <RefreshCw size={17} />
            영상 재연결
          </button>
        </div>
      </header>

      <main className="grid flex-1 gap-4 xl:min-h-[calc(100vh-132px)] xl:grid-cols-[minmax(0,1fr)_420px]">
        <section className="flex min-h-[560px] flex-col overflow-hidden rounded-2xl border border-[#dbe3ee] bg-white shadow-[0_8px_30px_rgba(23,32,51,0.08)]">
          <div className="relative min-h-[480px] flex-1 overflow-hidden bg-[#0b1220]">
            <img
              key={streamKey}
              src={getVisionStreamUrl(streamKey)}
              alt="실시간 볼트 체결 검사 영상"
              loading="eager"
              fetchPriority="high"
              className="h-full w-full object-contain"
              onLoad={() => setStreamError(false)}
              onError={() => setStreamError(true)}
            />

            <div className="absolute left-5 top-5 flex items-center gap-2 rounded-full border border-white/15 bg-[#111827]/85 px-4 py-2 text-sm font-bold text-white backdrop-blur">
              <span
                className={[
                  'h-2.5 w-2.5 rounded-full',
                  isLive
                    ? 'animate-pulse bg-[#42d6af]'
                    : 'bg-slate-500',
                ].join(' ')}
              />
              {isLive ? 'LIVE · 분석 중' : '연결 대기'}
            </div>

            {latestInspection && (
              <div className="absolute right-5 top-5 rounded-full border border-white/15 bg-[#111827]/85 px-4 py-2 text-xs font-semibold text-white backdrop-blur">
                {latestInspection.metrics.modelType}
              </div>
            )}

            {streamError && (
              <div className="absolute inset-0 flex items-center justify-center bg-[#050b12]/95 p-8 text-center text-white">
                <div>
                  <WifiOff
                    size={44}
                    className="mx-auto text-red-400"
                  />

                  <p className="mt-4 text-lg font-bold">
                    영상 스트림에 연결할 수 없습니다.
                  </p>

                  <p className="mt-2 text-sm text-slate-300">
                    Flask 서버와 카메라 연결 상태를
                    확인한 후 영상 재연결을 눌러주세요.
                  </p>
                </div>
              </div>
            )}
          </div>

          <footer className="flex flex-wrap items-center gap-x-6 gap-y-2 border-t border-[#e5eaf1] px-5 py-3 text-xs text-[#64748b]">
            <span className="font-bold text-[#172033]">
              실시간 분석
            </span>
            <span>
              추론 시간{' '}
              {latestInspection
                ? `${latestInspection.metrics.inferenceTimeMs.toFixed(1)} ms`
                : '-'}
            </span>
            <span>검출 객체 {counts.total}개</span>
            <span>
              서버 {systemStatus?.visionWorkerRunning ? '정상' : '대기'}
            </span>
            <span className="ml-auto font-bold text-[#172033]">
              화면을 크게 보려면 브라우저 전체 화면을 사용하세요.
            </span>
          </footer>
        </section>

        <aside className="flex flex-col rounded-2xl border border-[#dbe3ee] bg-white p-3 shadow-[0_8px_30px_rgba(23,32,51,0.08)] sm:p-4">
          <div className="flex items-center justify-between px-1 pb-3">
            <div>
              <p className="text-xs font-bold uppercase tracking-[0.16em] text-[#64748b]">
                Realtime inspection
              </p>
              <h2 className="mt-1 text-xl font-black text-[#172033]">
                현재 검사 결과
              </h2>
            </div>

            {isLive ? (
              <Wifi
                size={22}
                className="text-[#00a98f]"
              />
            ) : (
              <WifiOff
                size={22}
                className="text-red-500"
              />
            )}
          </div>

          {(inspectionError || statusError) && (
            <div className="mb-3 rounded-xl border border-red-200 bg-red-50 p-3 text-sm text-red-700">
              <div className="flex items-start gap-2">
                <AlertTriangle
                  size={18}
                  className="mt-0.5 shrink-0"
                />
                <span>
                  {inspectionError || statusError}
                </span>
              </div>
            </div>
          )}

          {!latestInspection ? (
            <div className="flex flex-1 items-center justify-center rounded-2xl border border-dashed border-[#cdd8e5] bg-[#f7f9fc] p-8 text-center">
              <div>
                <Activity
                  size={38}
                  className="mx-auto animate-pulse text-[#185aa5]"
                />
                <p className="mt-4 font-bold text-[#172033]">
                  첫 분석 결과 대기 중
                </p>
                <p className="mt-2 text-sm text-[#64748b]">
                  첫 프레임 처리가 완료되면 결과가
                  자동으로 표시됩니다.
                </p>
              </div>
            </div>
          ) : (
            <>
              <OverallResult
                status={latestInspection.overallResult}
                inspectionTime={latestInspection.inspectionTime}
              />

              <h3 className="mb-2 mt-4 px-1 text-sm font-black text-[#172033]">
                검사 항목
              </h3>

              <div className="grid grid-cols-2 gap-2.5">
                <StatusCard
                  label="구성품 개수"
                  status={latestInspection.missingComponentResult}
                />
                <StatusCard
                  label="조립 순서"
                  status={latestInspection.assemblySequenceResult}
                />
                <StatusCard
                  label="체결 상태"
                  status={latestInspection.fasteningResult}
                />
              </div>

              <div className="mt-3 rounded-xl border border-[#e0e6ef] bg-[#f7f9fc] p-3.5">
                <div className="flex items-center justify-between">
                  <p className="text-sm font-black text-[#64748b]">
                    검출 부품
                  </p>
                  <span className="rounded-full bg-[#dff7f0] px-3 py-1 text-xs font-black text-[#08765c]">
                    전체 {counts.total}
                  </span>
                </div>

                <div className="mt-3 grid grid-cols-3 gap-2">
                  <MetricCard label="볼트" value={counts.bolt} />
                  <MetricCard label="와셔" value={counts.washer} />
                  <MetricCard label="나사산" value={counts.thread} />
                </div>
              </div>

              {assemblyReasons.length > 0 && (
                <div className="mt-3 rounded-xl border border-red-200 bg-red-50 p-3.5">
                  <p className="text-sm font-black text-red-700">
                    불량 원인
                  </p>
                  <ul className="mt-2 space-y-1 text-sm text-red-700">
                    {assemblyReasons.map((reason) => (
                      <li key={reason}>
                        · {getReasonLabel(reason)}
                      </li>
                    ))}
                  </ul>
                </div>
              )}

              <div
                className={[
                  'mt-3 rounded-xl border p-3.5',
                  persistenceReady
                    ? 'border-[#c9daf7] bg-[#eef4ff]'
                    : 'border-amber-200 bg-amber-50',
                ].join(' ')}
              >
                <div className="flex items-start gap-3">
                  <Database
                    size={21}
                    className={
                      persistenceReady
                        ? 'text-[#185aa5]'
                        : 'text-amber-600'
                    }
                  />
                  <div className="min-w-0 flex-1">
                    <p className="text-sm font-black text-[#172033]">
                      {persistenceReady
                        ? '검사 결과 저장 활성'
                        : 'DB 저장 상태 확인 필요'}
                    </p>
                    <p className="mt-1 text-xs font-bold text-[#164b86]">
                      정상 · 불량 모두 저장
                    </p>
                    <p className="mt-1 text-xs text-[#64748b]">
                      이번 실행 저장{' '}
                      {systemStatus?.persistedInspectionCount ?? 0}건
                      {' · '}대기{' '}
                      {systemStatus?.pendingPersistenceEvents ?? 0}건
                    </p>
                  </div>
                </div>
              </div>

              <div className="mt-3 rounded-xl border border-[#e0e6ef] bg-white p-3">
                <InfoRow
                  label="검사 시각"
                  value={formatDateTime(latestInspection.inspectionTime)}
                />
              </div>
            </>
          )}

          <div className="mt-3 grid grid-cols-4 gap-2">
            <ConnectionCard
              icon={Video}
              label="카메라"
              connected={systemStatus?.cameraConnected ?? false}
            />
            <ConnectionCard
              icon={Server}
              label="서버"
              connected={systemStatus?.visionWorkerRunning ?? false}
            />
            <ConnectionCard
              icon={Database}
              label="DB"
              connected={systemStatus?.databaseConnected ?? false}
            />
            <ConnectionCard
              icon={Activity}
              label="모델"
              connected={systemStatus?.modelLoaded ?? false}
            />
          </div>
        </aside>
      </main>
    </div>
  )
}

function OverallResult({
  status,
  inspectionTime,
}: {
  status: ResultStatus
  inspectionTime: string
}) {
  const isNormal = status === 'NORMAL'

  return (
    <div
      className={[
        'rounded-2xl border p-5 text-white',
        isNormal
          ? 'border-[#00a98f] bg-[#00a98f]'
          : 'border-red-600 bg-red-600',
      ].join(' ')}
    >
      <div className="flex items-start justify-between gap-4">
        <div>
          <p className="text-sm font-bold text-white/85">
            현재 프레임 최종 판정
          </p>
          <p className="mt-3 text-5xl font-black tracking-tight">
            {getStatusLabel(status)}
          </p>
        </div>

        {isNormal ? (
          <CheckCircle2 size={38} />
        ) : (
          <AlertTriangle size={38} />
        )}
      </div>

      <div className="mt-4 flex items-center gap-2 text-xs font-bold text-white/90">
        <span className="h-2 w-2 rounded-full bg-white/80" />
        {formatTimeOnly(inspectionTime)} · 실시간 갱신
      </div>
    </div>
  )
}

function StatusCard({
  label,
  status,
}: {
  label: string
  status: ResultStatus
}) {
  const isNormal = status === 'NORMAL'

  return (
    <div
      className={[
        'min-h-28 rounded-xl border p-4',
        isNormal
          ? 'border-[#b8eadb] bg-[#f1fbf8] text-[#08765c]'
          : 'border-red-200 bg-red-50 text-red-700',
      ].join(' ')}
    >
      <p className="text-sm font-bold text-[#64748b]">
        {label}
      </p>
      <div className="mt-4 flex items-center gap-2">
        {isNormal ? (
          <CheckCircle2 size={22} />
        ) : (
          <AlertTriangle size={22} />
        )}
        <span className="text-2xl font-black">
          {getStatusLabel(status)}
        </span>
      </div>
    </div>
  )
}

function MetricCard({
  label,
  value,
}: {
  label: string
  value: number
}) {
  return (
    <div className="rounded-lg border border-[#e0e6ef] bg-white px-2 py-2.5 text-center">
      <p className="text-xs font-bold text-[#64748b]">
        {label}
      </p>
      <p className="mt-1 text-xl font-black text-[#172033]">
        {value}
      </p>
    </div>
  )
}

function InfoRow({
  label,
  value,
}: {
  label: string
  value: string
}) {
  return (
    <div className="flex items-center justify-between gap-4 py-1.5 text-xs">
      <span className="flex items-center gap-1.5 text-[#64748b]">
        {label === '검사 시각' && (
          <Clock3 size={14} />
        )}
        {label}
      </span>
      <span className="truncate font-bold text-[#172033]">
        {value}
      </span>
    </div>
  )
}

function ConnectionCard({
  icon: Icon,
  label,
  connected,
}: {
  icon: typeof Activity
  label: string
  connected: boolean
}) {
  return (
    <div className="rounded-lg border border-[#e0e6ef] bg-[#f7f9fc] p-2 text-center">
      <Icon
        size={16}
        className={[
          'mx-auto',
          connected
            ? 'text-[#00a98f]'
            : 'text-red-500',
        ].join(' ')}
      />
      <p className="mt-1 text-[11px] font-bold text-[#64748b]">
        {label}
      </p>
    </div>
  )
}

function getStatusLabel(status: ResultStatus) {
  switch (status) {
    case 'NORMAL':
      return '정상'
    case 'DEFECT':
    case 'NOT_EVALUATED':
      return '불량'
  }
}

function formatDateTime(value: string) {
  const date = new Date(value)

  if (Number.isNaN(date.getTime())) {
    return '-'
  }

  return date.toLocaleString('ko-KR', {
    hour12: false,
  })
}

function formatTimeOnly(value: string) {
  const date = new Date(value)

  if (Number.isNaN(date.getTime())) {
    return '-'
  }

  return date.toLocaleTimeString('ko-KR', {
    hour12: false,
  })
}

function getReasonLabel(reason: string) {
  const labels: Record<string, string> = {
    THREAD_MISSING: '나사산이 검출되지 않았습니다.',
    AXIS_FAIL: '볼트 축을 계산할 수 없습니다.',
    NUT_MISSING: '너트가 누락되었습니다.',
    NUT_EXTRA: '너트가 기준 수량보다 많습니다.',
    WASHER_MISSING_HEAD_SIDE: '볼트 머리 쪽 와셔가 누락되었습니다.',
    WASHER_MISSING_NUT_SIDE: '너트 쪽 와셔가 누락되었습니다.',
    WASHER_MISSING: '와셔가 누락되었습니다.',
    WASHER_EXTRA: '와셔가 기준 수량보다 많습니다.',
    ORDER_ERROR: '조립 순서가 올바르지 않습니다.',
    LOOSE: '나사산 노출이 부족하여 체결 불량입니다.',
    GAP: '너트와 와셔 사이의 틈이 허용 범위를 초과했습니다.',
    NUT_NOT_SEATED: '너트가 정상 위치까지 체결되지 않았습니다.',
    FASTEN_UNMEASURED: '체결 상태를 측정할 수 없습니다.',
  }

  return labels[reason] ?? reason
}
