import {
  Camera,
  CheckCircle2,
  Database,
  FileArchive,
  HardDrive,
  RefreshCw,
  Server,
  ShieldCheck,
  VideoOff,
  XCircle,
} from 'lucide-react'
import type { LucideIcon } from 'lucide-react'
import {
  useEffect,
  useRef,
  useState,
} from 'react'

type CameraPermission =
  | 'UNKNOWN'
  | 'GRANTED'
  | 'DENIED'

type ServiceStatus =
  | 'CONNECTED'
  | 'DISCONNECTED'
  | 'UNKNOWN'

export default function SettingsPage() {
  const [cameraDevices, setCameraDevices] =
    useState<MediaDeviceInfo[]>([])

  const [selectedCameraId, setSelectedCameraId] =
    useState('')

  const [cameraPermission, setCameraPermission] =
    useState<CameraPermission>('UNKNOWN')

  const [cameraError, setCameraError] = useState('')
  const [cameraStream, setCameraStream] =
    useState<MediaStream | null>(null)

  const videoRef = useRef<HTMLVideoElement>(null)
  const streamRef = useRef<MediaStream | null>(null)

  useEffect(() => {
    void loadCameraDevices()

    return () => {
      streamRef.current
        ?.getTracks()
        .forEach((track) => track.stop())
    }
  }, [])

  useEffect(() => {
    if (!videoRef.current) {
      return
    }

    videoRef.current.srcObject = cameraStream
  }, [cameraStream])

  async function loadCameraDevices() {
    setCameraError('')

    if (!navigator.mediaDevices?.enumerateDevices) {
      setCameraError(
        '현재 브라우저에서 카메라 장치 조회를 지원하지 않습니다.',
      )
      return
    }

    try {
      const devices =
        await navigator.mediaDevices.enumerateDevices()

      const cameras = devices.filter(
        (device) => device.kind === 'videoinput',
      )

      setCameraDevices(cameras)

      if (
        cameras.length > 0 &&
        !selectedCameraId
      ) {
        setSelectedCameraId(cameras[0].deviceId)
      }
    } catch (error) {
      setCameraError(getCameraErrorMessage(error))
    }
  }

  async function testCamera() {
    setCameraError('')
    stopCamera()

    if (!navigator.mediaDevices?.getUserMedia) {
      setCameraError(
        '현재 브라우저에서 카메라 촬영을 지원하지 않습니다.',
      )
      return
    }

    const videoConstraints:
      | boolean
      | MediaTrackConstraints =
      selectedCameraId
        ? {
            deviceId: {
              exact: selectedCameraId,
            },
            width: {
              ideal: 1920,
            },
            height: {
              ideal: 1080,
            },
          }
        : {
            width: {
              ideal: 1920,
            },
            height: {
              ideal: 1080,
            },
          }

    try {
      const stream =
        await navigator.mediaDevices.getUserMedia({
          video: videoConstraints,
          audio: false,
        })

      streamRef.current = stream
      setCameraStream(stream)
      setCameraPermission('GRANTED')

      const devices =
        await navigator.mediaDevices.enumerateDevices()

      const cameras = devices.filter(
        (device) => device.kind === 'videoinput',
      )

      setCameraDevices(cameras)

      const currentDeviceId =
        stream
          .getVideoTracks()[0]
          ?.getSettings().deviceId ?? ''

      if (currentDeviceId) {
        setSelectedCameraId(currentDeviceId)
      }
    } catch (error) {
      setCameraPermission('DENIED')
      setCameraError(getCameraErrorMessage(error))
    }
  }

  function stopCamera() {
    streamRef.current
      ?.getTracks()
      .forEach((track) => track.stop())

    streamRef.current = null
    setCameraStream(null)
  }

  function changeCamera(deviceId: string) {
    stopCamera()
    setSelectedCameraId(deviceId)
  }

  return (
    <div className="p-5 sm:p-7 lg:p-9">
      <header className="flex flex-col justify-between gap-4 sm:flex-row sm:items-start">
        <div>
          <h1 className="text-3xl font-bold text-[#172a3a]">
            환경 설정
          </h1>

          <p className="mt-2 text-[#697d90]">
            검사 기준과 장치·저장소·서비스 상태를
            확인합니다.
          </p>
        </div>

        <div className="flex w-fit items-center gap-2 rounded-lg border border-[#d9e4ee] bg-[#f3f7fb] px-4 py-3 text-sm">
          <ShieldCheck
            size={18}
            className="text-[#0075c9]"
          />
          공용 검사 기준은 조회 전용입니다.
        </div>
      </header>

      <div className="mt-7 grid gap-6 xl:grid-cols-2">
        <InspectionCriteriaCard />

        <section className="rounded-xl border border-[#d9e4ee] bg-white p-5">
          <div className="flex items-center justify-between">
            <div>
              <h2 className="text-xl font-bold">
                카메라 설정
              </h2>

              <p className="mt-1 text-sm text-[#697d90]">
                이 브라우저와 기기에만 적용됩니다.
              </p>
            </div>

            <CameraStatusBadge
              permission={cameraPermission}
            />
          </div>

          {cameraError && (
            <div className="mt-5 flex items-start gap-2 rounded-lg border border-red-200 bg-red-50 p-4 text-sm text-red-700">
              <XCircle
                size={18}
                className="mt-0.5 shrink-0"
              />
              {cameraError}
            </div>
          )}

          <div className="mt-5">
            <label className="text-sm text-[#697d90]">
              카메라 장치
            </label>

            <div className="mt-2 flex flex-col gap-3 sm:flex-row">
              <select
                value={selectedCameraId}
                onChange={(event) =>
                  changeCamera(event.target.value)
                }
                className="h-11 min-w-0 flex-1 rounded-lg border border-[#d9e4ee] bg-[#f8fafc] px-3 outline-none focus:border-[#0075c9]"
              >
                {cameraDevices.length === 0 && (
                  <option value="">
                    검색된 카메라 없음
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
                className="flex h-11 items-center justify-center gap-2 rounded-lg border border-[#d9e4ee] px-4 font-semibold hover:bg-[#f3f7fb]"
              >
                <RefreshCw size={17} />
                새로고침
              </button>
            </div>
          </div>

          <div className="mt-5 grid gap-4 sm:grid-cols-2">
            <SettingValue
              label="촬영 해상도"
              value="1920 × 1080"
            />

            <SettingValue
              label="카메라 권한"
              value={getPermissionLabel(
                cameraPermission,
              )}
            />
          </div>

          <div className="mt-5 overflow-hidden rounded-xl border border-[#d9e4ee] bg-[#0b1f33]">
            {cameraStream ? (
              <video
                ref={videoRef}
                autoPlay
                muted
                playsInline
                className="aspect-video w-full object-cover"
              />
            ) : (
              <div className="flex aspect-video flex-col items-center justify-center text-slate-300">
                <VideoOff size={38} />

                <p className="mt-3 text-sm">
                  카메라 미리보기가 꺼져 있습니다.
                </p>
              </div>
            )}
          </div>

          <div className="mt-4 flex flex-wrap gap-3">
            <button
              type="button"
              onClick={() => void testCamera()}
              className="flex items-center gap-2 rounded-lg bg-[#0075c9] px-5 py-3 font-semibold text-white hover:bg-[#0065ad]"
            >
              <Camera size={18} />
              카메라 테스트
            </button>

            <button
              type="button"
              disabled={!cameraStream}
              onClick={stopCamera}
              className="rounded-lg border border-[#d9e4ee] px-5 py-3 font-semibold disabled:cursor-not-allowed disabled:opacity-40"
            >
              미리보기 종료
            </button>
          </div>
        </section>
      </div>

      <div className="mt-6 grid gap-6 xl:grid-cols-2">
        <FilePolicyCard />
        <StorageCard />
      </div>

      <SystemInformation />
    </div>
  )
}

function InspectionCriteriaCard() {
  return (
    <section className="rounded-xl border border-[#d9e4ee] bg-white p-5">
      <div className="flex items-center justify-between">
        <h2 className="text-xl font-bold">
          검사 기준
        </h2>

        <span className="rounded-full bg-slate-100 px-3 py-1 text-xs font-semibold text-slate-600">
          조회 전용
        </span>
      </div>

      <div className="mt-5 divide-y divide-[#e1e9f0]">
        <InformationRow
          label="필수 부품"
          value="볼트 · 와셔 · 너트"
        />

        <InformationRow
          label="정상 조립 순서"
          value="볼트 → 와셔 → 너트"
        />

        <InformationRow
          label="간격 허용 범위"
          value="미설정"
          warning
        />

        <InformationRow
          label="노출 길이 허용 범위"
          value="미설정"
          warning
        />

        <InformationRow
          label="너트 기울기 허용값"
          value="미설정"
          warning
        />
      </div>

      <div className="mt-5 rounded-lg border border-amber-200 bg-amber-50 p-4 text-sm text-amber-800">
        실제 데이터 검증 전까지 허용 범위를 임의로
        설정하지 않습니다.
      </div>
    </section>
  )
}

function FilePolicyCard() {
  return (
    <section className="rounded-xl border border-[#d9e4ee] bg-white p-5">
      <div className="flex items-center gap-3">
        <div className="rounded-lg bg-blue-50 p-2 text-[#0075c9]">
          <FileArchive size={22} />
        </div>

        <h2 className="text-xl font-bold">
          파일 및 배치
        </h2>
      </div>

      <div className="mt-5 divide-y divide-[#e1e9f0]">
        <InformationRow
          label="지원 형식"
          value="JPG · JPEG · PNG"
        />

        <InformationRow
          label="이미지 제한"
          value="파일당 최대 10MB"
        />

        <InformationRow
          label="입력 방식"
          value="다중 이미지 · 카메라"
        />

        <InformationRow
          label="배치 처리"
          value="선택 이미지 단위 검사"
        />
      </div>

      <p className="mt-5 text-sm text-[#697d90]">
        폴더 및 ZIP 자동 검사는 백엔드 배치 API가
        추가된 후 연결합니다.
      </p>
    </section>
  )
}

function StorageCard() {
  return (
    <section className="rounded-xl border border-[#d9e4ee] bg-white p-5">
      <div className="flex items-center gap-3">
        <div className="rounded-lg bg-cyan-50 p-2 text-[#00a9ce]">
          <HardDrive size={22} />
        </div>

        <h2 className="text-xl font-bold">저장소</h2>
      </div>

      <div className="mt-5 divide-y divide-[#e1e9f0]">
        <InformationRow
          label="보관 정책"
          value="사용자가 삭제할 때까지"
        />

        <InformationRow
          label="저장 이미지"
          value="2,496개"
        />

        <InformationRow
          label="사용량"
          value="4.8 GB"
        />
      </div>

      <div className="mt-5">
        <div className="flex justify-between text-sm text-[#697d90]">
          <span>저장소 사용량</span>
          <span>32%</span>
        </div>

        <div className="mt-2 h-3 overflow-hidden rounded-full bg-[#e8eff5]">
          <div className="h-full w-[32%] rounded-full bg-[#00a9ce]" />
        </div>
      </div>

      <p className="mt-4 text-sm text-[#697d90]">
        이미지 삭제는 검사 이력 화면에서 수행합니다.
      </p>
    </section>
  )
}

function SystemInformation() {
  return (
    <section className="mt-6 rounded-xl border border-[#d9e4ee] bg-white p-5">
      <h2 className="text-xl font-bold">
        시스템 정보
      </h2>

      <div className="mt-5 grid gap-4 sm:grid-cols-2 xl:grid-cols-4">
        <ServiceCard
          icon={Server}
          name="Spring Boot"
          status="UNKNOWN"
          label="연결 대기"
          detail="http://localhost:8080"
        />

        <ServiceCard
          icon={Camera}
          name="Vision Service"
          status="UNKNOWN"
          label="연결 대기"
          detail="http://localhost:8000"
        />

        <ServiceCard
          icon={Database}
          name="MySQL"
          status="UNKNOWN"
          label="백엔드 연결 후 확인"
          detail="Port 3306"
        />

        <ServiceCard
          icon={ShieldCheck}
          name="프로그램 정보"
          status="CONNECTED"
          label="프론트엔드 정상"
          detail="Smart Bolt Vision Program"
        />
      </div>
    </section>
  )
}

function ServiceCard({
  icon: Icon,
  name,
  status,
  label,
  detail,
}: {
  icon: LucideIcon
  name: string
  status: ServiceStatus
  label: string
  detail: string
}) {
  const statusColor = getServiceStatusColor(status)

  return (
    <article className="rounded-xl border border-[#dce6ef] bg-[#f3f7fb] p-4">
      <div className="flex items-center gap-3">
        <div className="rounded-lg bg-white p-2 text-[#0075c9]">
          <Icon size={20} />
        </div>

        <div>
          <p className="font-bold">{name}</p>

          <div className="mt-1 flex items-center gap-2">
            <span
              className={`h-2.5 w-2.5 rounded-full ${statusColor}`}
            />

            <span className="text-xs text-[#697d90]">
              {label}
            </span>
          </div>
        </div>
      </div>

      <p className="mt-4 break-all text-xs text-[#697d90]">
        {detail}
      </p>
    </article>
  )
}

function CameraStatusBadge({
  permission,
}: {
  permission: CameraPermission
}) {
  if (permission === 'GRANTED') {
    return (
      <span className="flex items-center gap-1 rounded-full bg-emerald-100 px-3 py-1 text-xs font-semibold text-emerald-700">
        <CheckCircle2 size={14} />
        허용됨
      </span>
    )
  }

  if (permission === 'DENIED') {
    return (
      <span className="flex items-center gap-1 rounded-full bg-red-100 px-3 py-1 text-xs font-semibold text-red-700">
        <XCircle size={14} />
        거부됨
      </span>
    )
  }

  return (
    <span className="rounded-full bg-slate-100 px-3 py-1 text-xs font-semibold text-slate-600">
      확인 전
    </span>
  )
}

function SettingValue({
  label,
  value,
}: {
  label: string
  value: string
}) {
  return (
    <div>
      <p className="text-sm text-[#697d90]">
        {label}
      </p>

      <div className="mt-2 rounded-lg border border-[#d9e4ee] bg-[#f8fafc] px-4 py-3 font-semibold">
        {value}
      </div>
    </div>
  )
}

function InformationRow({
  label,
  value,
  warning = false,
}: {
  label: string
  value: string
  warning?: boolean
}) {
  return (
    <div className="flex items-center justify-between gap-5 py-4">
      <span className="text-sm text-[#697d90]">
        {label}
      </span>

      <strong
        className={[
          'text-right text-sm',
          warning ? 'text-amber-600' : '',
        ].join(' ')}
      >
        {value}
      </strong>
    </div>
  )
}

function getPermissionLabel(
  permission: CameraPermission,
) {
  const labels: Record<CameraPermission, string> = {
    UNKNOWN: '확인 전',
    GRANTED: '허용됨',
    DENIED: '거부됨',
  }

  return labels[permission]
}

function getServiceStatusColor(
  status: ServiceStatus,
) {
  const colors: Record<ServiceStatus, string> = {
    CONNECTED: 'bg-emerald-500',
    DISCONNECTED: 'bg-red-500',
    UNKNOWN: 'bg-slate-400',
  }

  return colors[status]
}

function getCameraErrorMessage(error: unknown) {
  if (!(error instanceof DOMException)) {
    return '카메라를 실행하지 못했습니다.'
  }

  if (
    error.name === 'NotAllowedError' ||
    error.name === 'PermissionDeniedError'
  ) {
    return '카메라 권한이 거부되었습니다. Chrome 주소창의 카메라 권한을 허용해주세요.'
  }

  if (
    error.name === 'NotFoundError' ||
    error.name === 'DevicesNotFoundError'
  ) {
    return '사용 가능한 카메라를 찾을 수 없습니다.'
  }

  if (
    error.name === 'NotReadableError' ||
    error.name === 'TrackStartError'
  ) {
    return '다른 프로그램에서 카메라를 사용 중인지 확인해주세요.'
  }

  if (error.name === 'OverconstrainedError') {
    return '선택한 카메라 또는 해상도를 사용할 수 없습니다.'
  }

  return `카메라 오류: ${error.message}`
}