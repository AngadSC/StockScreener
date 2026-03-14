import * as React from "react"
import { Slot } from "@radix-ui/react-slot"
import { cva, type VariantProps } from "class-variance-authority"

import { cn } from "@/lib/utils"

const buttonVariants = cva(
  "inline-flex items-center justify-center gap-2 whitespace-nowrap rounded-md border border-transparent px-5 py-2.5 text-sm font-semibold leading-[1.4] text-foreground shadow-sm focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring/40 focus-visible:ring-offset-0 disabled:pointer-events-none disabled:opacity-50 active:scale-[0.97] [&_svg]:pointer-events-none [&_svg]:size-4 [&_svg]:shrink-0 transition-[background,border-color,box-shadow,color,transform] duration-[180ms]",
  {
    variants: {
      variant: {
        default:
          "bg-primary text-white hover:bg-[var(--accent-hover)] hover:shadow-[var(--glow-accent)]",
        destructive:
          "border border-negative bg-transparent text-negative hover:border-negative hover:bg-[var(--negative-bg)] hover:text-negative",
        outline:
          "border border-[var(--border-strong)] bg-transparent text-foreground hover:border-primary hover:bg-[var(--accent-subtle)] hover:text-primary",
        secondary:
          "border border-[var(--border-strong)] bg-transparent text-foreground hover:border-primary hover:bg-[var(--accent-subtle)] hover:text-primary",
        ghost: "border border-transparent bg-transparent text-foreground hover:border-primary hover:bg-[var(--accent-subtle)] hover:text-primary",
        link: "text-primary underline-offset-4 hover:underline",
      },
      size: {
        default: "h-11",
        sm: "h-9 px-3 text-xs",
        lg: "h-12 px-6 text-sm",
        icon: "h-11 w-11 px-0",
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
