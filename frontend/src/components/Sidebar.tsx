import { Plus } from "lucide-react"

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
  "w-full rounded-lg border border-zinc-300 bg-white px-3 py-2 text-sm disabled:opacity-50"

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
    <aside className="flex w-64 flex-col border-r border-zinc-200 bg-[#f0eee8] p-3">
      <Button
        variant="ghost"
        className="justify-start gap-2 rounded-lg"
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
