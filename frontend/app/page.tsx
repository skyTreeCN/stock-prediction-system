'use client'

import { useState, useEffect, useRef } from 'react'
import { ChevronDown, ChevronUp, ChevronLeft, ChevronRight, Download } from 'lucide-react'
import jsPDF from 'jspdf'
import html2canvas from 'html2canvas'
import axios from 'axios'
import DataFetcher from '@/components/DataFetcher'
import DataAnalyzer from '@/components/DataAnalyzer'
import SimilarityAnalysis from '@/components/SimilarityAnalysis'

const API_BASE = 'http://localhost:8000'

// 生成3年模拟数据的辅助函数（约750个交易日）
function generate30DaysData(pattern: string) {
  const data = []
  const basePrice = 10.0
  let currentPrice = basePrice
  const totalDays = 750 // 3年约750个交易日

  if (pattern === 'consolidation_breakout') {
    // 前期700天：正常波动走势
    for (let i = 0; i < 700; i++) {
      const trendFactor = i < 350 ? 1.0002 : 0.9999 // 前半段缓慢上涨，后半段小幅下跌
      const variation = (Math.random() * 0.04 - 0.02) * currentPrice // ±2%波动
      const open = currentPrice + variation
      const close = open * trendFactor * (1 + (Math.random() * 0.02 - 0.01))
      const high = Math.max(open, close) * (1 + Math.random() * 0.01)
      const low = Math.min(open, close) * (1 - Math.random() * 0.01)
      data.push({
        date: `${i + 1}日`,
        open: parseFloat(open.toFixed(2)),
        close: parseFloat(close.toFixed(2)),
        high: parseFloat(high.toFixed(2)),
        low: parseFloat(low.toFixed(2)),
        volume: 3000 + Math.random() * 2000
      })
      currentPrice = close
    }

    // 底部横盘整理模式 - 25天横盘
    for (let i = 700; i < 725; i++) {
      const variation = currentPrice * 0.015 * (Math.random() - 0.5) // ±1.5%波动
      const open = currentPrice + variation
      const close = currentPrice + (currentPrice * 0.01 * (Math.random() - 0.5))
      const high = Math.max(open, close) * 1.008
      const low = Math.min(open, close) * 0.992
      data.push({
        date: `${i + 1}日`,
        open: parseFloat(open.toFixed(2)),
        close: parseFloat(close.toFixed(2)),
        high: parseFloat(high.toFixed(2)),
        low: parseFloat(low.toFixed(2)),
        volume: 2000 + Math.random() * 500 // 低量横盘
      })
      currentPrice = close
    }
    // 突破日 - 大阳线 + 3倍成交量
    const breakoutOpen = currentPrice
    const breakoutClose = currentPrice * 1.06 // 6%涨幅
    data.push({
      date: '726日',
      open: parseFloat(breakoutOpen.toFixed(2)),
      close: parseFloat(breakoutClose.toFixed(2)),
      high: parseFloat((breakoutClose * 1.01).toFixed(2)),
      low: parseFloat(breakoutOpen.toFixed(2)),
      volume: 7500 // 3倍放量
    })
    currentPrice = breakoutClose
    // 突破后持续上涨
    for (let i = 726; i < 750; i++) {
      const open = currentPrice
      const close = currentPrice * (1 + Math.random() * 0.02)
      const high = Math.max(open, close) * 1.005
      const low = Math.min(open, close) * 0.995
      data.push({
        date: `${i + 1}日`,
        open: parseFloat(open.toFixed(2)),
        close: parseFloat(close.toFixed(2)),
        high: parseFloat(high.toFixed(2)),
        low: parseFloat(low.toFixed(2)),
        volume: 4000 + Math.random() * 1000
      })
      currentPrice = close
    }
  } else if (pattern === 'pullback_breakout') {
    // 缩量回调突破模式
    // 前710天：正常波动
    for (let i = 0; i < 710; i++) {
      const trendFactor = i < 400 ? 1.0001 : 0.9999
      const variation = (Math.random() * 0.04 - 0.02) * currentPrice
      const open = currentPrice + variation
      const close = open * trendFactor * (1 + (Math.random() * 0.02 - 0.01))
      const high = Math.max(open, close) * (1 + Math.random() * 0.01)
      const low = Math.min(open, close) * (1 - Math.random() * 0.01)
      data.push({
        date: `${i + 1}日`,
        open: parseFloat(open.toFixed(2)),
        close: parseFloat(close.toFixed(2)),
        high: parseFloat(high.toFixed(2)),
        low: parseFloat(low.toFixed(2)),
        volume: 3000 + Math.random() * 2000
      })
      currentPrice = close
    }

    // 前期上涨10天
    for (let i = 710; i < 720; i++) {
      const open = currentPrice
      const close = currentPrice * (1 + Math.random() * 0.025)
      const high = Math.max(open, close) * 1.005
      const low = Math.min(open, close) * 0.995
      data.push({
        date: `${i + 1}日`,
        open: parseFloat(open.toFixed(2)),
        close: parseFloat(close.toFixed(2)),
        high: parseFloat(high.toFixed(2)),
        low: parseFloat(low.toFixed(2)),
        volume: 5000 + Math.random() * 1000
      })
      currentPrice = close
    }
    const previousHigh = currentPrice

    // 10天缩量回调
    for (let i = 720; i < 730; i++) {
      const open = currentPrice
      const close = currentPrice * (1 - Math.random() * 0.01)
      const high = Math.max(open, close) * 1.002
      const low = Math.min(open, close) * 0.998
      data.push({
        date: `${i + 1}日`,
        open: parseFloat(open.toFixed(2)),
        close: parseFloat(close.toFixed(2)),
        high: parseFloat(high.toFixed(2)),
        low: parseFloat(low.toFixed(2)),
        volume: 1500 + Math.random() * 300 // 缩量至1/3
      })
      currentPrice = close
    }

    // 突破日
    data.push({
      date: '731日',
      open: parseFloat(currentPrice.toFixed(2)),
      close: parseFloat((previousHigh * 1.02).toFixed(2)),
      high: parseFloat((previousHigh * 1.025).toFixed(2)),
      low: parseFloat(currentPrice.toFixed(2)),
      volume: 12000 // 大幅放量
    })
    currentPrice = previousHigh * 1.02

    // 持续上涨
    for (let i = 731; i < 750; i++) {
      const open = currentPrice
      const close = currentPrice * (1 + Math.random() * 0.015)
      data.push({
        date: `${i + 1}日`,
        open: parseFloat(open.toFixed(2)),
        close: parseFloat(close.toFixed(2)),
        high: parseFloat((Math.max(open, close) * 1.005).toFixed(2)),
        low: parseFloat((Math.min(open, close) * 0.995).toFixed(2)),
        volume: 6000 + Math.random() * 1500
      })
      currentPrice = close
    }
  } else if (pattern === 'gap_up') {
    // 跳空缺口模式
    // 前720天：正常波动
    for (let i = 0; i < 720; i++) {
      const trendFactor = 1.0001
      const variation = (Math.random() * 0.04 - 0.02) * currentPrice
      const open = currentPrice + variation
      const close = open * trendFactor * (1 + (Math.random() * 0.02 - 0.01))
      const high = Math.max(open, close) * (1 + Math.random() * 0.01)
      const low = Math.min(open, close) * (1 - Math.random() * 0.01)
      data.push({
        date: `${i + 1}日`,
        open: parseFloat(open.toFixed(2)),
        close: parseFloat(close.toFixed(2)),
        high: parseFloat(high.toFixed(2)),
        low: parseFloat(low.toFixed(2)),
        volume: 3000 + Math.random() * 2000
      })
      currentPrice = close
    }

    // 缺口前15天温和上涨
    for (let i = 720; i < 735; i++) {
      const open = currentPrice
      const close = currentPrice * (1 + Math.random() * 0.015)
      data.push({
        date: `${i + 1}日`,
        open: parseFloat(open.toFixed(2)),
        close: parseFloat(close.toFixed(2)),
        high: parseFloat((Math.max(open, close) * 1.005).toFixed(2)),
        low: parseFloat((Math.min(open, close) * 0.995).toFixed(2)),
        volume: 4000 + Math.random() * 800
      })
      currentPrice = close
    }
    const preGapHigh = data[data.length - 1].high

    // 跳空缺口日
    const gapOpen = preGapHigh * 1.03 // 跳空3%
    const gapClose = gapOpen * 1.04
    data.push({
      date: '736日',
      open: parseFloat(gapOpen.toFixed(2)),
      close: parseFloat(gapClose.toFixed(2)),
      high: parseFloat((gapClose * 1.005).toFixed(2)),
      low: parseFloat(gapOpen.toFixed(2)),
      volume: 10000 // 2.5倍放量
    })
    currentPrice = gapClose

    // 缺口后持续
    for (let i = 736; i < totalDays; i++) {
      const open = currentPrice
      const close = currentPrice * (1 + Math.random() * 0.01)
      data.push({
        date: `${i + 1}日`,
        open: parseFloat(open.toFixed(2)),
        close: parseFloat(close.toFixed(2)),
        high: parseFloat((Math.max(open, close) * 1.003).toFixed(2)),
        low: parseFloat((Math.min(open, close) * 0.997).toFixed(2)),
        volume: 5500 + Math.random() * 1000
      })
      currentPrice = close
    }
  }

  return data
}

