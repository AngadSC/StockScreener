import * as React from "react"

import { cn } from "@/lib/utils"

const Input = React.forwardRef<HTMLInputElement, React.ComponentProps<"input">>(
  ({ className, type, ...props }, ref) => {
    return (
      <input
        type={type}
        className={cn(
          "flex h-11 w-full rounded-[var(--radius-md)] border border-[var(--line)] bg-[var(--surface)] px-3.5 py-2.5 text-[13px] text-foreground shadow-[var(--shadow-1)] file:border-0 file:bg-transparent file:text-sm file:font-medium file:text-foreground placeholder:text-[var(--whisper)] hover:border-[var(--line-2)] focus-visible:border-primary focus-visible:outline-none focus-visible:ring-0 focus-visible:shadow-[0_0_0_3px_var(--accent-subtle),var(--shadow-1)] disabled:cursor-not-allowed disabled:opacity-50",
          className
        )}
        ref={ref}
        {...props}
      />
    )
  }
)
Input.displayName = "Input"

export { Input }
