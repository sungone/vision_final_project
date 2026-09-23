import {
  Camera,
  RefreshCw,
  Square,
  Video,
  VideoOff,
} from 'lucide-react'
import {
  useEffect,
  useRef,
  useState,
} from 'react'
import { useLocalStorageState } from '../hooks/useLocalStorageState'

type CameraLiveCaptureProps = {
  onCapture: (file: File) => void
  onError: (message: string) => void
}

export default function CameraLiveCapture({
  onCapture,
  onError,
}: CameraLiveCaptureProps) {
  const [cameraDevices, setCameraDevices] =
    useState<MediaDeviceInfo[]>([])

  const [selectedCameraId, setSelectedCameraId] =
    useLocalStorageState(
      'smart-bolt-camera-device',
      '',
    )

  const [cameraActive, setCameraActive] =
    useState(false)

  const [cameraReady, setCameraReady] =
    useState(false)

  const [cameraStarting, setCameraStarting] =
    useState(false)

  const [cameraError, setCameraError] =
    useState('')

  const [captureMessage, setCaptureMessage] =
    useState('')

  const videoRef =
    useRef<HTMLVideoElement>(null)

  const streamRef =
    useRef<MediaStream | null>(null)

  const requestIdRef = useRef(0)

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

      stopCamera()
    }
    // 최초 진입 시 한 번만 카메라 실행
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [])

  async function loadCameraDevices() {
    if (!navigator.mediaDevices?.enumerateDevices) {
      return
    }

    try {
      const devices =
        await navigator.mediaDevices.enumerateDevices()

      const cameras = devices.filter(
        (device) =>
          device.kind === 'videoinput',
      )

      setCameraDevices(cameras)

      if (
        cameras.length > 0 &&
        !cameras.some(
          (camera) =>
            camera.deviceId === selectedCameraId,
        )
      ) {
        setSelectedCameraId(
          cameras[0].deviceId,
        )
      }
    } catch {
      // 카메라 실행 오류 메시지를 우선 표시
    }
  }

  async function startCamera(
    requestedDeviceId = selectedCameraId,
  ) {
    setCameraError('')
    setCaptureMessage('')
    setCameraReady(false)

    if (!window.isSecureContext) {
      const message =
        '카메라는 localhost 또는 HTTPS 환경에서만 사용할 수 있습니다.'

      setCameraError(message)
      onError(message)
      return
    }

    if (!navigator.mediaDevices?.getUserMedia) {
      const message =
        '현재 브라우저에서 카메라 기능을 지원하지 않습니다.'

      setCameraError(message)
      onError(message)
      return
    }

    releaseCurrentStream()

    const requestId =
      ++requestIdRef.current

    setCameraStarting(true)

    try {
      let stream: MediaStream

      try {
        stream =
          await navigator.mediaDevices.getUserMedia({
            video: requestedDeviceId
              ? {
                  deviceId: {
                    exact: requestedDeviceId,
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
            await navigator.mediaDevices.getUserMedia({
              video: {
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
        } else {
          throw error
        }
      }

      if (
        requestId !== requestIdRef.current
      ) {
        stream
          .getTracks()
          .forEach((track) => track.stop())

        return
      }

      streamRef.current = stream

      if (videoRef.current) {
        videoRef.current.srcObject = stream

        await videoRef.current
          .play()
          .catch(() => undefined)
      }

      setCameraActive(true)

      const currentDeviceId =
        stream
          .getVideoTracks()[0]
          ?.getSettings().deviceId ?? ''

      if (currentDeviceId) {
        setSelectedCameraId(currentDeviceId)
      }

      await loadCameraDevices()
    } catch (error) {
      const message =
        getCameraErrorMessage(error)

      setCameraError(message)
      setCameraActive(false)
      onError(message)
    } finally {
      if (
        requestId === requestIdRef.current
      ) {
        setCameraStarting(false)
      }
    }
  }

  function stopCamera() {
    requestIdRef.current += 1
    releaseCurrentStream()
    setCameraActive(false)
    setCameraReady(false)
    setCameraStarting(false)
  }

  function releaseCurrentStream() {
    streamRef.current
      ?.getTracks()
      .forEach((track) => track.stop())

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

  async function captureCurrentFrame() {
    const video = videoRef.current

    if (
      !video ||
      !cameraActive ||
      video.readyState < 2
    ) {
      const message =
        '카메라 영상이 준비되지 않았습니다.'

      setCameraError(message)
      return
    }

    const canvas =
      document.createElement('canvas')

    canvas.width = video.videoWidth
    canvas.height = video.videoHeight

    const context =
      canvas.getContext('2d')

    if (!context) {
      setCameraError(
        '촬영 이미지를 생성하지 못했습니다.',
      )
      return
    }

    context.drawImage(
      video,
      0,
      0,
      canvas.width,
      canvas.height,
    )

    try {
      const blob =
        await canvasToBlob(canvas)

      const timestamp =
        new Date()
          .toISOString()
          .replace(/[:.]/g, '-')

      const file = new File(
        [blob],
        `camera_${timestamp}.jpg`,
        {
          type: 'image/jpeg',
          lastModified: Date.now(),
        },
      )

      onCapture(file)

      setCaptureMessage(
        '촬영한 이미지를 검사 목록에 추가했습니다.',
      )

      window.setTimeout(() => {
        setCaptureMessage('')
      }, 2500)
    } catch {
      setCameraError(
        '촬영 이미지를 생성하지 못했습니다.',
      )
    }
  }

  return (
    <section className="mt-6 rounded-xl border border-[#d9e4ee] bg-white p-5">
      <div className="flex flex-col justify-between gap-4 sm:flex-row sm:items-start">
        <div>
          <div className="flex items-center gap-3">
            <h2 className="text-xl font-bold">
              실시간 카메라
            </h2>

            <span
              className={[
                'rounded-full px-3 py-1 text-xs font-semibold',
                cameraActive
                  ? 'bg-emerald-100 text-emerald-700'
                  : 'bg-slate-100 text-slate-600',
              ].join(' ')}
            >
              {cameraActive
                ? '연결됨'
                : '연결 대기'}
            </span>
          </div>

          <p className="mt-1 text-sm text-[#697d90]">
            실시간 영상을 확인하고 현재 장면을
            검사 이미지로 촬영합니다.
          </p>
        </div>

        <div className="flex flex-wrap gap-2">
          <select
            value={selectedCameraId}
            disabled={
              cameraDevices.length === 0
            }
            onChange={(event) =>
              void changeCamera(
                event.target.value,
              )
            }
            className="h-11 min-w-[180px] rounded-lg border border-[#d9e4ee] bg-white px-3 text-sm outline-none focus:border-[#0075c9] disabled:opacity-50"
          >
            {cameraDevices.length === 0 && (
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
                  value={device.deviceId}
                >
                  {device.label ||
                    `카메라 ${index + 1}`}
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
        </div>
      </div>

      {cameraError && (
        <div className="mt-4 rounded-lg border border-red-200 bg-red-50 px-4 py-3 text-sm text-red-700">
          {cameraError}
        </div>
      )}

      {captureMessage && (
        <div className="mt-4 rounded-lg border border-emerald-200 bg-emerald-50 px-4 py-3 text-sm text-emerald-700">
          {captureMessage}
        </div>
      )}

      <div className="relative mt-5 overflow-hidden rounded-xl bg-[#0b1f33]">
        <video
          ref={videoRef}
          autoPlay
          muted
          playsInline
          onLoadedMetadata={() =>
            setCameraReady(true)
          }
          className="aspect-video w-full object-contain"
        />

        {!cameraActive && (
          <div className="absolute inset-0 flex flex-col items-center justify-center text-slate-300">
            {cameraStarting ? (
              <>
                <Video
                  size={42}
                  className="animate-pulse"
                />

                <p className="mt-3 text-sm">
                  카메라를 연결하고 있습니다.
                </p>
              </>
            ) : (
              <>
                <VideoOff size={42} />

                <p className="mt-3 text-sm">
                  카메라 미리보기가 꺼져
                  있습니다.
                </p>
              </>
            )}
          </div>
        )}
      </div>

      <div className="mt-4 flex flex-wrap gap-3">
        <button
          type="button"
          disabled={
            cameraStarting ||
            (cameraActive && cameraReady)
          }
          onClick={() => void startCamera()}
          className="flex items-center gap-2 rounded-lg border border-[#d9e4ee] bg-white px-5 py-3 font-semibold hover:bg-[#f3f7fb] disabled:cursor-not-allowed disabled:opacity-40"
        >
          <Video size={18} />
          {cameraStarting
            ? '연결 중'
            : '카메라 시작'}
        </button>

        <button
          type="button"
          disabled={
            !cameraActive || !cameraReady
          }
          onClick={() =>
            void captureCurrentFrame()
          }
          className="flex items-center gap-2 rounded-lg bg-[#0075c9] px-5 py-3 font-semibold text-white hover:bg-[#0065ad] disabled:cursor-not-allowed disabled:bg-slate-300"
        >
          <Camera size={18} />
          현재 화면 촬영
        </button>

        <button
          type="button"
          disabled={!cameraActive}
          onClick={stopCamera}
          className="flex items-center gap-2 rounded-lg border border-[#d9e4ee] bg-white px-5 py-3 font-semibold hover:bg-[#f3f7fb] disabled:cursor-not-allowed disabled:opacity-40"
        >
          <Square size={16} />
          카메라 종료
        </button>
      </div>

      <p className="mt-4 text-xs text-[#697d90]">
        촬영한 이미지는 아래 검사 이미지 목록에
        추가됩니다. 실제 검사는 이미지 선택 후 검사
        버튼을 눌러 실행합니다.
      </p>
    </section>
  )
}

function canvasToBlob(
  canvas: HTMLCanvasElement,
) {
  return new Promise<Blob>(
    (resolve, reject) => {
      canvas.toBlob(
        (blob) => {
          if (blob) {
            resolve(blob)
          } else {
            reject(
              new Error(
                '이미지 변환에 실패했습니다.',
              ),
            )
          }
        },
        'image/jpeg',
        0.92,
      )
    },
  )
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
    return '카메라 권한이 거부되었습니다. Chrome 주소창의 카메라 권한을 허용해주세요.'
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
    return '다른 프로그램이 카메라를 사용 중인지 확인해주세요.'
  }

  if (
    error.name ===
    'OverconstrainedError'
  ) {
    return '선택한 카메라 또는 해상도를 사용할 수 없습니다.'
  }

  return `카메라 오류: ${error.message}`
}