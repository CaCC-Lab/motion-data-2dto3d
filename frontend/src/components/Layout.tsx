import React from 'react'

interface Props {
  left: React.ReactNode
  right: React.ReactNode
}

export default function Layout({ left, right }: Props) {
  return (
    <div style={styles.container}>
      <div style={styles.left}>{left}</div>
      <div style={styles.right}>{right}</div>
    </div>
  )
}

const styles: Record<string, React.CSSProperties> = {
  container: {
    display: 'flex',
    height: 'calc(100vh - 57px)',
    overflow: 'hidden',
  },
  left: {
    width: '380px',
    minWidth: '380px',
    padding: '16px',
    overflowY: 'auto',
    borderRight: '1px solid #2a2a35',
  },
  right: {
    flex: 1,
    position: 'relative',
    overflow: 'hidden',
  },
}
