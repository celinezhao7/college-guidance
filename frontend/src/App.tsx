import { useEffect, useLayoutEffect, useRef, useState } from "react"
import { BookOpenText, Compass, FilePenLine } from "lucide-react"

import { ChatComposer } from "@/components/ChatComposer"
import { ChatMessage, type Message } from "@/components/ChatMessage"
import { Sidebar } from "@/components/Sidebar"
import { ScrollArea } from "@/components/ui/scroll-area"
import {
  loadRecommendationOptions,
  continueCollegeConversation,
  streamRecommendation,
  type Profile,
  type RecommendationMode,
  type CollegePreferences,
  type QuickReply,
} from "@/lib/api"

const defaultCollegePreferences: CollegePreferences = {
  sat: null,
  act: null,
  states: "CA",
  max_cost: null,
  size: ["any"],
  ownership: ["any"],
  institution_format: ["either"],
  competition: ["any"],
  admission_rate_min: 0,
  admission_rate_max: 100,
  field: "Computer Science",
  targets: "No specific target",
  count: 5,
}

type LoadingPhase = "conversation" | "recommendation" | null
type CollegeScenario = "college_first" | "major_first" | "explore" | null

function App() {
  const [input, setInput] = useState("")
  const [messages, setMessages] = useState<Message[]>([])
  const [profiles, setProfiles] = useState<Profile[]>([])
  const [modes, setModes] = useState<RecommendationMode[]>([])
  const [profileId, setProfileId] = useState("")
  const [modeId, setModeId] = useState("")
  const [language, setLanguage] = useState<"en" | "zh">("en")
  const [isLoadingOptions, setIsLoadingOptions] = useState(true)
  const [isStreaming, setIsStreaming] = useState(false)
  const [loadingPhase, setLoadingPhase] = useState<LoadingPhase>(null)
  const [setupError, setSetupError] = useState("")
  const [collegePreferences, setCollegePreferences] = useState(defaultCollegePreferences)
  const [sessionId, setSessionId] = useState<string | null>(null)
  const [collegeScenario, setCollegeScenario] = useState<CollegeScenario>(null)
  const [answeredPreferences, setAnsweredPreferences] = useState<string[]>([])
  const [quickReplies, setQuickReplies] = useState<QuickReply[]>([])
  const [awaitingPreference, setAwaitingPreference] = useState<string | null>(null)
  const scrollViewportRef = useRef<HTMLDivElement>(null)

  useEffect(() => {
    loadRecommendationOptions()
      .then(({ profiles: nextProfiles, modes: nextModes }) => {
        setProfiles(nextProfiles)
        setModes(nextModes)
        setProfileId(nextProfiles[0]?.id ?? "")
      })
      .catch((error: unknown) => {
        setSetupError(
          error instanceof Error ? error.message : "Could not reach the API.",
        )
      })
      .finally(() => setIsLoadingOptions(false))
  }, [])

  useLayoutEffect(() => {
    const viewport = scrollViewportRef.current
    if (!viewport) return
    const frame = requestAnimationFrame(() => {
      viewport.scrollTo({
        top: viewport.scrollHeight,
        behavior: isStreaming ? "auto" : "smooth",
      })
    })
    return () => cancelAnimationFrame(frame)
  }, [messages, isStreaming])

  async function handleSend() {
    const trimmedInput = input.trim()
    const isCollegeMode = modeId === "college_field"
    if (!trimmedInput || !profileId || !modeId || isStreaming) return

    const casualReply = getCasualFeedbackReply(trimmedInput, language)
    if (casualReply) {
      setMessages((previous) => [
        ...previous,
        { role: "user", content: trimmedInput },
        { role: "assistant", content: casualReply },
      ])
      setInput("")
      return
    }

    if (isClearlyUnclearMessage(trimmedInput, awaitingPreference)) {
      const replyInChinese = language === "zh" || /[\u4e00-\u9fff]/.test(trimmedInput)
      setMessages((previous) => [
        ...previous,
        { role: "user", content: trimmedInput },
        {
          role: "assistant",
          content: getUnclearInputReply(modeId, replyInChinese),
        },
      ])
      setInput("")
      return
    }

    if (isCollegeMode) {
      await handleCollegeMessage(trimmedInput)
      return
    }

    setMessages((previous) => [
      ...previous,
      { role: "user", content: trimmedInput },
      { role: "assistant", content: "" },
    ])
    setInput("")
    setIsStreaming(true)
    setLoadingPhase("recommendation")

    try {
      await streamRecommendation(
        {
          profileId,
          mode: modeId,
          language,
          query: trimmedInput,
          collegePreferences: undefined,
        },
        (chunk) => {
          setMessages((previous) =>
            previous.map((message, index) =>
              index === previous.length - 1
                ? { ...message, content: message.content + chunk }
                : message,
            ),
          )
        },
      )
    } catch {
      setMessages((previous) =>
        previous.map((message, index) =>
          index === previous.length - 1
            ? {
                ...message,
                content:
                  language === "zh"
                    ? "抱歉，暂时无法生成推荐，请稍后重试。"
                    : "Sorry, I couldn’t generate the recommendation right now. Please try again.",
              }
            : message,
        ),
      )
    } finally {
      setIsStreaming(false)
      setLoadingPhase(null)
    }
  }

  async function handleCollegeMessage(message: string, choiceId?: string) {
    setMessages((previous) => [...previous, { role: "user", content: message }])
    setQuickReplies([])
    setInput("")
    setIsStreaming(true)
    setLoadingPhase("conversation")
    try {
      const response = await continueCollegeConversation({
        sessionId,
        profileId,
        language,
        message,
        choiceId,
      })
      setSessionId(response.session_id)
      setCollegeScenario(response.scenario as CollegeScenario)
      setCollegePreferences(response.preferences)
      setAnsweredPreferences(response.answered)
      setQuickReplies(response.quick_replies)
      setAwaitingPreference(response.awaiting)
      setMessages((previous) => [
        ...previous,
        { role: "assistant", content: response.reply },
      ])

      if (response.ready) {
        setLoadingPhase("recommendation")
        setMessages((previous) => [
          ...previous,
          { role: "assistant", content: "" },
        ])
        await streamRecommendation(
          {
            profileId,
            mode: modeId,
            language,
            query: message,
            collegePreferences: response.preferences,
            collegeScenario: response.scenario,
          },
          (chunk) => {
            setMessages((previous) =>
              previous.map((item, index) =>
                index === previous.length - 1
                  ? { ...item, content: item.content + chunk }
                  : item,
              ),
            )
          },
        )
      }
    } catch {
      setMessages((previous) => [
        ...previous,
        {
          role: "assistant",
          content: language === "zh" ? "抱歉，请求暂时无法完成，请稍后重试。" : "Sorry, I couldn’t complete that request right now. Please try again.",
        },
      ])
    } finally {
      setIsStreaming(false)
      setLoadingPhase(null)
    }
  }

  const controlsDisabled = isLoadingOptions || isStreaming
  const composerDisabled =
    controlsDisabled || Boolean(setupError) || !profileId || !modeId
  const zh = language === "zh"
  const streamingStatus = loadingPhase === "conversation"
    ? zh ? "正在理解你的回答……" : "Processing your answer…"
    : modeId !== "college_field"
      ? zh ? "正在生成推荐……" : "Generating recommendation…"
      : collegeScenario === "major_first"
        ? zh ? "正在查找符合专业偏好的大学……" : "Finding colleges that match your field…"
        : collegeScenario === "college_first"
          ? zh ? "正在探索目标大学的相关专业领域……" : "Exploring fields of study at your target college…"
          : collegeScenario === "explore"
            ? zh ? "正在根据你的经历推荐专业领域……" : "Recommending fields of study based on your experiences…"
            : zh ? "正在准备下一步……" : "Preparing the next step…"
  const modeDescription = modeId
    ? {
        college_field: zh
          ? "探索大学和宽泛的专业领域；我会一次问一个有用的问题。"
          : "Explore colleges and broad fields of study. I’ll ask one useful question at a time.",
        common_app: zh
          ? "根据学生档案中的经历，找出最适合展开的三道 Common App 主文书题目。"
          : "Find the three Common App prompts that best fit the student’s documented experiences.",
        uc_piq: zh
          ? "根据学生档案中的经历，找出最适合展现个人特质的四道 UC PIQ 题目。"
          : "Find the four UC PIQ prompts that best showcase the student’s documented experiences.",
      }[modeId]
    : undefined

  function handleLanguageChange(nextLanguage: "en" | "zh") {
    setLanguage(nextLanguage)
    setCollegePreferences((previous) => ({
      ...previous,
      field:
        previous.field === "Computer Science" && nextLanguage === "zh"
          ? "计算机科学"
          : previous.field === "计算机科学" && nextLanguage === "en"
            ? "Computer Science"
            : previous.field,
      targets:
        previous.targets === "No specific target" && nextLanguage === "zh"
          ? "无特定目标"
          : previous.targets === "无特定目标" && nextLanguage === "en"
            ? "No specific target"
            : previous.targets,
    }))
  }

  function handleNewChat() {
    setMessages([])
    setModeId("")
    setSessionId(null)
    setCollegeScenario(null)
    setLoadingPhase(null)
    setAnsweredPreferences([])
    setQuickReplies([])
    setAwaitingPreference(null)
    setCollegePreferences(defaultCollegePreferences)
  }

  function toggleMode(nextModeId: string) {
    setModeId((currentModeId) => currentModeId === nextModeId ? "" : nextModeId)
  }

  return (
    <div className="dream-shell flex h-screen overflow-hidden text-zinc-900">
      <Sidebar
        profiles={profiles}
        modes={modes}
        profileId={profileId}
        modeId={modeId}
        language={language}
        disabled={controlsDisabled}
        onProfileChange={setProfileId}
        onModeChange={setModeId}
        onLanguageChange={handleLanguageChange}
        onNewChat={handleNewChat}
      />

      <main className="flex min-h-0 min-w-0 flex-1 flex-col overflow-hidden">
        {messages.length === 0 ? (
          <div className="flex flex-1 items-center justify-center px-6">
            <div className="w-full max-w-3xl">
              <div className="mb-6 text-center">
                <h1 className="dream-heading text-3xl font-medium tracking-tight">
                  {zh ? "今天想探索什么？" : "How can I help you today?"}
                </h1>
                <p className="mt-2 text-sm text-zinc-500">
                  {zh ? "选择学生档案和推荐类型，然后告诉我你的需求。" : "Choose a student and recommendation type, then tell me what you need."}
                </p>
                {setupError && (
                  <p className="mt-3 text-sm text-red-600">
                    {zh ? "无法连接服务，请确认本地后端已启动后重试。" : `Could not load the backend: ${setupError}`}
                  </p>
                )}
              </div>
              <div className="mb-6 grid gap-3 sm:grid-cols-3" aria-label={zh ? "选择推荐功能" : "Choose a recommendation tool"}>
                <button
                  type="button"
                  aria-pressed={modeId === "college_field"}
                  disabled={controlsDisabled}
                  onClick={() => toggleMode("college_field")}
                  className={`dream-mode-button ${modeId === "college_field" ? "is-active" : ""}`}
                >
                  <Compass className="h-4.5 w-4.5" />
                  <span>{zh ? "大学与专业领域" : "Colleges & fields of study"}</span>
                </button>
                <button
                  type="button"
                  aria-pressed={modeId === "common_app"}
                  disabled={controlsDisabled}
                  onClick={() => toggleMode("common_app")}
                  className={`dream-mode-button ${modeId === "common_app" ? "is-active" : ""}`}
                >
                  <FilePenLine className="h-4.5 w-4.5" />
                  <span>{zh ? "Common App 文书" : "Common App essay"}</span>
                </button>
                <button
                  type="button"
                  aria-pressed={modeId === "uc_piq"}
                  disabled={controlsDisabled}
                  onClick={() => toggleMode("uc_piq")}
                  className={`dream-mode-button ${modeId === "uc_piq" ? "is-active" : ""}`}
                >
                  <BookOpenText className="h-4.5 w-4.5" />
                  <span>{zh ? "UC PIQ 题目" : "UC PIQ prompts"}</span>
                </button>
              </div>
              {modeDescription && (
                <p className="mb-5 text-center text-sm text-zinc-500">
                  {modeDescription}
                </p>
              )}
              <ChatComposer
                input={input}
                setInput={setInput}
                onSend={handleSend}
                disabled={composerDisabled}
                requireInput
                placeholder={zh ? "请输入关于大学、专业领域或申请的问题……" : "Ask about colleges, fields of study, or your application..."}
              />
            </div>
          </div>
        ) : (
          <>
            <ScrollArea className="min-h-0 flex-1" viewportRef={scrollViewportRef}>
              <div className="mx-auto w-full max-w-3xl px-6 py-10">
                <div className="space-y-8">
                  {messages.map((message, index) => (
                    <ChatMessage key={index} message={message} />
                  ))}
                  {isStreaming && !messages.at(-1)?.content && (
                    <p className="text-sm text-zinc-500">
                      {streamingStatus}
                    </p>
                  )}
                </div>
              </div>
            </ScrollArea>
            <div className="px-6 pb-6">
              <div className="mx-auto w-full max-w-3xl">
                {modeId === "college_field" && answeredPreferences.length > 0 && (
                  <PreferenceSummary
                    preferences={collegePreferences}
                    answered={answeredPreferences}
                    language={language}
                  />
                )}
                {modeId === "college_field" && !isStreaming && awaitingPreference === "competition" && (
                    <AdmissionRateRange
                      disabled={isStreaming}
                      language={language}
                      onSubmit={(min, max) => handleCollegeMessage(`${min}%–${max}%`)}
                    />
                )}
                {modeId === "college_field" && quickReplies.length > 0 && !isStreaming && awaitingPreference !== "competition" && (
                    <div className="mb-3 flex flex-wrap gap-2" aria-label={zh ? "快捷回答" : "Quick replies"}>
                      {quickReplies.map((reply) => (
                        <button
                          key={reply.id}
                          type="button"
                          className="quick-reply"
                          onClick={() => handleCollegeMessage(reply.label, reply.id)}
                        >
                          {reply.label}
                        </button>
                      ))}
                    </div>
                )}
                <ChatComposer
                  input={input}
                  setInput={setInput}
                  onSend={handleSend}
                  disabled={composerDisabled}
                  placeholder={zh ? "请输入关于大学、专业或申请的问题……" : "Ask about colleges, majors, or your application..."}
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

function getCasualFeedbackReply(message: string, language: "en" | "zh") {
  const normalized = message.trim().toLowerCase()
  const asksForWork = /[?？]|推荐|分析|帮我|请问|怎么|如何|recommend|analy[sz]e|help|which|what|how/.test(normalized)
  if (asksForWork) return null

  const isChineseFeedback = /(?:网站|网页|界面|设计).{0,8}(?:好看|漂亮|不错|很棒|喜欢)/.test(normalized)
  const isEnglishFeedback = /(?:website|site|app|interface|design).{0,12}(?:looks?\s+)?(?:great|good|nice|beautiful|lovely)|love.{0,8}(?:website|site|app|interface|design)/.test(normalized)
  const isPositiveSiteFeedback = isChineseFeedback || isEnglishFeedback

  if (!isPositiveSiteFeedback) return null
  return language === "zh" || isChineseFeedback
    ? "谢谢！很高兴你喜欢这个网站的设计。"
    : "Thank you! I’m glad you like the design."
}

function isClearlyUnclearMessage(message: string, awaitingPreference: string | null) {
  const compact = message.trim().toLowerCase().replace(/\s+/g, "")
  if (/[?？]/.test(compact) || /\d/.test(compact)) return false
  if (["hi", "go", "ok", "yes", "no", "嗨", "你好", "是", "否"].includes(compact)) return false
  if (awaitingPreference === "field") return false
  if (awaitingPreference === "states" && /^[a-z]{2}$/.test(compact)) return false
  return /^[a-z]$/.test(compact) || /^[a-z]{2}$/.test(compact)
}

function getUnclearInputReply(modeId: string, chinese: boolean) {
  if (modeId === "college_field") {
    return chinese
      ? "抱歉，我没有理解你的意思。这个功能用于探索大学和专业领域；你可以告诉我是否已有目标大学、目标专业，或仍在探索。"
      : "Sorry, I didn’t understand that. This tool helps you explore colleges and fields of study—tell me whether you have a target college, a target field, or are still exploring."
  }
  if (modeId === "common_app") {
    return chinese
      ? "抱歉，我没有理解你的意思。这个功能用于根据学生档案推荐 Common App 主文书题目，请告诉我你希望获得哪方面的帮助。"
      : "Sorry, I didn’t understand that. This tool recommends Common App essay prompts based on the student profile—tell me what you’d like help with."
  }
  return chinese
    ? "抱歉，我没有理解你的意思。这个功能用于根据学生档案推荐 UC PIQ 题目，请告诉我你希望获得哪方面的帮助。"
    : "Sorry, I didn’t understand that. This tool recommends UC PIQ prompts based on the student profile—tell me what you’d like help with."
}

function PreferenceSummary({ preferences, answered, language }: { preferences: CollegePreferences; answered: string[]; language: "en" | "zh" }) {
  const zh = language === "zh"
  const localizedValue = (value: string) => {
    if (!zh) return value
    return {
      any: "不限",
      either: "不限",
      small: "小型",
      medium: "中型",
      large: "大型",
      low: "较低",
      high: "较高",
      public: "公立",
      private_nonprofit: "私立非营利",
      private_for_profit: "私立营利",
      university: "综合性大学",
      liberal_arts: "文理学院",
    }[value] ?? value
  }
  const labels: Record<string, string> = {
    field: preferences.field,
    states: preferences.states || (zh ? "州不限" : "Any state"),
    max_cost: preferences.max_cost ? `$${preferences.max_cost.toLocaleString()}` : (zh ? "费用不限" : "No cost limit"),
    size: localizedValue(preferences.size[0]),
    competition: `${preferences.admission_rate_min}%–${preferences.admission_rate_max}%`,
    sat: preferences.sat ? `SAT ${preferences.sat}` : (zh ? "未提供 SAT" : "SAT skipped"),
    act: preferences.act ? `ACT ${preferences.act}` : (zh ? "未提供 ACT" : "ACT skipped"),
    ownership: localizedValue(preferences.ownership[0]),
    institution_format: localizedValue(preferences.institution_format[0]),
    targets: preferences.targets,
    count: zh ? `${preferences.count} 所学校` : `${preferences.count} schools`,
  }
  return (
    <div className="mb-3 flex flex-wrap gap-2">
      {answered.map((key) => <span key={key} className="dream-chip rounded-full px-3 py-1 text-xs text-zinc-700">{labels[key]}</span>)}
    </div>
  )
}

function AdmissionRateRange({ disabled, language, onSubmit }: { disabled: boolean; language: "en" | "zh"; onSubmit: (min: number, max: number) => void }) {
  const [min, setMin] = useState(0)
  const [max, setMax] = useState(100)
  const zh = language === "zh"
  const fill = { left: `${min}%`, right: `${100 - max}%` }

  return (
    <div className="mb-3 rounded-2xl border border-zinc-200 bg-white p-4 shadow-sm">
      <div className="mb-3 flex items-center justify-between gap-4">
        <span className="text-sm font-medium text-zinc-700">{zh ? "学校整体录取率范围" : "Overall admission-rate range"}</span>
        <span className="rounded-full bg-zinc-100 px-3 py-1 text-sm tabular-nums text-zinc-700">{min}%–{max}%</span>
      </div>
      <div className="relative h-8" aria-label={zh ? "录取率范围" : "Admission-rate range"}>
        <div className="absolute inset-x-0 top-3 h-2 rounded-full bg-zinc-200" />
        <div className="absolute top-3 h-2 rounded-full bg-zinc-800" style={fill} />
        <input className="range-thumb absolute inset-x-0 top-0 w-full" type="range" min="0" max="100" step="1" value={min} disabled={disabled} aria-label={zh ? "最低录取率" : "Minimum admission rate"} onChange={(e) => setMin(Math.min(Number(e.target.value), max - 1))} />
        <input className="range-thumb absolute inset-x-0 top-0 w-full" type="range" min="0" max="100" step="1" value={max} disabled={disabled} aria-label={zh ? "最高录取率" : "Maximum admission rate"} onChange={(e) => setMax(Math.max(Number(e.target.value), min + 1))} />
      </div>
      <div className="mt-1 flex items-center justify-between text-xs text-zinc-400"><span>0%</span><span>100%</span></div>
      <div className="mt-3 flex items-center justify-between gap-3">
        <p className="text-xs text-zinc-500">{zh ? "这是学校整体录取率，不代表你的个人录取概率。" : "This is the school's overall rate, not your personal admission chance."}</p>
        <button type="button" className="quick-reply shrink-0" disabled={disabled} onClick={() => onSubmit(min, max)}>{zh ? "确认范围" : "Apply range"}</button>
      </div>
    </div>
  )
}
