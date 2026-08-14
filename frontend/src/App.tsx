import { useState } from "react"

import { Sidebar } from "@/components/Sidebar"
import { ChatComposer } from "@/components/ChatComposer"
import { ChatMessage, type Message } from "@/components/ChatMessage"
import { ScrollArea } from "@/components/ui/scroll-area"

function App() {
  const [input, setInput] = useState("")
  const [messages, setMessages] = useState<Message[]>([])

  function handleSend() {
    const trimmedInput = input.trim()

    if (!trimmedInput) return

    setMessages((previousMessages) => [
      ...previousMessages,
      {
        role: "user",
        content: trimmedInput,
      },
      {
        role: "assistant",
        content: "This is a temporary mock response.",
      },
    ])

    setInput("")
  }

  return (
    <div className="flex h-screen bg-[#f7f6f2] text-zinc-900">
      <Sidebar />

      <main className="flex min-w-0 flex-1 flex-col">
        {messages.length === 0 ? (
          <div className="flex flex-1 items-center justify-center px-6">
            <div className="w-full max-w-3xl">
              <div className="mb-8 text-center">
                <h1 className="text-3xl font-medium tracking-tight">
                  How can I help you today?
                </h1>

                <p className="mt-2 text-sm text-zinc-500">
                  Ask about colleges, majors, or your application.
                </p>
              </div>

              <ChatComposer
                input={input}
                setInput={setInput}
                onSend={handleSend}
              />
            </div>
          </div>
        ) : (
          <>
            <ScrollArea className="flex-1">
              <div className="mx-auto w-full max-w-3xl px-6 py-10">
                <div className="space-y-8">
                  {messages.map((message, index) => (
                    <ChatMessage
                      key={index}
                      message={message}
                    />
                  ))}
                </div>
              </div>
            </ScrollArea>

            <div className="px-6 pb-6">
              <div className="mx-auto w-full max-w-3xl">
                <ChatComposer
                  input={input}
                  setInput={setInput}
                  onSend={handleSend}
                />
              </div>
            </div>
          </>
        )}
      </main>
    </div>
  )
}

export default App