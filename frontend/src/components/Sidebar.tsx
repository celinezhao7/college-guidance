import { Plus } from "lucide-react"

import { Button } from "@/components/ui/button"

export function Sidebar() {
  return (
    <aside className="flex w-64 flex-col border-r border-zinc-200 bg-[#f0eee8] p-3">
      <Button
        variant="ghost"
        className="justify-start gap-2 rounded-lg"
      >
        <Plus className="h-4 w-4" />
        New chat
      </Button>

      <div className="mt-6">
        <p className="mb-2 px-3 text-xs font-medium text-zinc-500">
          Recent
        </p>

        <div className="space-y-1">
          <button className="w-full truncate rounded-lg px-3 py-2 text-left text-sm hover:bg-black/5">
            College recommendations
          </button>

          <button className="w-full truncate rounded-lg px-3 py-2 text-left text-sm hover:bg-black/5">
            Major guidance
          </button>
        </div>
      </div>
    </aside>
  )
}