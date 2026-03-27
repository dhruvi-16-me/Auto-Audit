import * as React from "react";
import { cva, type VariantProps } from "class-variance-authority";
import { cn } from "@/lib/utils";

const badgeVariants = cva(
  "inline-flex items-center gap-1 rounded-full px-2.5 py-0.5 text-xs font-semibold tracking-wide transition-colors",
  {
    variants: {
      variant: {
        default: "bg-blue-600/20 text-blue-400 border border-blue-600/30",
        critical: "bg-red-600/20 text-red-400 border border-red-600/30",
        high: "bg-orange-600/20 text-orange-400 border border-orange-600/30",
        medium: "bg-amber-600/20 text-amber-400 border border-amber-600/30",
        low: "bg-yellow-600/20 text-yellow-400 border border-yellow-600/30",
        success: "bg-emerald-600/20 text-emerald-400 border border-emerald-600/30",
        neutral: "bg-[#1a2340] text-[#8b9cc4] border border-[#1e2d4a]",
        purple: "bg-purple-600/20 text-purple-400 border border-purple-600/30",
      },
    },
    defaultVariants: {
      variant: "default",
    },
  }
);

export interface BadgeProps
  extends React.HTMLAttributes<HTMLDivElement>,
    VariantProps<typeof badgeVariants> {}

function Badge({ className, variant, ...props }: BadgeProps) {
  return (
    <div className={cn(badgeVariants({ variant }), className)} {...props} />
  );
}

export { Badge, badgeVariants };
