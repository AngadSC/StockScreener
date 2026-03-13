import * as React from "react"
import { cva, type VariantProps } from "class-variance-authority"

import { cn } from "@/lib/utils"

const badgeVariants = cva(
  "inline-flex items-center border px-2.5 py-1 text-[11px] uppercase tracking-[0.2em] transition-colors focus:outline-none focus:ring-2 focus:ring-ring focus:ring-offset-2",
  {
    variants: {
      variant: {
        default:
          "border-primary/25 bg-primary/10 text-primary shadow-[0_0_18px_rgba(212,175,55,0.08)] hover:bg-primary/20",
        secondary:
          "border-secondary/35 bg-secondary/20 text-secondary-foreground hover:bg-secondary/35",
        destructive:
          "border-destructive/35 bg-destructive/10 text-destructive-foreground shadow hover:bg-destructive/20",
        outline: "border-primary/30 text-foreground",
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
