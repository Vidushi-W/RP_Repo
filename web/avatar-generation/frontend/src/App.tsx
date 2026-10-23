import { BrowserRouter, Routes, Route, Link } from 'react-router-dom';
import { lazy, Suspense } from 'react';
import { PreferencesProvider } from './hooks/usePreferences';
import { AppLayout } from './components/layout/AppLayout';
const Dashboard = lazy(() => import('./pages/Dashboard'));
const VideoTranslation = lazy(() => import('./pages/VideoTranslation'));
const VocabularyLibrary = lazy(() => import('./pages/VocabularyLibrary'));
const Settings = lazy(() => import('./pages/Settings'));
const LiveTranslation = lazy(() => import('./pages/VideoTranslation/LiveTranslation'));
export default function App() { return <PreferencesProvider><BrowserRouter><Suspense fallback={<p role="status" className="loading">Opening LankaSigns…</p>}><Routes><Route path="translation" element={<LiveTranslation/>}/><Route element={<AppLayout/>}><Route index element={<Dashboard/>}/><Route path="research" element={<VideoTranslation/>}/><Route path="vocabulary" element={<VocabularyLibrary/>}/><Route path="settings" element={<Settings/>}/><Route path="*" element={<div className="panel"><h1>Page not found</h1><Link to="/">Return to Home</Link></div>}/></Route></Routes></Suspense></BrowserRouter></PreferencesProvider>; }
