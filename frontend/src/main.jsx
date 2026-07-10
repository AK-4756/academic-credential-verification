// frontend/src/main.jsx
// ReactDOM entry point — minimal mount
// Architecture Reference: docs/frontend.md (Phase 7.1: Project Foundation)

import { StrictMode } from 'react'
import { createRoot } from 'react-dom/client'
import './index.css'
import App from './App.jsx'

createRoot(document.getElementById('root')).render(
  <StrictMode>
    <App />
  </StrictMode>,
)
