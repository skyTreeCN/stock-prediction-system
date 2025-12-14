'use client'

import { useState, useEffect } from 'react'
import axios from 'axios'

const API_BASE = 'http://localhost:8000'

interface Prediction {
  code: string
  name: string
  probability: number
  reason: string
  current_price: number
  last_date: string
}

export default function SimilarityAnalysis() {
  const [loading, setLoading] = useState(false)
  const [status, setStatus] = useState('')
  const [progress, setProgress] = useState(0)
  const [predictions, setPredictions] = useState<Prediction[]>([])

  // 获取预测结果
  const fetchPredictions = async () => {
    try {
      const res = await axios.get(`${API_BASE}/api/predictions`)
      setPredictions(res.data)
    } catch (error) {
      console.error('获取预测结果失败', error)
    }
  }

  // 轮询任务状态
  const pollTaskStatus = async () => {
    try {
      const res = await axios.get(`${API_BASE}/api/task-status/predict`)
      if (res.data.success) {
        const taskData = res.data.data
        setStatus(taskData.message)
        setProgress(taskData.progress)
        setLoading(taskData.running)

        if (!taskData.running && taskData.progress === 100) {
          fetchPredictions()
        }

        return taskData.running
      }
    } catch (error) {
      return false
    }
  }

  useEffect(() => {
    if (loading) {
      const interval = setInterval(async () => {
        const isRunning = await pollTaskStatus()
        if (!isRunning) {
          clearInterval(interval)
        }
      }, 3000)

      return () => clearInterval(interval)
    }
  }, [loading])

  const handlePredict = async () => {
    try {
      setLoading(true)
      setPredictions([])
      const res = await axios.post(`${API_BASE}/api/predict`)

      if (res.data.success) {
        setStatus('预测任务已启动')
      }
    } catch (error: any) {
      setStatus('错误: ' + error.message)
      setLoading(false)
    }
  }

  const getProbabilityColor = (prob: number) => {
    if (prob >= 90) return 'text-red-600 font-bold'
    if (prob >= 80) return 'text-orange-600 font-semibold'
    if (prob >= 70) return 'text-yellow-600 font-semibold'
    return 'text-green-600'
  }

  return (
    <div className="bg-white rounded-lg shadow-md p-6">
      <h2 className="text-xl font-bold mb-4 text-purple-600">区域3：相似性分析与预测</h2>

      <div className="mb-4">
        <button
          onClick={handlePredict}
          disabled={loading}
          className={`px-6 py-3 rounded-lg font-semibold text-white ${
            loading
              ? 'bg-gray-400 cursor-not-allowed'
              : 'bg-purple-600 hover:bg-purple-700'
          }`}
        >
          {loading ? '预测中...' : '开始预测'}
        </button>
      </div>

      {status && (
        <div className="mb-4 p-3 bg-purple-50 rounded">
          <p className="text-sm text-gray-700">{status}</p>
          {loading && progress > 0 && (
            <div className="mt-2 w-full bg-gray-200 rounded-full h-2">
              <div
                className="bg-purple-600 h-2 rounded-full transition-all"
                style={{ width: `${progress}%` }}
              />
            </div>
          )}
        </div>
      )}

      {predictions.length > 0 && (
        <div className="mt-4">
          <h3 className="font-semibold mb-3">
            预测结果（前{predictions.length}只股票）：
          </h3>
          <div className="overflow-x-auto">
            <table className="min-w-full text-sm">
              <thead className="bg-gray-100">
                <tr>
                  <th className="px-4 py-2 text-left">排名</th>
                  <th className="px-4 py-2 text-left">股票代码</th>
                  <th className="px-4 py-2 text-left">股票名称</th>
                  <th className="px-4 py-2 text-left">当前价格</th>
                  <th className="px-4 py-2 text-left">数据日期</th>
                  <th className="px-4 py-2 text-left">上涨概率</th>
                  <th className="px-4 py-2 text-left">原因</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-gray-200">
                {predictions.map((pred, idx) => (
                  <tr key={idx} className="hover:bg-gray-50">
                    <td className="px-4 py-2">{idx + 1}</td>
                    <td className="px-4 py-2 font-mono">{pred.code}</td>
                    <td className="px-4 py-2">{pred.name}</td>
                    <td className="px-4 py-2">¥{pred.current_price.toFixed(2)}</td>
                    <td className="px-4 py-2 text-gray-600 text-xs">{pred.last_date || 'N/A'}</td>
                    <td className={`px-4 py-2 ${getProbabilityColor(pred.probability)}`}>
                      {pred.probability.toFixed(1)}%
                    </td>
                    <td className="px-4 py-2 text-gray-600">{pred.reason}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </div>
      )}

      <div className="mt-4 text-xs text-gray-500">
        <p>说明：基于最近1个月的K线数据与上涨模式进行相似度匹配</p>
        <p>预计需要3-10分钟，会调用Claude API</p>
        <p className="text-red-500 font-semibold mt-1">
          ⚠️ 免责声明：预测结果仅供参考，不构成投资建议
        </p>
      </div>
    </div>
  )
}
