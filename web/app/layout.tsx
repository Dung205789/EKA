import './globals.css'
import type { Metadata } from 'next'

export const metadata: Metadata = {
  title: 'EKA Brain',
  description: 'Local-first AI Knowledge Brain'
}

export default function RootLayout({ children }: { children: React.ReactNode }) {
  return (
    <html lang="en">
      <body className="h-full bg-neutral-50 text-neutral-900">
        {children}
      </body>
    </html>
  )
}
