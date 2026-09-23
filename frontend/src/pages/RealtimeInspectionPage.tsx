import {
  AlertCircle,
  Camera,
  Expand,
  Play,
  RefreshCw,
  ScanLine,
  Square,
  VideoOff,
  Wifi,
} from 'lucide-react'
import {
  useEffect,
  useRef,
  useState,
} from 'react'
import { useLocalStorageState } from '../hooks/useLocalStorageState'

type CheckResult = 'PASS' | 'FAIL'

type Detection = {
  label: string
  confidence: number
  x: number
  y: number
  width: number
  height: number
  result: CheckResult
}

type RealtimeAnalysisResult = {
  finalResult: CheckResult
  assemblyResult: CheckResult
  fasteningResult: CheckResult
  confidence: number
  latencyMs: number
  timestamp: string
  detections: Detection[]
}

type RecentResult =
  RealtimeAnalysisResult & {
    id: string
  }

const REALTIME_MODE =
  import.meta.env.VITE_REALTIME_MODE ??
  'mock'

const USE_MOCK_ANALYSIS =
  REALTIME_MODE !== 'server'

const WEBSOCKET_URL =
  import.meta.env.VITE_REALTIME_WS_URL ??
  'ws://localhost:8080/ws/realtime-inspection'

export default function RealtimeInspectionPage() {
  const [cameraDevices, setCameraDevices] =
    useState<MediaDeviceInfo[]>([])

  const [
    selectedCameraId,
    setSelectedCameraId,
  ] = useLocalStorageState(
    'smart-bolt-camera-device',
    '',
  )

  const [cameraActive, setCameraActive] =
    useState(false)

  const [cameraReady, setCameraReady] =
    useState(false)

  const [cameraStarting, setCameraStarting] =
    useState(false)

  const [analysisActive, setAnalysisActive] =
    useState(false)

  const [frameRate, setFrameRate] =
    useState(2)

  const [cameraError, setCameraError] =
    useState('')

  const [analysisError, setAnalysisError] =
    useState('')

  const [lastResult, setLastResult] =
    useState<RealtimeAnalysisResult | null>(
      null,
    )

  const [recentResults, setRecentResults] =
    useState<RecentResult[]>([])

  const [totalFrames, setTotalFrames] =
    useState(0)

  const [fullscreen, setFullscreen] =
    useState(false)

  const videoRef =
    useRef<HTMLVideoElement>(null)

  const captureCanvasRef =
    useRef<HTMLCanvasElement>(null)

  const inspectionAreaRef =
    useRef<HTMLElement>(null)

  const streamRef =
    useRef<MediaStream | null>(null)

  const socketRef =
    useRef<WebSocket | null>(null)

  const cameraRequestIdRef = useRef(0)
  const analysisActiveRef = useRef(false)
  const sendingRef = useRef(false)
  const frameCounterRef = useRef(0)
  const lastSentAtRef = useRef(0)

  const responseTimerRef =
    useRef<number | null>(null)

  useEffect(() => {
    void startCamera()

    function handleDeviceChange() {
      void loadCameraDevices()
    }

    navigator.mediaDevices?.addEventListener(
      'devicechange',
      handleDeviceChange,
    )

    return () => {
      navigator.mediaDevices?.removeEventListener(
        'devicechange',
        handleDeviceChange,
      )

      cameraRequestIdRef.current += 1
      analysisActiveRef.current = false

      clearResponseTimer()
      closeWebSocket()
      releaseCameraStream()
    }
    // 최초 진입 시 한 번만 실행
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [])

  useEffect(() => {
    function handleFullscreenChange() {
      setFullscreen(
        document.fullscreenElement ===
          inspectionAreaRef.current,
      )
    }

    document.addEventListener(
      'fullscreenchange',
      handleFullscreenChange,
    )

    return () => {
      document.removeEventListener(
        'fullscreenchange',
        handleFullscreenChange,
      )
    }
  }, [])

  useEffect(() => {
    if (!analysisActive) {
      return
    }

    const intervalMilliseconds =
      Math.max(
        200,
        Math.round(1000 / frameRate),
      )

    void analyzeCurrentFrame()

    const intervalId = window.setInterval(
      () => {
        void analyzeCurrentFrame()
      },
      intervalMilliseconds,
    )

    return () => {
      window.clearInterval(intervalId)
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [analysisActive, frameRate])

  async function loadCameraDevices() {
    if (
      !navigator.mediaDevices
        ?.enumerateDevices
    ) {
      return
    }

    try {
      const devices =
        await navigator.mediaDevices
          .enumerateDevices()

      const cameras = devices.filter(
        (device) =>
          device.kind === 'videoinput',
      )

      setCameraDevices(cameras)

      if (
        cameras.length > 0 &&
        !cameras.some(
          (camera) =>
            camera.deviceId ===
            selectedCameraId,
        )
      ) {
        setSelectedCameraId(
          cameras[0].deviceId,
        )
      }
    } catch {
      // 카메라 오류 메시지를 우선 표시
    }
  }

  async function startCamera(
    requestedDeviceId =
      selectedCameraId,
  ) {
    setCameraError('')
    setAnalysisError('')
    setCameraReady(false)

    if (!window.isSecureContext) {
      setCameraError(
        '카메라는 localhost 또는 HTTPS 환경에서만 사용할 수 있습니다.',
      )
      return
    }

    if (
      !navigator.mediaDevices
        ?.getUserMedia
    ) {
      setCameraError(
        '현재 브라우저에서 카메라 기능을 지원하지 않습니다.',
      )
      return
    }

    stopAnalysis()
    releaseCameraStream()

    const requestId =
      ++cameraRequestIdRef.current

    setCameraStarting(true)

    try {
      let stream: MediaStream

      try {
        stream =
          await navigator.mediaDevices
            .getUserMedia({
              video: requestedDeviceId
                ? {
                    deviceId: {
                      exact:
                        requestedDeviceId,
                    },
                    width: {
                      ideal: 1920,
                    },
                    height: {
                      ideal: 1080,
                    },
                  }
                : {
                    facingMode: {
                      ideal: 'environment',
                    },
                    width: {
                      ideal: 1920,
                    },
                    height: {
                      ideal: 1080,
                    },
                  },
              audio: false,
            })
      } catch (error) {
        if (
          requestedDeviceId &&
          error instanceof DOMException &&
          error.name ===
            'OverconstrainedError'
        ) {
          stream =
            await navigator.mediaDevices
              .getUserMedia({
                video: {
                  facingMode: {
                    ideal:
                      'environment',
                  },
                  width: {
                    ideal: 1920,
                  },
                  height: {
                    ideal: 1080,
                  },
                },
                audio: false,
              })
        } else {
          throw error
        }
      }

      if (
        requestId !==
        cameraRequestIdRef.current
      ) {
        stream
          .getTracks()
          .forEach((track) =>
            track.stop(),
          )

        return
      }

      streamRef.current = stream

      if (videoRef.current) {
        videoRef.current.srcObject =
          stream

        await videoRef.current
          .play()
          .catch(() => undefined)
      }

      const currentDeviceId =
        stream
          .getVideoTracks()[0]
          ?.getSettings().deviceId ?? ''

      if (currentDeviceId) {
        setSelectedCameraId(
          currentDeviceId,
        )
      }

      setCameraActive(true)
      await loadCameraDevices()
    } catch (error) {
      setCameraError(
        getCameraErrorMessage(error),
      )

      setCameraActive(false)
    } finally {
      if (
        requestId ===
        cameraRequestIdRef.current
      ) {
        setCameraStarting(false)
      }
    }
  }

  function stopCamera() {
    cameraRequestIdRef.current += 1

    stopAnalysis()
    releaseCameraStream()

    setCameraActive(false)
    setCameraReady(false)
    setCameraStarting(false)
  }

  function releaseCameraStream() {
    streamRef.current
      ?.getTracks()
      .forEach((track) =>
        track.stop(),
      )

    streamRef.current = null

    if (videoRef.current) {
      videoRef.current.srcObject = null
    }
  }

  async function changeCamera(
    deviceId: string,
  ) {
    setSelectedCameraId(deviceId)
    await startCamera(deviceId)
  }

  async function startAnalysis() {
    if (
      !cameraActive ||
      !cameraReady
    ) {
      setAnalysisError(
        '카메라 영상이 준비된 후 분석을 시작해주세요.',
      )
      return
    }

    setAnalysisError('')
    setLastResult(null)
    setRecentResults([])
    setTotalFrames(0)

    frameCounterRef.current = 0
    sendingRef.current = false

    if (!USE_MOCK_ANALYSIS) {
      try {
        await connectWebSocket()
      } catch (error) {
        setAnalysisError(
          error instanceof Error
            ? error.message
            : '실시간 분석 서버에 연결하지 못했습니다.',
        )
        return
      }
    }

    analysisActiveRef.current = true
    setAnalysisActive(true)
  }

  function stopAnalysis() {
    analysisActiveRef.current = false
    sendingRef.current = false

    clearResponseTimer()
    closeWebSocket()

    setAnalysisActive(false)
  }

  async function analyzeCurrentFrame() {
    if (
      !analysisActiveRef.current ||
      sendingRef.current ||
      !videoRef.current ||
      videoRef.current.readyState < 2
    ) {
      return
    }

    sendingRef.current = true
    lastSentAtRef.current =
      performance.now()

    if (USE_MOCK_ANALYSIS) {
      try {
        const frameNumber =
          ++frameCounterRef.current

        await delay(
          70 +
            (frameNumber % 4) * 12,
        )

        if (
          !analysisActiveRef.current
        ) {
          return
        }

        const latencyMs = Math.round(
          performance.now() -
            lastSentAtRef.current,
        )

        handleAnalysisResult(
          createMockResult(
            frameNumber,
            latencyMs,
          ),
        )
      } finally {
        sendingRef.current = false
      }

      return
    }

    try {
      const frameBlob =
        await createCurrentFrameBlob()

      const socket = socketRef.current

      if (
        !socket ||
        socket.readyState !==
          WebSocket.OPEN
      ) {
        throw new Error(
          '실시간 분석 서버 연결이 끊어졌습니다.',
        )
      }

      socket.send(frameBlob)

      clearResponseTimer()

      responseTimerRef.current =
        window.setTimeout(() => {
          sendingRef.current = false

          setAnalysisError(
            '분석 서버 응답 시간이 초과되었습니다.',
          )
        }, 3000)
    } catch (error) {
      sendingRef.current = false

      setAnalysisError(
        error instanceof Error
          ? error.message
          : '프레임 전송에 실패했습니다.',
      )
    }
  }

  function handleAnalysisResult(
    result: RealtimeAnalysisResult,
  ) {
    setLastResult(result)

    setTotalFrames(
      (current) => current + 1,
    )

    setRecentResults(
      (current) =>
        [
          {
            ...result,
            id: crypto.randomUUID(),
          },
          ...current,
        ].slice(0, 3),
    )
  }

  async function createCurrentFrameBlob() {
    const video = videoRef.current
    const canvas =
      captureCanvasRef.current

    if (!video || !canvas) {
      throw new Error(
        '카메라 프레임을 생성하지 못했습니다.',
      )
    }

    canvas.width = 640
    canvas.height = 360

    const context =
      canvas.getContext('2d')

    if (!context) {
      throw new Error(
        '카메라 프레임을 생성하지 못했습니다.',
      )
    }

    context.drawImage(
      video,
      0,
      0,
      canvas.width,
      canvas.height,
    )

    return new Promise<Blob>(
      (resolve, reject) => {
        canvas.toBlob(
          (blob) => {
            if (blob) {
              resolve(blob)
            } else {
              reject(
                new Error(
                  '이미지 압축에 실패했습니다.',
                ),
              )
            }
          },
          'image/jpeg',
          0.82,
        )
      },
    )
  }

  function connectWebSocket() {
    return new Promise<void>(
      (resolve, reject) => {
        closeWebSocket()

        const socket =
          new WebSocket(
            WEBSOCKET_URL,
          )

        socket.binaryType =
          'arraybuffer'

        socketRef.current = socket

        let settled = false

        const connectionTimer =
          window.setTimeout(() => {
            if (settled) {
              return
            }

            settled = true
            socket.close()

            reject(
              new Error(
                '실시간 분석 서버 연결 시간이 초과되었습니다.',
              ),
            )
          }, 5000)

        socket.onopen = () => {
          if (settled) {
            return
          }

          settled = true

          window.clearTimeout(
            connectionTimer,
          )

          resolve()
        }

        socket.onmessage = (
          event,
        ) => {
          clearResponseTimer()
          sendingRef.current = false

          try {
            if (
              typeof event.data !==
              'string'
            ) {
              throw new Error(
                'JSON 응답이 아닙니다.',
              )
            }

            const result =
              JSON.parse(
                event.data,
              ) as RealtimeAnalysisResult

            handleAnalysisResult({
              ...result,
              latencyMs:
                result.latencyMs ??
                Math.round(
                  performance.now() -
                    lastSentAtRef.current,
                ),
            })
          } catch {
            setAnalysisError(
              '분석 서버 응답 형식이 올바르지 않습니다.',
            )
          }
        }

        socket.onerror = () => {
          if (!settled) {
            settled = true

            window.clearTimeout(
              connectionTimer,
            )

            reject(
              new Error(
                '실시간 분석 서버에 연결하지 못했습니다.',
              ),
            )
          }
        }

        socket.onclose = () => {
          clearResponseTimer()
          sendingRef.current = false

          if (
            analysisActiveRef.current
          ) {
            analysisActiveRef.current =
              false

            setAnalysisActive(false)

            setAnalysisError(
              '실시간 분석 서버 연결이 종료되었습니다.',
            )
          }
        }
      },
    )
  }

  function closeWebSocket() {
    const socket =
      socketRef.current

    if (socket) {
      socket.onclose = null
      socket.close()
    }

    socketRef.current = null
  }

  function clearResponseTimer() {
    if (
      responseTimerRef.current !== null
    ) {
      window.clearTimeout(
        responseTimerRef.current,
      )

      responseTimerRef.current = null
    }
  }

  async function toggleFullscreen() {
    const element =
      inspectionAreaRef.current

    if (!element) {
      return
    }

    try {
      if (!document.fullscreenElement) {
        await element.requestFullscreen()
      } else {
        await document.exitFullscreen()
      }
    } catch {
      setAnalysisError(
        '전체 화면 모드를 실행하지 못했습니다.',
      )
    }
  }

  return (
    <div className="p-4 sm:p-5 lg:p-6">
      {!fullscreen && (
        <header className="flex flex-col justify-between gap-4 xl:flex-row xl:items-start">
          <div>
            <div className="flex flex-wrap items-center gap-3">
              <h1 className="text-3xl font-bold text-[#172a3a]">
                실시간 영상 검사
              </h1>

              {USE_MOCK_ANALYSIS && (
                <span className="rounded-full bg-amber-100 px-3 py-1 text-xs font-bold text-amber-700">
                  MOCK ANALYSIS
                </span>
              )}
            </div>

            <p className="mt-2 text-[#697d90]">
              카메라 영상에서 검출 영역과
              판정 결과를 동시에 확인합니다.
            </p>
          </div>

          <div className="flex flex-wrap gap-2">
            <select
              value={selectedCameraId}
              disabled={
                cameraDevices.length ===
                0
              }
              onChange={(event) =>
                void changeCamera(
                  event.target.value,
                )
              }
              className="h-11 min-w-[180px] rounded-lg border border-[#d9e4ee] bg-white px-3 outline-none focus:border-[#0075c9]"
            >
              {cameraDevices.length ===
                0 && (
                <option value="">
                  카메라 검색 중
                </option>
              )}

              {cameraDevices.map(
                (device, index) => (
                  <option
                    key={
                      device.deviceId ||
                      `camera-${index}`
                    }
                    value={
                      device.deviceId
                    }
                  >
                    {device.label ||
                      `카메라 ${
                        index + 1
                      }`}
                  </option>
                ),
              )}
            </select>

            <button
              type="button"
              onClick={() =>
                void loadCameraDevices()
              }
              className="flex h-11 items-center gap-2 rounded-lg border border-[#d9e4ee] bg-white px-4 font-semibold hover:bg-[#f3f7fb]"
            >
              <RefreshCw size={17} />
              새로고침
            </button>

            <select
              value={frameRate}
              onChange={(event) =>
                setFrameRate(
                  Number(
                    event.target.value,
                  ),
                )
              }
              className="h-11 rounded-lg border border-[#d9e4ee] bg-white px-3 outline-none focus:border-[#0075c9]"
            >
              <option value={1}>
                분석 1 FPS
              </option>
              <option value={2}>
                분석 2 FPS
              </option>
              <option value={5}>
                분석 5 FPS
              </option>
            </select>
          </div>
        </header>
      )}

      {!fullscreen &&
        (cameraError ||
          analysisError) && (
          <div className="mt-4 flex items-start gap-2 rounded-lg border border-red-200 bg-red-50 px-4 py-3 text-sm text-red-700">
            <AlertCircle
              size={18}
              className="mt-0.5 shrink-0"
            />

            <div>
              {cameraError && (
                <p>{cameraError}</p>
              )}

              {analysisError && (
                <p>{analysisError}</p>
              )}
            </div>
          </div>
        )}

      <section
        ref={inspectionAreaRef}
        className={[
          'overflow-hidden rounded-xl border border-[#d9e4ee] bg-white',
          fullscreen
            ? 'h-screen rounded-none border-0'
            : 'mt-4',
        ].join(' ')}
      >
        <div
          className={[
            'relative overflow-hidden bg-[#081a2a]',
            fullscreen
              ? 'h-[calc(100vh-68px)]'
              : 'h-[calc(100vh-220px)] min-h-[560px]',
          ].join(' ')}
        >
          <video
            ref={videoRef}
            autoPlay
            muted
            playsInline
            onLoadedMetadata={() =>
              setCameraReady(true)
            }
            className="h-full w-full object-cover"
          />

          {lastResult?.detections.map(
            (detection, index) => (
              <DetectionOverlay
                key={`${detection.label}-${index}`}
                detection={detection}
              />
            ),
          )}

          <div className="absolute left-5 top-5 flex items-center gap-2 rounded-full bg-black/70 px-4 py-2 text-sm font-bold text-white backdrop-blur-sm">
            <span
              className={[
                'h-2.5 w-2.5 rounded-full',
                analysisActive
                  ? 'animate-pulse bg-emerald-400'
                  : 'bg-slate-400',
              ].join(' ')}
            />

            {analysisActive
              ? `LIVE · 분석 중 · ${frameRate} FPS`
              : 'LIVE · 분석 대기'}
          </div>

          {analysisActive && (
            <div className="pointer-events-none absolute inset-x-0 top-1/2 h-0.5 animate-pulse bg-cyan-400/70 shadow-[0_0_18px_4px_rgba(34,211,238,0.5)]" />
          )}

          {!cameraActive && (
            <div className="absolute inset-0 flex flex-col items-center justify-center bg-[#081a2a] text-slate-300">
              <VideoOff size={54} />

              <p className="mt-4 text-lg font-semibold">
                {cameraStarting
                  ? '카메라 연결 중'
                  : '카메라가 꺼져 있습니다.'}
              </p>
            </div>
          )}

          <RealtimeOverlay
            result={lastResult}
            recentResults={
              recentResults
            }
            analysisActive={
              analysisActive
            }
            totalFrames={totalFrames}
          />
        </div>

        <div className="flex h-[68px] flex-wrap items-center gap-2 border-t border-[#d9e4ee] bg-[#f8fafc] px-4">
          <button
            type="button"
            disabled={
              cameraStarting ||
              cameraActive
            }
            onClick={() =>
              void startCamera()
            }
            className="flex items-center gap-2 rounded-lg border border-[#d9e4ee] bg-white px-4 py-2 font-semibold hover:bg-[#f3f7fb] disabled:cursor-not-allowed disabled:opacity-40"
          >
            <Camera size={17} />
            카메라 시작
          </button>

          <button
            type="button"
            disabled={
              !cameraActive ||
              !cameraReady ||
              analysisActive
            }
            onClick={() =>
              void startAnalysis()
            }
            className="flex items-center gap-2 rounded-lg bg-[#0075c9] px-4 py-2 font-semibold text-white hover:bg-[#0065ad] disabled:cursor-not-allowed disabled:bg-slate-300"
          >
            <Play size={17} />
            분석 시작
          </button>

          <button
            type="button"
            disabled={!analysisActive}
            onClick={stopAnalysis}
            className="flex items-center gap-2 rounded-lg bg-[#263746] px-4 py-2 font-semibold text-white disabled:cursor-not-allowed disabled:opacity-40"
          >
            <Square size={15} />
            분석 중지
          </button>

          <button
            type="button"
            disabled={!cameraActive}
            onClick={stopCamera}
            className="rounded-lg border border-[#d9e4ee] bg-white px-4 py-2 font-semibold disabled:cursor-not-allowed disabled:opacity-40"
          >
            카메라 종료
          </button>

          <div className="hidden items-center gap-5 text-xs text-[#697d90] xl:flex">
            <span>
              해상도 1920 × 1080
            </span>

            <span>
              전송 640 × 360 JPEG
            </span>

            <span className="flex items-center gap-1.5">
              <Wifi size={15} />
              {USE_MOCK_ANALYSIS
                ? 'Mock 분석'
                : '서버 연결'}
            </span>
          </div>

          <button
            type="button"
            onClick={() =>
              void toggleFullscreen()
            }
            className="ml-auto flex items-center gap-2 rounded-lg border border-[#d9e4ee] bg-white px-4 py-2 font-semibold hover:bg-[#f3f7fb]"
          >
            <Expand size={17} />
            {fullscreen
              ? '전체 화면 종료'
              : '전체 화면'}
          </button>
        </div>

        <canvas
          ref={captureCanvasRef}
          className="hidden"
        />
      </section>
    </div>
  )
}

function RealtimeOverlay({
  result,
  recentResults,
  analysisActive,
  totalFrames,
}: {
  result: RealtimeAnalysisResult | null
  recentResults: RecentResult[]
  analysisActive: boolean
  totalFrames: number
}) {
  const normal =
    result?.finalResult === 'PASS'

  return (
    <aside className="absolute bottom-4 left-4 right-4 max-h-[48%] overflow-y-auto rounded-xl border border-white/20 bg-[#102438]/90 p-5 text-white shadow-2xl backdrop-blur-md md:bottom-auto md:left-auto md:right-5 md:top-5 md:w-[330px] md:max-h-[calc(100%-40px)]">
      <h2 className="text-xl font-bold">
        실시간 검사 결과
      </h2>

      <div className="mt-4 border-t border-white/15 pt-4">
        {!result ? (
          <div className="flex min-h-[180px] flex-col items-center justify-center text-center text-slate-300">
            <ScanLine size={38} />

            <p className="mt-4 font-semibold">
              {analysisActive
                ? '첫 분석 결과를 기다리는 중'
                : '분석 시작 전'}
            </p>

            <p className="mt-2 text-xs">
              실시간 분석을 시작하면 판정
              결과가 표시됩니다.
            </p>
          </div>
        ) : (
          <>
            <div className="flex items-end justify-between">
              <div>
                <p className="text-xs text-slate-300">
                  최종 판정
                </p>

                <p
                  className={[
                    'mt-1 text-6xl font-extrabold',
                    normal
                      ? 'text-white'
                      : 'text-red-400',
                  ].join(' ')}
                >
                  {normal ? 'OK' : 'NG'}
                </p>
              </div>

              <span
                className={[
                  'rounded-full px-4 py-2 text-sm font-bold',
                  normal
                    ? 'bg-white text-[#172a3a]'
                    : 'bg-red-500 text-white',
                ].join(' ')}
              >
                {(
                  result.confidence * 100
                ).toFixed(1)}
                %
              </span>
            </div>

            <div className="mt-5 divide-y divide-white/10">
              <OverlayRow
                label="조립 순서"
                value={
                  result.assemblyResult ===
                  'PASS'
                    ? '정상'
                    : '불량'
                }
                failure={
                  result.assemblyResult ===
                  'FAIL'
                }
              />

              <OverlayRow
                label="체결 상태"
                value={
                  result.fasteningResult ===
                  'PASS'
                    ? '정상'
                    : '불량'
                }
                failure={
                  result.fasteningResult ===
                  'FAIL'
                }
              />

              <OverlayRow
                label="부품 감지"
                value={`${result.detections.length}개`}
              />
            </div>

            <div className="mt-5 grid grid-cols-2 gap-3">
              <OverlayMetric
                label="분석 지연시간"
                value={`${result.latencyMs} ms`}
              />

              <OverlayMetric
                label="누적 프레임"
                value={totalFrames.toLocaleString()}
              />
            </div>

            <div className="mt-5 rounded-lg border border-white/15 bg-black/20 p-4">
              <p className="text-xs text-slate-300">
                최근 판정
              </p>

              <div className="mt-3 space-y-2">
                {recentResults.map(
                  (recent) => (
                    <div
                      key={recent.id}
                      className="flex items-center justify-between text-xs"
                    >
                      <span>
                        {formatTime(
                          recent.timestamp,
                        )}
                      </span>

                      <strong
                        className={
                          recent.finalResult ===
                          'PASS'
                            ? 'text-emerald-300'
                            : 'text-red-300'
                        }
                      >
                        {recent.finalResult ===
                        'PASS'
                          ? 'OK'
                          : 'NG'}
                        {' · '}
                        {(
                          recent.confidence *
                          100
                        ).toFixed(1)}
                        %
                      </strong>
                    </div>
                  ),
                )}

                {recentResults.length ===
                  0 && (
                  <p className="text-xs text-slate-400">
                    판정 기록 없음
                  </p>
                )}
              </div>
            </div>
          </>
        )}
      </div>
    </aside>
  )
}

function DetectionOverlay({
  detection,
}: {
  detection: Detection
}) {
  const normal =
    detection.result === 'PASS'

  return (
    <div
      className={[
        'pointer-events-none absolute border-[3px]',
        normal
          ? 'border-emerald-400'
          : 'border-red-500',
      ].join(' ')}
      style={{
        left: `${detection.x * 100}%`,
        top: `${detection.y * 100}%`,
        width: `${detection.width * 100}%`,
        height: `${detection.height * 100}%`,
      }}
    >
      <span
        className={[
          'absolute -top-7 left-[-3px] whitespace-nowrap px-2 py-1 text-xs font-bold text-white',
          normal
            ? 'bg-emerald-500'
            : 'bg-red-500',
        ].join(' ')}
      >
        {detection.label}{' '}
        {(
          detection.confidence * 100
        ).toFixed(0)}
        %
      </span>
    </div>
  )
}

function OverlayRow({
  label,
  value,
  failure = false,
}: {
  label: string
  value: string
  failure?: boolean
}) {
  return (
    <div className="flex items-center justify-between py-3 text-sm">
      <span className="text-slate-300">
        {label}
      </span>

      <strong
        className={
          failure
            ? 'text-red-300'
            : 'text-white'
        }
      >
        {value}
      </strong>
    </div>
  )
}

function OverlayMetric({
  label,
  value,
}: {
  label: string
  value: string
}) {
  return (
    <div>
      <p className="text-xs text-slate-300">
        {label}
      </p>

      <p className="mt-1 text-xl font-bold">
        {value}
      </p>
    </div>
  )
}

function createMockResult(
  frameNumber: number,
  latencyMs: number,
): RealtimeAnalysisResult {
  const assemblyFail =
    frameNumber % 17 === 0

  const fasteningFail =
    frameNumber % 11 === 0

  const finalResult: CheckResult =
    assemblyFail || fasteningFail
      ? 'FAIL'
      : 'PASS'

  const movement =
    Math.sin(frameNumber / 4) * 0.01

  return {
    finalResult,
    assemblyResult: assemblyFail
      ? 'FAIL'
      : 'PASS',
    fasteningResult: fasteningFail
      ? 'FAIL'
      : 'PASS',
    confidence:
      0.91 +
      (frameNumber % 7) * 0.01,
    latencyMs,
    timestamp: new Date().toISOString(),
    detections: [
      {
        label: 'BOLT',
        confidence: 0.97,
        x: 0.30 + movement,
        y: 0.17,
        width: 0.19,
        height: 0.56,
        result: assemblyFail
          ? 'FAIL'
          : 'PASS',
      },
      {
        label: 'WASHER',
        confidence: 0.94,
        x: 0.43 + movement,
        y: 0.46,
        width: 0.15,
        height: 0.14,
        result: assemblyFail
          ? 'FAIL'
          : 'PASS',
      },
      {
        label: 'NUT',
        confidence: 0.95,
        x: 0.51 + movement,
        y: 0.25,
        width: 0.17,
        height: 0.25,
        result: fasteningFail
          ? 'FAIL'
          : 'PASS',
      },
    ],
  }
}

function formatTime(value: string) {
  return new Intl.DateTimeFormat(
    'ko-KR',
    {
      hour: '2-digit',
      minute: '2-digit',
      second: '2-digit',
    },
  ).format(new Date(value))
}

function delay(milliseconds: number) {
  return new Promise<void>((resolve) => {
    window.setTimeout(
      resolve,
      milliseconds,
    )
  })
}

function getCameraErrorMessage(
  error: unknown,
) {
  if (!(error instanceof DOMException)) {
    return '카메라를 실행하지 못했습니다.'
  }

  if (
    error.name === 'NotAllowedError' ||
    error.name ===
      'PermissionDeniedError'
  ) {
    return '카메라 권한이 거부되었습니다. Chrome 주소창에서 카메라 권한을 허용해주세요.'
  }

  if (
    error.name === 'NotFoundError' ||
    error.name ===
      'DevicesNotFoundError'
  ) {
    return '연결된 카메라를 찾을 수 없습니다.'
  }

  if (
    error.name === 'NotReadableError' ||
    error.name === 'TrackStartError'
  ) {
    return '다른 프로그램에서 카메라를 사용 중인지 확인해주세요.'
  }

  return `카메라 오류: ${error.message}`
}