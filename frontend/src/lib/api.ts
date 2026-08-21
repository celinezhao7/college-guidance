export type Profile = {
  id: string
  display_name: string
  display_name_en: string
  display_name_zh: string
}

export type RecommendationMode = {
  id: string
  title_en: string
  title_zh: string
}

export type CollegePreferences = {
  sat: number | null
  act: number | null
  states: string
  max_cost: number | null
  size: string[]
  ownership: string[]
  institution_format: string[]
  competition: string[]
  admission_rate_min: number
  admission_rate_max: number
  field: string
  targets: string
  count: number
}

export type QuickReply = {
  id: string
  label: string
}

export type ProfileAddition = {
  experience_number: number | null
  experience_title: string | null
  action: string
  outcome: string
  reflection: string
  source: string
}

export type ProfileAdditionRecord = ProfileAddition & {
  id: string
  confirmed_at: string
}

export type StructuredExperience = {
  experience_number: number | null
  experience_title: string
  category: string
  background: string
  challenge: string
  action: string
  outcome: string
  reflection: string
  traits: string[]
  missing_fields: Array<"action" | "outcome" | "reflection">
  status: "documented" | "enriched" | "user_confirmed"
  sources: Array<{
    kind: "original_profile" | "user_confirmed"
    label: string
    record_id: string | null
    confirmed_at: string | null
  }>
  additions: ProfileAdditionRecord[]
}

export type StructuredStudentProfile = {
  profile_id: string
  profile_name: string
  academic_interests: string[]
  background: string[]
  core_themes: string[]
  experiences: StructuredExperience[]
}

const RECOMMENDATION_TOTAL_TIMEOUT_MS = 180_000
const RECOMMENDATION_IDLE_TIMEOUT_MS = 45_000

type ProfilesResponse = { profiles: Profile[] }
type ModesResponse = { modes: RecommendationMode[] }

export class ApiError extends Error {
  status: number
  retryAfter: number | null

  constructor(
    status: number,
    message: string,
    retryAfter: number | null = null,
  ) {
    super(message)
    this.name = "ApiError"
    this.status = status
    this.retryAfter = retryAfter
  }
}

async function responseError(response: Response) {
  const payload = (await response.json().catch(() => null)) as
    | { detail?: string }
    | null
  const retryAfter = Number(response.headers.get("Retry-After"))
  return new ApiError(
    response.status,
    payload?.detail ?? `Request failed (${response.status})`,
    Number.isFinite(retryAfter) ? retryAfter : null,
  )
}

async function requestJson<T>(path: string): Promise<T> {
  const response = await fetch(path)

  if (!response.ok) {
    throw await responseError(response)
  }

  return response.json() as Promise<T>
}

export async function loadRecommendationOptions() {
  const [profilesResponse, modesResponse] = await Promise.all([
    requestJson<ProfilesResponse>("/api/profiles"),
    requestJson<ModesResponse>("/api/modes"),
  ])

  return {
    profiles: profilesResponse.profiles,
    modes: modesResponse.modes,
  }
}

