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
    }, 1000)

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
    }, 3000)

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

  function reconnectStream() {
    setStreamError(false)
    setStreamKey(Date.now())
  }

  return (
    <div className="flex min-h-[calc(100vh-64px)] flex-col bg-[#edf3f7] p-4 sm:p-5">
      <header className="mb-4 flex flex-wrap items-center justify-between gap-3">
        <div>
          <div className="flex items-center gap-3">
            <Video
              size={28}
              className="text-[#0075c9]"
            />

            <h1 className="text-2xl font-bold text-[#172a3a] sm:text-3xl">
              실시간 영상 검사
            </h1>
          </div>

          <p className="mt-1 text-sm text-[#697d90]">
            카메라 영상과 볼트 체결 분석 결과를
            실시간으로 확인합니다.
          </p>
        </div>

        <button
          type="button"
          onClick={reconnectStream}
          className="flex items-center gap-2 rounded-lg border border-[#b9cad8] bg-white px-4 py-2 text-sm font-semibold text-[#0066a6] shadow-sm hover:bg-[#f4f9fc]"
        >
          <RefreshCw size={17} />
          영상 재연결
        </button>
      </header>

      <section className="relative h-[calc(100vh-170px)] min-h-[600px] overflow-hidden rounded-2xl border border-[#243647] bg-[#050b12] shadow-xl">
        <img
          key={streamKey}
          src={getVisionStreamUrl(streamKey)}
          alt="실시간 볼트 체결 검사 영상"
          className="h-full w-full object-contain"
          onLoad={() => setStreamError(false)}
          onError={() => setStreamError(true)}
        />

        <div className="absolute left-4 top-4 flex items-center gap-2 rounded-full border border-white/15 bg-black/60 px-4 py-2 text-sm font-bold text-white backdrop-blur">
          <span
            className={[
              'h-2.5 w-2.5 rounded-full',
              isLive
                ? 'animate-pulse bg-red-500'
                : 'bg-slate-500',
            ].join(' ')}
          />

          {isLive ? 'LIVE' : '연결 대기'}
        </div>

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

        <aside className="absolute inset-x-3 bottom-3 max-h-[52%] overflow-y-auto rounded-xl border border-white/15 bg-[#071724]/90 p-4 text-white shadow-2xl backdrop-blur-md lg:inset-y-4 lg:left-auto lg:right-4 lg:max-h-none lg:w-[360px]">
          <div className="flex items-center justify-between border-b border-white/10 pb-4">
            <div>
              <p className="text-xs font-semibold uppercase tracking-[0.18em] text-slate-400">
                Realtime inspection
              </p>

              <h2 className="mt-1 text-lg font-bold">
                현재 검사 결과
              </h2>
            </div>

            {isLive ? (
              <Wifi
                size={22}
                className="text-emerald-400"
              />
            ) : (
              <WifiOff
                size={22}
                className="text-red-400"
              />
            )}
          </div>

          {(inspectionError || statusError) && (
            <div className="mt-4 rounded-lg border border-red-400/30 bg-red-500/15 p-3 text-sm text-red-100">
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
            <div className="mt-4 rounded-xl border border-white/10 bg-white/5 p-5 text-center">
              <Activity
                size={32}
                className="mx-auto animate-pulse text-cyan-300"
              />

              <p className="mt-3 font-bold">
                첫 분석 결과 대기 중
              </p>

              <p className="mt-1 text-sm text-slate-400">
                Vision Worker가 첫 프레임을 처리하면
                결과가 자동으로 표시됩니다.
              </p>
            </div>
          ) : (
            <>
              <OverallResult
                status={
                  latestInspection.overallResult
                }
              />

              <div className="mt-4 space-y-2">
                <StatusRow
                  label="조립 상태"
                  status={
                    latestInspection
                      .assemblySequenceResult
                  }
                />

                <StatusRow
                  label="체결 상태"
                  status={
                    latestInspection
                      .fasteningQualityResult
                  }
                />

                <StatusRow
                  label="정렬 상태"
                  status={
                    latestInspection.alignmentResult
                  }
                />
              </div>

              <div className="mt-4 grid grid-cols-4 gap-2">
                <MetricCard
                  label="볼트"
                  value={counts.bolt}
                />

                <MetricCard
                  label="와셔"
                  value={counts.washer}
                />

                <MetricCard
                  label="나사산"
                  value={counts.thread}
                />

                <MetricCard
                  label="전체"
                  value={counts.total}
                />
              </div>

              <div className="mt-4 rounded-lg border border-white/10 bg-white/5 p-3">
                <InfoRow
                  label="추론 시간"
                  value={`${latestInspection.metrics.inferenceTimeMs.toFixed(1)} ms`}
                />

                <InfoRow
                  label="모델"
                  value={
                    latestInspection.metrics.modelType
                  }
                />

                <InfoRow
                  label="검사 시각"
                  value={formatDateTime(
                    latestInspection.inspectionTime,
                  )}
                />

                {latestInspection.metrics
                  .fasteningEvaluated && (
                  <>
                    <InfoRow
                      label="나사산 길이"
                      value={formatCentimeter(
                        latestInspection.metrics
                          .measuredThreadCm,
                      )}
                    />

                    <InfoRow
                      label="판정 기준"
                      value={formatCentimeter(
                        latestInspection.metrics
                          .threadThresholdCm,
                      )}
                    />
                  </>
                )}
              </div>

              {latestInspection.metrics
                .assemblyReasons.length > 0 && (
                <div className="mt-4 rounded-lg border border-red-400/30 bg-red-500/10 p-3">
                  <p className="text-sm font-bold text-red-200">
                    불량 원인
                  </p>

                  <ul className="mt-2 space-y-1 text-sm text-red-100">
                    {latestInspection.metrics
                      .assemblyReasons.map(
                        (reason) => (
                          <li key={reason}>
                            · {getReasonLabel(reason)}
                          </li>
                        ),
                      )}
                  </ul>
                </div>
              )}
            </>
          )}

          <div className="mt-4 grid grid-cols-2 gap-2">
            <ConnectionCard
              icon={Video}
              label="카메라"
              connected={
                systemStatus?.cameraConnected ??
                false
              }
            />

            <ConnectionCard
              icon={Server}
              label="분석 서버"
              connected={
                systemStatus?.visionWorkerRunning ??
                false
              }
            />

            <ConnectionCard
              icon={Database}
              label="데이터베이스"
              connected={
                systemStatus?.databaseConnected ??
                false
              }
            />

            <ConnectionCard
              icon={Activity}
              label="모델"
              connected={
                systemStatus?.modelLoaded ?? false
              }
            />
          </div>
        </aside>
      </section>
    </div>
  )
}

