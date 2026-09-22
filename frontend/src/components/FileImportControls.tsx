import JSZip from 'jszip'
import {
  Camera,
  FileArchive,
  FolderOpen,
  Images,
  LoaderCircle,
} from 'lucide-react'
import {
  type ChangeEvent,
  forwardRef,
  useEffect,
  useImperativeHandle,
  useRef,
  useState,
} from 'react'

export type FileImportControlsHandle = {
  openImagePicker: () => void
}

type FileImportControlsProps = {
  onFiles: (files: File[]) => void
  onError: (message: string) => void
}

const FileImportControls = forwardRef<
  FileImportControlsHandle,
  FileImportControlsProps
>(function FileImportControls(
  {
    onFiles,
    onError,
  },
  ref,
) {
  const imageInputRef =
    useRef<HTMLInputElement>(null)

  const cameraInputRef =
    useRef<HTMLInputElement>(null)

  const folderInputRef =
    useRef<HTMLInputElement>(null)

  const zipInputRef =
    useRef<HTMLInputElement>(null)

  const [readingZip, setReadingZip] =
    useState(false)

  useImperativeHandle(ref, () => ({
    openImagePicker() {
      imageInputRef.current?.click()
    },
  }))

  useEffect(() => {
    const folderInput = folderInputRef.current

    if (!folderInput) {
      return
    }

    folderInput.setAttribute(
      'webkitdirectory',
      '',
    )

    folderInput.setAttribute(
      'directory',
      '',
    )
  }, [])

  function handleImageFiles(
    event: ChangeEvent<HTMLInputElement>,
  ) {
    const files = Array.from(
      event.target.files ?? [],
    )

    if (files.length > 0) {
      onFiles(files)
    }

    event.target.value = ''
  }

  async function handleZipFile(
    event: ChangeEvent<HTMLInputElement>,
  ) {
    const zipFile = event.target.files?.[0]

    event.target.value = ''

    if (!zipFile) {
      return
    }

    if (!zipFile.name.toLowerCase().endsWith('.zip')) {
      onError('ZIP 파일만 선택할 수 있습니다.')
      return
    }

    setReadingZip(true)
    onError('')

    try {
      const zip = await JSZip.loadAsync(zipFile)

      const imageEntries = Object.values(
        zip.files,
      ).filter(
        (entry) =>
          !entry.dir &&
          /\.(jpg|jpeg|png)$/i.test(entry.name),
      )

      if (imageEntries.length === 0) {
        onError(
          'ZIP 안에서 JPG, JPEG, PNG 이미지를 찾지 못했습니다.',
        )
        return
      }

      const extractedFiles: File[] = []

      for (const entry of imageEntries) {
        const blob = await entry.async('blob')

        const fileName =
          entry.name.split('/').pop() ||
          entry.name

        const extension =
          fileName
            .split('.')
            .pop()
            ?.toLowerCase() ?? ''

        const mimeType =
          extension === 'png'
            ? 'image/png'
            : 'image/jpeg'

        extractedFiles.push(
          new File(
            [blob],
            fileName,
            {
              type: mimeType,
              lastModified:
                zipFile.lastModified,
            },
          ),
        )
      }

      onFiles(extractedFiles)
    } catch (error) {
      const message =
        error instanceof Error
          ? error.message
          : '알 수 없는 ZIP 오류'

      onError(
        `ZIP 파일을 읽지 못했습니다: ${message}`,
      )
    } finally {
      setReadingZip(false)
    }
  }

  return (
    <>
      <input
        ref={imageInputRef}
        type="file"
        accept=".jpg,.jpeg,.png"
        multiple
        hidden
        onChange={handleImageFiles}
      />

      <input
        ref={cameraInputRef}
        type="file"
        accept="image/*"
        capture="environment"
        hidden
        onChange={handleImageFiles}
      />

      <input
        ref={folderInputRef}
        type="file"
        accept=".jpg,.jpeg,.png"
        multiple
        hidden
        onChange={handleImageFiles}
      />

      <input
        ref={zipInputRef}
        type="file"
        accept=".zip,application/zip"
        hidden
        onChange={(event) =>
          void handleZipFile(event)
        }
      />

      <div className="flex flex-wrap gap-2">
        <button
          type="button"
          onClick={() =>
            cameraInputRef.current?.click()
          }
          className="flex items-center gap-2 rounded-lg border border-[#d9e4ee] bg-white px-4 py-3 font-semibold hover:bg-[#f3f7fb]"
        >
          <Camera size={18} />
          촬영
        </button>

        <button
          type="button"
          onClick={() =>
            imageInputRef.current?.click()
          }
          className="flex items-center gap-2 rounded-lg bg-[#0075c9] px-4 py-3 font-semibold text-white hover:bg-[#0065ad]"
        >
          <Images size={18} />
          이미지
        </button>

        <button
          type="button"
          onClick={() =>
            folderInputRef.current?.click()
          }
          className="flex items-center gap-2 rounded-lg border border-[#d9e4ee] bg-white px-4 py-3 font-semibold hover:bg-[#f3f7fb]"
        >
          <FolderOpen size={18} />
          폴더
        </button>

        <button
          type="button"
          disabled={readingZip}
          onClick={() =>
            zipInputRef.current?.click()
          }
          className="flex items-center gap-2 rounded-lg border border-[#d9e4ee] bg-white px-4 py-3 font-semibold hover:bg-[#f3f7fb] disabled:cursor-not-allowed disabled:opacity-50"
        >
          {readingZip ? (
            <LoaderCircle
              size={18}
              className="animate-spin"
            />
          ) : (
            <FileArchive size={18} />
          )}

          {readingZip ? 'ZIP 확인 중' : 'ZIP'}
        </button>
      </div>
    </>
  )
})

export default FileImportControls