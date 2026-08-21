import { useEffect, useRef, useState } from "react"
import { CheckCircle2, CircleDashed, Pencil, Plus, Trash2, X } from "lucide-react"
import type { ProfileAddition, ProfileAdditionRecord, StructuredStudentProfile } from "@/lib/api"

type Props = { open: boolean; language: "en" | "zh"; records: ProfileAdditionRecord[]; profile: StructuredStudentProfile | null; loading: boolean; error: string; onClose: () => void; onCreate: (addition: ProfileAddition) => Promise<void>; onUpdate: (id: string, addition: ProfileAddition) => Promise<void>; onDelete: (id: string) => Promise<void> }

const emptyAddition: ProfileAddition = { experience_number: null, experience_title: "", action: "", outcome: "", reflection: "", source: "user_confirmed" }

export function ProfileInformationManager({ open, language, records, profile, loading, error, onClose, onCreate, onUpdate, onDelete }: Props) {
  const [editing, setEditing] = useState<ProfileAdditionRecord | null>(null)
  const [creating, setCreating] = useState(false)
  const [draft, setDraft] = useState<ProfileAddition>(emptyAddition)
  const dialogRef = useRef<HTMLElement>(null)
  useEffect(() => {
    if (!open) return
    const previousFocus = document.activeElement instanceof HTMLElement ? document.activeElement : null
    const previousOverflow = document.body.style.overflow
    document.body.style.overflow = "hidden"
    const frame = requestAnimationFrame(() => dialogRef.current?.querySelector<HTMLElement>("[data-dialog-close]")?.focus())
    return () => {
      cancelAnimationFrame(frame)
      document.body.style.overflow = previousOverflow
      const mobileReturn = document.querySelector<HTMLElement>("[data-dialog-return]")
      if (mobileReturn?.getClientRects().length) mobileReturn.focus()
      else if (previousFocus?.isConnected && previousFocus.getClientRects().length > 0 && getComputedStyle(previousFocus).visibility !== "hidden") previousFocus.focus()
    }
  }, [open])
  if (!open) return null
  const zh = language === "zh"
  const setField = (field: "action" | "outcome" | "reflection", value: string) => setEditing((current) => current ? { ...current, [field]: value } : null)
  return <div
    className="fixed inset-0 z-50 flex items-center justify-center bg-[#302c42]/25 p-4 backdrop-blur-sm"
    onMouseDown={(event) => {
      if (event.target === event.currentTarget) onClose()
    }}
  >
    <section ref={dialogRef} role="dialog" aria-modal="true" aria-labelledby="profile-dialog-title" className="max-h-[90dvh] w-full max-w-3xl overflow-y-auto overscroll-contain rounded-2xl border border-[#dfdce8] bg-[#fcfbfe] p-5 shadow-2xl" onKeyDown={(event) => {
      if (event.key === "Escape") { event.preventDefault(); onClose(); return }
      if (event.key !== "Tab" || !dialogRef.current) return
      const focusable = [...dialogRef.current.querySelectorAll<HTMLElement>('button:not([disabled]), input:not([disabled]), textarea:not([disabled]), select:not([disabled]), a[href], [tabindex]:not([tabindex="-1"])')].filter((item) => item.offsetParent !== null)
      if (!focusable.length) return
      const first = focusable[0], last = focusable[focusable.length - 1]
      if (event.shiftKey && document.activeElement === first) { event.preventDefault(); last.focus() }
      else if (!event.shiftKey && document.activeElement === last) { event.preventDefault(); first.focus() }
    }}>
      <div className="mb-5 flex items-start gap-3"><div><h2 id="profile-dialog-title" className="text-lg font-semibold">{zh ? "统一学生画像" : "Unified student profile"}</h2><p className="mt-1 text-sm text-zinc-500">{zh ? "原始档案与用户确认信息已合并；来源始终保留，原始档案只读。" : "Original evidence and user-confirmed additions are merged with source labels. Original evidence is read-only."}</p></div><button data-dialog-close type="button" className="ml-auto flex h-11 w-11 shrink-0 items-center justify-center rounded-full hover:bg-zinc-100" onClick={onClose} aria-label={zh ? "关闭" : "Close"}><X className="h-4 w-4" /></button></div>
      {error && <p className="mb-4 rounded-lg bg-red-50 px-3 py-2 text-sm text-red-700">{error}</p>}
      {loading && <p className="text-sm text-zinc-500">{zh ? "正在整理学生画像……" : "Organizing student profile…"}</p>}
      {!loading && profile && <><section className="mb-5 grid gap-3 md:grid-cols-3"><Summary title={zh ? "学术兴趣" : "Academic interests"} values={profile.academic_interests} /><Summary title={zh ? "背景" : "Background"} values={profile.background} /><Summary title={zh ? "核心主题" : "Core themes"} values={profile.core_themes} /></section>
        <div className="mb-3 flex flex-wrap items-center gap-3"><h3 className="font-semibold">{zh ? `经历（${profile.experiences.length}）` : `Experiences (${profile.experiences.length})`}</h3><span className="text-xs text-zinc-400">{zh ? `${records.length} 条用户确认补充` : `${records.length} user-confirmed additions`}</span><button type="button" className="quick-reply ml-auto flex items-center gap-1" onClick={() => setCreating(true)}><Plus className="h-3.5 w-3.5" />{zh ? "新增经历" : "Add experience"}</button></div>
        {creating && <NewExperienceForm zh={zh} draft={draft} setDraft={setDraft} onCancel={() => { setCreating(false); setDraft(emptyAddition) }} onSave={async () => { await onCreate(draft); setCreating(false); setDraft(emptyAddition) }} />}
        <p className="mb-3 text-xs text-zinc-500">{zh ? "“档案未记录”仅表示原始资料中没有该字段；只有它可能影响当前推荐时，系统才会询问。" : "“Not documented” means the source profile does not contain that field. The system asks only when it may affect the current recommendation."}</p>
        <div className="space-y-4">{profile.experiences.map((experience, index) => <article key={`${experience.experience_number ?? "new"}-${index}`} className="rounded-xl border border-[#e2dfea] bg-white p-4">
          <div className="flex flex-wrap items-start gap-2"><div><h4 className="font-medium">{experience.experience_number ? `Experience ${experience.experience_number}: ` : ""}{experience.experience_title}</h4>{experience.category && <p className="mt-0.5 text-xs text-zinc-500">{experience.category}</p>}</div><Status status={experience.status} zh={zh} /></div>
          <dl className="mt-4 grid gap-3 text-sm md:grid-cols-2"><Item label={zh ? "背景" : "Background"} value={experience.background} missing={!experience.background.trim()} zh={zh} /><Item label={zh ? "挑战" : "Challenge"} value={experience.challenge} missing={!experience.challenge.trim()} zh={zh} /><Item label={zh ? "学生行动" : "Student action"} value={experience.action} missing={experience.missing_fields.includes("action")} zh={zh} /><Item label={zh ? "结果或影响" : "Outcome or impact"} value={experience.outcome} missing={experience.missing_fields.includes("outcome")} zh={zh} /><Item label={zh ? "反思或成长" : "Reflection or growth"} value={experience.reflection} missing={experience.missing_fields.includes("reflection")} wide zh={zh} /></dl>
          {experience.traits.length > 0 && <div className="mt-3 flex flex-wrap gap-1.5">{experience.traits.map((trait) => <span key={trait} className="rounded-full bg-[#f1eef8] px-2 py-1 text-xs text-[#665d7a]">{trait}</span>)}</div>}
          <p className="mt-3 text-xs text-zinc-400">{zh ? "来源" : "Sources"}: {experience.sources.map((source) => source.kind === "original_profile" ? (zh ? "原始档案" : "Original profile") : (zh ? "用户确认" : "User confirmed")).join(" + ")}</p>
          {experience.additions.map((addition) => editing?.id === addition.id ? <div key={addition.id} className="mt-4 space-y-3 rounded-lg border border-[#ddd7ea] bg-[#faf8fd] p-3"><Field label={zh ? "补充的学生行动" : "Added student action"} value={editing.action} onChange={(value) => setField("action", value)} /><Field label={zh ? "补充的结果或影响" : "Added outcome or impact"} value={editing.outcome} onChange={(value) => setField("outcome", value)} /><Field label={zh ? "补充的反思或成长" : "Added reflection or growth"} value={editing.reflection} onChange={(value) => setField("reflection", value)} /><div className="flex gap-2"><button type="button" className="quick-reply" onClick={() => void onUpdate(addition.id, editing).then(() => setEditing(null))}>{zh ? "保存修改" : "Save changes"}</button><button type="button" className="quick-reply" onClick={() => setEditing(null)}>{zh ? "取消" : "Cancel"}</button></div></div> : <div key={addition.id} className="mt-3 flex items-center gap-2 rounded-lg bg-[#faf8fd] px-3 py-2 text-xs text-zinc-500"><span>{zh ? "用户确认补充" : "User-confirmed addition"} · {new Date(addition.confirmed_at).toLocaleString()}</span><button type="button" className="ml-auto rounded-lg p-1.5 hover:bg-zinc-100" onClick={() => setEditing(addition)} aria-label={zh ? "编辑" : "Edit"}><Pencil className="h-3.5 w-3.5" /></button><button type="button" className="rounded-lg p-1.5 text-red-600 hover:bg-red-50" onClick={() => { if (window.confirm(zh ? "确定删除这条补充信息吗？" : "Delete this profile addition?")) void onDelete(addition.id) }} aria-label={zh ? "删除" : "Delete"}><Trash2 className="h-3.5 w-3.5" /></button></div>)}
        </article>)}</div></>}
    </section>
  </div>
}

