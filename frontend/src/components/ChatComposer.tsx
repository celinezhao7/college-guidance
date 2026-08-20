import { ArrowUp, Square } from "lucide-react"

import { Button } from "@/components/ui/button"
import { Textarea } from "@/components/ui/textarea"

type ChatComposerProps = {
  input: string
  setInput: (value: string) => void
  onSend: () => void
  disabled?: boolean
  requireInput?: boolean
  placeholder?: string
  isGenerating?: boolean
  onStop?: () => void
  stopLabel?: string
}

export function ChatComposer({
  input,
  setInput,
  onSend,
  disabled = false,
  requireInput = true,
  placeholder = "Ask about colleges, majors, or your application...",
  isGenerating = false,
  onStop,
  stopLabel = "Stop generating",
}: ChatComposerProps) {
  return (
    <div className="dream-composer w-full rounded-3xl border p-3 shadow-[0_12px_32px_rgba(72,65,94,0.08)]">
      <Textarea
        value={input}
        onChange={(event) => setInput(event.target.value)}
        placeholder={placeholder}
        disabled={disabled}
        onKeyDown={(event) => {
          if (event.key === "Enter" && !event.shiftKey) {
            event.preventDefault()
            onSend()
          }
        }}
        className="min-h-[60px] resize-none border-0 bg-transparent px-1 shadow-none focus-visible:ring-0"
      />

      <div className="flex justify-end">
        {isGenerating && onStop ? (
          <Button
            size="icon"
            onClick={onStop}
            aria-label={stopLabel}
            className="h-9 w-9 rounded-full border border-[#c9c6d6] bg-white text-[#625e70] shadow-sm hover:bg-[#f3f2f6]"
          >
            <Square className="h-3.5 w-3.5 fill-current" />
          </Button>
        ) : (
          <Button
            size="icon"
            onClick={onSend}
            disabled={disabled || (requireInput && !input.trim())}
            className="dream-send h-9 w-9 rounded-full border-0 text-white"
          >
            <ArrowUp className="h-4 w-4" />
          </Button>
        )}
      </div>
    </div>
  )
}
