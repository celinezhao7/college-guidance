import { MessageSquareText, Plus, UserRoundPen, X } from "lucide-react"

import { Button } from "@/components/ui/button"
import type { Profile, RecommendationMode } from "@/lib/api"

type SidebarProps = {
  profiles: Profile[]
  modes: RecommendationMode[]
  profileId: string
  modeId: string
  language: "en" | "zh"
  disabled: boolean
  mobileOpen: boolean
  desktopOpen: boolean
  modeHistoryIds: string[]
  historyItems: Array<{ id: string; modeId: string; title: string; preview: string }>
  onProfileChange: (value: string) => void
  onManageProfile: () => void
  onModeChange: (value: string) => void
  onLanguageChange: (value: "en" | "zh") => void
  onNewChat: () => void
  onHistoryOpen: (id: string) => void
  onMobileClose: () => void
  onClose: () => void
}

const selectClassName =
  "h-10 w-full rounded-lg border border-[#dddce7] bg-white/75 px-3 py-2 text-sm shadow-[0_2px_10px_rgba(84,78,112,0.035)] outline-none transition focus:border-[#aaa6ca] focus:ring-2 focus:ring-[#b8b4d8]/20 disabled:opacity-50"
const headerControlClassName =
  "flex h-11 w-11 shrink-0 items-center justify-center rounded-full border border-[#d5d2e2] bg-white/55 text-xs font-medium text-[#625e70] transition hover:border-[#aaa6ca] hover:bg-white/75 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-[#b8b4d8]/35 disabled:opacity-50"

export function Sidebar({
  profiles,
  modes,
  profileId,
  modeId,
  language,
  disabled,
  mobileOpen,
  desktopOpen,
  modeHistoryIds,
  historyItems,
  onProfileChange,
  onManageProfile,
  onModeChange,
  onLanguageChange,
  onNewChat,
  onHistoryOpen,
  onMobileClose,
  onClose,
}: SidebarProps) {
  const zh = language === "zh"
  return (
    <aside
      className={`dream-sidebar fixed left-0 top-0 z-40 flex h-[100dvh] w-72 max-w-[calc(100vw-1rem)] flex-col border-r border-[#e3e1ea] px-3 transition-[transform,visibility] duration-200 md:relative md:z-auto md:h-[100dvh] md:max-w-none ${mobileOpen ? "visible translate-x-0" : "invisible pointer-events-none -translate-x-full"} ${desktopOpen ? "md:visible md:flex md:pointer-events-auto md:translate-x-0" : "md:hidden"}`}
      style={{
        paddingTop: "max(0.75rem, env(safe-area-inset-top))",
        paddingBottom: "max(0.75rem, env(safe-area-inset-bottom))",
      }}
    >
      <div className="flex min-w-0 items-center gap-2.5 px-2 pb-5 pt-2">
        <span className="dream-brand-title min-w-0 truncate font-heading text-xl font-semibold tracking-tight">
          CollegeGuide
        </span>
        <div className="ml-auto flex shrink-0 items-center gap-1.5">
          <button
            type="button"
            className={headerControlClassName}
            disabled={disabled}
            onClick={() => onLanguageChange(zh ? "en" : "zh")}
            aria-label={zh ? "Switch to English" : "切换到中文"}
            title={zh ? "Switch to English" : "切换到中文"}
          >
            {zh ? "EN" : "中"}
          </button>
          <button
            type="button"
            className={headerControlClassName}
            onClick={onClose}
            aria-label={zh ? "关闭菜单" : "Close menu"}
          >
            <X className="h-4 w-4" />
          </button>
        </div>
      </div>
      <Button
        variant="ghost"
        className="mx-1 h-11 justify-start gap-2 rounded-lg text-[#45445a] hover:bg-white/55 hover:text-[#343247]"
        onClick={() => {
          onNewChat()
          onMobileClose()
        }}
      >
        <Plus className="h-4 w-4" />
        {zh ? "新对话" : "New chat"}
      </Button>

      <div className="mt-5 space-y-5 px-1">
        <div className="space-y-1">
          <label className="block space-y-2">
            <span className="text-xs font-medium text-zinc-500">{zh ? "学生档案" : "Student profile"}</span>
            <select
              className={selectClassName}
              value={profileId}
              disabled={disabled}
              onChange={(event) => {
                onProfileChange(event.target.value)
                onMobileClose()
              }}
            >
              {profiles.map((profile) => (
                <option key={profile.id} value={profile.id}>
                  {zh ? profile.display_name_zh : profile.display_name_en}
                </option>
              ))}
            </select>
          </label>
          <button
            type="button"
            className="flex min-h-11 w-full items-center gap-2 rounded-lg px-2 py-2 text-left text-xs text-[#67627b] transition hover:bg-white/55"
            disabled={disabled || !profileId}
            onClick={() => {
              onManageProfile()
              onMobileClose()
            }}
          >
            <UserRoundPen className="h-3.5 w-3.5" />
            {zh ? "管理补充画像信息" : "Manage profile information"}
          </button>
        </div>

        <label className="block space-y-2">
          <span className="text-xs font-medium text-zinc-500">{zh ? "推荐类型" : "Recommendation"}</span>
          <select
            className={selectClassName}
            value={modeId}
            disabled={disabled}
            onChange={(event) => {
              onModeChange(event.target.value)
              onMobileClose()
            }}
          >
            <option value="" disabled>
              {zh ? "请选择推荐类型" : "Select a recommendation type"}
            </option>
            {modes.map((mode) => (
              <option key={mode.id} value={mode.id}>
                {language === "zh" ? mode.title_zh : mode.title_en}{modeHistoryIds.includes(mode.id) ? "  •" : ""}
              </option>
            ))}
          </select>
        </label>

      </div>

      {historyItems.length > 0 && (
        <section className="mt-4 min-h-0 px-1">
          <h2 className="mb-2 px-2 text-xs font-medium text-zinc-500">
            {zh ? "最近对话" : "Recent chats"}
          </h2>
          <div className="max-h-48 space-y-1 overflow-y-auto pr-1">
            {historyItems.map((item) => (
              <button
                key={item.id}
                type="button"
                disabled={disabled}
                onClick={() => {
                  onHistoryOpen(item.id)
                  onMobileClose()
                }}
                className={`group flex w-full items-start gap-2 rounded-lg px-2.5 py-2 text-left transition disabled:opacity-50 ${modeId === item.modeId ? "bg-white/65 text-[#44415d]" : "text-[#666278] hover:bg-white/45"}`}
              >
                <MessageSquareText className="mt-0.5 h-3.5 w-3.5 shrink-0 text-[#85809e]" />
                <span className="min-w-0">
                  <span className="block truncate text-xs font-medium">{item.title}</span>
                  <span className="mt-0.5 block truncate text-[11px] text-[#898695]">{item.preview}</span>
                </span>
              </button>
            ))}
          </div>
        </section>
      )}

    </aside>
  )
}
