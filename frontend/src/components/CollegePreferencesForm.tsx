import type { CollegePreferences } from "@/lib/api"

type Props = {
  value: CollegePreferences
  disabled: boolean
  onChange: (value: CollegePreferences) => void
  language: "en" | "zh"
}

const inputClass =
  "w-full rounded-lg border border-zinc-300 bg-white px-3 py-2 text-sm disabled:opacity-50"

export function CollegePreferencesForm({ value, disabled, onChange, language }: Props) {
  const zh = language === "zh"
  const update = <K extends keyof CollegePreferences>(
    key: K,
    nextValue: CollegePreferences[K],
  ) => onChange({ ...value, [key]: nextValue })

  const optionalNumber = (raw: string) => (raw === "" ? null : Number(raw))

  return (
    <div className="mb-6 rounded-2xl border border-zinc-200 bg-white p-5 shadow-sm">
      <h2 className="mb-4 font-medium">{zh ? "大学推荐偏好" : "College recommendation preferences"}</h2>
      <div className="grid grid-cols-2 gap-4 md:grid-cols-3">
        <Field label={zh ? "SAT 分数（可选）" : "SAT score (optional)"}>
          <input className={inputClass} type="number" min="400" max="1600" value={value.sat ?? ""} disabled={disabled} onChange={(e) => update("sat", optionalNumber(e.target.value))} />
        </Field>
        <Field label={zh ? "ACT 分数（可选）" : "ACT score (optional)"}>
          <input className={inputClass} type="number" min="1" max="36" value={value.act ?? ""} disabled={disabled} onChange={(e) => update("act", optionalNumber(e.target.value))} />
        </Field>
        <Field label={zh ? "偏好的州" : "Preferred states"}>
          <input className={inputClass} value={value.states} disabled={disabled} placeholder="CA, MI" onChange={(e) => update("states", e.target.value)} />
        </Field>
        <Field label={zh ? "助学金前最高年度费用" : "Maximum annual cost before aid"}>
          <input className={inputClass} type="number" min="1" value={value.max_cost ?? ""} disabled={disabled} onChange={(e) => update("max_cost", optionalNumber(e.target.value))} />
        </Field>
        <Field label={zh ? "学校规模" : "School size"}>
          <Select value={value.size[0]} disabled={disabled} onChange={(v) => update("size", [v])} options={zh ? { any: "不限", small: "小型", medium: "中型", large: "大型" } : { any: "Any", small: "Small", medium: "Medium", large: "Large" }} />
        </Field>
        <Field label={zh ? "学校性质" : "School ownership"}>
          <Select value={value.ownership[0]} disabled={disabled} onChange={(v) => update("ownership", [v])} options={zh ? { any: "不限", public: "公立", private_nonprofit: "私立非营利", private_for_profit: "私立营利" } : { any: "Any", public: "Public", private_nonprofit: "Private nonprofit", private_for_profit: "Private for-profit" }} />
        </Field>
        <Field label={zh ? "学校类型" : "Institution format"}>
          <Select value={value.institution_format[0]} disabled={disabled} onChange={(v) => update("institution_format", [v])} options={zh ? { either: "不限", university: "综合性大学", liberal_arts: "文理学院" } : { either: "Either", university: "University", liberal_arts: "Liberal arts college" }} />
        </Field>
        <Field label={zh ? "学校竞争程度" : "Institutional competition"}>
          <Select value={value.competition[0]} disabled={disabled} onChange={(v) => update("competition", [v])} options={zh ? { any: "不限", low: "较低（录取率 60% 以上）", medium: "中等（25%–60%）", high: "较高（低于 25%）" } : { any: "Any", low: "Lower (60%+ admit rate)", medium: "Medium (25–60%)", high: "Higher (under 25%)" }} />
        </Field>
        <Field label={zh ? "意向专业领域" : "Intended field"}>
          <input className={inputClass} value={value.field} disabled={disabled} onChange={(e) => update("field", e.target.value)} />
        </Field>
        <Field label={zh ? "目标大学或大学系统" : "Target schools or systems"}>
          <input className={inputClass} value={value.targets} disabled={disabled} placeholder="UC, UMich" onChange={(e) => update("targets", e.target.value)} />
        </Field>
        <Field label={zh ? "推荐学校数量" : "Number of recommendations"}>
          <input className={inputClass} type="number" min="1" max="20" value={value.count} disabled={disabled} onChange={(e) => update("count", Number(e.target.value))} />
        </Field>
      </div>
      <p className="mt-4 text-xs text-zinc-500">
        {zh ? "SAT 和 ACT 仅作为背景信息；本工具不会计算个人录取概率。" : "SAT and ACT provide context only. The app does not calculate personal admission chances."}
      </p>
    </div>
  )
}

function Field({ label, children }: { label: string; children: React.ReactNode }) {
  return <label className="space-y-1.5 text-xs font-medium text-zinc-600"><span>{label}</span>{children}</label>
}

function Select({ value, disabled, onChange, options }: { value: string; disabled: boolean; onChange: (value: string) => void; options: Record<string, string> }) {
  return <select className={inputClass} value={value} disabled={disabled} onChange={(e) => onChange(e.target.value)}>{Object.entries(options).map(([key, label]) => <option key={key} value={key}>{label}</option>)}</select>
}
