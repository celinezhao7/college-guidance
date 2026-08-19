import { GraduationCap, Plus, ShieldCheck } from "lucide-react"

import { Button } from "@/components/ui/button"
import type { Profile, RecommendationMode } from "@/lib/api"

type SidebarProps = {
  profiles: Profile[]
  modes: RecommendationMode[]
  profileId: string
  modeId: string
  language: "en" | "zh"
  disabled: boolean
  onProfileChange: (value: string) => void
  onModeChange: (value: string) => void
  onLanguageChange: (value: "en" | "zh") => void
  onNewChat: () => void
}

const selectClassName =
  "h-10 w-full rounded-lg border border-[#dddce7] bg-white/75 px-3 py-2 text-sm shadow-[0_2px_10px_rgba(84,78,112,0.035)] outline-none transition focus:border-[#aaa6ca] focus:ring-2 focus:ring-[#b8b4d8]/20 disabled:opacity-50"

export function Sidebar({
  profiles,
  modes,
  profileId,
  modeId,
  language,
  disabled,
  onProfileChange,
  onModeChange,
  onLanguageChange,
  onNewChat,
}: SidebarProps) {
  const zh = language === "zh"
  return (
    <aside className="dream-sidebar flex w-72 flex-col border-r border-[#e3e1ea] p-3">
      <div className="flex items-center gap-2.5 px-2 pb-5 pt-2">
        <div className="flex h-8 w-8 items-center justify-center rounded-xl bg-white/70 text-[#5f5b82] shadow-sm">
          <GraduationCap className="h-4.5 w-4.5" />
        </div>
        <span className="font-heading text-xl font-semibold tracking-tight text-[#3f3d58]">
          CollegeGuide
        </span>
        <button
          type="button"
          className="ml-auto flex h-8 min-w-8 items-center justify-center rounded-full border border-[#d5d2e2] bg-white/55 px-2 text-xs font-medium text-[#55516f] transition hover:border-[#aaa6ca] hover:bg-gradient-to-r hover:from-[#eef1fa] hover:to-[#faeee7] focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-[#b8b4d8]/35 disabled:opacity-50"
          disabled={disabled}
          onClick={() => onLanguageChange(zh ? "en" : "zh")}
          aria-label={zh ? "切换到英文" : "Switch to Chinese"}
          title={zh ? "切换到英文" : "Switch to Chinese"}
        >
          {zh ? "EN" : "中"}
        </button>
      </div>
      <Button
        variant="ghost"
        className="mx-1 h-10 justify-start gap-2 rounded-lg text-[#45445a] hover:bg-white/55 hover:text-[#343247]"
        onClick={onNewChat}
      >
        <Plus className="h-4 w-4" />
        {zh ? "新对话" : "New chat"}
      </Button>

      <div className="mt-6 space-y-5 px-1">
        <label className="block space-y-2">
          <span className="text-xs font-medium text-zinc-500">{zh ? "学生档案" : "Student profile"}</span>
          <select
            className={selectClassName}
            value={profileId}
            disabled={disabled}
            onChange={(event) => onProfileChange(event.target.value)}
          >
            {profiles.map((profile) => (
              <option key={profile.id} value={profile.id}>
                {zh ? profile.display_name_zh : profile.display_name_en}
              </option>
            ))}
          </select>
        </label>

        <label className="block space-y-2">
          <span className="text-xs font-medium text-zinc-500">{zh ? "推荐类型" : "Recommendation"}</span>
          <select
            className={selectClassName}
            value={modeId}
            disabled={disabled}
            onChange={(event) => onModeChange(event.target.value)}
          >
            <option value="" disabled>
              {zh ? "请选择推荐类型" : "Select a recommendation type"}
            </option>
            {modes.map((mode) => (
              <option key={mode.id} value={mode.id}>
                {language === "zh" ? mode.title_zh : mode.title_en}
              </option>
            ))}
          </select>
        </label>

      </div>

      <section className="relative mx-1 mb-1 mt-auto overflow-hidden rounded-xl border border-[#dedbe9] bg-gradient-to-br from-white/70 via-[#f4f1fa]/75 to-[#fbf1e9]/65 p-4 shadow-[0_8px_24px_rgba(83,75,111,0.05)]">
        <div className="absolute right-3 top-3 h-1.5 w-1.5 rounded-full bg-[#dda06f]/70" aria-hidden="true" />
        <div className="mb-2 flex items-center gap-2 text-[#494664]">
          <ShieldCheck className="h-4 w-4 text-[#6f6a92]" />
          <h2 className="text-xs font-semibold">
            {zh ? "推荐如何产生" : "How recommendations work"}
          </h2>
        </div>
        <p className="text-[11px] leading-5 text-[#706d7d]">
          {zh
            ? "结合学生经历、官方申请指导与 College Scorecard 数据。精确专业请前往大学官网核实。"
            : "Combines student experiences, official application guidance, and College Scorecard data. Verify exact programs on university websites."}
        </p>
      </section>
    </aside>
  )
}