function OverallResult({
  status,
}: {
  status: ResultStatus
}) {
  const isNormal = status === 'NORMAL'

  return (
    <div
      className={[
        'mt-4 rounded-xl border p-4',
        isNormal
          ? 'border-emerald-400/30 bg-emerald-500/15'
          : 'border-red-400/30 bg-red-500/15',
      ].join(' ')}
    >
      <div className="flex items-center gap-3">
        {isNormal ? (
          <CheckCircle2
            size={31}
            className="text-emerald-400"
          />
        ) : (
          <AlertTriangle
            size={31}
            className="text-red-400"
          />
        )}

        <div>
          <p className="text-xs font-semibold text-slate-300">
            최종 판정
          </p>

          <p
            className={[
              'text-2xl font-black',
              isNormal
                ? 'text-emerald-300'
                : 'text-red-300',
            ].join(' ')}
          >
            {getStatusLabel(status)}
          </p>
        </div>
      </div>
    </div>
  )
}

function StatusRow({
  label,
  status,
}: {
  label: string
  status: ResultStatus
}) {
  return (
    <div className="flex items-center justify-between rounded-lg border border-white/10 bg-white/5 px-3 py-2.5">
      <span className="text-sm text-slate-300">
        {label}
      </span>

      <span className={getStatusClass(status)}>
        {getStatusLabel(status)}
      </span>
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
    <div className="rounded-lg border border-white/10 bg-white/5 p-2 text-center">
      <p className="text-xs text-slate-400">
        {label}
      </p>

      <p className="mt-1 text-lg font-black">
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
    <div className="flex items-center justify-between gap-4 py-1.5 text-sm">
      <span className="flex items-center gap-1.5 text-slate-400">
        {label === '검사 시각' && (
          <Clock3 size={14} />
        )}
        {label}
      </span>

      <span className="truncate font-semibold text-slate-100">
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
    <div className="flex items-center gap-2 rounded-lg border border-white/10 bg-white/5 p-2.5">
      <Icon
        size={17}
        className={
          connected
            ? 'text-emerald-400'
            : 'text-red-400'
        }
      />

      <div>
        <p className="text-xs text-slate-400">
          {label}
        </p>

        <p className="text-xs font-bold">
          {connected ? '정상' : '연결 안 됨'}
        </p>
      </div>
    </div>
  )
}

function getStatusLabel(status: ResultStatus) {
  switch (status) {
    case 'NORMAL':
      return '정상'

    case 'DEFECT':
      return '불량'

    case 'NOT_EVALUATED':
      return '미평가'
  }
}

function getStatusClass(status: ResultStatus) {
  switch (status) {
    case 'NORMAL':
      return 'rounded-full bg-emerald-400/15 px-2.5 py-1 text-xs font-bold text-emerald-300'

    case 'DEFECT':
      return 'rounded-full bg-red-400/15 px-2.5 py-1 text-xs font-bold text-red-300'

    case 'NOT_EVALUATED':
      return 'rounded-full bg-slate-400/15 px-2.5 py-1 text-xs font-bold text-slate-300'
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

function formatCentimeter(value?: number) {
  if (value == null) {
    return '-'
  }

  return `${value.toFixed(2)} cm`
}

function getReasonLabel(reason: string) {
  if (reason === 'no_thread') {
    return '나사산이 검출되지 않았습니다.'
  }

  if (reason === 'no_bolt') {
    return '볼트가 검출되지 않았습니다.'
  }

  if (reason === 'no_nut') {
    return '너트가 검출되지 않았습니다.'
  }

  if (reason.startsWith('dup_thread')) {
    return '나사산이 중복 검출되었습니다.'
  }

  if (reason.startsWith('extra_bolt')) {
    return '볼트가 기준 수량보다 많습니다.'
  }

  if (reason.startsWith('washer_low')) {
    return '와셔가 기준 수량보다 적습니다.'
  }

  if (reason.startsWith('washer_high')) {
    return '와셔가 기준 수량보다 많습니다.'
  }

  return reason
}