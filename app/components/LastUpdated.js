'use client'

import { useEffect, useState } from 'react'

export default function LastUpdated() {
  const [lastUpdated, setLastUpdated] = useState(null)
  const [error, setError] = useState(null)

  useEffect(() => {
    async function fetchLastCommit() {
      try {
        const response = await fetch(
          'https://api.github.com/repos/Bjornh-cmd/database/commits/master'
        )
        if (!response.ok) throw new Error('Failed to fetch')
        const data = await response.json()
        const date = new Date(data.commit.committer.date)
        setLastUpdated(date.toLocaleDateString('nl-NL', {
          day: 'numeric',
          month: 'long',
          year: 'numeric',
          hour: '2-digit',
          minute: '2-digit'
        }))
      } catch (err) {
        setError('Kon laatste update niet ophalen')
      }
    }

    fetchLastCommit()
  }, [])

  if (error) {
    return (
      <footer style={footerStyle}>
        <small style={{ color: '#666' }}>{error}</small>
      </footer>
    )
  }

  if (!lastUpdated) {
    return (
      <footer style={footerStyle}>
        <small style={{ color: '#666' }}>Laden...</small>
      </footer>
    )
  }

  return (
    <footer style={footerStyle}>
      <small style={{ color: '#666' }}>
        Laatst bijgewerkt: {lastUpdated}
      </small>
    </footer>
  )
}

const footerStyle = {
  padding: '20px',
  textAlign: 'center',
  borderTop: '1px solid #eee',
  marginTop: 'auto'
}
