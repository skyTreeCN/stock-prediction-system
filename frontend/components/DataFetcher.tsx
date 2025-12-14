'use client'

import { useState, useEffect } from 'react'
import axios from 'axios'

const API_BASE = 'http://localhost:8000'

export default function DataFetcher() {
  const [loading, setLoading] = useState(false)
  const [poolLoading, setPoolLoading] = useState(false)
  const [status, setStatus] = useState('')
  const [poolStatus, setPoolStatus] = useState('')
  const [progress, setProgress] = useState(0)
  const [poolProgress, setPoolProgress] = useState(0)
  const [stats, setStats] = useState<any>(null)
  const [poolStats, setPoolStats] = useState<any>(null)

  // 获取数据统计
  const fetchStats = async () => {
    try {
      const res = await axios.get(`${API_BASE}/api/statistics`)
      if (res.data.success) {
        setStats(res.data.data)
      }
    } catch (error) {
      console.error('获取统计信息失败', error)
    }
  }

  // 获取股票池统计
  const fetchPoolStats = async () => {
    try {
      const res = await axios.get(`${API_BASE}/api/stock-pool/status`)
      if (res.data.success) {
        setPoolStats(res.data)
      }
    } catch (error) {
      console.error('获取股票池信息失败', error)
    }
  }

  // 轮询任务状态
  const pollTaskStatus = async () => {
    try {
      const res = await axios.get(`${API_BASE}/api/task-status/fetch_data`)
      if (res.data.success) {
        const taskData = res.data.data
        setStatus(taskData.message)
        setProgress(taskData.progress)
        setLoading(taskData.running)

        if (!taskData.running && taskData.progress === 100) {
          fetchStats()
        }

        return taskData.running
      }
    } catch (error) {
      return false
    }
  }

  // 轮询股票池更新状态
  const pollPoolStatus = async () => {
    try {
      const res = await axios.get(`${API_BASE}/api/task-status/update_pool`)
      if (res.data.success) {
        const taskData = res.data.data
        setPoolStatus(taskData.message)
        setPoolProgress(taskData.progress)
        setPoolLoading(taskData.running)

        if (!taskData.running && taskData.progress === 100) {
          fetchPoolStats()
        }

        return taskData.running
      }
    } catch (error) {
      return false
    }
  }

  useEffect(() => {
    fetchStats()
    fetchPoolStats()
  }, [])

  useEffect(() => {
    if (loading) {
      const interval = setInterval(async () => {
        const isRunning = await pollTaskStatus()
        if (!isRunning) {
          clearInterval(interval)
        }
      }, 2000)

      return () => clearInterval(interval)
    }
  }, [loading])

  useEffect(() => {
    if (poolLoading) {
      const interval = setInterval(async () => {
        const isRunning = await pollPoolStatus()
        if (!isRunning) {
          clearInterval(interval)
        }
      }, 2000)

      return () => clearInterval(interval)
    }
  }, [poolLoading])

  const handleUpdatePool = async () => {
    try {
      setPoolLoading(true)
      const res = await axios.post(`${API_BASE}/api/stock-pool/update`)

      if (res.data.success) {
        setPoolStatus('任务已启动')
      }
    } catch (error: any) {
      setPoolStatus('错误: ' + error.message)
      setPoolLoading(false)
    }
  }

  const handleFetchData = async () => {
    try {
      setLoading(true)
      const res = await axios.post(`${API_BASE}/api/fetch-data`, {
        years: 5
      })

      if (res.data.success) {
        setStatus('任务已启动')
      }
    } catch (error: any) {
      setStatus('错误: ' + error.message)
      setLoading(false)
    }
  }

  return (
    <div className="bg-white rounded-lg shadow-md p-6">
      <h2 className="text-xl font-bold mb-4 text-blue-600">区域1：数据获取</h2>

      {/* 步骤1: 更新股票池 */}
      <div className="mb-6">
        <h3 className="font-semibold mb-2 text-gray-700">步骤1：更新股票池</h3>
        <button
          onClick={handleUpdatePool}
          disabled={poolLoading}
          className={`px-6 py-3 rounded-lg font-semibold text-white ${
            poolLoading
              ? 'bg-gray-400 cursor-not-allowed'
              : 'bg-green-600 hover:bg-green-700'
          }`}
        >
          {poolLoading ? '更新中...' : '获取上证成分股列表'}
        </button>

        {poolStatus && (
          <div className="mt-3 p-3 bg-green-50 rounded">
            <p className="text-sm text-gray-700">{poolStatus}</p>
            {poolLoading && poolProgress > 0 && (
              <div className="mt-2 w-full bg-gray-200 rounded-full h-2">
                <div
                  className="bg-green-600 h-2 rounded-full transition-all"
                  style={{ width: `${poolProgress}%` }}
                />
              </div>
            )}
          </div>
        )}

        {poolStats && (
          <div className="mt-3 p-3 bg-gray-50 rounded text-sm">
            <span className="text-gray-600">股票池：</span>
            <span className="font-semibold">
              {poolStats.is_empty ? '空' : `${poolStats.count} 只股票`}
            </span>
          </div>
        )}
      </div>

      {/* 步骤2: 获取K线数据 */}
      <div className="mb-4">
        <h3 className="font-semibold mb-2 text-gray-700">步骤2：获取K线数据</h3>
        <button
          onClick={handleFetchData}
          disabled={loading || (poolStats && poolStats.is_empty)}
          className={`px-6 py-3 rounded-lg font-semibold text-white ${
            loading || (poolStats && poolStats.is_empty)
              ? 'bg-gray-400 cursor-not-allowed'
              : 'bg-blue-600 hover:bg-blue-700'
          }`}
        >
          {loading ? '获取中...' : '获取股票K线数据'}
        </button>

        {poolStats && poolStats.is_empty && (
          <p className="mt-2 text-sm text-red-600">请先完成步骤1</p>
        )}
      </div>

      {status && (
        <div className="mb-4 p-3 bg-blue-50 rounded">
          <p className="text-sm text-gray-700">{status}</p>
          {loading && progress > 0 && (
            <div className="mt-2 w-full bg-gray-200 rounded-full h-2">
              <div
                className="bg-blue-600 h-2 rounded-full transition-all"
                style={{ width: `${progress}%` }}
              />
            </div>
          )}
        </div>
      )}

      {stats && (
        <div className="mt-4 p-4 bg-gray-50 rounded">
          <h3 className="font-semibold mb-2">数据统计</h3>
          <div className="grid grid-cols-2 gap-2 text-sm">
            <div>
              <span className="text-gray-600">股票数量：</span>
              <span className="font-semibold">{stats.stock_count}</span>
            </div>
            <div>
              <span className="text-gray-600">数据记录：</span>
              <span className="font-semibold">{stats.record_count}</span>
            </div>
            <div className="col-span-2">
              <span className="text-gray-600">日期范围：</span>
              <span className="font-semibold">
                {stats.date_from} ~ {stats.date_to}
              </span>
            </div>
          </div>
        </div>
      )}

      <div className="mt-4 text-xs text-gray-500">
        <p>说明：</p>
        <p>步骤1：获取上证50/180/380成分股代码</p>
        <p>步骤2：根据股票池获取最近5年K线数据（预计10-30分钟）</p>
      </div>
    </div>
  )
}
