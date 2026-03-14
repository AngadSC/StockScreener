import * as React from "react"
import { cva, type VariantProps } from "class-variance-authority"

import { cn } from "@/lib/utils"

const badgeVariants = cva(
  "inline-flex items-center rounded-full border px-2.5 py-1 text-xs font-medium transition-[background,border-color,box-shadow,color,transform] duration-[180ms] focus:outline-none focus:ring-2 focus:ring-ring/40",
  {
    variants: {
      variant: {
        default:
          "border-primary/25 bg-[var(--accent-subtle)] text-primary hover:bg-[var(--accent-subtle-hover)]",
        secondary:
          "border-border bg-muted/30 text-foreground hover:bg-muted/50",
        destructive:
          "border-negative/35 bg-[var(--negative-bg)] text-negative hover:bg-[var(--negative-bg)]",
        outline: "border-border text-foreground",
      },
    },
    defaultVariants: {
      variant: "default",
    },
  }
)

export interface BadgeProps
  extends React.HTMLAttributes<HTMLDivElement>,
    VariantProps<typeof badgeVariants> {}

function Badge({ className, variant, ...props }: BadgeProps) {
  return (
    <div className={cn(badgeVariants({ variant }), className)} {...props} />
  )
}

export { Badge, badgeVariants }
