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
    height: 'calc(100vh - var(--header-height))',
    overflow: 'hidden',
  },
  left: {
    width: 'var(--sidebar-width)',
    minWidth: 'var(--sidebar-width)',
    padding: 'var(--space-lg)',
    overflowY: 'auto',
    borderRight: '1px solid var(--border-default)',
    background: 'var(--bg-surface)',
    display: 'flex',
    flexDirection: 'column',
    gap: 'var(--space-lg)',
  },
  right: {
    flex: 1,
    position: 'relative',
    overflow: 'hidden',
    background: 'var(--bg-root)',
  },
}
