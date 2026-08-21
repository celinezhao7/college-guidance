import { describe, expect, it } from "vitest"

import { ApiError } from "@/lib/api"
import {
  annotateRecognizedPinyin,
  detectInputLanguage,
  explicitlyRequestedMode,
  isAmbiguousBarePromptNumber,
  isValidCollegeCount,
  persistableConversation,
  recommendationErrorMessage,
  smallTalkReply,
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

describe("small talk", () => {
  it("answers common small talk without introducing application guidance", () => {
    const reply = smallTalkReply("how are you doing", "en")
    expect(reply).toBe("I’m doing well, thanks! What would you like to talk about?")
    expect(reply).not.toContain("UC")
    expect(reply).not.toContain("application")
  })

  it("handles Chinese small talk and thanks", () => {
    expect(smallTalkReply("你好吗", "zh")).toContain("我很好")
    expect(smallTalkReply("谢谢", "zh")).toBe("不客气！")
  })

  it("does not intercept substantive questions", () => {
    expect(smallTalkReply("How should I choose a PIQ?", "en")).toBeNull()
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

describe("prompt-number clarification", () => {
  it("treats a bare valid prompt number as ambiguous", () => {
    expect(isAmbiguousBarePromptNumber("4", "common_app")).toBe(true)
    expect(isAmbiguousBarePromptNumber("8", "uc_piq")).toBe(true)
  })

  it("does not intercept an explicit request or an invalid prompt number", () => {
    expect(isAmbiguousBarePromptNumber("recommend 4", "common_app")).toBe(false)
    expect(isAmbiguousBarePromptNumber("8", "common_app")).toBe(false)
  })
})

describe("explicit tool requests", () => {
  it("recognizes PIQ requests embedded in Chinese text", () => {
    expect(explicitlyRequestedMode("我想要四个piq推荐")).toBe("uc_piq")
    expect(explicitlyRequestedMode("请推荐四个 PIQs")).toBe("uc_piq")
  })

  it("recognizes Common App requests without guessing ordinary college requests", () => {
    expect(explicitlyRequestedMode("帮我选 Common App prompt")).toBe("common_app")
    expect(explicitlyRequestedMode("推荐几个大学")).toBeNull()
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
