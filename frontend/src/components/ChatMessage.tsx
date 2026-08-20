import Markdown from "react-markdown"

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

  const markdownContent = normalizeAssistantMarkdown(message.content)

  return (
    <div className="max-w-2xl">
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
        {markdownContent}
      </Markdown>
    </div>
  )
}

const blockLabels = [
  { match: "Fit Level", display: "Fit Level" },
  { match: "Why it fits", display: "Why it fits" },
  { match: "Skills/Interests it develops", display: "Skills/Interests it develops" },
  { match: "Evidence Limitations", display: "Evidence Limitations" },
  { match: "Question to investigate", display: "Question to investigate" },
  { match: "适配度", display: "适配度" },
  { match: "适配原因", display: "适配原因" },
  { match: "培养的技能/兴趣", display: "培养的技能/兴趣" },
  { match: "证据局限", display: "证据局限" },
  { match: "探索问题", display: "探索问题" },
]

function normalizeAssistantMarkdown(content: string) {
  const isFieldReport = /\bFit Level\s*:|\bSkills\/Interests it develops\s*:|适配度\s*:|培养的技能\/兴趣\s*:/i.test(content)
  if (!isFieldReport) return content

  let normalized = content.replace(
    /^(?!#)(\d+)\.\s+([^\n]+)$/gm,
    "## $1. $2",
  )

  for (const label of blockLabels) {
    const escaped = label.match.replace(/[.*+?^${}()|[\]\\]/g, "\\$&")
    normalized = normalized.replace(
      new RegExp(`(?<!\\*)${escaped}\\s*[:：]\\s*`, "gi"),
      `\n\n**${label.display}:**\n\n`,
    )
  }

  normalized = normalized
    .replace(/(?<![#*])\bSupporting Evidence\s*:\s*/gi, "\n\n### Supporting Evidence\n\n")
    .replace(/(?<![#*])支持证据\s*[:：]\s*/g, "\n\n### 支持证据\n\n")
    .replace(/\bComparison of Top Two Fields\s+/gi, "\n\n## Comparison of the Top Two Fields\n\n")
    .replace(/\bNext Step\s+/gi, "\n\n## Next Step\n\n")
    .replace(/前两项比较\s*[:：]?\s*/g, "\n\n## 前两项比较\n\n")
    .replace(/下一步\s*[:：]?\s*/g, "\n\n## 下一步\n\n")

  return normalized.trim()
}