export async function streamRecommendation(
  request: {
    profileId: string
    mode: string
    language: "en" | "zh"
    query: string
    collegePreferences?: CollegePreferences
    collegeScenario?: string | null
    history?: Array<{ role: "user" | "assistant"; content: string }>
    signal?: AbortSignal
  },
  onChunk: (text: string) => void,
) {
  const controller = new AbortController()
  const totalTimeout = setTimeout(
    () => controller.abort("total-timeout"),
    RECOMMENDATION_TOTAL_TIMEOUT_MS,
  )
  const cancelFromCaller = () => controller.abort("user-cancelled")
  if (request.signal?.aborted) cancelFromCaller()
  request.signal?.addEventListener("abort", cancelFromCaller, { once: true })

  try {
  const response = await fetch("/api/recommend", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({
      profile_id: request.profileId,
      mode: request.mode,
      language: request.language,
      query: request.query,
      college_preferences: request.collegePreferences,
      college_scenario: request.collegeScenario,
      history: request.history ?? [],
    }),
    signal: controller.signal,
  })

  if (!response.ok) {
    throw await responseError(response)
  }

  if (!response.body) {
    throw new Error("The server returned an empty response.")
  }

  const reader = response.body.getReader()
  const decoder = new TextDecoder()
  let pendingText = ""
  let flushTimer: ReturnType<typeof setTimeout> | null = null

  const flush = () => {
    if (pendingText) {
      onChunk(pendingText)
      pendingText = ""
    }
    flushTimer = null
  }

  const queueForRender = (text: string) => {
    pendingText += text
    if (flushTimer === null) flushTimer = setTimeout(flush, 50)
  }

  while (true) {
    let idleTimeout: ReturnType<typeof setTimeout> | null = null
    const idleFailure = new Promise<never>((_, reject) => {
      idleTimeout = setTimeout(
        () => {
          controller.abort("idle-timeout")
          reject(new Error("RECOMMENDATION_TIMEOUT"))
        },
        RECOMMENDATION_IDLE_TIMEOUT_MS,
      )
    })
    let readResult: ReadableStreamReadResult<Uint8Array>
    try {
      readResult = await Promise.race([reader.read(), idleFailure])
    } finally {
      if (idleTimeout !== null) clearTimeout(idleTimeout)
    }
    const { done, value } = readResult
    if (done) break
    queueForRender(decoder.decode(value, { stream: true }))
  }

  const finalChunk = decoder.decode()
  if (finalChunk) pendingText += finalChunk
  if (flushTimer !== null) clearTimeout(flushTimer)
  flush()
  } catch (error) {
    if (controller.signal.aborted && controller.signal.reason === "user-cancelled") {
      throw new Error("RECOMMENDATION_CANCELLED", { cause: error })
    }
    if (
      controller.signal.aborted
      || (error instanceof Error && error.message === "RECOMMENDATION_TIMEOUT")
    ) {
      throw new Error("RECOMMENDATION_TIMEOUT", { cause: error })
    }
    throw error
  } finally {
    clearTimeout(totalTimeout)
    request.signal?.removeEventListener("abort", cancelFromCaller)
  }
}

export async function continueCollegeConversation(request: {
  sessionId: string | null
  profileId: string
  language: "en" | "zh"
  message: string
  choiceId?: string
}) {
  const response = await fetch("/api/chat", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({
      session_id: request.sessionId,
      profile_id: request.profileId,
      language: request.language,
      message: request.message,
      choice_id: request.choiceId,
    }),
  })
  if (!response.ok) {
    throw await responseError(response)
  }
  return response.json() as Promise<{
    session_id: string
    reply: string
    ready: boolean
    preferences: CollegePreferences
    answered: string[]
    scenario: string | null
    quick_replies: QuickReply[]
    awaiting: string | null
    session_reset: boolean
  }>
}

export async function previewProfileAddition(request: {
  profileId: string
  question: string
  answer: string
}) {
  const response = await fetch("/api/profile-additions/preview", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({
      profile_id: request.profileId,
      question: request.question,
      answer: request.answer,
    }),
  })
  if (!response.ok) throw await responseError(response)
  return response.json() as Promise<ProfileAddition>
}

export async function saveProfileAddition(profileId: string, addition: ProfileAddition) {
  const response = await fetch("/api/profile-additions", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ profile_id: profileId, addition }),
  })
  if (!response.ok) throw await responseError(response)
  return response.json() as Promise<ProfileAdditionRecord>
}

export async function loadProfileAdditions(profileId: string) {
  return requestJson<ProfileAdditionRecord[]>(`/api/profile-additions/${profileId}`)
}

export async function loadStructuredProfile(profileId: string) {
  return requestJson<StructuredStudentProfile>(`/api/profiles/${profileId}/information`)
}

export async function updateProfileAddition(
  profileId: string,
  additionId: string,
  addition: ProfileAddition,
) {
  const response = await fetch(`/api/profile-additions/${profileId}/${additionId}`, {
    method: "PUT",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(addition),
  })
  if (!response.ok) throw await responseError(response)
  return response.json() as Promise<ProfileAdditionRecord>
}

export async function deleteProfileAddition(profileId: string, additionId: string) {
  const response = await fetch(`/api/profile-additions/${profileId}/${additionId}`, {
    method: "DELETE",
  })
  if (!response.ok) throw await responseError(response)
}
