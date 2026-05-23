import React from 'react'
import ReactDOM from 'react-dom/client'
import { BrowserRouter } from 'react-router-dom'
import { AuthCtx, useAuthProvider } from './hooks/useAuth'
import App from './App'
import './index.css'

function Root() {
  const auth = useAuthProvider()
  return (
    <AuthCtx.Provider value={auth}>
      <App />
    </AuthCtx.Provider>
  )
}

ReactDOM.createRoot(document.getElementById('root')!).render(
  <React.StrictMode>
    <BrowserRouter>
      <Root />
    </BrowserRouter>
  </React.StrictMode>
)
