import { useEffect, useLayoutEffect, useRef, useState } from "react"
import { BookOpenText, Compass, FilePenLine, Menu, Minus, Plus } from "lucide-react"

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
import {
  annotateRecognizedPinyin,
  detectInputLanguage,
  isAmbiguousBarePromptNumber,
  isValidCollegeCount,
  persistableConversation,
  recommendationErrorMessage,
} from "@/lib/uiLogic"

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
type PendingLanguageSwitch = {
  message: string
  target: "en" | "zh"
} | null
type ModeConversationState = {
  input: string
  messages: Message[]
  collegePreferences: CollegePreferences
  sessionId: string | null
  collegeScenario: CollegeScenario
  answeredPreferences: string[]
  quickReplies: QuickReply[]
  awaitingPreference: string | null
}
type StoredWorkspace = {
  activeModeId: string
  conversations: Record<string, ModeConversationState>
}

function emptyModeConversation(): ModeConversationState {
  return {
    input: "",
    messages: [],
    collegePreferences: { ...defaultCollegePreferences },
    sessionId: null,
    collegeScenario: null,
    answeredPreferences: [],
    quickReplies: [],
    awaitingPreference: null,
  }
}

function storageKey(profileId: string) {
  return `college-guide:session:${profileId}`
}

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
  const [pendingLanguageSwitch, setPendingLanguageSwitch] = useState<PendingLanguageSwitch>(null)
  const [languageCheckBypass, setLanguageCheckBypass] = useState<string | null>(null)
  const [inputError, setInputError] = useState("")
  const [modeSwitchNotice, setModeSwitchNotice] = useState("")
  const [mobileSidebarOpen, setMobileSidebarOpen] = useState(false)
  const [desktopSidebarOpen, setDesktopSidebarOpen] = useState(true)
  const [storageHydrated, setStorageHydrated] = useState(false)
  const [canStopGeneration, setCanStopGeneration] = useState(false)
  const scrollViewportRef = useRef<HTMLDivElement>(null)
  const generationAbortRef = useRef<AbortController | null>(null)
  const modeConversationsRef = useRef<Record<string, ModeConversationState>>({})
  const submissionLockRef = useRef(false)
  const hasShownModeSwitchNoticeRef = useRef(false)

  useEffect(() => {
    const phoneViewport = window.matchMedia("(max-width: 767px)")
    const collapseOnPhone = (event?: MediaQueryListEvent) => {
      if (event?.matches ?? phoneViewport.matches) {
        setMobileSidebarOpen(false)
      }
    }

    collapseOnPhone()
    phoneViewport.addEventListener("change", collapseOnPhone)
    return () => phoneViewport.removeEventListener("change", collapseOnPhone)
  }, [])

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

  useEffect(() => {
    if (!profileId) return
    setStorageHydrated(false)
    try {
      const raw = sessionStorage.getItem(storageKey(profileId))
      const stored = raw ? JSON.parse(raw) as StoredWorkspace : null
      modeConversationsRef.current = stored?.conversations ?? {}
      const restoredMode = stored?.activeModeId ?? ""
      setModeId(restoredMode)
      applyModeConversation(
        modeConversationsRef.current[restoredMode] ?? emptyModeConversation(),
      )
    } catch {
      modeConversationsRef.current = {}
      setModeId("")
      applyModeConversation(emptyModeConversation())
    } finally {
      setStorageHydrated(true)
    }
  }, [profileId])

  useEffect(() => {
    if (!profileId || !storageHydrated) return
    const conversations = { ...modeConversationsRef.current }
    if (modeId) {
      conversations[modeId] = persistableConversation({
        input,
        messages,
        collegePreferences,
        sessionId,
        collegeScenario,
        answeredPreferences,
        quickReplies,
        awaitingPreference,
      })
    }
    modeConversationsRef.current = conversations
    const stored: StoredWorkspace = { activeModeId: modeId, conversations }
    sessionStorage.setItem(storageKey(profileId), JSON.stringify(stored))
  }, [answeredPreferences, awaitingPreference, collegePreferences, collegeScenario, input, messages, modeId, profileId, quickReplies, sessionId, storageHydrated])

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

  useEffect(() => {
    if (!modeSwitchNotice) return
    const timeout = setTimeout(() => setModeSwitchNotice(""), 3500)
    return () => clearTimeout(timeout)
  }, [modeSwitchNotice])

  async function handleSend() {
    const trimmedInput = input.trim()
    const isCollegeMode = modeId === "college_field"
    if (!trimmedInput || !profileId || !modeId || isStreaming || submissionLockRef.current) return
    setModeSwitchNotice("")

    const detectedLanguage = detectInputLanguage(trimmedInput)
    if (
      detectedLanguage
      && detectedLanguage !== language
      && languageCheckBypass !== trimmedInput
    ) {
      setPendingLanguageSwitch({ message: trimmedInput, target: detectedLanguage })
      return
    }
    setPendingLanguageSwitch(null)
    setLanguageCheckBypass(null)
    const semanticInput = annotateRecognizedPinyin(trimmedInput)

    if (isCollegeMode && awaitingPreference === "count" && !isValidCollegeCount(trimmedInput)) {
      setInputError(
        language === "zh"
          ? "请输入 1–20 之间的整数。"
          : "Enter a whole number from 1 to 20.",
      )
      return
    }
    setInputError("")

    if (!isCollegeMode && isAmbiguousBarePromptNumber(trimmedInput, modeId)) {
      brieflyLockSubmission()
      const promptName = modeId === "common_app" ? "Common App prompt" : "UC PIQ"
      setMessages((previous) => [
        ...previous,
        { role: "user", content: trimmedInput },
        {
          role: "assistant",
          content: language === "zh"
            ? `我不确定“${trimmedInput}”指的是数量还是题号。你希望我推荐 ${trimmedInput} 个题目，还是分析第 ${trimmedInput} 题？请回复“推荐 ${trimmedInput} 个”或“分析第 ${trimmedInput} 题”。`
            : `I’m not sure whether “${trimmedInput}” is a quantity or a prompt number. Would you like ${trimmedInput} ${promptName}s recommended, or an analysis of ${promptName} #${trimmedInput}? Reply “recommend ${trimmedInput}” or “analyze #${trimmedInput}.”`,
        },
      ])
      setInput("")
      return
    }

    if (!isCollegeMode && isCasualGreeting(trimmedInput)) {
      brieflyLockSubmission()
      const replyInChinese = language === "zh" || /[\u4e00-\u9fff]/.test(trimmedInput)
      setMessages((previous) => [
        ...previous,
        { role: "user", content: trimmedInput },
        {
          role: "assistant",
          content: modeId === "common_app"
            ? (replyInChinese
                ? "你好！这个功能可以根据学生档案推荐 Common App 主文书题目。告诉我你希望获得什么帮助吧。"
                : "Hi! This tool recommends Common App essay prompts based on the student profile. Tell me what you’d like help with.")
            : (replyInChinese
                ? "你好！这个功能可以根据学生档案推荐 UC PIQ 题目。告诉我你希望获得什么帮助吧。"
                : "Hi! This tool recommends UC PIQ prompts based on the student profile. Tell me what you’d like help with."),
        },
      ])
      setInput("")
      return
    }

    const casualReply = getCasualFeedbackReply(trimmedInput, language)
    if (casualReply) {
      brieflyLockSubmission()
      setMessages((previous) => [
        ...previous,
        { role: "user", content: trimmedInput },
        { role: "assistant", content: casualReply },
      ])
      setInput("")
      return
    }

    if (isClearlyUnclearMessage(semanticInput, awaitingPreference)) {
      brieflyLockSubmission()
      const replyInChinese = language === "zh" || /[\u4e00-\u9fff]/.test(trimmedInput)
      setMessages((previous) => [
        ...previous,
        { role: "user", content: trimmedInput },
        {
          role: "assistant",
          content: getUnclearInputReply(modeId, replyInChinese),
        },
      ])
      if (isCollegeMode) {
        setQuickReplies(getScenarioQuickReplies(replyInChinese ? "zh" : "en"))
        setAwaitingPreference("scenario")
      }
      setInput("")
      return
    }

    if (isCollegeMode) {
      await handleCollegeMessage(semanticInput, undefined, trimmedInput)
      return
    }

    submissionLockRef.current = true
    setMessages((previous) => [
      ...previous,
      { role: "user", content: trimmedInput },
      { role: "assistant", content: "" },
    ])
    setInput("")
    setIsStreaming(true)
    setLoadingPhase("recommendation")
    const recommendationHistory = messages
      .filter((message) => message.content.trim())
      .slice(-8)
    const generationController = new AbortController()
    generationAbortRef.current = generationController
    setCanStopGeneration(true)

    try {
      await streamRecommendation(
        {
          profileId,
          mode: modeId,
          language,
          query: semanticInput,
          collegePreferences: undefined,
          history: recommendationHistory,
          signal: generationController.signal,
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
    } catch (error) {
      setMessages((previous) =>
        previous.map((message, index) =>
          index === previous.length - 1
            ? {
                ...message,
                content: isRecommendationCancelled(error)
                  ? message.content || stoppedGenerationMessage(language)
                  : recommendationErrorMessage(error, language),
              }
            : message,
        ),
      )
    } finally {
      if (generationAbortRef.current === generationController) {
        generationAbortRef.current = null
      }
      setCanStopGeneration(false)
      setIsStreaming(false)
      setLoadingPhase(null)
      submissionLockRef.current = false
    }
  }

  async function handleCollegeMessage(
    message: string,
    choiceId?: string,
    displayedMessage = message,
  ) {
    if (submissionLockRef.current) return
    submissionLockRef.current = true
    setMessages((previous) => [...previous, { role: "user", content: displayedMessage }])
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
      if (response.session_reset) {
        setMessages([{ role: "assistant", content: response.reply }])
        return
      }
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
        const generationController = new AbortController()
        generationAbortRef.current = generationController
        setCanStopGeneration(true)
        await streamRecommendation(
          {
            profileId,
            mode: modeId,
            language,
            query: message,
            collegePreferences: response.preferences,
            collegeScenario: response.scenario,
            signal: generationController.signal,
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
    } catch (error) {
      if (isRecommendationCancelled(error)) {
        setMessages((previous) =>
          previous.map((item, index) =>
            index === previous.length - 1 && item.role === "assistant"
              ? { ...item, content: item.content || stoppedGenerationMessage(language) }
              : item,
          ),
        )
      } else {
        setMessages((previous) => [
          ...previous,
          {
            role: "assistant",
            content: recommendationErrorMessage(error, language),
          },
        ])
      }
    } finally {
      generationAbortRef.current = null
      setCanStopGeneration(false)
      setIsStreaming(false)
      setLoadingPhase(null)
      submissionLockRef.current = false
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
          ? "根据学生档案中的经历推荐最适合展开的题目。Common App 主文书提交 1 篇，最多 650 字。"
          : "Find the best-fitting prompt for the student’s documented experiences. The Common App personal essay is one essay of up to 650 words.",
        uc_piq: zh
          ? "根据学生档案中的经历推荐最适合展现个人特质的题目。UC 要求从 8 道 PIQ 中选择 4 道，每篇最多 350 字。"
          : "Find the PIQs that best showcase the student’s documented experiences. UC requires 4 of the 8 PIQs, with up to 350 words per response.",
      }[modeId]
    : undefined
  const modeHistoryIds = modes
    .filter((mode) => (
      mode.id === modeId
        ? messages.length > 0
        : (modeConversationsRef.current[mode.id]?.messages.length ?? 0) > 0
    ))
    .map((mode) => mode.id)

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

  async function handleEditPreference(key: string, label: string) {
    const message = language === "zh" ? `修改${label}` : `Change ${label}`
    await handleCollegeMessage(message, `edit_${key}`)
  }

  function handleStopGeneration() {
    generationAbortRef.current?.abort()
  }

  function brieflyLockSubmission() {
    submissionLockRef.current = true
    setTimeout(() => {
      submissionLockRef.current = false
    }, 400)
  }

  function handleInputChange(value: string) {
    setInput(value)
    setInputError("")
    if (pendingLanguageSwitch?.message !== value.trim()) {
      setPendingLanguageSwitch(null)
    }
    if (languageCheckBypass !== value.trim()) {
      setLanguageCheckBypass(null)
    }
  }

  function handleNewChat() {
    modeConversationsRef.current = {}
    setInput("")
    setMessages([])
    setModeId("")
    setSessionId(null)
    setCollegeScenario(null)
    setLoadingPhase(null)
    setAnsweredPreferences([])
    setQuickReplies([])
    setAwaitingPreference(null)
    setPendingLanguageSwitch(null)
    setLanguageCheckBypass(null)
    setInputError("")
    setModeSwitchNotice("")
    hasShownModeSwitchNoticeRef.current = false
    setCollegePreferences(defaultCollegePreferences)
  }

  function resetConversationState() {
    modeConversationsRef.current = {}
    setInput("")
    setMessages([])
    setSessionId(null)
    setCollegeScenario(null)
    setLoadingPhase(null)
    setAnsweredPreferences([])
    setQuickReplies([])
    setAwaitingPreference(null)
    setPendingLanguageSwitch(null)
    setLanguageCheckBypass(null)
    setInputError("")
    setModeSwitchNotice("")
    hasShownModeSwitchNoticeRef.current = false
  }

  function handleProfileChange(nextProfileId: string) {
    if (nextProfileId !== profileId) {
      setStorageHydrated(false)
      resetConversationState()
    }
    setProfileId(nextProfileId)
  }

  function handleModeChange(nextModeId: string) {
    if (nextModeId === modeId) return
    if (modeId) {
      modeConversationsRef.current[modeId] = {
        input,
        messages,
        collegePreferences,
        sessionId,
        collegeScenario,
        answeredPreferences,
        quickReplies,
        awaitingPreference,
      }
      if (messages.length > 0 && !hasShownModeSwitchNoticeRef.current) {
        setModeSwitchNotice(
          language === "zh"
            ? "当前功能的对话已保存，切换回来可以继续。"
            : "This conversation was saved. Switch back anytime to continue.",
        )
        hasShownModeSwitchNoticeRef.current = true
      }
    }

    const nextConversation = modeConversationsRef.current[nextModeId]
      ?? emptyModeConversation()
    applyModeConversation(nextConversation)
    setModeId(nextModeId)
  }

  function applyModeConversation(nextConversation: ModeConversationState) {
    setInput(nextConversation.input)
    setMessages(nextConversation.messages)
    setCollegePreferences(nextConversation.collegePreferences)
    setSessionId(nextConversation.sessionId)
    setCollegeScenario(nextConversation.collegeScenario)
    setAnsweredPreferences(nextConversation.answeredPreferences)
    setQuickReplies(nextConversation.quickReplies)
    setAwaitingPreference(nextConversation.awaitingPreference)
    setLoadingPhase(null)
    setPendingLanguageSwitch(null)
    setLanguageCheckBypass(null)
    setInputError("")
  }

  function toggleMode(nextModeId: string) {
    handleModeChange(modeId === nextModeId ? "" : nextModeId)
  }

  return (
    <div className="dream-shell flex h-[100dvh] min-h-[100dvh] overflow-hidden text-zinc-900">
      {modeSwitchNotice && (
        <div className="fixed left-1/2 top-4 z-50 -translate-x-1/2 rounded-full border border-[#d9d6e4] bg-white/95 px-4 py-2 text-sm text-[#5d5970] shadow-lg backdrop-blur" role="status">
          {modeSwitchNotice}
        </div>
      )}
      <Sidebar
        profiles={profiles}
        modes={modes}
        profileId={profileId}
        modeId={modeId}
        language={language}
        disabled={controlsDisabled}
        mobileOpen={mobileSidebarOpen}
        desktopOpen={desktopSidebarOpen}
        modeHistoryIds={modeHistoryIds}
        onProfileChange={handleProfileChange}
        onModeChange={handleModeChange}
        onLanguageChange={handleLanguageChange}
        onNewChat={handleNewChat}
        onMobileClose={() => setMobileSidebarOpen(false)}
        onClose={() => {
          setMobileSidebarOpen(false)
          setDesktopSidebarOpen(false)
        }}
      />

      {mobileSidebarOpen && (
        <button
          type="button"
          className="fixed inset-0 z-30 bg-[#373348]/20 backdrop-blur-[1px] md:hidden"
          onClick={() => setMobileSidebarOpen(false)}
          aria-label={zh ? "点击背景关闭侧栏" : "Dismiss sidebar backdrop"}
        />
      )}

      <main className="relative flex min-h-0 min-w-0 flex-1 flex-col overflow-hidden">
        <button
          type="button"
          className="absolute left-4 top-[max(1rem,env(safe-area-inset-top))] z-20 flex h-10 w-10 items-center justify-center rounded-xl border border-[#dedbe9] bg-white/85 text-[#5d5970] shadow-sm backdrop-blur md:hidden"
          onClick={() => setMobileSidebarOpen(true)}
          aria-label={zh ? "打开菜单" : "Open menu"}
        >
          <Menu className="h-5 w-5" />
        </button>
        {!desktopSidebarOpen && (
          <button
            type="button"
            className="absolute left-4 top-4 z-20 hidden h-10 w-10 items-center justify-center rounded-xl border border-[#dedbe9] bg-white/85 text-[#5d5970] shadow-sm backdrop-blur transition hover:bg-white md:flex"
            onClick={() => setDesktopSidebarOpen(true)}
            aria-label={zh ? "打开侧栏" : "Open sidebar"}
          >
            <Menu className="h-5 w-5" />
          </button>
        )}
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
              {pendingLanguageSwitch && (
                <LanguageSwitchPrompt
                  target={pendingLanguageSwitch.target}
                  onSwitch={() => {
                    handleLanguageChange(pendingLanguageSwitch.target)
                    setPendingLanguageSwitch(null)
                  }}
                  onKeep={() => {
                    setLanguageCheckBypass(pendingLanguageSwitch.message)
                    setPendingLanguageSwitch(null)
                  }}
                />
              )}
              {inputError && <p className="mb-2 text-sm text-red-600" role="alert">{inputError}</p>}
              <ChatComposer
                input={input}
                setInput={handleInputChange}
                onSend={handleSend}
                disabled={composerDisabled}
                requireInput
                placeholder={zh ? "请输入关于大学、专业领域或申请的问题……" : "Ask about colleges, fields of study, or your application..."}
                isGenerating={canStopGeneration}
                onStop={handleStopGeneration}
                stopLabel={zh ? "停止生成" : "Stop generating"}
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
                    <LoadingStatus label={streamingStatus} />
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
                    disabled={isStreaming}
                    onEdit={handleEditPreference}
                  />
                )}
                {modeId === "college_field" && !isStreaming && awaitingPreference === "competition" && (
                    <AdmissionRateRange
                      disabled={isStreaming}
                      language={language}
                      onSubmit={(min, max) => handleCollegeMessage(`${min}%–${max}%`)}
                    />
                )}
                {modeId === "college_field" && quickReplies.length > 0 && !isStreaming && awaitingPreference !== "competition" && awaitingPreference !== "count" && (
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
                {modeId === "college_field" && !isStreaming && awaitingPreference === "count" && (
                  <CollegeCountInput
                    language={language}
                    disabled={isStreaming}
                    initialValue={collegePreferences.count}
                    onSubmit={(count) => handleCollegeMessage(String(count))}
                  />
                )}
                {pendingLanguageSwitch && (
                  <LanguageSwitchPrompt
                    target={pendingLanguageSwitch.target}
                    onSwitch={() => {
                      handleLanguageChange(pendingLanguageSwitch.target)
                      setPendingLanguageSwitch(null)
                    }}
                    onKeep={() => {
                      setLanguageCheckBypass(pendingLanguageSwitch.message)
                      setPendingLanguageSwitch(null)
                    }}
                  />
                )}
                {inputError && <p className="mb-2 text-sm text-red-600" role="alert">{inputError}</p>}
                <ChatComposer
                  input={input}
                  setInput={handleInputChange}
                  onSend={handleSend}
                  disabled={composerDisabled}
                  placeholder={zh ? "请输入关于大学、专业或申请的问题……" : "Ask about colleges, majors, or your application..."}
                  isGenerating={canStopGeneration}
                  onStop={handleStopGeneration}
                  stopLabel={zh ? "停止生成" : "Stop generating"}
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

function LoadingStatus({ label }: { label: string }) {
  const text = label.replace(/[.…]+$/, "")
  return (
    <div className="dream-loading inline-flex items-center gap-2 text-sm" role="status" aria-live="polite">
      <span className="dream-loading-text">{text}</span>
      <span className="dream-loading-dots" aria-hidden="true">
        <span />
        <span />
        <span />
      </span>
      <span className="sr-only">{label}</span>
    </div>
  )
}

function LanguageSwitchPrompt({
  target,
  onSwitch,
  onKeep,
}: {
  target: "en" | "zh"
  onSwitch: () => void
  onKeep: () => void
}) {
  const switchingToChinese = target === "zh"
  return (
    <div className="language-switch-card mb-3 rounded-2xl px-4 py-3 text-sm text-zinc-700" role="status">
      <p>
        {switchingToChinese
          ? "检测到你输入了中文。是否切换到中文模式？"
          : "检测到你输入了英文。是否切换到英文模式？"}
      </p>
      <div className="mt-3 flex flex-wrap gap-2">
        <button type="button" className="language-switch-button is-primary" onClick={onSwitch}>
          {switchingToChinese ? "切换到中文" : "切换到英文"}
        </button>
        <button type="button" className="language-switch-button is-secondary" onClick={onKeep}>
          {switchingToChinese ? "继续使用英文" : "继续使用中文"}
        </button>
      </div>
    </div>
  )
}

function isRecommendationCancelled(error: unknown) {
  return error instanceof Error && error.message === "RECOMMENDATION_CANCELLED"
}

function stoppedGenerationMessage(language: "en" | "zh") {
  return language === "zh" ? "已停止生成。" : "Generation stopped."
}

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

function isCasualGreeting(message: string) {
  const normalized = message.trim().toLowerCase().replace(/[^a-z0-9\u3400-\u9fff]+/g, " ").trim()
  return ["hi", "hello", "hey", "你好", "您好", "嗨", "哈喽"].includes(normalized)
}

function isClearlyUnclearMessage(message: string, awaitingPreference: string | null) {
  const compact = message.trim().toLowerCase().replace(/\s+/g, "")
  if (awaitingPreference !== null) return false
  if (/[?？]/.test(compact) || /\d/.test(compact)) return false
  if (["hi", "go", "ok", "yes", "no", "嗨", "你好", "是", "否"].includes(compact)) return false
  if (["欸", "诶", "呃", "嗯", "额", "啊", "哦", "噢"].includes(compact)) return true
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

function getScenarioQuickReplies(language: "en" | "zh"): QuickReply[] {
  return language === "zh"
    ? [
        { id: "scenario_college", label: "我有目标大学" },
        { id: "scenario_major", label: "我有目标专业" },
        { id: "scenario_explore", label: "我还在探索" },
      ]
    : [
        { id: "scenario_college", label: "I have a target college" },
        { id: "scenario_major", label: "I have a target field" },
        { id: "scenario_explore", label: "I’m still exploring" },
      ]
}

function PreferenceSummary({ preferences, answered, language, disabled, onEdit }: { preferences: CollegePreferences; answered: string[]; language: "en" | "zh"; disabled: boolean; onEdit: (key: string, label: string) => void }) {
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
    field: zh ? `专业：${preferences.field}` : `Field: ${preferences.field}`,
    states: zh ? `地区：${preferences.states || "不限"}` : `Location: ${preferences.states || "Any"}`,
    max_cost: zh ? `费用：${preferences.max_cost ? `$${preferences.max_cost.toLocaleString()}` : "不限"}` : `Cost: ${preferences.max_cost ? `$${preferences.max_cost.toLocaleString()}` : "Any"}`,
    size: zh ? `规模：${localizedValue(preferences.size[0])}` : `Size: ${localizedValue(preferences.size[0])}`,
    competition: zh ? `整体录取率：${preferences.admission_rate_min}%–${preferences.admission_rate_max}%` : `Overall admission rate: ${preferences.admission_rate_min}%–${preferences.admission_rate_max}%`,
    sat: preferences.sat ? `SAT：${preferences.sat}` : (zh ? "SAT：未提供" : "SAT: skipped"),
    act: preferences.act ? `ACT：${preferences.act}` : (zh ? "ACT：未提供" : "ACT: skipped"),
    ownership: zh ? `性质：${localizedValue(preferences.ownership[0])}` : `Control: ${localizedValue(preferences.ownership[0])}`,
    institution_format: zh ? `院校类型：${localizedValue(preferences.institution_format[0])}` : `Institution type: ${localizedValue(preferences.institution_format[0])}`,
    targets: zh ? `目标大学：${preferences.targets}` : `Target: ${preferences.targets}`,
    count: zh ? `数量：${preferences.count} 所` : `Count: ${preferences.count}`,
  }
  return (
    <div className="mb-3 flex flex-wrap gap-2">
      {answered.filter((key) => labels[key]).map((key) => (
        <button
          key={key}
          type="button"
          className="dream-chip rounded-full px-3 py-1 text-xs text-zinc-700 transition hover:-translate-y-px hover:shadow-sm disabled:opacity-60"
          disabled={disabled}
          onClick={() => onEdit(key, labels[key])}
          title={zh ? "点击修改" : "Click to edit"}
        >
          {labels[key]}
        </button>
      ))}
    </div>
  )
}

function AdmissionRateRange({ disabled, language, onSubmit }: { disabled: boolean; language: "en" | "zh"; onSubmit: (min: number, max: number) => void }) {
  const [min, setMin] = useState(0)
  const [max, setMax] = useState(100)
  const [activeThumb, setActiveThumb] = useState<"min" | "max" | null>(null)
  const zh = language === "zh"
  const fill = { left: `${min}%`, right: `${100 - max}%` }

  return (
    <div className="mb-3 rounded-2xl border border-zinc-200 bg-white p-4 shadow-sm">
      <div className="mb-3 flex items-center justify-between gap-4">
        <span className="text-sm font-medium text-zinc-700">{zh ? "学校整体录取率范围" : "Overall admission-rate range"}</span>
        <span className="rounded-full bg-zinc-100 px-3 py-1 text-sm tabular-nums text-zinc-700">{min}%–{max}%</span>
      </div>
      <div className="admission-range relative h-10" aria-label={zh ? "录取率范围" : "Admission-rate range"}>
        <div className="admission-range-rail absolute inset-x-0 top-[17px] h-1.5 rounded-full" />
        <div className="admission-range-fill absolute top-[17px] h-1.5 rounded-full" style={fill} />
        <input className="range-thumb absolute inset-x-0 top-0 w-full" style={{ zIndex: activeThumb === "min" ? 5 : 3 }} type="range" min="0" max="100" step="1" value={min} disabled={disabled} aria-label={zh ? "最低录取率" : "Minimum admission rate"} onFocus={() => setActiveThumb("min")} onPointerDown={() => setActiveThumb("min")} onPointerUp={() => setActiveThumb(null)} onBlur={() => setActiveThumb(null)} onChange={(e) => setMin(Math.min(Number(e.target.value), max - 1))} />
        <input className="range-thumb absolute inset-x-0 top-0 w-full" style={{ zIndex: activeThumb === "max" ? 5 : 4 }} type="range" min="0" max="100" step="1" value={max} disabled={disabled} aria-label={zh ? "最高录取率" : "Maximum admission rate"} onFocus={() => setActiveThumb("max")} onPointerDown={() => setActiveThumb("max")} onPointerUp={() => setActiveThumb(null)} onBlur={() => setActiveThumb(null)} onChange={(e) => setMax(Math.max(Number(e.target.value), min + 1))} />
      </div>
      <div className="flex items-center justify-between px-0.5 text-xs tabular-nums text-zinc-400"><span>0%</span><span>100%</span></div>
      <div className="mt-3 flex items-center justify-between gap-3">
        <p className="text-xs text-zinc-500">{zh ? "这是学校整体录取率，不代表你的个人录取概率。" : "This is the school's overall rate, not your personal admission chance."}</p>
        <button type="button" className="quick-reply shrink-0" disabled={disabled} onClick={() => onSubmit(min, max)}>{zh ? "确认范围" : "Apply range"}</button>
      </div>
    </div>
  )
}

function CollegeCountInput({ language, disabled, initialValue, onSubmit }: { language: "en" | "zh"; disabled: boolean; initialValue: number; onSubmit: (count: number) => void }) {
  const [count, setCount] = useState(Math.min(20, Math.max(1, initialValue)))
  const zh = language === "zh"
  return (
    <div className="mb-3 flex flex-wrap items-center justify-between gap-3 rounded-2xl border border-[#e1dee9] bg-white/80 p-3 shadow-sm">
      <span className="text-sm text-zinc-600">{zh ? "推荐数量" : "Number of colleges"}</span>
      <div className="flex items-center gap-2">
        <button type="button" className="flex h-9 w-9 items-center justify-center rounded-full border border-[#d7d3e1] bg-white text-[#625e70] hover:bg-[#f5f3f7] disabled:opacity-40" disabled={disabled || count <= 1} onClick={() => setCount((value) => Math.max(1, value - 1))} aria-label={zh ? "减少数量" : "Decrease count"}><Minus className="h-4 w-4" /></button>
        <input className="h-9 w-14 rounded-lg border border-[#d7d3e1] bg-white text-center text-sm tabular-nums outline-none focus:border-[#9993b7] focus:ring-2 focus:ring-[#b8b4d8]/25" type="number" min="1" max="20" value={count} disabled={disabled} onChange={(event) => setCount(Math.min(20, Math.max(1, Number(event.target.value) || 1)))} aria-label={zh ? "推荐大学数量" : "College count"} />
        <button type="button" className="flex h-9 w-9 items-center justify-center rounded-full border border-[#d7d3e1] bg-white text-[#625e70] hover:bg-[#f5f3f7] disabled:opacity-40" disabled={disabled || count >= 20} onClick={() => setCount((value) => Math.min(20, value + 1))} aria-label={zh ? "增加数量" : "Increase count"}><Plus className="h-4 w-4" /></button>
        <button type="button" className="quick-reply ml-1" disabled={disabled} onClick={() => onSubmit(count)}>{zh ? "确认" : "Apply"}</button>
      </div>
    </div>
  )
}
