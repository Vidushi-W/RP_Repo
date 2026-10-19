import * as React from 'react'
import { cva, type VariantProps } from 'class-variance-authority'
import { cn } from '@/lib/utils'

const badgeVariants = cva('inline-flex items-center rounded-full border px-2.5 py-0.5 text-xs font-medium', {
  variants: {
    variant: {
      default: 'border-transparent bg-indigo-50 text-indigo-700',
      secondary: 'border-[var(--color-border)] bg-white text-[var(--color-muted)]',
      success: 'border-transparent bg-emerald-50 text-emerald-700',
      warning: 'border-transparent bg-amber-50 text-amber-800',
    },
  },
  defaultVariants: { variant: 'default' },
})

export function Badge({ className, variant, ...props }: React.HTMLAttributes<HTMLDivElement> & VariantProps<typeof badgeVariants>) {
  return <div className={cn(badgeVariants({ variant }), className)} {...props} />
}
