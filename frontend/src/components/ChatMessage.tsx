import Markdown from "react-markdown"
import { parseCollegeFactContent, type CollegeFact } from "../lib/collegeFacts"
import { normalizeAssistantMarkdown } from "../lib/assistantMarkdown"

export type Message = {
  role: "user" | "assistant"
  content: string
}

type ChatMessageProps = {
  message: Message
}

export function ChatMessage({ message }: ChatMessageProps) {
  if (message.role === "user") {
    return (
      <div className="flex justify-end">
        <div className="dream-message max-w-[70%] rounded-2xl px-4 py-2.5 text-[#383748]">
          <p className="whitespace-pre-wrap leading-7">
            {message.content}
          </p>
        </div>
      </div>
    )
  }

  const parts = parseCollegeFactContent(message.content)
  const isChinese = /[\u3400-\u9fff]/.test(message.content)

  return (
    <div className="max-w-2xl space-y-4">
      {parts.map((part, index) => part.type === "college" ? (
        <CollegeFactCard key={`college-${index}`} fact={part.fact} isChinese={isChinese} />
      ) : (
        <AssistantMarkdown key={`markdown-${index}`} content={part.content} />
      ))}
    </div>
  )
}

function AssistantMarkdown({ content }: { content: string }) {
  return (
    <Markdown
      components={{
          h1: ({ children }) => (
            <h1 className="mb-4 mt-9 text-2xl font-semibold tracking-tight first:mt-0">
              {children}
            </h1>
          ),

          h2: ({ children }) => (
            <h2 className="mb-3 mt-8 text-[1.35rem] font-semibold tracking-tight first:mt-0">
              {children}
            </h2>
          ),

          h3: ({ children }) => (
            <h3 className="mb-3 mt-8 text-xl font-semibold first:mt-0">
              {children}
            </h3>
          ),

          p: ({ children }) => (
            <p className="mb-4 leading-7">
              {children}
            </p>
          ),

          strong: ({ children }) => (
            <strong className="font-semibold text-zinc-900">
              {children}
            </strong>
          ),

          ul: ({ children }) => (
            <ul className="mb-5 ml-6 list-disc space-y-2">
              {children}
            </ul>
          ),

          ol: ({ children }) => (
            <ol className="mb-5 ml-6 list-decimal space-y-2">
              {children}
            </ol>
          ),

          li: ({ children }) => (
            <li className="leading-7">
              {children}
            </li>
          ),

          hr: () => (
            <hr className="my-8 border-zinc-300" />
          ),
      }}
    >
      {normalizeAssistantMarkdown(content)}
    </Markdown>
  )
}

function CollegeFactCard({ fact, isChinese }: { fact: CollegeFact; isChinese: boolean }) {
  const missing = isChinese ? "未验证" : "Not verified"
  const labels = isChinese
    ? { location: "地点", rate: "录取率", cost: "年度就读成本", net: "平均净价", size: "本科生人数", field: "相关专业领域", fieldStatus: "匹配方式", official: "学校官网", source: "数据来源", retrieved: "检索日期" }
    : { location: "Location", rate: "Admission rate", cost: "Annual attendance cost", net: "Average net price", size: "Undergraduate enrollment", field: "Related field", fieldStatus: "Match type", official: "Official website", source: "Data source", retrieved: "Retrieved" }
  const currency = new Intl.NumberFormat(isChinese ? "zh-CN" : "en-US", { style: "currency", currency: "USD", maximumFractionDigits: 0 })
  const number = new Intl.NumberFormat(isChinese ? "zh-CN" : "en-US")
  const value = (input: string | number | null, formatter?: (item: number) => string) =>
    input == null ? missing : formatter && typeof input === "number" ? formatter(input) : String(input)
  const location = [fact.city, fact.state].filter(Boolean).join(", ") || null
  const fieldStatus = {
    direct_title_match: isChinese ? "CIP 标题直接匹配" : "Direct CIP title match",
    related_cip_field: isChinese ? "相关的宽泛 CIP 领域" : "Related broad CIP field",
    not_verified: missing,
  }[fact.reported_field_status]
  const officialSourceLabels = isChinese
    ? { majors: "核实本科专业", first_year_requirements: "核实申请要求", cost: "核实最新费用" }
    : { majors: "Verify undergraduate majors", first_year_requirements: "Verify application requirements", cost: "Verify current costs" }

  return (
    <section className="rounded-2xl border border-[#ddd8e7] bg-white p-5 shadow-[0_8px_24px_rgba(56,55,72,0.05)]">
      <div className="mb-4 flex items-start justify-between gap-4">
        <h3 className="text-lg font-semibold text-zinc-900">{fact.name || missing}</h3>
        <span className="rounded-full bg-[#f1eef7] px-2.5 py-1 text-xs text-[#6f6685]">{fact.source}</span>
      </div>
      <dl className="grid gap-x-6 gap-y-3 sm:grid-cols-2">
        <FactRow label={labels.location} value={value(location)} />
        <FactRow label={labels.rate} value={value(fact.admission_rate, item => `${(item * 100).toFixed(1)}%`)} />
        <FactRow label={labels.cost} value={value(fact.attendance_cost, item => currency.format(item))} />
        <FactRow label={labels.net} value={value(fact.average_net_price, item => currency.format(item))} />
        <FactRow label={labels.size} value={value(fact.undergraduate_size, item => number.format(item))} />
        <FactRow label={labels.field} value={value(fact.reported_field)} />
        <FactRow label={labels.fieldStatus} value={fieldStatus} />
      </dl>
      <div className="mt-4 flex flex-wrap items-center justify-between gap-3 border-t border-zinc-100 pt-4 text-sm">
        <span className="text-zinc-500">{labels.source}: {fact.source} · {fact.data_vintage} · {labels.retrieved}: {fact.retrieved_on}</span>
        {fact.official_url && (
          <a className="font-medium text-[#65578a] underline-offset-4 hover:underline" href={fact.official_url} target="_blank" rel="noreferrer">
            {labels.official} ↗
          </a>
        )}
      </div>
      {fact.official_sources?.length > 0 && <div className="mt-3 flex flex-wrap gap-2">{fact.official_sources.map((source) => <a key={source.kind} className="rounded-full border border-[#d9d3e7] px-3 py-2 text-xs font-medium text-[#65578a] hover:bg-[#f6f3fa]" href={source.url} target="_blank" rel="noreferrer">{officialSourceLabels[source.kind]} ↗</a>)}</div>}
    </section>
  )
}

function FactRow({ label, value }: { label: string; value: string }) {
  return (
    <div>
      <dt className="text-xs font-medium uppercase tracking-wide text-zinc-500">{label}</dt>
      <dd className={`mt-1 text-sm ${value === "未验证" || value === "Not verified" ? "italic text-amber-700" : "text-zinc-800"}`}>{value}</dd>
    </div>
  )
}
