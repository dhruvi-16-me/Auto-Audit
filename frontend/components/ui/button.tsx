"use client";

import * as React from "react";
import { Slot } from "@radix-ui/react-slot";
import { cva, type VariantProps } from "class-variance-authority";
import { cn } from "@/lib/utils";

const buttonVariants = cva(
  "inline-flex items-center justify-center gap-2 whitespace-nowrap rounded-lg text-sm font-medium transition-all focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-blue-500 disabled:pointer-events-none disabled:opacity-40 cursor-pointer",
  {
    variants: {
      variant: {
        default:
          "bg-blue-600 text-white hover:bg-blue-500 shadow-lg shadow-blue-900/30",
        destructive:
          "bg-red-600/20 text-red-400 border border-red-600/30 hover:bg-red-600/30",
        outline:
          "border border-[#1e2d4a] bg-[#0f1629] text-[#8b9cc4] hover:bg-[#151d35] hover:text-[#e8edf8]",
        ghost:
          "text-[#8b9cc4] hover:bg-[#151d35] hover:text-[#e8edf8]",
        success:
          "bg-emerald-600/20 text-emerald-400 border border-emerald-600/30 hover:bg-emerald-600/30",
        warning:
          "bg-amber-600/20 text-amber-400 border border-amber-600/30 hover:bg-amber-600/30",
      },
      size: {
        default: "h-9 px-4 py-2",
        sm: "h-7 px-3 text-xs",
        lg: "h-11 px-6",
        icon: "h-9 w-9",
      },
    },
    defaultVariants: {
      variant: "default",
      size: "default",
    },
  }
);

export interface ButtonProps
  extends React.ButtonHTMLAttributes<HTMLButtonElement>,
    VariantProps<typeof buttonVariants> {
  asChild?: boolean;
}

const Button = React.forwardRef<HTMLButtonElement, ButtonProps>(
  ({ className, variant, size, asChild = false, ...props }, ref) => {
    const Comp = asChild ? Slot : "button";
    return (
      <Comp
        className={cn(buttonVariants({ variant, size, className }))}
        ref={ref}
        {...props}
      />
    );
  }
);
Button.displayName = "Button";

export { Button, buttonVariants };
