'use client'

import { useRef, useEffect } from 'react'

interface KLineData {
  date: string
  open: number
  high: number
  low: number
  close: number
  volume: number
}

interface Annotation {
  date: string
  price: number
  label: string
  type: 'high' | 'low' | 'volume' | 'breakout' | 'consolidation'
}

interface KLineChartProps {
  klineData: KLineData[]
  annotations: Annotation[]
  height?: number
}

export default function KLineChart({ klineData, annotations, height = 250 }: KLineChartProps) {
  const canvasRef = useRef<HTMLCanvasElement>(null)

  useEffect(() => {
    if (!canvasRef.current || !klineData || klineData.length === 0) return

    const canvas = canvasRef.current
    const ctx = canvas.getContext('2d')
    if (!ctx) return

    // 设置canvas尺寸
    const dpr = window.devicePixelRatio || 1
    const rect = canvas.getBoundingClientRect()
    canvas.width = rect.width * dpr
    canvas.height = rect.height * dpr
    ctx.scale(dpr, dpr)

    // 清空画布
    ctx.clearRect(0, 0, rect.width, rect.height)

    // 绘制区域配置
    const padding = { top: 40, right: 60, bottom: 60, left: 10 }
    const chartWidth = rect.width - padding.left - padding.right
    const priceChartHeight = (rect.height - padding.top - padding.bottom) * 0.7
    const volumeChartHeight = (rect.height - padding.top - padding.bottom) * 0.25
    const gap = (rect.height - padding.top - padding.bottom) * 0.05

    // 计算价格范围
    const prices = klineData.flatMap(d => [d.high, d.low])
    const maxPrice = Math.max(...prices)
    const minPrice = Math.min(...prices)
    const priceRange = maxPrice - minPrice
    const pricePadding = priceRange * 0.1

    // 计算成交量范围
    const volumes = klineData.map(d => d.volume)
    const maxVolume = Math.max(...volumes)

    // 计算每个K线的宽度
    const candleWidth = chartWidth / klineData.length
    const candleBodyWidth = Math.max(candleWidth * 0.6, 2)

    // 绘制函数：价格转Y坐标
    const priceToY = (price: number) => {
      return padding.top + priceChartHeight - ((price - minPrice + pricePadding) / (priceRange + 2 * pricePadding)) * priceChartHeight
    }

    // 绘制函数：成交量转Y坐标
    const volumeToY = (volume: number) => {
      const volumeTop = padding.top + priceChartHeight + gap
      return volumeTop + volumeChartHeight - (volume / maxVolume) * volumeChartHeight
    }

    // 绘制网格线
    ctx.strokeStyle = '#e5e7eb'
    ctx.lineWidth = 1
    for (let i = 0; i <= 5; i++) {
      const y = padding.top + (priceChartHeight / 5) * i
      ctx.beginPath()
      ctx.moveTo(padding.left, y)
      ctx.lineTo(padding.left + chartWidth, y)
      ctx.stroke()

      // 绘制价格标签
      const price = maxPrice + pricePadding - (priceRange + 2 * pricePadding) * (i / 5)
      ctx.fillStyle = '#6b7280'
      ctx.font = '10px sans-serif'
      ctx.textAlign = 'left'
      ctx.fillText(price.toFixed(2), padding.left + chartWidth + 5, y + 3)
    }

    // 绘制K线
    klineData.forEach((data, index) => {
      const x = padding.left + index * candleWidth + candleWidth / 2

      // 确定颜色（涨红跌绿）
      const isRise = data.close >= data.open
      const candleColor = isRise ? '#ef4444' : '#22c55e'
      const wickColor = isRise ? '#ef4444' : '#22c55e'

      // 绘制影线
      ctx.strokeStyle = wickColor
      ctx.lineWidth = 1
      ctx.beginPath()
      ctx.moveTo(x, priceToY(data.high))
      ctx.lineTo(x, priceToY(data.low))
      ctx.stroke()

      // 绘制K线实体
      const openY = priceToY(data.open)
      const closeY = priceToY(data.close)
      const bodyHeight = Math.abs(closeY - openY)
      const bodyY = Math.min(openY, closeY)

      ctx.fillStyle = candleColor
      if (bodyHeight < 1) {
        // 十字星
        ctx.fillRect(x - candleBodyWidth / 2, bodyY, candleBodyWidth, 1)
      } else {
        ctx.fillRect(x - candleBodyWidth / 2, bodyY, candleBodyWidth, bodyHeight)
      }

      // 绘制成交量柱
      const volumeTop = padding.top + priceChartHeight + gap
      const volumeHeight = (data.volume / maxVolume) * volumeChartHeight
      ctx.fillStyle = isRise ? '#fecaca' : '#bbf7d0'
      ctx.fillRect(x - candleBodyWidth / 2, volumeToY(data.volume), candleBodyWidth, volumeHeight)
    })

    // 绘制日期标签（每隔几天显示一次）
    const dateStep = Math.max(1, Math.floor(klineData.length / 6))
    ctx.fillStyle = '#6b7280'
    ctx.font = '10px sans-serif'
    ctx.textAlign = 'center'
    klineData.forEach((data, index) => {
      if (index % dateStep === 0 || index === klineData.length - 1) {
        const x = padding.left + index * candleWidth + candleWidth / 2
        const y = padding.top + priceChartHeight + gap + volumeChartHeight + 15
        const dateStr = data.date.slice(5) // 只显示月-日
        ctx.fillText(dateStr, x, y)
      }
    })

    // 绘制标注点
    annotations.forEach(annotation => {
      const dataIndex = klineData.findIndex(d => d.date === annotation.date)
      if (dataIndex === -1) return

      const x = padding.left + dataIndex * candleWidth + candleWidth / 2
      const y = priceToY(annotation.price)

      // 根据类型选择颜色
      let color = '#3b82f6'
      switch (annotation.type) {
        case 'high':
          color = '#ef4444'
          break
        case 'low':
          color = '#22c55e'
          break
        case 'volume':
          color = '#f59e0b'
          break
        case 'breakout':
          color = '#8b5cf6'
          break
        case 'consolidation':
          color = '#6366f1'
          break
      }

      // 绘制标注点
      ctx.fillStyle = color
      ctx.beginPath()
      ctx.arc(x, y, 4, 0, Math.PI * 2)
      ctx.fill()

      // 绘制标签背景
      ctx.font = '11px sans-serif'
      const textWidth = ctx.measureText(annotation.label).width
      const labelX = x + 8
      const labelY = y - 8

      ctx.fillStyle = color
      ctx.fillRect(labelX - 2, labelY - 12, textWidth + 4, 16)

      // 绘制标签文字
      ctx.fillStyle = '#ffffff'
      ctx.textAlign = 'left'
      ctx.fillText(annotation.label, labelX, labelY)
    })

    // 绘制标题
    ctx.fillStyle = '#1f2937'
    ctx.font = 'bold 12px sans-serif'
    ctx.textAlign = 'left'
    ctx.fillText('K线图', padding.left, 20)

    // 绘制成交量标题
    const volumeTop = padding.top + priceChartHeight + gap
    ctx.fillStyle = '#6b7280'
    ctx.font = '10px sans-serif'
    ctx.fillText('成交量', padding.left, volumeTop - 5)

  }, [klineData, annotations, height])

  return (
    <div className="w-full" style={{ height: `${height}px` }}>
      <canvas
        ref={canvasRef}
        className="w-full h-full"
        style={{ width: '100%', height: '100%' }}
      />
    </div>
  )
}
