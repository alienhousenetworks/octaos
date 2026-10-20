import * as React from "react"
import { cva, type VariantProps } from "class-variance-authority"
import { cn } from "@/lib/utils"

const badgeVariants = cva(
  "inline-flex items-center rounded-md border px-2 py-0.5 text-xs font-medium transition-colors focus:outline-none focus:ring-2 focus:ring-ring focus:ring-offset-2",
  {
    variants: {
      variant: {
        default:
          "border-transparent bg-primary/10 text-primary border-primary/20",
        secondary:
          "border-border bg-muted/60 text-muted-foreground",
        destructive:
          "border-[#D9828B]/20 bg-[#462F35] text-[#D9828B]",
        success:
          "border-[#64B99A]/20 bg-[#263D38] text-[#64B99A]",
        warning:
          "border-[#D9AD68]/20 bg-[#443A2D] text-[#D9AD68]",
        info:
          "border-[#75AFCB]/20 bg-[#2B3945] text-[#75AFCB]",
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
