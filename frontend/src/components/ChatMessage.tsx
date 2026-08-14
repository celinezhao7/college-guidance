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
      <p className="whitespace-pre-wrap leading-7">
        {message.content}
      </p>
    </div>
  )
}