import { StrictMode } from 'react'
import { createRoot } from 'react-dom/client'
import './index.css'
import App from './App.tsx'
import ReportPage from './components/ReportPage.tsx'

const REPORT_ID = new URLSearchParams(window.location.search).get('report') // ?report=<result_id>

createRoot(document.getElementById('root')!).render(
  <StrictMode>
    {REPORT_ID ? <ReportPage id={REPORT_ID} /> : <App />}
  </StrictMode>,
)
