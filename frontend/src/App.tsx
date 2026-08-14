import { useState } from "react"
import { Button } from "@/components/ui/button"
import { Textarea } from "@/components/ui/textarea"
import { ScrollArea } from "@/components/ui/scroll-area"

type Message = {
  role: "user" | "assistant"
  content: string
}

function App() {
  const [input, setInput] = useState("")
  const [messages, setMessages] = useState<Message[]>([
    {
      role: "assistant",
      content: "Hi — tell me what you're looking for in a college.",
    },
  ])

  function handleSend() {
    if (!input.trim()) return

    setMessages((prev) => [
      ...prev,
      { role: "user", content: input },
      {
        role: "assistant",
        content: "This is a temporary mock response. We'll connect FastAPI next.",
      },
    ])

    setInput("")
  }

  return (
    <div className="flex h-screen bg-[#f7f6f2] text-zinc-900">
      <aside className="w-64 border-r border-zinc-200 bg-[#f0eee8] p-4">
        <Button className="w-full justify-start" variant="outline">
          + New chat
        </Button>

        <div className="mt-6 space-y-2 text-sm">
          <button className="w-full rounded-lg px-3 py-2 text-left hover:bg-black/5">
            College recommendations
          </button>
          <button className="w-full rounded-lg px-3 py-2 text-left hover:bg-black/5">
            Major guidance
          </button>
        </div>
      </aside>

      <main className="flex min-w-0 flex-1 flex-col">
        <header className="border-b border-zinc-200 px-6 py-4">
          <h1 className="text-sm font-medium">College Guidance</h1>
        </header>

        <ScrollArea className="flex-1">
          <div className="mx-auto w-full max-w-3xl px-6 py-10">
            <div className="space-y-8">
              {messages.map((message, index) => (
                <div
                  key={index}
                  className={
                    message.role === "user"
                      ? "ml-auto max-w-xl rounded-2xl bg-white px-4 py-3 shadow-sm"
                      : "max-w-2xl"
                  }
                >
                  <p className="whitespace-pre-wrap leading-7">
                    {message.content}
                  </p>
                </div>
              ))}
            </div>
          </div>
        </ScrollArea>

        <div className="border-t border-zinc-200 bg-[#f7f6f2] px-6 py-5">
          <div className="mx-auto flex max-w-3xl items-end gap-3 rounded-2xl border border-zinc-300 bg-white p-3 shadow-sm">
            <Textarea
              value={input}
              onChange={(e) => setInput(e.target.value)}
              placeholder="Ask about colleges, majors, or your application..."
              className="min-h-[48px] resize-none border-0 shadow-none focus-visible:ring-0"
            />

            <Button onClick={handleSend} disabled={!input.trim()}>
              Send
            </Button>
          </div>
        </div>
      </main>
    </div>
  )
}

export default App