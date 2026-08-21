import { render, screen } from "@testing-library/react"
import userEvent from "@testing-library/user-event"
import { describe, expect, it, vi } from "vitest"

import { ChatComposer } from "../src/components/ChatComposer"
import { normalizeAssistantMarkdown } from "../src/lib/assistantMarkdown"


describe("ChatComposer", () => {
  it("clicking Send invokes the callback without forwarding the mouse event", async () => {
    const onSend = vi.fn()
    render(<ChatComposer input="hello" setInput={() => {}} onSend={onSend} />)
    await userEvent.click(screen.getByRole("button", { name: "Send message" }))
    expect(onSend).toHaveBeenCalledWith()
  })
})

describe("assistant field-report formatting", () => {
  it("separates labels and evidence even when the model puts them on one line", () => {
    const raw = [
      "1. Computer Science",
      "Fit level: Direct fit Why it fits: Strong coding evidence. Skills/interests it develops: Programming. Evidence limitations: No research. Question to investigate: Compare curricula.",
      "Supporting evidence",
      "Experience 2: Learned programming and debugged projects.",
      "Experience 6: Led communications for a club.",
      "Comparison of the top two fields",
      "Computer Science has the strongest fit.",
      "Next Step",
      "Review exact majors.",
    ].join("\n")

    const formatted = normalizeAssistantMarkdown(raw)

    expect(formatted).toContain("## 1. Computer Science")
    expect(formatted).toContain("**Fit Level:**\n\nDirect fit")
    expect(formatted).toContain("**Why it fits:**\n\nStrong coding evidence.")
    expect(formatted).toContain("### Supporting Evidence\n\n- Experience 2:")
    expect(formatted).toContain("\n- Experience 6:")
    expect(formatted).toContain("## Comparison of the Top Two Fields")
    expect(formatted).toContain("## Next Step")
  })
})
