import { describe, expect, it } from "vitest"

import { ApiError } from "@/lib/api"
import {
  annotateRecognizedPinyin,
  detectInputLanguage,
  isValidCollegeCount,
  persistableConversation,
  recommendationErrorMessage,
} from "@/lib/uiLogic"

describe("language handling", () => {
  it("recognizes relevant Chinese pinyin and preserves an interpretation", () => {
    expect(detectInputLanguage("diannao")).toBe("zh")
    expect(annotateRecognizedPinyin("diannao")).toContain("电脑 / computer")
  })

  it("does not classify a normal English greeting as pinyin", () => {
    expect(detectInputLanguage("hello")).toBe("en")
  })
})

describe("college count validation", () => {
  it("accepts only whole numbers from 1 through 20", () => {
    expect(isValidCollegeCount("1")).toBe(true)
    expect(isValidCollegeCount("20")).toBe(true)
    expect(isValidCollegeCount("0")).toBe(false)
    expect(isValidCollegeCount("21")).toBe(false)
    expect(isValidCollegeCount("5.5")).toBe(false)
    expect(isValidCollegeCount("five")).toBe(false)
  })
})

describe("privacy-preserving session state", () => {
  it("keeps ordinary conversations", () => {
    const result = persistableConversation({
      input: "Recommend two PIQs",
      messages: [{ role: "user", content: "Recommend two PIQs" }],
      sessionId: "session-1",
    })
    expect(result.messages).toHaveLength(1)
    expect(result.sessionId).toBe("session-1")
  })

  it("does not persist secrets or sensitive experiences", () => {
    const result = persistableConversation({
      input: "",
      messages: [{ role: "user", content: "My card is 4111 1111 1111 1111" }],
      sessionId: "session-1",
    })
    expect(result.messages).toEqual([])
    expect(result.sessionId).toBeNull()
  })
})

describe("UI guidance", () => {
  it("maps rate limits and network failures to specific messages", () => {
    expect(recommendationErrorMessage(new ApiError(429, "limited", 12), "en"))
      .toContain("12 seconds")
    expect(recommendationErrorMessage(new TypeError("fetch failed"), "zh"))
      .toContain("无法连接")
  })
})
