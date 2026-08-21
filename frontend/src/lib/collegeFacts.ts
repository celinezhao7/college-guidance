export type CollegeFact = {
  name: string | null
  city: string | null
  state: string | null
  admission_rate: number | null
  attendance_cost: number | null
  average_net_price: number | null
  undergraduate_size: number | null
  reported_field: string | null
  reported_field_status: "direct_title_match" | "related_cip_field" | "not_verified"
  field_taxonomy: string
  official_url: string | null
  source: string
  data_vintage: string
  retrieved_on: string
  official_sources: Array<{ kind: "majors" | "first_year_requirements" | "cost"; url: string; status: "official_link" }>
}

export type CollegeContentPart =
  | { type: "markdown"; content: string }
  | { type: "college"; fact: CollegeFact }

const startMarker = ":::college-fact"
const endMarker = "\n:::"

export function parseCollegeFactContent(content: string): CollegeContentPart[] {
  const parts: CollegeContentPart[] = []
  let cursor = 0

  while (cursor < content.length) {
    const start = content.indexOf(startMarker, cursor)
    if (start < 0) {
      pushMarkdown(parts, content.slice(cursor))
      break
    }

    pushMarkdown(parts, content.slice(cursor, start))
    const jsonStart = start + startMarker.length
    const end = content.indexOf(endMarker, jsonStart)
    if (end < 0) break // The stream has not delivered the complete card yet.

    try {
      const fact = JSON.parse(content.slice(jsonStart, end).trim()) as CollegeFact
      parts.push({ type: "college", fact })
    } catch {
      pushMarkdown(parts, content.slice(start, end + endMarker.length))
    }
    cursor = end + endMarker.length
  }

  return parts
}

function pushMarkdown(parts: CollegeContentPart[], content: string) {
  if (content.trim()) parts.push({ type: "markdown", content })
}
