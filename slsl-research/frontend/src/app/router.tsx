import { createBrowserRouter, Navigate } from 'react-router-dom'
import { AppShell } from '@/components/layout/AppShell'
import { StudioPage } from '@/features/studio/StudioPage'
export const router = createBrowserRouter([{ path: '/', element: <AppShell />, children: [
  { index: true, element: <StudioPage page="overview" /> },
  { path: 'datasets', element: <StudioPage page="data" /> },
  { path: 'training', element: <StudioPage page="train" /> },
  { path: 'test', element: <StudioPage page="test" /> },
  { path: 'dictionary', element: <StudioPage page="dictionary" /> },
  { path: 'evaluation', element: <Navigate to="/test" replace /> },
  { path: 'playground', element: <Navigate to="/test" replace /> },
  { path: '*', element: <Navigate to="/" replace /> },
]}])