function NewExperienceForm({ zh, draft, setDraft, onCancel, onSave }: { zh: boolean; draft: ProfileAddition; setDraft: (value: ProfileAddition) => void; onCancel: () => void; onSave: () => Promise<void> }) {
  const valid = Boolean(draft.experience_title?.trim() && (draft.action.trim() || draft.outcome.trim() || draft.reflection.trim()))
  return <section className="mb-4 space-y-3 rounded-xl border border-[#d9d2e8] bg-white p-4">
    <h4 className="font-medium">{zh ? "新增一段用户确认的经历" : "Add a user-confirmed experience"}</h4>
    <div className="grid gap-3 md:grid-cols-[8rem_1fr]">
      <label className="text-sm"><span className="mb-1 block font-medium">{zh ? "经历编号（可选）" : "Experience number (optional)"}</span><input className="h-10 w-full rounded-lg border border-zinc-300 px-2" type="number" min="1" value={draft.experience_number ?? ""} onChange={(event) => setDraft({ ...draft, experience_number: event.target.value ? Number(event.target.value) : null })} /></label>
      <label className="text-sm"><span className="mb-1 block font-medium">{zh ? "经历标题" : "Experience title"}</span><input className="h-10 w-full rounded-lg border border-zinc-300 px-2" maxLength={300} value={draft.experience_title ?? ""} onChange={(event) => setDraft({ ...draft, experience_title: event.target.value })} /></label>
    </div>
    <Field label={zh ? "我具体做了什么" : "What I specifically did"} value={draft.action} onChange={(action) => setDraft({ ...draft, action })} />
    <Field label={zh ? "结果或影响" : "Outcome or impact"} value={draft.outcome} onChange={(outcome) => setDraft({ ...draft, outcome })} />
    <Field label={zh ? "反思或成长" : "Reflection or growth"} value={draft.reflection} onChange={(reflection) => setDraft({ ...draft, reflection })} />
    <p className="text-xs text-zinc-500">{zh ? "至少填写标题，以及行动、结果、反思中的一项。保存后会用于之后的推荐。" : "Enter a title and at least one of action, outcome, or reflection. Saved evidence will be available to future recommendations."}</p>
    <div className="flex gap-2"><button type="button" className="quick-reply" disabled={!valid} onClick={() => void onSave()}>{zh ? "保存经历" : "Save experience"}</button><button type="button" className="quick-reply" onClick={onCancel}>{zh ? "取消" : "Cancel"}</button></div>
  </section>
}

