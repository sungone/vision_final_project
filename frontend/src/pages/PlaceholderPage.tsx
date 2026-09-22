type PlaceholderPageProps = {
  title: string
  description: string
}

export default function PlaceholderPage({
  title,
  description,
}: PlaceholderPageProps) {
  return (
    <div className="p-5 sm:p-7 lg:p-9">
      <h1 className="text-3xl font-bold text-[#172a3a]">{title}</h1>
      <p className="mt-2 text-[#697d90]">{description}</p>

      <div className="mt-8 rounded-xl border border-[#d9e4ee] bg-white p-10 text-center">
        <p className="font-semibold text-[#172a3a]">
          다음 구현 단계에서 화면이 추가됩니다.
        </p>
      </div>
    </div>
  )
}