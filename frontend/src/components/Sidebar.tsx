import { GraduationCap, Plus } from "lucide-react"

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
  "w-full rounded-lg border border-[#dddce7] bg-white/75 px-3 py-2 text-sm shadow-[0_2px_10px_rgba(84,78,112,0.035)] outline-none transition focus:border-[#aaa6ca] focus:ring-2 focus:ring-[#b8b4d8]/20 disabled:opacity-50"

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
        <span className="font-heading text-lg font-semibold tracking-tight text-[#3f3d58]">
          CollegeGuide
        </span>
      </div>
      <Button
        variant="ghost"
        className="justify-start gap-2 rounded-lg text-[#45445a] hover:bg-white/55 hover:text-[#343247]"
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
                {profile.display_name}
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

        <label className="block space-y-2">
          <span className="text-xs font-medium text-zinc-500">{zh ? "语言" : "Language"}</span>
          <select
            className={selectClassName}
            value={language}
            disabled={disabled}
            onChange={(event) =>
              onLanguageChange(event.target.value as "en" | "zh")
            }
          >
            <option value="en">English</option>
            <option value="zh">简体中文</option>
          </select>
        </label>
      </div>
    </aside>
  )
}