function Summary({ title, values }: { title: string; values: string[] }) { return <div className="rounded-xl border border-[#e2dfea] bg-white p-3"><h3 className="text-xs font-semibold uppercase tracking-wide text-zinc-500">{title}</h3><ul className="mt-2 space-y-1 text-sm text-zinc-700">{values.length ? values.map((value) => <li key={value}>• {value}</li>) : <li>—</li>}</ul></div> }
function Status({ status, zh }: { status: "documented" | "enriched" | "user_confirmed"; zh: boolean }) { const enriched = status !== "documented"; return <span className={`ml-auto flex items-center gap-1 rounded-full px-2 py-1 text-xs ${enriched ? "bg-emerald-50 text-emerald-700" : "bg-zinc-100 text-zinc-600"}`}>{enriched && <CheckCircle2 className="h-3 w-3" />}{status === "enriched" ? (zh ? "已补充" : "Enriched") : status === "user_confirmed" ? (zh ? "用户新增" : "User added") : (zh ? "原始档案" : "Documented")}</span> }
function Field({ label, value, onChange }: { label: string; value: string; onChange: (value: string) => void }) { return <label className="block text-sm"><span className="mb-1 block font-medium">{label}</span><textarea className="min-h-20 w-full rounded-lg border border-zinc-300 p-2" value={value} onChange={(event) => onChange(event.target.value)} /></label> }
function Item({ label, value, missing = false, wide = false, zh }: { label: string; value: string; missing?: boolean; wide?: boolean; zh: boolean }) { return <div className={wide ? "md:col-span-2" : ""}><dt className="flex items-center gap-1 font-medium text-zinc-600">{missing && <CircleDashed className="h-3.5 w-3.5 text-zinc-400" />}{label}</dt><dd className={`mt-1 whitespace-pre-line ${missing ? "italic text-zinc-400" : "text-zinc-700"}`}>{value || (zh ? "档案未记录" : "Not documented")}</dd></div> }