// 模拟模式数据 - 使用30天真实数据
const MOCK_PATTERNS = [
  {
    id: 1,
    pattern_name: "缩量回调突破模式",
    description: "股价经过一段上涨后，在高位进行缩量调整，随后在成交量放大的情况下向上突破前高，形成新的上涨趋势。",
    characteristics: [
      "前期上涨10天，累计涨幅25%",
      "回调期10天，成交量萎缩至前期1/3",
      "突破时成交量放大至回调期4倍",
      "突破日收盘价站稳前高2%以上"
    ],
    klineData: generate30DaysData('pullback_breakout'),
    quantitativeData: {
      consolidationDays: 10,
      avgVolumeBefore: 5000,
      avgVolumeDuring: 1600,
      breakoutVolume: 12000,
      previousHigh: 12.5,
      breakoutClose: 12.75,
      riseBeforePercent: 25
    }
  },
  {
    id: 2,
    pattern_name: "跳空缺口上涨模式",
    description: "股价以向上跳空缺口的形式开盘，当日收阳线且成交量明显放大，缺口未被回补，后续延续上涨。",
    characteristics: [
      "开盘价高于前一日最高价3%以上",
      "成交量在缺口形成当日放大2.5倍",
      "缺口未被回补（后续15天低点不破缺口）",
      "缺口后连续5天收阳"
    ],
    klineData: generate30DaysData('gap_up'),
    quantitativeData: {
      gapSize: 3.2,
      gapDate: '16日',
      avgVolumeBefore: 4200,
      gapVolume: 10000,
      daysAfterGap: 14,
      noFillback: true
    }
  },
  {
    id: 3,
    pattern_name: "底部放量反转模式",
    description: "股价在低位盘整后，出现放量大阳线，突破盘整区间，成交量是前期的3倍以上，形成反转信号。",
    characteristics: [
      "底部横盘整理25天，振幅<3%",
      "突破日大阳线，涨幅6%",
      "成交量是横盘期平均量的3.3倍",
      "突破后4天不再回到盘整区间"
    ],
    klineData: generate30DaysData('consolidation_breakout'),
    quantitativeData: {
      consolidationDays: 25,
      consolidationRange: 2.8,
      avgVolumeConsolidation: 2250,
      breakoutVolume: 7500,
      breakoutRise: 6.0,
      daysNoReturn: 4
    }
  }
]

// 模拟推荐股票数据
const MOCK_PREDICTIONS = [
  {
    rank: 1,
    code: '600519.SS',
    name: '贵州茅台',
    probability: 87.5,
    current_price: 1678.50,
    matched_pattern: '缩量回调突破模式',
    reason: '符合缩量回调突破模式，回调期成交量萎缩至前期30%，今日放量突破前高',
    klineData: generate30DaysData('pullback_breakout'),
    matchedQuantitativeData: {
      consolidationDays: 11,
      avgVolumeBefore: 48000,
      avgVolumeDuring: 15000,
      breakoutVolume: 125000,
      previousHigh: 1695,
      breakoutClose: 1710,
      volumeRatio: 8.3
    }
  },
  {
    rank: 2,
    code: '000858.SZ',
    name: '五粮液',
    probability: 82.3,
    current_price: 156.80,
    matched_pattern: '跳空缺口上涨模式',
    reason: '今日跳空高开形成3.1%向上缺口,成交量放大2.4倍,缺口未回补',
    klineData: generate30DaysData('gap_up'),
    matchedQuantitativeData: {
      gapSize: 3.1,
      gapDate: '16日',
      avgVolumeBefore: 42000,
      gapVolume: 105000,
      daysAfterGap: 14,
      volumeRatio: 2.5
    }
  }
]

