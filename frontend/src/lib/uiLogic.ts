import { ApiError } from "@/lib/api"

const recognizedPinyinTerms = [
  { pattern: /\bdiannao\b/gi, meaning: "电脑 / computer" },
  { pattern: /\bjisuanji\b/gi, meaning: "计算机 / computer science" },
  { pattern: /\bdaxue\b/gi, meaning: "大学 / university" },
  { pattern: /\bxuexiao\b/gi, meaning: "学校 / school" },
  { pattern: /\bzhuanye\b/gi, meaning: "专业 / field of study" },
  { pattern: /\bwenshu\b/gi, meaning: "文书 / application essay" },
  { pattern: /\btuijian\b/gi, meaning: "推荐 / recommendation" },
]

export function detectInputLanguage(message: string): "en" | "zh" | null {
  const normalized = message.trim().toLowerCase().replace(/[^a-z]+/g, "")
  if (["hi", "hey", "hello", "yo", "sup"].includes(normalized)) return "en"
  const chineseCharacters = message.match(/[\u3400-\u9fff]/g)?.length ?? 0
  if (chineseCharacters >= 2) return "zh"
  if (containsRecognizedPinyin(message)) return "zh"
  const latinLetters = message.match(/[a-z]/gi)?.length ?? 0
  if (chineseCharacters === 0 && latinLetters >= 4) return "en"
  return null
}

export function smallTalkReply(message: string, language: "en" | "zh") {
  const normalized = message.trim().toLowerCase().replace(/[^a-z0-9\u3400-\u9fff']+/g, " ").trim()
  const asksHow = /^(?:how are you(?: doing)?|how(?:'s| is) it going|what(?:'s| is) up|how are things)$/.test(normalized)
    || /^(?:你好吗|你怎么样|最近怎么样)$/.test(normalized)
  if (asksHow) {
    return language === "zh" || /[\u3400-\u9fff]/.test(message)
      ? "我很好，谢谢！你想聊些什么？"
      : "I’m doing well, thanks! What would you like to talk about?"
  }
  const thanks = /^(?:thanks|thank you|thx|谢谢|感谢)$/.test(normalized)
  if (thanks) {
    return language === "zh" || /[\u3400-\u9fff]/.test(message)
      ? "不客气！"
      : "You’re welcome!"
  }
  return null
}

export function annotateRecognizedPinyin(message: string) {
  const interpretations: string[] = []
  for (const { pattern, meaning } of recognizedPinyinTerms) {
    pattern.lastIndex = 0
    if (pattern.test(message)) interpretations.push(meaning)
  }
  if (interpretations.length === 0) return message
  return `${message}\n\n[Recognized Chinese pinyin: ${interpretations.join("; ")}]`
}

function containsRecognizedPinyin(message: string) {
  return recognizedPinyinTerms.some(({ pattern }) => {
    pattern.lastIndex = 0
    return pattern.test(message)
  })
}

export function isValidCollegeCount(message: string) {
  if (!/^\d+$/.test(message.trim())) return false
  const value = Number(message)
  return value >= 1 && value <= 20
}

export function isAmbiguousBarePromptNumber(message: string, modeId: string) {
  if (!/^[1-8]$/.test(message.trim())) return false
  if (modeId === "common_app") return Number(message.trim()) <= 7
  return modeId === "uc_piq"
}

export function explicitlyRequestedMode(message: string): "uc_piq" | "common_app" | null {
  if (/\bpiqs?\b|personal insight questions?|个人洞察/i.test(message)) return "uc_piq"
  if (/common\s*app|主文书/i.test(message)) return "common_app"
  return null
}

export function containsNonPersistableContent(value: string) {
  return /\b(?:\d[ -]*?){13,19}\b|\b(?:sk|pk)-[A-Za-z0-9_-]{16,}\b|\b\d{3}-\d{2}-\d{4}\b|(?:api[_ -]?key|password|passwd|access[_ -]?token|secret)\s*[:=]|(?:银行卡|身份证|密码|密钥|抑郁|霸凌|自残|自杀|性侵)|\b(?:depression|bullying|self[- ]harm|suicid(?:e|al)?|sexual assault)\b/i.test(value)
}

export function persistableConversation<T extends {
  input: string
  messages: Array<{ role: string; content: string }>
  sessionId: string | null
}>(conversation: T): T {
  const containsSensitiveMessage = conversation.messages.some((message) => (
    containsNonPersistableContent(message.content)
  ))
  return {
    ...conversation,
    input: containsNonPersistableContent(conversation.input) ? "" : conversation.input,
    messages: containsSensitiveMessage ? [] : conversation.messages,
    sessionId: containsSensitiveMessage ? null : conversation.sessionId,
  }
}

export function recommendationErrorMessage(error: unknown, language: "en" | "zh") {
  if (error instanceof Error && error.message === "RECOMMENDATION_TIMEOUT") {
    return language === "zh"
      ? "生成时间过长，已停止本次请求。请重试，或把问题缩短一些。"
      : "The response took too long, so this request was stopped. Please retry or make the request shorter."
  }
  if (error instanceof ApiError && error.status === 429) {
    const wait = error.retryAfter ? ` ${error.retryAfter} ${language === "zh" ? "秒" : "seconds"}` : ""
    return language === "zh"
      ? `请求过于频繁，请等待${wait || "片刻"}后重试。`
      : `Too many requests. Please wait${wait || " a moment"} and try again.`
  }
  if (error instanceof ApiError && error.status === 409) {
    return language === "zh"
      ? "当前学生档案尚未建立检索索引，请先重新构建档案索引。"
      : "This student profile has not been indexed yet. Rebuild the profile index and try again."
  }
  if (error instanceof ApiError && error.status >= 500) {
    return language === "zh"
      ? "大学数据或生成服务暂时不可用，请稍后重试。"
      : "The college-data or generation service is temporarily unavailable. Please try again later."
  }
  if (error instanceof TypeError) {
    return language === "zh"
      ? "无法连接到服务，请检查网络或确认后端正在运行。"
      : "Could not connect to the service. Check your network and make sure the backend is running."
  }
  return language === "zh"
    ? "抱歉，请求暂时无法完成，请稍后重试。"
    : "Sorry, I couldn’t complete that request right now. Please try again."
}
