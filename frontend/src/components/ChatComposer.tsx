import { ArrowUp } from "lucide-react"

import { Button } from "@/components/ui/button"
import { Textarea } from "@/components/ui/textarea"

type ChatComposerProps = {
  input: string
  setInput: (value: string) => void
  onSend: () => void
}

export function ChatComposer({
  input,
  setInput,
  onSend,
}: ChatComposerProps) {
  return (
    <div className="w-full rounded-3xl border border-zinc-300 bg-white p-3 shadow-sm">
      <Textarea
        value={input}
        onChange={(event) => setInput(event.target.value)}
        placeholder="Ask about colleges, majors, or your application..."
        className="min-h-[60px] resize-none border-0 bg-transparent px-1 shadow-none focus-visible:ring-0"
      />

      <div className="flex justify-end">
        <Button
          size="icon"
          onClick={onSend}
          disabled={!input.trim()}
          className="h-9 w-9 rounded-full"
        >
          <ArrowUp className="h-4 w-4" />
        </Button>
      </div>
    </div>
  )
}