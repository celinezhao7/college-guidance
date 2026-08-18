import { useEffect, useLayoutEffect, useRef, useState } from "react"

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
  field: "Computer Science",
  targets: "No specific target",
  count: 5,
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
  const [setupError, setSetupError] = useState("")
  const [collegePreferences, setCollegePreferences] = useState(defaultCollegePreferences)
  const [sessionId, setSessionId] = useState<string | null>(null)
  const [answeredPreferences, setAnsweredPreferences] = useState<string[]>([])
  const scrollViewportRef = useRef<HTMLDivElement>(null)

  useEffect(() => {
    loadRecommendationOptions()
      .then(({ profiles: nextProfiles, modes: nextModes }) => {
        setProfiles(nextProfiles)
        setModes(nextModes)
        setProfileId(nextProfiles[0]?.id ?? "")
        setModeId(nextModes[0]?.id ?? "")
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
    } catch (error) {
      const detail =
        error instanceof Error ? error.message : "The recommendation failed."
      setMessages((previous) =>
        previous.map((message, index) =>
          index === previous.length - 1
            ? {
                ...message,
                content:
                  language === "zh"
                    ? `抱歉，无法生成推荐。${detail}`
                    : `Sorry, I couldn't generate a recommendation. ${detail}`,
              }
            : message,
        ),
      )
    } finally {
      setIsStreaming(false)
    }
  }

  async function handleCollegeMessage(message: string) {
    setMessages((previous) => [...previous, { role: "user", content: message }])
    setInput("")
    setIsStreaming(true)
    try {
      const response = await continueCollegeConversation({
        sessionId,
        profileId,
        language,
        message,
      })
      setSessionId(response.session_id)
      setCollegePreferences(response.preferences)
      setAnsweredPreferences(response.answered)
      setMessages((previous) => [
        ...previous,
        { role: "assistant", content: response.reply },
      ])

      if (response.ready) {
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
    } catch (error) {
      const detail = error instanceof Error ? error.message : "Request failed."
      setMessages((previous) => [
        ...previous,
        {
          role: "assistant",
          content: language === "zh" ? `抱歉，出现错误：${detail}` : `Sorry, something went wrong: ${detail}`,
        },
      ])
    } finally {
      setIsStreaming(false)
    }
  }

  const controlsDisabled = isLoadingOptions || isStreaming
  const composerDisabled =
    controlsDisabled || Boolean(setupError) || !profileId || !modeId
  const zh = language === "zh"

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
    setSessionId(null)
    setAnsweredPreferences([])
    setCollegePreferences(defaultCollegePreferences)
  }

  return (
    <div className="flex h-screen overflow-hidden bg-[#f7f6f2] text-zinc-900">
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
              <div className="mb-8 text-center">
                <h1 className="text-3xl font-medium tracking-tight">
                  {zh ? "今天想探索什么？" : "How can I help you today?"}
                </h1>
                <p className="mt-2 text-sm text-zinc-500">
                  {zh ? "选择学生档案和推荐类型，然后告诉我你的需求。" : "Choose a student and recommendation type, then tell me what you need."}
                </p>
                {setupError && (
                  <p className="mt-3 text-sm text-red-600">
                    {zh ? "无法连接后端：" : "Could not load the backend: "}{setupError}
                  </p>
                )}
              </div>
              {modeId === "college_field" && (
                <p className="mb-5 text-center text-sm text-zinc-500">
                  {zh ? "直接告诉我你的目标，我会一次问一个问题。" : "Tell me your goal naturally. I’ll ask one useful question at a time."}
                </p>
              )}
              <ChatComposer
                input={input}
                setInput={setInput}
                onSend={handleSend}
                disabled={composerDisabled}
                requireInput
                placeholder={zh ? "请输入关于大学、专业或申请的问题……" : "Ask about colleges, majors, or your application..."}
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
                      {modeId === "college_field"
                        ? (zh ? "正在查找符合条件的大学……" : "Searching for colleges that match your preferences…")
                        : (zh ? "正在生成推荐……" : "Generating recommendation…")}
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

function PreferenceSummary({ preferences, answered, language }: { preferences: CollegePreferences; answered: string[]; language: "en" | "zh" }) {
  const labels: Record<string, string> = {
    field: preferences.field,
    states: preferences.states || (language === "zh" ? "州不限" : "Any state"),
    max_cost: preferences.max_cost ? `$${preferences.max_cost.toLocaleString()}` : (language === "zh" ? "费用不限" : "No cost limit"),
    size: preferences.size[0],
    competition: preferences.competition[0],
    sat: preferences.sat ? `SAT ${preferences.sat}` : (language === "zh" ? "未提供 SAT" : "SAT skipped"),
    act: preferences.act ? `ACT ${preferences.act}` : (language === "zh" ? "未提供 ACT" : "ACT skipped"),
    ownership: preferences.ownership[0],
    institution_format: preferences.institution_format[0],
    targets: preferences.targets,
    count: language === "zh" ? `${preferences.count} 所学校` : `${preferences.count} schools`,
  }
  return (
    <div className="mb-3 flex flex-wrap gap-2">
      {answered.map((key) => <span key={key} className="rounded-full bg-zinc-200 px-3 py-1 text-xs text-zinc-700">{labels[key]}</span>)}
    </div>
  )
}
