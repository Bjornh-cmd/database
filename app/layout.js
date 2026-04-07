export const metadata = {
  title: 'Item Storage',
  description: 'Simple personal storage with optional password protection',
}

export default function RootLayout({ children }) {
  return (
    <html lang="en">
      <body style={{ margin: 0, padding: 0 }}>{children}</body>
    </html>
  )
}
