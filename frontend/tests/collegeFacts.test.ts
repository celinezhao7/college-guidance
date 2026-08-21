import { describe, expect, it } from "vitest"
import { parseCollegeFactContent } from "../src/lib/collegeFacts"

const fact = { name: "Example University", city: "Example", state: "CA", admission_rate: 0.25, attendance_cost: 50000, average_net_price: null, undergraduate_size: 12000, reported_field: "Computer Science", reported_field_status: "direct_title_match" as const, field_taxonomy: "NCES CIP 2020 four-digit field", official_url: "https://example.edu", source: "College Scorecard", data_vintage: "latest available value per metric; reporting years may differ", retrieved_on: "2026-08-21", official_sources: [] }

describe("parseCollegeFactContent", () => {
  it("separates deterministic fact cards from model prose", () => {
    const content = `Before\n\n:::college-fact\n${JSON.stringify(fact)}\n:::\n\n## Personalized fit explanations`
    const parts = parseCollegeFactContent(content)
    expect(parts.map(part => part.type)).toEqual(["markdown", "college", "markdown"])
    expect(parts[1]).toMatchObject({ type: "college", fact: { name: "Example University" } })
  })

  it("hides an incomplete streaming card until its closing marker arrives", () => {
    const parts = parseCollegeFactContent(`Visible note\n\n:::college-fact\n{"name":"Ex`)
    expect(parts).toEqual([{ type: "markdown", content: "Visible note\n\n" }])
  })

  it("leaves ordinary markdown unchanged", () => {
    expect(parseCollegeFactContent("## Hello")).toEqual([{ type: "markdown", content: "## Hello" }])
  })
})
