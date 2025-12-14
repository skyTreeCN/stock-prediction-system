import type { Metadata } from 'next'
import './globals.css'

export const metadata: Metadata = {
  title: '股票预测系统',
  description: '基于Claude AI的股票上涨概率预测系统',
}

export default function RootLayout({
  children,
}: {
  children: React.ReactNode
}) {
  return (
    <html lang="zh-CN">
      <body>{children}</body>
    </html>
  )
}