export default function DemoPage() {
  const [activeTab, setActiveTab] = useState<'data' | 'patterns' | 'predictions'>('patterns')
  const [expandedPattern, setExpandedPattern] = useState<number>(1)
  const [currentStockIndex, setCurrentStockIndex] = useState(0)
  const [isClient, setIsClient] = useState(false)
  const [isDownloading, setIsDownloading] = useState(false)

  // 真实数据状态
  const [realPredictions, setRealPredictions] = useState<any[]>([])

  // 仅在客户端渲染，避免SSR水合不匹配
  useEffect(() => {
    setIsClient(true)
  }, [])

  // 获取真实的预测数据
  const fetchRealPredictions = async () => {
    try {
      const res = await axios.get(`${API_BASE}/api/predictions`)
      if (res.data && Array.isArray(res.data)) {
        setRealPredictions(res.data)
      }
    } catch (error) {
      console.error('获取预测数据失败', error)
    }
  }

  // 在组件挂载时获取数据
  useEffect(() => {
    fetchRealPredictions()
  }, [])

  // 当切换到预测标签页时重新获取数据
  useEffect(() => {
    if (activeTab === 'predictions') {
      fetchRealPredictions()
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [activeTab])

  // PDF下载功能 - 下载当前股票
  const handleDownloadPDF = async () => {
    if (isDownloading) return

    setIsDownloading(true)
    try {
      const element = document.getElementById('stock-detail-card')
      if (!element) {
        alert('未找到要下载的内容')
        return
      }

      // 使用html2canvas截取页面内容
      const canvas = await html2canvas(element, {
        scale: 2,
        useCORS: true,
        logging: false,
        backgroundColor: '#ffffff'
      })

      // 创建PDF
      const imgData = canvas.toDataURL('image/png')
      const pdf = new jsPDF({
        orientation: 'portrait',
        unit: 'mm',
        format: 'a4'
      })

      const imgWidth = 210
      const pageHeight = 297
      const imgHeight = (canvas.height * imgWidth) / canvas.width
      let heightLeft = imgHeight
      let position = 0

      pdf.addImage(imgData, 'PNG', 0, position, imgWidth, imgHeight)
      heightLeft -= pageHeight

      while (heightLeft > 0) {
        position = heightLeft - imgHeight
        pdf.addPage()
        pdf.addImage(imgData, 'PNG', 0, position, imgWidth, imgHeight)
        heightLeft -= pageHeight
      }

      // 获取当前股票信息
      const currentStock = realPredictions.length > 0
        ? realPredictions.slice(0, 10)[currentStockIndex]
        : MOCK_PREDICTIONS[currentStockIndex]

      const fileName = `股票推荐_${currentStock.name}_${currentStock.code}_${new Date().toISOString().split('T')[0]}.pdf`
      pdf.save(fileName)

      alert('PDF下载成功!')
    } catch (error) {
      console.error('PDF生成失败:', error)
      alert('PDF生成失败，请重试')
    } finally {
      setIsDownloading(false)
    }
  }

  // PDF下载功能 - 下载全部10只股票
  const handleDownloadAllPDF = async () => {
    if (isDownloading) return

    setIsDownloading(true)
    try {
      const pdf = new jsPDF({
        orientation: 'portrait',
        unit: 'mm',
        format: 'a4'
      })

      const stocksToDownload = realPredictions.length > 0
        ? realPredictions.slice(0, 10)
        : MOCK_PREDICTIONS

      // 保存原始索引
      const originalIndex = currentStockIndex

      for (let i = 0; i < stocksToDownload.length; i++) {
        // 切换到对应股票
        setCurrentStockIndex(i)

        // 等待DOM更新
        await new Promise(resolve => setTimeout(resolve, 500))

        const element = document.getElementById('stock-detail-card')
        if (!element) continue

        const canvas = await html2canvas(element, {
          scale: 2,
          useCORS: true,
          logging: false,
          backgroundColor: '#ffffff'
        })

        const imgData = canvas.toDataURL('image/png')
        const imgWidth = 210
        const pageHeight = 297
        const imgHeight = (canvas.height * imgWidth) / canvas.width

        // 第一只股票不需要添加新页
        if (i > 0) {
          pdf.addPage()
        }

        let position = 0
        let heightLeft = imgHeight

        pdf.addImage(imgData, 'PNG', 0, position, imgWidth, imgHeight)
        heightLeft -= pageHeight

        while (heightLeft > 0) {
          position = heightLeft - imgHeight
          pdf.addPage()
          pdf.addImage(imgData, 'PNG', 0, position, imgWidth, imgHeight)
          heightLeft -= pageHeight
        }
      }

      // 恢复原始索引
      setCurrentStockIndex(originalIndex)

      const fileName = `股票推荐_前10只_${new Date().toISOString().split('T')[0]}.pdf`
      pdf.save(fileName)

      alert(`PDF下载成功! 已生成${stocksToDownload.length}只股票的报告`)
    } catch (error) {
      console.error('PDF生成失败:', error)
      alert('PDF生成失败，请重试')
    } finally {
      setIsDownloading(false)
    }
  }

  if (!isClient) {
    return <div className="min-h-screen bg-gradient-to-br from-blue-50 via-white to-purple-50 flex items-center justify-center">
      <div className="text-gray-600">加载中...</div>
    </div>
  }

  return (
    <div className="min-h-screen bg-gradient-to-br from-blue-50 via-white to-purple-50">
      <div className="container mx-auto px-4 py-8">
        {/* 标题 */}
        <div className="text-center mb-8">
          <h1 className="text-4xl font-bold bg-gradient-to-r from-blue-600 to-purple-600 bg-clip-text text-transparent mb-2">
            股票预测分析系统
          </h1>
          <p className="text-gray-600">AI驱动的智能选股助手 - 数据驱动决策</p>
        </div>

        {/* Tab导航 */}
        <div className="bg-white rounded-t-2xl shadow-lg">
          <div className="flex border-b border-gray-200">
            <button
              onClick={() => setActiveTab('data')}
              className={`flex-1 px-6 py-4 text-lg font-semibold transition-all ${
                activeTab === 'data'
                  ? 'text-blue-600 border-b-4 border-blue-600 bg-blue-50'
                  : 'text-gray-600 hover:text-blue-600 hover:bg-gray-50'
              }`}
            >
              📊 数据获取
            </button>
            <button
              onClick={() => setActiveTab('patterns')}
              className={`flex-1 px-6 py-4 text-lg font-semibold transition-all ${
                activeTab === 'patterns'
                  ? 'text-purple-600 border-b-4 border-purple-600 bg-purple-50'
                  : 'text-gray-600 hover:text-purple-600 hover:bg-gray-50'
              }`}
            >
              🔍 上涨模式分析
            </button>
            <button
              onClick={() => setActiveTab('predictions')}
              className={`flex-1 px-6 py-4 text-lg font-semibold transition-all ${
                activeTab === 'predictions'
                  ? 'text-green-600 border-b-4 border-green-600 bg-green-50'
                  : 'text-gray-600 hover:text-green-600 hover:bg-gray-50'
              }`}
            >
              ⭐ 推荐股票
            </button>
          </div>

          {/* Tab内容 */}
          <div className="p-8">
            {/* Tab 1: 数据获取 */}
            {activeTab === 'data' && (
              <div>
                <DataFetcher />
              </div>
            )}

            {/* Tab 2: 模式可视化 */}
            {activeTab === 'patterns' && (
              <div>
                <DataAnalyzer />
              </div>
            )}

            {/* Tab 3: 推荐股票 */}
            {activeTab === 'predictions' && (
              <div>
                <SimilarityAnalysis />

                {realPredictions.length > 0 ? (
                  <>
                    <div className="mt-8 mb-6">
                      <h2 className="text-2xl font-bold text-green-600 mb-2">推荐股票</h2>
                      <p className="text-gray-600">以下是AI预测上涨概率较高的{realPredictions.length}只股票</p>
                    </div>

                    <div className="space-y-4">
                      {realPredictions.map((pred, idx) => (
                        <div
                          key={idx}
                          className="border-2 rounded-xl overflow-hidden border-gray-200 shadow-md"
                        >
                          <div className="w-full px-6 py-4 bg-gradient-to-r from-green-500 to-green-600 text-white">
                            <div className="flex items-center gap-3">
                              <span className="text-2xl font-bold text-white">
                                {idx + 1}
                              </span>
                              <span className="text-lg font-semibold">{pattern.pattern_name}</span>
                            </div>
                          </div>

                          <div className="p-6 bg-white">
                            <div className="mb-4">
                              <h3 className="text-lg font-semibold text-gray-800 mb-2">模式说明</h3>
                              <p className="text-gray-700 leading-relaxed">{pattern.description}</p>
                            </div>

                            {/* 量化指标卡片 */}
                            {pattern.key_features && pattern.key_features.length > 0 && (
                              <div className="mb-6 bg-amber-50 rounded-lg p-4 border-2 border-amber-200">
                                <h3 className="text-lg font-semibold text-amber-900 mb-3 flex items-center gap-2">
                                  <span>📊</span> 量化指标（AI分析依据）
                                </h3>
                                <div className="grid grid-cols-2 gap-3">
                                  {/* 关键天数 */}
                                  {pattern.key_days && (
                                    <div className="bg-white rounded p-3 border border-amber-200">
                                      <div className="text-xs text-gray-600">关键时间段</div>
                                      <div className="text-xl font-bold text-purple-600">{pattern.key_days}</div>
                                    </div>
                                  )}
                                  {/* 示例股票代码 */}
                                  {pattern.example_stock_code && (
                                    <div className="bg-white rounded p-3 border border-amber-200">
                                      <div className="text-xs text-gray-600">示例股票代码</div>
                                      <div className="text-xl font-bold text-blue-600">{pattern.example_stock_code}</div>
                                    </div>
                                  )}
                                  {/* 关键特征 */}
                                  {pattern.key_features.map((feature: string, idx: number) => (
                                    <div key={idx} className="bg-white rounded p-3 border border-amber-200">
                                      <div className="text-xs text-gray-600">关键特征 {idx + 1}</div>
                                      <div className="text-sm font-semibold text-green-600">{feature}</div>
                                    </div>
                                  ))}
                                </div>
                              </div>
                            )}

                            <div className="mb-6">
                              <h3 className="text-lg font-semibold text-gray-800 mb-3">核心特征</h3>
                              <div className="grid grid-cols-2 gap-3">
                                {pattern.characteristics.map((char: string, i: number) => (
                                  <div
                                    key={i}
                                    className="flex items-start gap-2 bg-purple-50 rounded-lg p-3 border border-purple-200"
                                  >
                                    <span className="text-purple-600 font-bold">✓</span>
                                    <span className="text-sm text-gray-700 font-medium">{char}</span>
                                  </div>
                                ))}
                              </div>
                            </div>

                            {/* K线图 */}
                            {pattern.kline_data && pattern.kline_data.length > 0 && (
                              <div className="mt-6">
                                <h3 className="text-lg font-semibold text-gray-800 mb-3">典型案例K线图</h3>
                                <ChartScrollContainer patternId={idx + 1}>
                                  <div className="mb-4">
                                    <div className="text-xs text-gray-600 mb-2 font-semibold">K线图</div>
                                    <KLineChart
                                      data={pattern.kline_data}
                                      patternId={idx + 1}
                                      quantData={{
                                        key_days: pattern.key_days || '',
                                        key_features: pattern.key_features || []
                                      }}
                                    />
                                  </div>
                                  <div>
                                    <div className="text-xs text-gray-600 mb-2 font-semibold">成交量</div>
                                    <VolumeChart
                                      data={pattern.kline_data}
                                      patternId={idx + 1}
                                      quantData={{
                                        key_days: pattern.key_days || '',
                                        key_features: pattern.key_features || []
                                      }}
                                    />
                                  </div>
                                </ChartScrollContainer>
                              </div>
                            )}
                          </div>
                        </div>
                      ))}
                    </div>
                  </>
                ) : (
                  <>
                    <div className="mt-8 mb-6">
                      <h2 className="text-2xl font-bold text-purple-600 mb-2">上涨模式可视化（示例）</h2>
                      <p className="text-gray-600">以下是模拟的模式展示效果，实际数据将来自AI分析结果</p>
                    </div>

                    <div className="space-y-4">
                      {MOCK_PATTERNS.map((pattern) => (
                        <div
                          key={pattern.id}
                          className={`border-2 rounded-xl overflow-hidden transition-all duration-300 ${
                            expandedPattern === pattern.id
                              ? 'border-purple-500 shadow-xl'
                              : 'border-gray-200 shadow-md hover:border-purple-300'
                          }`}
                        >
                          {/* 模式标题栏 */}
                          <button
                            onClick={() => setExpandedPattern(pattern.id)}
                            className={`w-full px-6 py-4 flex items-center justify-between transition-colors ${
                              expandedPattern === pattern.id
                                ? 'bg-gradient-to-r from-purple-500 to-purple-600 text-white'
                                : 'bg-gray-50 hover:bg-purple-50'
                            }`}
                          >
                            <div className="flex items-center gap-3">
                              <span className={`text-2xl font-bold ${
                                expandedPattern === pattern.id ? 'text-white' : 'text-purple-600'
                              }`}>
                                {pattern.id}
                              </span>
                              <span className="text-lg font-semibold">{pattern.pattern_name}</span>
                            </div>
                            {expandedPattern === pattern.id ? (
                              <ChevronUp className="w-6 h-6" />
                            ) : (
                              <ChevronDown className="w-6 h-6" />
                            )}
                          </button>

                          {/* 模式详细内容 */}
                          {expandedPattern === pattern.id && (
                            <div className="p-6 bg-white">
                              {/* 模式描述 */}
                              <div className="mb-6">
                                <h3 className="text-lg font-semibold text-gray-800 mb-2">模式说明</h3>
                                <p className="text-gray-700 leading-relaxed">{pattern.description}</p>
                              </div>

                          {/* 量化指标 */}
                          <div className="mb-6 bg-amber-50 rounded-lg p-4 border-2 border-amber-300">
                            <h3 className="text-lg font-semibold text-amber-900 mb-3 flex items-center gap-2">
                              <span>📊</span> 量化指标（AI分析依据）
                            </h3>
                            <div className="grid grid-cols-3 gap-4">
                              {pattern.id === 1 && (
                                <>
                                  <div className="bg-white rounded p-3 border border-amber-200">
                                    <div className="text-xs text-gray-600">前期上涨天数</div>
                                    <div className="text-xl font-bold text-purple-600">{pattern.quantitativeData.consolidationDays}天</div>
                                  </div>
                                  <div className="bg-white rounded p-3 border border-amber-200">
                                    <div className="text-xs text-gray-600">回调期平均成交量</div>
                                    <div className="text-xl font-bold text-blue-600">{pattern.quantitativeData.avgVolumeDuring?.toLocaleString()}</div>
                                    <div className="text-xs text-red-600">↓ 前期的{((pattern.quantitativeData.avgVolumeDuring || 0) / (pattern.quantitativeData.avgVolumeBefore || 1) * 100).toFixed(0)}%</div>
                                  </div>
                                  <div className="bg-white rounded p-3 border border-amber-200">
                                    <div className="text-xs text-gray-600">突破日成交量</div>
                                    <div className="text-xl font-bold text-green-600">{pattern.quantitativeData.breakoutVolume?.toLocaleString()}</div>
                                    <div className="text-xs text-green-600">↑ 回调期的{((pattern.quantitativeData.breakoutVolume || 0) / (pattern.quantitativeData.avgVolumeDuring || 1)).toFixed(1)}倍</div>
                                  </div>
                                  <div className="bg-white rounded p-3 border border-amber-200">
                                    <div className="text-xs text-gray-600">前高价格</div>
                                    <div className="text-xl font-bold text-gray-700">¥{pattern.quantitativeData.previousHigh?.toFixed(2)}</div>
                                  </div>
                                  <div className="bg-white rounded p-3 border border-amber-200">
                                    <div className="text-xs text-gray-600">突破价格</div>
                                    <div className="text-xl font-bold text-green-600">¥{pattern.quantitativeData.breakoutClose?.toFixed(2)}</div>
                                    <div className="text-xs text-green-600">↑ +{(((pattern.quantitativeData.breakoutClose || 0) / (pattern.quantitativeData.previousHigh || 1) - 1) * 100).toFixed(1)}%</div>
                                  </div>
                                  <div className="bg-white rounded p-3 border border-amber-200">
                                    <div className="text-xs text-gray-600">前期涨幅</div>
                                    <div className="text-xl font-bold text-purple-600">{pattern.quantitativeData.riseBeforePercent}%</div>
                                  </div>
                                </>
                              )}
                              {pattern.id === 2 && (
                                <>
                                  <div className="bg-white rounded p-3 border border-amber-200">
                                    <div className="text-xs text-gray-600">缺口大小</div>
                                    <div className="text-xl font-bold text-cyan-600">{pattern.quantitativeData.gapSize}%</div>
                                  </div>
                                  <div className="bg-white rounded p-3 border border-amber-200">
                                    <div className="text-xs text-gray-600">缺口形成日</div>
                                    <div className="text-xl font-bold text-purple-600">{pattern.quantitativeData.gapDate}</div>
                                  </div>
                                  <div className="bg-white rounded p-3 border border-amber-200">
                                    <div className="text-xs text-gray-600">成交量放大</div>
                                    <div className="text-xl font-bold text-green-600">{((pattern.quantitativeData.gapVolume || 0) / (pattern.quantitativeData.avgVolumeBefore || 1)).toFixed(1)}倍</div>
                                  </div>
                                  <div className="bg-white rounded p-3 border border-amber-200">
                                    <div className="text-xs text-gray-600">缺口后天数</div>
                                    <div className="text-xl font-bold text-blue-600">{pattern.quantitativeData.daysAfterGap}天</div>
                                  </div>
                                  <div className="bg-white rounded p-3 border border-amber-200">
                                    <div className="text-xs text-gray-600">缺口状态</div>
                                    <div className="text-lg font-bold text-green-600">未回补 ✓</div>
                                  </div>
                                </>
                              )}
                              {pattern.id === 3 && (
                                <>
                                  <div className="bg-white rounded p-3 border border-amber-200">
                                    <div className="text-xs text-gray-600">横盘整理天数</div>
                                    <div className="text-xl font-bold text-gray-600">{pattern.quantitativeData.consolidationDays}天</div>
                                  </div>
                                  <div className="bg-white rounded p-3 border border-amber-200">
                                    <div className="text-xs text-gray-600">横盘振幅</div>
                                    <div className="text-xl font-bold text-gray-600">{pattern.quantitativeData.consolidationRange}%</div>
                                  </div>
                                  <div className="bg-white rounded p-3 border border-amber-200">
                                    <div className="text-xs text-gray-600">横盘期平均量</div>
                                    <div className="text-xl font-bold text-blue-600">{pattern.quantitativeData.avgVolumeConsolidation?.toLocaleString()}</div>
                                  </div>
                                  <div className="bg-white rounded p-3 border border-amber-200">
                                    <div className="text-xs text-gray-600">突破日成交量</div>
                                    <div className="text-xl font-bold text-green-600">{pattern.quantitativeData.breakoutVolume?.toLocaleString()}</div>
                                    <div className="text-xs text-green-600">↑ {((pattern.quantitativeData.breakoutVolume || 0) / (pattern.quantitativeData.avgVolumeConsolidation || 1)).toFixed(1)}倍</div>
                                  </div>
                                  <div className="bg-white rounded p-3 border border-amber-200">
                                    <div className="text-xs text-gray-600">突破日涨幅</div>
                                    <div className="text-xl font-bold text-green-600">{pattern.quantitativeData.breakoutRise}%</div>
                                  </div>
                                  <div className="bg-white rounded p-3 border border-amber-200">
                                    <div className="text-xs text-gray-600">突破后不回落</div>
                                    <div className="text-xl font-bold text-purple-600">{pattern.quantitativeData.daysNoReturn}天</div>
                                  </div>
                                </>
                              )}
                            </div>
                          </div>

                          {/* 特征列表 */}
                          <div className="mb-6">
                            <h3 className="text-lg font-semibold text-gray-800 mb-3">核心特征</h3>
                            <div className="grid grid-cols-2 gap-3">
                              {pattern.characteristics.map((char, idx) => (
                                <div
                                  key={idx}
                                  className="flex items-start gap-2 bg-purple-50 rounded-lg p-3 border border-purple-200"
                                >
                                  <span className="text-purple-600 font-bold">✓</span>
                                  <span className="text-sm text-gray-700 font-medium">{char}</span>
                                </div>
                              ))}
                            </div>
                          </div>

                          {/* K线图 + 成交量图 */}
                          <div className="mb-4">
                            <h3 className="text-lg font-semibold text-gray-800 mb-3">典型案例图表（30天完整数据）</h3>

                            {/* K线图和成交量图 - 同步滚动 */}
                            <div className="bg-gray-50 rounded-lg p-4 border border-gray-200">
                              <ChartScrollContainer patternId={pattern.id}>
                                {/* K线图 */}
                                <div className="mb-3">
                                  <div className="text-xs text-gray-600 mb-2 font-semibold">K线图 - 红色空心代表上涨，绿色实心代表下跌</div>
                                  <KLineChart
                                    data={pattern.klineData}
                                    patternId={pattern.id}
                                    quantData={pattern.quantitativeData}
                                  />
                                </div>

                                {/* 成交量图 */}
                                <div>
                                  <div className="text-xs text-gray-600 mb-2 font-semibold">成交量</div>
                                  <VolumeChart
                                    data={pattern.klineData}
                                    patternId={pattern.id}
                                    quantData={pattern.quantitativeData}
                                  />
                                </div>
                              </ChartScrollContainer>
                            </div>
                          </div>
                        </div>
                      )}
                    </div>
                  ))}
                </div>
                  </>
                )}
              </div>
            )}

            {/* Tab 3: 推荐股票 */}
            {activeTab === 'predictions' && (
              <div>
                <SimilarityAnalysis />

                {realPredictions.length > 0 ? (
                  <>
                    <div className="mt-8 mb-6 flex items-center justify-between">
                      <div>
                        <h2 className="text-2xl font-bold text-green-600 mb-2">推荐股票可视化</h2>
                        <p className="text-gray-600">
                          以下是AI预测的前10只高概率上涨股票 | 当前第 {currentStockIndex + 1} 只
                        </p>
                      </div>
                      <div className="flex gap-2">
                        <button
                          onClick={handleDownloadPDF}
                          disabled={isDownloading}
                          className="flex items-center gap-2 px-4 py-2 rounded-lg bg-green-600 text-white hover:bg-green-700 disabled:opacity-50 disabled:cursor-not-allowed font-semibold"
                        >
                          <Download className="w-5 h-5" />
                          {isDownloading ? '生成中...' : '下载当前'}
                        </button>
                        <button
                          onClick={handleDownloadAllPDF}
                          disabled={isDownloading}
                          className="flex items-center gap-2 px-4 py-2 rounded-lg bg-blue-600 text-white hover:bg-blue-700 disabled:opacity-50 disabled:cursor-not-allowed font-semibold"
                        >
                          <Download className="w-5 h-5" />
                          {isDownloading ? '生成中...' : '下载全部10只'}
                        </button>
                        <button
                          onClick={() => setCurrentStockIndex(Math.max(0, currentStockIndex - 1))}
                          disabled={currentStockIndex === 0}
                          className="p-2 rounded-lg bg-gray-200 hover:bg-gray-300 disabled:opacity-50 disabled:cursor-not-allowed"
                        >
                          <ChevronLeft className="w-6 h-6" />
                        </button>

                        {/* 页码指示器 */}
                        <div className="flex items-center gap-1 px-3 bg-gray-100 rounded-lg">
                          {Array.from({ length: Math.min(10, realPredictions.length) }).map((_, idx) => (
                            <button
                              key={idx}
                              onClick={() => setCurrentStockIndex(idx)}
                              className={`w-8 h-8 rounded font-semibold transition-colors ${
                                currentStockIndex === idx
                                  ? 'bg-green-600 text-white'
                                  : 'bg-white text-gray-600 hover:bg-gray-200'
                              }`}
                            >
                              {idx + 1}
                            </button>
                          ))}
                        </div>

                        <button
                          onClick={() =>
                            setCurrentStockIndex(
                              Math.min(Math.min(10, realPredictions.length) - 1, currentStockIndex + 1)
                            )
                          }
                          disabled={currentStockIndex === Math.min(10, realPredictions.length) - 1}
                          className="p-2 rounded-lg bg-gray-200 hover:bg-gray-300 disabled:opacity-50 disabled:cursor-not-allowed"
                        >
                          <ChevronRight className="w-6 h-6" />
                        </button>
                      </div>
                    </div>

                    {realPredictions.slice(0, 10)[currentStockIndex] && (
                      <RealStockDetailCard
                        stock={realPredictions.slice(0, 10)[currentStockIndex]}
                        rank={currentStockIndex + 1}
                      />
                    )}
                  </>
                ) : (
                  <>
                    <div className="mt-8 mb-6 flex items-center justify-between">
                      <div>
                        <h2 className="text-2xl font-bold text-green-600 mb-2">推荐股票可视化（示例）</h2>
                        <p className="text-gray-600">
                          以下是模拟的展示效果，共 {MOCK_PREDICTIONS.length} 只 | 当前第 {currentStockIndex + 1} 只
                        </p>
                      </div>
                      <div className="flex gap-2">
                        <button
                          onClick={handleDownloadPDF}
                          disabled={isDownloading}
                          className="flex items-center gap-2 px-4 py-2 rounded-lg bg-blue-600 text-white hover:bg-blue-700 disabled:opacity-50 disabled:cursor-not-allowed font-semibold"
                        >
                          <Download className="w-5 h-5" />
                          {isDownloading ? '生成中...' : '下载PDF'}
                        </button>
                        <button
                          onClick={() => setCurrentStockIndex(Math.max(0, currentStockIndex - 1))}
                          disabled={currentStockIndex === 0}
                          className="p-2 rounded-lg bg-gray-200 hover:bg-gray-300 disabled:opacity-50 disabled:cursor-not-allowed"
                        >
                          <ChevronLeft className="w-6 h-6" />
                        </button>
                        <button
                          onClick={() =>
                            setCurrentStockIndex(
                              Math.min(MOCK_PREDICTIONS.length - 1, currentStockIndex + 1)
                            )
                          }
                          disabled={currentStockIndex === MOCK_PREDICTIONS.length - 1}
                          className="p-2 rounded-lg bg-gray-200 hover:bg-gray-300 disabled:opacity-50 disabled:cursor-not-allowed"
                        >
                          <ChevronRight className="w-6 h-6" />
                        </button>
                      </div>
                    </div>

                    {MOCK_PREDICTIONS[currentStockIndex] && (
                      <StockDetailCard stock={MOCK_PREDICTIONS[currentStockIndex]} />
                    )}
                  </>
                )}
              </div>
            )}
          </div>
        </div>
      </div>
    </div>
  )
}

// 图表滚动容器组件 - 自动滚动到最右边
function ChartScrollContainer({ children, patternId }: { children: React.ReactNode, patternId: number }) {
  const scrollRef = useRef<HTMLDivElement>(null)

  useEffect(() => {
    // 组件挂载后，滚动到最右边
    if (scrollRef.current) {
      scrollRef.current.scrollLeft = scrollRef.current.scrollWidth
    }
  }, [patternId]) // 当patternId变化时，重新滚动到最右边

  return (
    <div ref={scrollRef} className="relative bg-gray-50 rounded-lg p-4">
      {children}
    </div>
  )
}

// K线图组件（改进版 - 30天数据 + 红涨绿跌 + 详细标注）
function KLineChart({
  data,
  patternId,
  quantData
}: {
  data: any[]
  patternId: number
  quantData: any
}) {
  const [hoveredIndex, setHoveredIndex] = useState<number | null>(null)

  const maxHigh = Math.max(...data.map((d) => d.high))
  const minLow = Math.min(...data.map((d) => d.low))
  const priceRange = maxHigh - minLow
  const padding = priceRange * 0.15

  const getY = (price: number) => {
    return ((maxHigh + padding - price) / (priceRange + 2 * padding)) * 200
  }

  // 对于750天数据，使用更合理的宽度计算
  const containerWidth = 1200 // 固定容器宽度（适应灰色背景）
  const leftMargin = 50
  const rightMargin = 80
  const chartWidth = containerWidth - leftMargin - rightMargin
  const xScale = chartWidth / data.length // 均匀分布，铺满容器
  const candleWidth = Math.max(4, Math.min(10, xScale * 0.6)) // 动态宽度4-10px
  const totalWidth = containerWidth

  return (
    <div className="relative">
      <svg width={totalWidth} height="280" viewBox={`0 0 ${totalWidth} 280`} className="overflow-visible">
        {/* 价格网格线 */}
        {[0, 1, 2, 3, 4].map((i) => {
          const price = maxHigh + padding - (priceRange + 2 * padding) * (i / 4)
          return (
            <g key={i}>
              <line
                x1={leftMargin}
                y1={i * 50}
                x2={totalWidth - rightMargin}
                y2={i * 50}
                stroke="#e5e7eb"
                strokeWidth="1"
              />
              <text x="10" y={i * 50 + 5} fontSize="10" fill="#6b7280">
                {price.toFixed(2)}
              </text>
            </g>
          )
        })}

        {/* 动态高亮区域 - 根据quantData.key_days */}
        {quantData && quantData.key_days && (() => {
          // 解析 "最近N天" 格式
          const match = quantData.key_days.match(/最近(\d+)天/)
          if (match) {
            const days = parseInt(match[1])
            const startIndex = Math.max(0, data.length - days)
            const highlightWidth = days * xScale
            const highlightX = leftMargin + startIndex * xScale

            return (
              <g>
                {/* 高亮背景 */}
                <rect
                  x={highlightX}
                  y="0"
                  width={highlightWidth}
                  height="200"
                  fill="#fef3c7"
                  opacity="0.3"
                />
                {/* 标签 */}
                <rect
                  x={highlightX + 5}
                  y="5"
                  width="80"
                  height="18"
                  fill="#fbbf24"
                  opacity="0.9"
                  rx="3"
                />
                <text
                  x={highlightX + 10}
                  y="17"
                  fontSize="11"
                  fontWeight="bold"
                  fill="#fff"
                >
                  {quantData.key_days}
                </text>
              </g>
            )
          }
          return null
        })()}

        {/* 模式1: 缩量回调突破 */}
        {patternId === 1 && (
          <>
            {/* 前期上涨区域标注（在最右侧710-720天的位置） */}
            <rect x={leftMargin + 710 * (candleWidth + 2)} y="5" width={(candleWidth + 2) * 10} height="15" fill="#e0e7ff" opacity="0.7" rx="3" />
            <text x={leftMargin + 710 * (candleWidth + 2) + 5} y="16" fontSize="10" fontWeight="bold" fill="#4f46e5">前期上涨(10天)</text>

            {/* 回调区域标注（在最右侧720-730天的位置） */}
            <rect x={leftMargin + 720 * (candleWidth + 2)} y="5" width={(candleWidth + 2) * 10} height="15" fill="#fef3c7" opacity="0.7" rx="3" />
            <text x={leftMargin + 720 * (candleWidth + 2) + 5} y="16" fontSize="10" fontWeight="bold" fill="#d97706">缩量回调(10天)</text>

            {/* 前高线 */}
            <line
              x1={leftMargin}
              y1={getY(quantData.previousHigh)}
              x2={totalWidth - rightMargin}
              y2={getY(quantData.previousHigh)}
              stroke="#f59e0b"
              strokeWidth="2"
              strokeDasharray="5,5"
            />
            <text x={totalWidth - 150} y={getY(quantData.previousHigh) - 5} fontSize="11" fontWeight="bold" fill="#f59e0b">
              前高 ¥{quantData.previousHigh}
            </text>
          </>
        )}

        {/* 模式2: 跳空缺口 */}
        {patternId === 2 && data[735] && (
          <>
            {/* 缺口标注区域（在735天位置） */}
            <rect
              x={leftMargin + 734 * (candleWidth + 2)}
              y={getY(data[735].low)}
              width={(candleWidth + 2) * 2}
              height={getY(data[734].high) - getY(data[735].low)}
              fill="#06b6d4"
              opacity="0.2"
              stroke="#06b6d4"
              strokeWidth="2"
              strokeDasharray="3,3"
            />
            <line
              x1={leftMargin + 734.5 * (candleWidth + 2)}
              y1={getY(data[734].high)}
              x2={leftMargin + 734.5 * (candleWidth + 2)}
              y2={getY(data[735].low)}
              stroke="#06b6d4"
              strokeWidth="3"
              markerEnd="url(#arrowhead)"
            />
            <text
              x={leftMargin + 735 * (candleWidth + 2) + 10}
              y={(getY(data[734].high) + getY(data[735].low)) / 2}
              fontSize="11"
              fontWeight="bold"
              fill="#06b6d4"
            >
              缺口{quantData.gapSize}%
            </text>
          </>
        )}

        {/* 模式3: 底部横盘 */}
        {patternId === 3 && (
          <>
            {/* 横盘区域（在700-725天位置） */}
            <rect
              x={leftMargin + 700 * (candleWidth + 2)}
              y={getY(Math.max(...data.slice(700, 725).map(d => d.high)))}
              width={(candleWidth + 2) * 25}
              height={getY(Math.min(...data.slice(700, 725).map(d => d.low))) - getY(Math.max(...data.slice(700, 725).map(d => d.high)))}
              fill="#fbbf24"
              opacity="0.1"
              stroke="#f59e0b"
              strokeWidth="2"
              strokeDasharray="5,5"
            />
            <text x={leftMargin + 700 * (candleWidth + 2) + 5} y={getY(Math.max(...data.slice(700, 725).map(d => d.high))) + 12} fontSize="10" fontWeight="bold" fill="#d97706">
              底部横盘25天 振幅{quantData.consolidationRange}%
            </text>
          </>
        )}

        {/* K线蜡烛 */}
        {data.map((candle, index) => {
          const x = leftMargin + index * xScale
          const isGreen = candle.close >= candle.open // 红涨绿跌

          return (
            <g key={index}>
              {/* 影线 */}
              <line
                x1={x}
                y1={getY(candle.high)}
                x2={x}
                y2={getY(candle.low)}
                stroke={isGreen ? '#ef4444' : '#22c55e'}
                strokeWidth="1.5"
              />
              {/* 实体 - 红色空心，绿色实心 */}
              <rect
                x={x - candleWidth / 2}
                y={getY(Math.max(candle.open, candle.close))}
                width={candleWidth}
                height={Math.max(2, Math.abs(getY(candle.close) - getY(candle.open)))}
                fill={isGreen ? '#ffffff' : '#22c55e'}
                stroke={isGreen ? '#ef4444' : '#22c55e'}
                strokeWidth={isGreen ? 1.5 : 0}
                onMouseEnter={() => setHoveredIndex(index)}
                onMouseLeave={() => setHoveredIndex(null)}
                className="cursor-pointer hover:opacity-80 transition-opacity"
              />

              {/* 日期标签（每5天显示） */}
              {index % 5 === 0 && (
                <text
                  x={x}
                  y="260"
                  fill="#6b7280"
                  fontSize="9"
                  textAnchor="middle"
                >
                  {candle.date}
                </text>
              )}

              {/* 突破日特殊标注 */}
              {((patternId === 1 && index === 20) ||
                (patternId === 2 && index === 15) ||
                (patternId === 3 && index === 25)) && (
                <>
                  <circle
                    cx={x}
                    cy={getY(candle.close) - 15}
                    r="10"
                    fill="#8b5cf6"
                    opacity="0.9"
                  />
                  <text
                    x={x}
                    y={getY(candle.close) - 11}
                    fill="white"
                    fontSize="10"
                    fontWeight="bold"
                    textAnchor="middle"
                  >
                    突
                  </text>
                </>
              )}
            </g>
          )
        })}

        {/* 箭头定义 */}
        <defs>
          <marker
            id="arrowhead"
            markerWidth="10"
            markerHeight="10"
            refX="5"
            refY="5"
            orient="auto"
          >
            <polygon points="0 0, 10 5, 0 10" fill="#06b6d4" />
          </marker>
        </defs>
      </svg>

      {/* 悬浮信息 */}
      {hoveredIndex !== null && (
        <div className="absolute top-0 left-0 bg-gray-900 text-white text-xs rounded px-3 py-2 pointer-events-none shadow-lg z-10">
          <div className="font-bold mb-1">{data[hoveredIndex].date}</div>
          <div>开: ¥{data[hoveredIndex].open}</div>
          <div>收: ¥{data[hoveredIndex].close}</div>
          <div>高: ¥{data[hoveredIndex].high}</div>
          <div>低: ¥{data[hoveredIndex].low}</div>
          <div className="mt-1 pt-1 border-t border-gray-700">
            量: {data[hoveredIndex].volume.toLocaleString()}
          </div>
          {/* 显示特征说明（如果在高亮区域内） */}
          {quantData && quantData.key_features && quantData.key_features.length > 0 && (() => {
            const match = quantData.key_days?.match(/最近(\d+)天/)
            if (match) {
              const days = parseInt(match[1])
              const isInHighlight = hoveredIndex >= data.length - days
              if (isInHighlight) {
                return (
                  <div className="mt-2 pt-2 border-t border-yellow-500">
                    <div className="font-bold text-yellow-300 mb-1">关键特征：</div>
                    {quantData.key_features.map((feature: string, idx: number) => (
                      <div key={idx} className="text-yellow-100">• {feature}</div>
                    ))}
                  </div>
                )
              }
            }
            return null
          })()}
        </div>
      )}
    </div>
  )
}

// 成交量图组件（改进版）
function VolumeChart({
  data,
  patternId,
  quantData
}: {
  data: any[]
  patternId: number
  quantData: any
}) {
  const maxVolume = Math.max(...data.map((d) => d.volume))
  const containerWidth = 1200 // 固定容器宽度（适应灰色背景）
  const leftMargin = 50
  const rightMargin = 80
  const chartWidth = containerWidth - leftMargin - rightMargin
  const xScale = chartWidth / data.length // 均匀分布，铺满容器
  const candleWidth = Math.max(4, Math.min(10, xScale * 0.6)) // 动态宽度4-10px
  const totalWidth = containerWidth

  // 计算平均成交量用于标注
  let avgVolume = 0
  if (patternId === 1) {
    avgVolume = quantData.avgVolumeDuring
  } else if (patternId === 2) {
    avgVolume = quantData.avgVolumeBefore
  } else if (patternId === 3) {
    avgVolume = quantData.avgVolumeConsolidation
  }

  return (
    <div className="relative">
      <svg width={totalWidth} height="120" viewBox={`0 0 ${totalWidth} 120`}>
        {/* 平均量参考线 */}
        {avgVolume > 0 && (
          <>
            <line
              x1={leftMargin}
              y1={100 - (avgVolume / maxVolume) * 100}
              x2={totalWidth - rightMargin}
              y2={100 - (avgVolume / maxVolume) * 100}
              stroke="#9ca3af"
              strokeWidth="1"
              strokeDasharray="3,3"
            />
            <text
              x={totalWidth - rightMargin + 10}
              y={100 - (avgVolume / maxVolume) * 100 + 5}
              fontSize="10"
              fill="#6b7280"
            >
              平均{avgVolume.toLocaleString()}
            </text>
          </>
        )}

        {data.map((candle, index) => {
          const x = leftMargin + index * xScale
          const height = (candle.volume / maxVolume) * 100
          const isGreen = candle.close >= candle.open

          // 判断是否是关键成交量（调整到3年数据的相应位置）
          const isBreakoutVolume =
            (patternId === 1 && index === 731) ||
            (patternId === 2 && index === 736) ||
            (patternId === 3 && index === 726)

          const isLowVolume = patternId === 1 && index >= 720 && index < 730

          return (
            <g key={index}>
              <rect
                x={x - candleWidth / 2}
                y={100 - height}
                width={candleWidth}
                height={height}
                fill={
                  isBreakoutVolume
                    ? '#8b5cf6'
                    : isLowVolume
                    ? '#6b7280'
                    : isGreen
                    ? '#ef4444'
                    : '#22c55e'
                }
                opacity={isBreakoutVolume || isLowVolume ? 1 : 0.7}
                className="cursor-pointer hover:opacity-100 transition-opacity"
              />
              {isBreakoutVolume && (
                <text
                  x={x}
                  y={100 - height - 5}
                  fontSize="9"
                  fontWeight="bold"
                  fill="#8b5cf6"
                  textAnchor="middle"
                >
                  {candle.volume.toLocaleString()}
                </text>
              )}
            </g>
          )
        })}
      </svg>
    </div>
  )
}

// 股票详情卡片组件（改进版）
function StockDetailCard({ stock }: { stock: any }) {
  return (
    <div id="stock-detail-card" className="bg-white rounded-2xl border-2 border-green-500 shadow-2xl overflow-hidden">
      {/* 股票头部信息 */}
      <div className="bg-gradient-to-r from-green-500 to-green-600 text-white p-6">
        <div className="flex items-start justify-between">
          <div>
            <div className="text-sm opacity-90 mb-1">#{stock.rank} 推荐</div>
            <h3 className="text-3xl font-bold mb-2">
              {stock.name} ({stock.code})
            </h3>
            <div className="flex items-center gap-4 text-sm">
              <div>
                <span className="opacity-90">当前价格</span>
                <div className="text-2xl font-bold">¥{stock.current_price.toFixed(2)}</div>
              </div>
              <div>
                <span className="opacity-90">上涨概率</span>
                <div className="text-2xl font-bold">{stock.probability.toFixed(1)}%</div>
              </div>
            </div>
          </div>
          <div className="bg-white/20 backdrop-blur-sm rounded-lg px-4 py-2">
            <div className="text-xs opacity-90">匹配模式</div>
            <div className="font-semibold">{stock.matched_pattern}</div>
          </div>
        </div>
      </div>

      {/* 股票图表和分析 */}
      <div className="p-6">
        {/* 量化匹配指标 - 仅在有数据时显示 */}
        {stock.matchedQuantitativeData && (
          <div className="mb-6 bg-green-50 rounded-lg p-4 border-2 border-green-300">
            <h4 className="font-semibold text-green-800 mb-3 flex items-center gap-2">
              <span>📊</span> 量化匹配指标
            </h4>
            <div className="grid grid-cols-3 gap-3">
              {stock.matchedQuantitativeData.consolidationDays && (
                <>
                  <div className="bg-white rounded p-2 border border-green-200">
                    <div className="text-xs text-gray-600">回调天数</div>
                    <div className="text-lg font-bold text-purple-600">{stock.matchedQuantitativeData.consolidationDays}天</div>
                  </div>
                  <div className="bg-white rounded p-2 border border-green-200">
                    <div className="text-xs text-gray-600">回调期成交量</div>
                    <div className="text-lg font-bold text-blue-600">{stock.matchedQuantitativeData.avgVolumeDuring.toLocaleString()}</div>
                    <div className="text-xs text-red-600">↓ 前期{(stock.matchedQuantitativeData.avgVolumeDuring / stock.matchedQuantitativeData.avgVolumeBefore * 100).toFixed(0)}%</div>
                  </div>
                  <div className="bg-white rounded p-2 border border-green-200">
                    <div className="text-xs text-gray-600">突破放量比</div>
                    <div className="text-lg font-bold text-green-600">{stock.matchedQuantitativeData.volumeRatio.toFixed(1)}倍</div>
                  </div>
                </>
              )}
              {stock.matchedQuantitativeData.gapSize && (
                <>
                  <div className="bg-white rounded p-2 border border-green-200">
                    <div className="text-xs text-gray-600">缺口大小</div>
                    <div className="text-lg font-bold text-cyan-600">{stock.matchedQuantitativeData.gapSize}%</div>
                  </div>
                  <div className="bg-white rounded p-2 border border-green-200">
                    <div className="text-xs text-gray-600">放量倍数</div>
                    <div className="text-lg font-bold text-green-600">{stock.matchedQuantitativeData.volumeRatio.toFixed(1)}倍</div>
                  </div>
                  <div className="bg-white rounded p-2 border border-green-200">
                    <div className="text-xs text-gray-600">缺口后天数</div>
                    <div className="text-lg font-bold text-purple-600">{stock.matchedQuantitativeData.daysAfterGap}天</div>
                  </div>
                </>
              )}
            </div>
          </div>
        )}

        {/* 分析理由 */}
        <div className="mb-6 bg-amber-50 rounded-lg p-4 border border-amber-200">
          <h4 className="font-semibold text-amber-900 mb-2">📊 AI分析</h4>
          <p className="text-gray-700 leading-relaxed">{stock.reason}</p>
        </div>

        {/* 最近30天走势 */}
        <div className="mb-4">
          <h4 className="font-semibold text-gray-800 mb-3">近期走势（最近30天完整数据）</h4>

          {/* K线图和成交量图 - 同步滚动 */}
          <div className="bg-gray-50 rounded-lg p-4 border border-gray-200">
            <ChartScrollContainer patternId={stock.rank}>
              {/* K线图 */}
              <div className="mb-3">
                <div className="text-xs text-gray-600 mb-2 font-semibold">K线图 - 红色空心代表上涨，绿色实心代表下跌</div>
                <KLineChart
                  data={stock.klineData}
                  patternId={stock.rank}
                  quantData={stock.matchedQuantitativeData || undefined}
                />
              </div>

              {/* 成交量图 */}
              <div>
                <div className="text-xs text-gray-600 mb-2 font-semibold">成交量</div>
                <VolumeChart
                  data={stock.klineData}
                  patternId={stock.rank}
                  quantData={stock.matchedQuantitativeData || undefined}
                />
              </div>
            </ChartScrollContainer>
          </div>
        </div>
      </div>
    </div>
  )
}

function RealStockDetailCard({ stock, rank }: { stock: any; rank: number }) {
  const [klineData, setKlineData] = useState<any[]>([])
  const [loading, setLoading] = useState(true)

  useEffect(() => {
    const fetchKlineData = async () => {
      try {
        setLoading(true)
        const res = await axios.get(`${API_BASE}/api/stock/${stock.code}/kline?days=90`)
        if (res.data && res.data.data) {
          setKlineData(res.data.data)
        }
      } catch (error) {
        console.error('获取K线数据失败', error)
      } finally {
        setLoading(false)
      }
    }

    fetchKlineData()
  }, [stock.code])

  // 从 reason 中提取特征
  const extractFeatures = (reason: string): string[] => {
    const features: string[] = []

    // 简单的特征提取逻辑
    if (reason.includes('连续') || reason.includes('阳线')) features.push('连续上涨形态')
    if (reason.includes('放量') || reason.includes('成交量')) features.push('成交量放大')
    if (reason.includes('突破') || reason.includes('压力')) features.push('突破关键位置')
    if (reason.includes('回调') || reason.includes('整理')) features.push('回调后启动')
    if (reason.includes('温和') || reason.includes('稳定')) features.push('稳定上涨')

    if (features.length === 0) features.push('技术形态良好')

    return features
  }

  const features = extractFeatures(stock.reason)

  // 构建quantData用于K线高亮
  const quantData = {
    key_days: '最近3天',
    key_features: features
  }

  return (
    <div id="stock-detail-card" className="bg-white rounded-2xl border-2 border-green-500 shadow-2xl overflow-hidden">
      {/* 股票头部信息 */}
      <div className="bg-gradient-to-r from-green-500 to-green-600 text-white p-6">
        <div className="flex items-start justify-between">
          <div>
            <div className="text-sm opacity-90 mb-1">#{rank} 推荐</div>
            <h3 className="text-3xl font-bold mb-2">
              {stock.name === stock.code ? stock.code : `${stock.name} (${stock.code})`}
            </h3>
            <div className="flex items-center gap-4 text-sm">
              <div>
                <span className="opacity-90">当前价格</span>
                <div className="text-2xl font-bold">¥{stock.current_price?.toFixed(2) || 'N/A'}</div>
              </div>
              <div>
                <span className="opacity-90">上涨概率</span>
                <div className="text-2xl font-bold">{stock.probability?.toFixed(1)}%</div>
              </div>
            </div>
          </div>
          <div className="bg-white/20 backdrop-blur-sm rounded-lg px-4 py-2">
            <div className="text-xs opacity-90">数据日期</div>
            <div className="font-semibold">{stock.last_date || 'N/A'}</div>
          </div>
        </div>
      </div>

      {/* 股票图表和分析 */}
      <div className="p-6">
        {/* 量化指标 */}
        <div className="mb-6 bg-amber-50 rounded-lg p-4 border-2 border-amber-200">
          <h4 className="text-lg font-semibold text-amber-900 mb-3 flex items-center gap-2">
            <span>📊</span> 量化指标（AI分析依据）
          </h4>
          <div className="grid grid-cols-2 gap-3">
            <div className="bg-white rounded p-3 border border-amber-200">
              <div className="text-xs text-gray-600">股票代码</div>
              <div className="text-xl font-bold text-blue-600">{stock.code}</div>
            </div>
            <div className="bg-white rounded p-3 border border-amber-200">
              <div className="text-xs text-gray-600">当前价格</div>
              <div className="text-xl font-bold text-green-600">¥{stock.current_price?.toFixed(2)}</div>
            </div>
            <div className="bg-white rounded p-3 border border-amber-200">
              <div className="text-xs text-gray-600">上涨概率</div>
              <div className="text-xl font-bold text-purple-600">{stock.probability?.toFixed(1)}%</div>
            </div>
            <div className="bg-white rounded p-3 border border-amber-200">
              <div className="text-xs text-gray-600">数据日期</div>
              <div className="text-sm font-semibold text-gray-700">{stock.last_date || 'N/A'}</div>
            </div>
          </div>
        </div>

        {/* 核心特征 */}
        <div className="mb-6">
          <h4 className="text-lg font-semibold text-gray-800 mb-3">核心特征</h4>
          <div className="grid grid-cols-2 gap-3">
            {features.map((feature: string, i: number) => (
              <div
                key={i}
                className="flex items-start gap-2 bg-purple-50 rounded-lg p-3 border border-purple-200"
              >
                <span className="text-purple-600 font-bold">✓</span>
                <span className="text-sm text-gray-700 font-medium">{feature}</span>
              </div>
            ))}
          </div>
        </div>

        {/* AI分析 */}
        <div className="mb-6 bg-blue-50 rounded-lg p-4 border border-blue-200">
          <h4 className="font-semibold text-blue-900 mb-2">🤖 AI分析</h4>
          <p className="text-gray-700 leading-relaxed">{stock.reason}</p>
        </div>

        {/* K线图 */}
        {loading ? (
          <div className="bg-gray-50 rounded-lg p-8 border border-gray-200 text-center">
            <div className="text-gray-600">加载K线数据中...</div>
          </div>
        ) : klineData.length > 0 ? (
          <div className="mb-4">
            <h4 className="font-semibold text-gray-800 mb-3">近期走势（最近90天）</h4>
            <div className="bg-gray-50 rounded-lg p-4 border border-gray-200">
              <ChartScrollContainer patternId={rank}>
                <div className="mb-3">
                  <div className="text-xs text-gray-600 mb-2 font-semibold">K线图 - 红色空心代表上涨，绿色实心代表下跌</div>
                  <KLineChart
                    data={klineData}
                    patternId={rank}
                    quantData={quantData}
                  />
                </div>
                <div>
                  <div className="text-xs text-gray-600 mb-2 font-semibold">成交量</div>
                  <VolumeChart
                    data={klineData}
                    patternId={rank}
                    quantData={quantData}
                  />
                </div>
              </ChartScrollContainer>
            </div>
          </div>
        ) : (
          <div className="bg-gray-50 rounded-lg p-8 border border-gray-200 text-center">
            <div className="text-gray-600">暂无K线数据</div>
          </div>
        )}
      </div>
    </div>
  )
}
