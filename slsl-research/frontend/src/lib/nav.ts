import { BookOpen, Brain, Database, LayoutDashboard, MessageSquare, type LucideIcon } from 'lucide-react'
export interface NavItem { to: string; label: string; icon: LucideIcon; description?: string }
export const mainNav: NavItem[] = [
  { to: '/', label: 'Overview', icon: LayoutDashboard, description: 'Your model at a glance' },
  { to: '/datasets', label: 'Data', icon: Database, description: 'Training and test recordings' },
  { to: '/training', label: 'Train', icon: Brain, description: 'Keep your model learning' },
  { to: '/test', label: 'Test', icon: MessageSquare, description: 'Recognize motion and check results' },
  { to: '/dictionary', label: 'Dictionary', icon: BookOpen, description: 'Explore your vocabulary' },
]
