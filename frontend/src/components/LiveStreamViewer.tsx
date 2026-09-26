import { RefreshCw, Video } from 'lucide-react'
import { useState } from 'react'
import { getVisionStreamUrl } from '../services/inspectionApi'

export default function LiveStreamViewer() {
  const [cacheKey, setCacheKey] = useState(() => Date.now())
  const [streamError, setStreamError] = useState(false)

  return (
    <section className="mt-7 rounded-xl border border-[#d9e4ee] bg-white p-5">
      <div className="flex flex-wrap items-center justify-between gap-3">
        <div>
          <div className="flex items-center gap-2">
            <Video size={21} className="text-[#0075c9]" />
            <h2 className="text-xl font-bold">실시간 U-Net Segmentation 검사 영상</h2>
          </div>
          <p className="mt-2 text-sm text-[#697d90]">
            볼트와 Thread/Nut 영역은 파란색, 와셔는 노란색 마스크로 표시됩니다.
          </p>
        </div>
        <button
          type="button"
          onClick={() => {
            setStreamError(false)
            setCacheKey(Date.now())
          }}
          className="flex items-center gap-2 rounded-lg border border-[#bfd0df] px-4 py-2 text-sm font-semibold text-[#0075c9] hover:bg-blue-50"
        >
          <RefreshCw size={16} />
          스트림 재연결
        </button>
      </div>

      <div className="relative mt-5 flex min-h-[360px] items-center justify-center overflow-hidden rounded-xl bg-[#101820]">
        <img
          key={cacheKey}
          src={getVisionStreamUrl(cacheKey)}
          alt="실시간 볼트 체결 U-Net Segmentation 검사"
          className="max-h-[70vh] w-full object-contain"
          onLoad={() => setStreamError(false)}
          onError={() => setStreamError(true)}
        />
        {streamError && (
          <div className="absolute inset-0 flex items-center justify-center bg-[#101820] p-8 text-center text-white">
            <div>
              <p className="font-bold">영상 스트림에 연결할 수 없습니다.</p>
              <p className="mt-2 text-sm text-slate-300">
                Flask 서버, 카메라 연결 및 /api/v1/system/status를 확인하세요.
              </p>
            </div>
          </div>
        )}
      </div>
    </section>
  )
}
