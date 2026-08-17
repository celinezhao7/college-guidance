export type Profile = {
  id: string
  display_name: string
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
  field: string
  targets: string
  count: number
}

type ProfilesResponse = { profiles: Profile[] }
type ModesResponse = { modes: RecommendationMode[] }

async function requestJson<T>(path: string): Promise<T> {
  const response = await fetch(path)

  if (!response.ok) {
    throw new Error(`Request failed (${response.status})`)
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
  },
  onChunk: (text: string) => void,
) {
  const response = await fetch("/api/recommend", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({
      profile_id: request.profileId,
      mode: request.mode,
      language: request.language,
      query: request.query,
      college_preferences: request.collegePreferences,
    }),
  })

  if (!response.ok) {
    const payload = (await response.json().catch(() => null)) as
      | { detail?: string }
      | null
    throw new Error(payload?.detail ?? `Request failed (${response.status})`)
  }

  if (!response.body) {
    throw new Error("The server returned an empty response.")
  }

  const reader = response.body.getReader()
  const decoder = new TextDecoder()

  while (true) {
    const { done, value } = await reader.read()
    if (done) break
    onChunk(decoder.decode(value, { stream: true }))
  }

  const finalChunk = decoder.decode()
  if (finalChunk) onChunk(finalChunk)
}

export async function continueCollegeConversation(request: {
  sessionId: string | null
  profileId: string
  language: "en" | "zh"
  message: string
}) {
  const response = await fetch("/api/chat", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({
      session_id: request.sessionId,
      profile_id: request.profileId,
      language: request.language,
      message: request.message,
    }),
  })
  if (!response.ok) {
    const payload = (await response.json().catch(() => null)) as { detail?: string } | null
    throw new Error(payload?.detail ?? `Request failed (${response.status})`)
  }
  return response.json() as Promise<{
    session_id: string
    reply: string
    ready: boolean
    preferences: CollegePreferences
    answered: string[]
  }>
}
