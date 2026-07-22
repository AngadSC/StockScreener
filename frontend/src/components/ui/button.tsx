import * as React from "react"
import { Slot } from "@radix-ui/react-slot"
import { cva, type VariantProps } from "class-variance-authority"

import { cn } from "@/lib/utils"

const buttonVariants = cva(
  "inline-flex items-center justify-center gap-2 whitespace-nowrap rounded-full border border-transparent px-5 py-2.5 text-[13px] font-medium leading-none text-foreground shadow-sm focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring/40 focus-visible:ring-offset-0 disabled:pointer-events-none disabled:opacity-50 active:scale-[0.98] [&_svg]:pointer-events-none [&_svg]:size-4 [&_svg]:shrink-0 transition-[background,border-color,box-shadow,color,transform] duration-[240ms]",
  {
    variants: {
      variant: {
        default:
          "bg-[var(--ink)] text-[var(--ivory)] hover:bg-[var(--forest)] hover:shadow-[0_4px_14px_-4px_rgba(49,169,196,0.42)] hover:-translate-y-px",
        destructive:
          "border border-negative bg-transparent text-negative hover:border-negative hover:bg-[var(--negative-bg)] hover:text-negative",
        outline:
          "border border-[var(--line-2)] bg-transparent text-foreground hover:border-[var(--ink-2)] hover:bg-[var(--surface)] hover:text-foreground",
        secondary:
          "border border-[var(--line)] bg-[var(--surface)] text-foreground hover:border-[var(--line-2)] hover:bg-[var(--surface-2)]",
        ghost: "border border-transparent bg-transparent text-foreground hover:border-[var(--line-2)] hover:bg-[rgba(221,228,225,0.04)] hover:text-foreground",
        link: "text-primary underline-offset-4 hover:underline",
      },
      size: {
        default: "h-10",
        sm: "h-8 px-3 text-xs",
        lg: "h-12 px-6 text-sm",
        icon: "h-10 w-10 px-0",
      },
    },
    defaultVariants: {
      variant: "default",
      size: "default",
    },
  }
)

export interface ButtonProps
  extends React.ButtonHTMLAttributes<HTMLButtonElement>,
    VariantProps<typeof buttonVariants> {
  asChild?: boolean
}

const Button = React.forwardRef<HTMLButtonElement, ButtonProps>(
  ({ className, variant, size, asChild = false, ...props }, ref) => {
    const Comp = asChild ? Slot : "button"
    return (
      <Comp
        className={cn(buttonVariants({ variant, size, className }))}
        ref={ref}
        {...props}
      />
    )
  }
)
Button.displayName = "Button"

export { Button, buttonVariants }
