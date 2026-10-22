import { cva, type VariantProps } from 'class-variance-authority'
import { cn } from '@/lib/utils'

const alertVariants = cva('rounded-lg border px-4 py-3 text-sm', {
  variants: {
    variant: {
      default: 'border-border bg-surface text-foreground',
      info: 'border-accent/20 bg-accent-soft text-foreground',
      success: 'border-emerald-200 bg-success-soft text-success',
      warning: 'border-amber-200 bg-warning-soft text-warning',
      danger: 'border-rose-200 bg-danger-soft text-danger',
    },
  },
  defaultVariants: { variant: 'default' },
})

export function Alert({
  className,
  variant,
  ...props
}: React.HTMLAttributes<HTMLDivElement> & VariantProps<typeof alertVariants>) {
  return <div role="alert" className={cn(alertVariants({ variant }), className)} {...props} />
}
