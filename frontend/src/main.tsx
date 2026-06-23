import React from 'react'
import ReactDOM from 'react-dom/client'
import App from './App.tsx'
import './index.css'
import { Toaster } from 'sonner'

// Inject Google Fonts
const link = document.createElement('link');
link.href = 'https://fonts.googleapis.com/css2?family=Outfit:wght@300;400;500;600;700&display=swap';
link.rel = 'stylesheet';
document.head.appendChild(link);

ReactDOM.createRoot(document.getElementById('root')!).render(
  <React.StrictMode>
    <App />
    <Toaster position="top-right" theme="dark" richColors />
  </React.StrictMode>,
)
