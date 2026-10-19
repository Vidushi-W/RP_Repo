import { createBrowserRouter } from 'react-router-dom'
import { AppShell } from '@/components/layout/AppShell'
import { DatasetsPage } from '@/features/datasets/DatasetsPage'
import { EvaluationPage } from '@/features/evaluation/EvaluationPage'
import { OverviewPage } from '@/features/overview/OverviewPage'
import { PlaygroundPage } from '@/features/playground/PlaygroundPage'
import { TrainingPage } from '@/features/training/TrainingPage'

export const router = createBrowserRouter([
  {
    path: '/',
    element: <AppShell />,
    children: [
      { index: true, element: <OverviewPage /> },
      { path: 'datasets', element: <DatasetsPage /> },
      { path: 'training', element: <TrainingPage /> },
      { path: 'evaluation', element: <EvaluationPage /> },
      { path: 'playground', element: <PlaygroundPage /> },
    ],
  },
])
