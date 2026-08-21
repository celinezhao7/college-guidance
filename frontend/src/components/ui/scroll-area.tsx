import { ScrollArea as ScrollAreaPrimitive } from "@base-ui/react/scroll-area"
import type { Ref } from "react"

import { cn } from "@/lib/utils"

function ScrollArea({
  className,
  children,
  viewportRef,
  ...props
}: ScrollAreaPrimitive.Root.Props & { viewportRef?: Ref<HTMLDivElement> }) {
  return (
    <ScrollAreaPrimitive.Root
      data-slot="scroll-area"
      className={cn("relative", className)}
      {...props}
    >
      <ScrollAreaPrimitive.Viewport
        ref={viewportRef}
        data-slot="scroll-area-viewport"
        className="size-full rounded-[inherit] transition-[color,box-shadow] outline-none focus-visible:ring-[3px] focus-visible:ring-ring/50 focus-visible:outline-1"
      >
        {children}
      </ScrollAreaPrimitive.Viewport>
      <ScrollBar />
      <ScrollAreaPrimitive.Corner />
    </ScrollAreaPrimitive.Root>
  )
}

function ScrollBar({
  className,
  orientation = "vertical",
  keepMounted = true,
  ...props
}: ScrollAreaPrimitive.Scrollbar.Props) {
  return (
    <ScrollAreaPrimitive.Scrollbar
      data-slot="scroll-area-scrollbar"
      data-orientation={orientation}
      orientation={orientation}
      keepMounted={keepMounted}
      className={cn(
        "z-20 flex touch-none bg-white p-0.5 transition-colors select-none data-horizontal:h-2 data-horizontal:flex-col data-vertical:absolute data-vertical:inset-y-0 data-vertical:right-0 data-vertical:h-full data-vertical:w-2.5",
        className
      )}
      {...props}
    >
      <ScrollAreaPrimitive.Thumb
        data-slot="scroll-area-thumb"
        className="relative flex-1 rounded-full bg-zinc-300 transition-colors hover:bg-zinc-400 active:bg-zinc-500"
      />
    </ScrollAreaPrimitive.Scrollbar>
  )
}

export { ScrollArea, ScrollBar }
