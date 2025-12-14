'use client'

import { useState, useRef, useEffect } from 'react'

interface KLineData {
  date: string
  open: number
  high: number
  low: number
  close: number
  volume: number
}

interface AnnotationRegion {
  start_index: number  // 负数：相对于末尾的偏移
  end_index: number
  label: string
  type: 'consolidation' | 'rise' | 'decline' | 'breakout'
  color?: string
}

interface AnnotationPoint {
  index: number  // 负数：相对于末尾的偏移
  label: string
  type: 'volume_spike' | 'price_breakout' | 'pattern_signal'
  position: 'above' | 'below' | 'volume'
}

interface AnnotationLine {
  price: number
  label: string
  type: 'resistance' | 'support'
  style: 'solid' | 'dashed'
}

interface Annotations {
  regions?: AnnotationRegion[]
  points?: AnnotationPoint[]
  lines?: AnnotationLine[]
}

interface Props {
  data: KLineData[]
  annotations?: Annotations | null
}

export default function AnnotatedKLineChart({ data, annotations }: Props) {
  const containerRef = useRef<HTMLDivElement>(null)
  const [containerWidth, setContainerWidth] = useState(1200)
  const [hoveredIndex, setHoveredIndex] = useState<number | null>(null)

  // 响应式宽度
  useEffect(() => {
    if (!containerRef.current) return

    const observer = new ResizeObserver(entries => {
      const width = entries[0].contentRect.width
      setContainerWidth(Math.max(800, width - 20))
    })

    observer.observe(containerRef.current)
    return () => observer.disconnect()
  }, [])

  if (!data || data.length === 0) {
    return <div className="text-gray-500 text-sm text-center py-8">暂无K线数据</div>
  }

  // 计算价格范围
  const prices = data.flatMap(d => [d.high, d.low])
  const maxPrice = Math.max(...prices)
  const minPrice = Math.min(...prices)
  const priceRange = maxPrice - minPrice
  const pricePadding = priceRange * 0.1

  // 计算成交量范围
  const maxVolume = Math.max(...data.map(d => d.volume))

  // 布局参数
  const margin = { top: 40, right: 10, bottom: 20, left: 60 }
  const chartHeight = 250
  const volumeHeight = 80
  const totalHeight = chartHeight + volumeHeight + margin.top + margin.bottom + 20

  const chartWidth = containerWidth - margin.left - margin.right
  const candleWidth = Math.max(3, Math.min(12, chartWidth / data.length * 0.6))
  const candleSpacing = chartWidth / data.length

  // 价格到Y坐标的转换
  const priceToY = (price: number) => {
    return margin.top + (maxPrice + pricePadding - price) / (priceRange + 2 * pricePadding) * chartHeight
  }

  // 成交量到高度的转换
  const volumeToHeight = (volume: number) => {
    return (volume / maxVolume) * volumeHeight
  }

  // 索引到X坐标的转换
  const indexToX = (index: number) => {
    return margin.left + index * candleSpacing + candleSpacing / 2
  }

  // 负索引转正索引（annotations使用负索引，-1表示最后一天）
  const negativeToPositive = (negIndex: number) => {
    return data.length + negIndex
  }

  // 渲染区域标注
  const renderRegions = () => {
    if (!annotations?.regions) return null

    return annotations.regions.map((region, idx) => {
      const startIdx = negativeToPositive(region.start_index)
      const endIdx = negativeToPositive(region.end_index)

      if (startIdx < 0 || endIdx >= data.length) return null

      const x = indexToX(startIdx)
      const width = (endIdx - startIdx + 1) * candleSpacing
      const y = margin.top
      const height = chartHeight

      return (
        <g key={`region-${idx}`}>
          {/* 区域高亮背景 */}
          <rect
            x={x - candleSpacing / 2}
            y={y}
            width={width}
            height={height}
            fill={region.color || 'rgba(147, 197, 253, 0.15)'}
            stroke="none"
          />
          {/* 区域标签 */}
          <text
            x={x + width / 2}
            y={y + 15}
            textAnchor="middle"
            className="text-xs font-semibold"
            fill="#1e40af"
          >
            {region.label}
          </text>
        </g>
      )
    })
  }

  // 渲染价格线标注
  const renderLines = () => {
    if (!annotations?.lines) return null

    return annotations.lines.map((line, idx) => {
      // 如果price为0，计算前期高点
      let actualPrice = line.price
      if (actualPrice === 0 && line.type === 'resistance') {
        // 取前70%数据的最高点作为压力位
        const earlyData = data.slice(0, Math.floor(data.length * 0.7))
        actualPrice = Math.max(...earlyData.map(d => d.high))
      } else if (actualPrice === 0 && line.type === 'support') {
        // 取前70%数据的最低点作为支撑位
        const earlyData = data.slice(0, Math.floor(data.length * 0.7))
        actualPrice = Math.min(...earlyData.map(d => d.low))
      }

      const y = priceToY(actualPrice)

      return (
        <g key={`line-${idx}`}>
          <line
            x1={margin.left}
            y1={y}
            x2={margin.left + chartWidth}
            y2={y}
            stroke="#9ca3af"
            strokeWidth={1.5}
            strokeDasharray={line.style === 'dashed' ? '5,5' : '0'}
            opacity={0.6}
          />
          <text
            x={margin.left + chartWidth - 5}
            y={y - 5}
            textAnchor="end"
            className="text-xs"
            fill="#6b7280"
          >
            {line.label}
          </text>
        </g>
      )
    })
  }

  // 渲染点标注
  const renderPoints = () => {
    if (!annotations?.points) return null

    return annotations.points.map((point, idx) => {
      const dataIdx = negativeToPositive(point.index)
      if (dataIdx < 0 || dataIdx >= data.length) return null

      const kline = data[dataIdx]
      const x = indexToX(dataIdx)

      // 根据position确定Y坐标
      let y: number
      let color: string

      if (point.position === 'volume') {
        // 成交量标注
        y = margin.top + chartHeight + 30
        color = '#f59e0b'  // 琥珀色
      } else if (point.position === 'above') {
        // K线上方标注
        y = priceToY(kline.high) - 20
        color = '#8b5cf6'  // 紫色
      } else {
        // K线下方标注
        y = priceToY(kline.low) + 20
        color = '#3b82f6'  // 蓝色
      }

      return (
        <g key={`point-${idx}`}>
          {/* 标注气泡 */}
          <g className="cursor-pointer">
            <circle
              cx={x}
              cy={point.position === 'volume' ? y - 10 : y}
              r={4}
              fill={color}
            />
            <text
              x={x}
              y={y + (point.position === 'below' ? 15 : -5)}
              textAnchor="middle"
              className="text-xs font-semibold"
              fill={color}
            >
              {point.label}
            </text>
          </g>
        </g>
      )
    })
  }

  return (
    <div ref={containerRef} className="w-full">
      <svg width={containerWidth} height={totalHeight} className="overflow-visible">
        {/* 区域标注（最底层） */}
        {renderRegions()}

        {/* 价格线标注 */}
        {renderLines()}

        {/* K线图 */}
        {data.map((d, i) => {
          const x = indexToX(i)
          const isRise = d.close >= d.open
          const color = isRise ? '#ef4444' : '#22c55e'

          return (
            <g
              key={i}
              onMouseEnter={() => setHoveredIndex(i)}
              onMouseLeave={() => setHoveredIndex(null)}
              className="cursor-crosshair"
            >
              {/* 上下影线 */}
              <line
                x1={x}
                y1={priceToY(d.high)}
                x2={x}
                y2={priceToY(d.low)}
                stroke={color}
                strokeWidth={1}
              />
              {/* 实体 */}
              <rect
                x={x - candleWidth / 2}
                y={priceToY(Math.max(d.open, d.close))}
                width={candleWidth}
                height={Math.max(1, Math.abs(priceToY(d.close) - priceToY(d.open)))}
                fill={isRise ? 'none' : color}
                stroke={color}
                strokeWidth={1}
              />
            </g>
          )
        })}

        {/* 成交量柱 */}
        {data.map((d, i) => {
          const x = indexToX(i)
          const isRise = d.close >= d.open
          const color = isRise ? '#ef4444' : '#22c55e'
          const height = volumeToHeight(d.volume)
          const volumeY = margin.top + chartHeight + 30

          return (
            <rect
              key={`vol-${i}`}
              x={x - candleWidth / 2}
              y={volumeY + volumeHeight - height}
              width={candleWidth}
              height={height}
              fill={color}
              opacity={0.3}
            />
          )
        })}

        {/* 点标注（最上层） */}
        {renderPoints()}

        {/* 悬浮提示 */}
        {hoveredIndex !== null && (
          <g>
            <rect
              x={margin.left + 10}
              y={margin.top + 10}
              width={180}
              height={100}
              fill="white"
              stroke="#d1d5db"
              strokeWidth={1}
              rx={4}
            />
            <text x={margin.left + 20} y={margin.top + 30} className="text-xs fill-gray-700">
              日期: {data[hoveredIndex].date}
            </text>
            <text x={margin.left + 20} y={margin.top + 48} className="text-xs fill-gray-700">
              开: {data[hoveredIndex].open.toFixed(2)}  收: {data[hoveredIndex].close.toFixed(2)}
            </text>
            <text x={margin.left + 20} y={margin.top + 66} className="text-xs fill-gray-700">
              高: {data[hoveredIndex].high.toFixed(2)}  低: {data[hoveredIndex].low.toFixed(2)}
            </text>
            <text x={margin.left + 20} y={margin.top + 84} className="text-xs fill-gray-700">
              量: {(data[hoveredIndex].volume / 10000).toFixed(0)}万
            </text>
          </g>
        )}

        {/* Y轴价格标签 */}
        {[0, 0.25, 0.5, 0.75, 1].map((ratio, i) => {
          const price = minPrice + priceRange * ratio
          const y = priceToY(price)
          return (
            <text
              key={`price-${i}`}
              x={margin.left - 10}
              y={y + 4}
              textAnchor="end"
              className="text-xs fill-gray-500"
            >
              {price.toFixed(2)}
            </text>
          )
        })}
      </svg>
    </div>
  )
}
