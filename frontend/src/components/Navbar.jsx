import { useEffect, useState } from 'react'
import { api } from '../services/api'

export default function Navbar() {

  const [online, setOnline] =
    useState(false)

  useEffect(() => {

    let mounted = true

    const check = async () => {

      try {

        await api.health()

        if (mounted)
          setOnline(true)

      } catch {

        if (mounted)
          setOnline(false)
      }
    }

    check()

    const timer =
      setInterval(check, 5000)

    return () =>
      clearInterval(timer)

  }, [])

  return (

    <header className="navbar">

      <div>

        <div className="brand-logo">
          CODE_STORM
        </div>

        <div className="brand-tag">
          Agent Permission Governor
        </div>

      </div>

      <div className="nav-badges">

        <div className="model-pill">
          Environment:
          <span> LOCAL</span>
        </div>

        <div className="model-pill">
          Agent:
          <span> demo-data-analyst</span>
        </div>

        <div className="status-badge">

          <span
            className={
              `status-dot ${
                online
                  ? 'online'
                  : 'offline'
              }`
            }
          />

          {online
            ? 'Governor Online'
            : 'Backend Offline'}

        </div>

      </div>

    </header>
  )
}