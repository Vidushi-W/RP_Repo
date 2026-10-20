import { cn } from '@/lib/utils'

export function PageContainer({ className, ...props }: React.HTMLAttributes<HTMLDivElement>) {
  return <div className={cn('mx-auto w-full max-w-7xl', className)} {...props} />
}
