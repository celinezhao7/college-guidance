const blockLabels = [
  { match: "Fit Level", display: "Fit Level" },
  { match: "Why it fits", display: "Why it fits" },
  { match: "Skills/Interests it develops", display: "Skills/Interests it develops" },
  { match: "Evidence Limitations", display: "Evidence Limitations" },
  { match: "Question to investigate", display: "Question to investigate" },
  { match: "适配度", display: "适配度" },
  { match: "适配原因", display: "适配原因" },
  { match: "培养的技能/兴趣", display: "培养的技能/兴趣" },
  { match: "证据局限", display: "证据局限" },
  { match: "探索问题", display: "探索问题" },
]

export function normalizeAssistantMarkdown(content: string) {
  const isFieldReport = /\bFit Level\s*:|\bSkills\/Interests it develops\s*:|适配度\s*:|培养的技能\/兴趣\s*:/i.test(content)
  if (!isFieldReport) return content

  let normalized = content

  for (const label of blockLabels) {
    const escaped = label.match.replace(/[.*+?^${}()|[\]\\]/g, "\\$&")
    normalized = normalized.replace(
      new RegExp(`(?<!\\*)${escaped}\\s*[:：]\\s*`, "gi"),
      `\n\n**${label.display}:**\n\n`,
    )
  }

  return normalized
    .replace(/(?<![#*])\bSupporting Evidence\s*[:：]?\s*/gi, "\n\n### Supporting Evidence\n\n")
    .replace(/(?<![#*])支持证据\s*[:：]?\s*/g, "\n\n### 支持证据\n\n")
    .replace(/\bComparison of(?: the)? Top Two Fields\s*[:：]?\s*/gi, "\n\n## Comparison of the Top Two Fields\n\n")
    .replace(/\bNext Step\s*[:：]?\s*/gi, "\n\n## Next Step\n\n")
    .replace(/前两项比较\s*[:：]?\s*/g, "\n\n## 前两项比较\n\n")
    .replace(/下一步\s*[:：]?\s*/g, "\n\n## 下一步\n\n")
    .replace(/^(?!#)(\d+)\.\s+([^\n]+)$/gm, "## $1. $2")
    .replace(/^(Experience\s+\d+\s*:[^\n]+)$/gim, "- $1")
    .replace(/^(经历\s*\d+\s*[:：][^\n]+)$/gm, "- $1")
    .replace(/\n{3,}/g, "\n\n")
    .trim()
}
