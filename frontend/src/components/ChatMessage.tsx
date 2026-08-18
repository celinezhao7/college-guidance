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
        <div className="max-w-[70%] rounded-2xl bg-[#e9e7e1] px-4 py-2.5">
          <p className="whitespace-pre-wrap leading-7">
            {message.content}
          </p>
        </div>
      </div>
    )
  }

  return (
    <div className="max-w-2xl">
      <Markdown
        components={{
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
        {message.content}
      </Markdown>
    </div>
  )
}