'use client'

import { useState, useEffect } from 'react'
import axios from 'axios'

const API_BASE = 'http://localhost:8000'

interface Pattern {
  pattern_name: string
  description: string
  characteristics: string[]
}

export default function DataAnalyzer() {
  const [loading, setLoading] = useState(false)
  const [status, setStatus] = useState('')
  const [progress, setProgress] = useState(0)
  const [patterns, setPatterns] = useState<Pattern[]>([])

  // AI训练工作流状态
  const [trainingLoading, setTrainingLoading] = useState(false)
  const [trainingStatus, setTrainingStatus] = useState('')
  const [trainingProgress, setTrainingProgress] = useState(0)
  const [currentTrainingTask, setCurrentTrainingTask] = useState('')
  const [trainingResults, setTrainingResults] = useState<any>(null)

  // 各步骤完成状态
  const [stepResults, setStepResults] = useState<any>({
    filter: null,
    extract: null,
    cluster: null,
    patterns: null,
    validation: null
  })

  // 获取已识别的模式
  const fetchPatterns = async () => {
    try {
      const res = await axios.get(`${API_BASE}/api/patterns`)
      setPatterns(res.data)
    } catch (error) {
      console.error('获取模式失败', error)
    }
  }

  useEffect(() => {
    fetchPatterns()
  }, [])

  // 轮询任务状态
  const pollStatus = async () => {
    try {
      const res = await axios.get(`${API_BASE}/api/analyze-status`)
      if (res.data.success) {
        setStatus(res.data.data.message)
        setProgress(res.data.data.progress)
        setLoading(res.data.data.running)

        if (!res.data.data.running && res.data.data.progress === 100) {
          await fetchPatterns()
        }

        return res.data.data.running
      }
    } catch (error) {
      return false
    }
  }

  useEffect(() => {
    if (loading) {
      const interval = setInterval(async () => {
        const isRunning = await pollStatus()
        if (!isRunning) {
          clearInterval(interval)
        }
      }, 2000)

      return () => clearInterval(interval)
    }
  }, [loading])

  // 轮询训练任务状态
  const pollTrainingStatus = async (taskName: string) => {
    try {
      const res = await axios.get(`${API_BASE}/api/training/task-status/${taskName}`)
      if (res.data.success) {
        const taskData = res.data.data
        setTrainingStatus(taskData.message)
        setTrainingProgress(taskData.progress)
        setTrainingLoading(taskData.running)

        if (!taskData.running && taskData.progress === 100) {
          // 任务完成，获取结果并保存到对应步骤
          if (taskName === 'filter_special_samples') {
            const resultRes = await axios.get(`${API_BASE}/api/training/results/special-samples`)
            setStepResults((prev: any) => ({ ...prev, filter: resultRes.data }))
          } else if (taskName === 'extract_ai_patterns') {
            const resultRes = await axios.get(`${API_BASE}/api/training/results/ai-patterns`)
            setStepResults((prev: any) => ({ ...prev, patterns: resultRes.data }))
          } else if (taskName === 'validate_patterns') {
            const resultRes = await axios.get(`${API_BASE}/api/training/results/pattern-validation`)
            setStepResults((prev: any) => ({ ...prev, validation: resultRes.data }))
          }
        }

        return taskData.running
      }
    } catch (error) {
      return false
    }
  }

  useEffect(() => {
    if (trainingLoading && currentTrainingTask) {
      const interval = setInterval(async () => {
        const isRunning = await pollTrainingStatus(currentTrainingTask)
        if (!isRunning) {
          clearInterval(interval)
        }
      }, 2000)

      return () => clearInterval(interval)
    }
  }, [trainingLoading, currentTrainingTask])

  const handleAnalyze = async () => {
    try {
      setLoading(true)
      const res = await axios.post(`${API_BASE}/api/analyze`, {
        pattern_count: 2000
      })

      if (res.data.success) {
        setStatus('分析任务已启动')
      }
    } catch (error: any) {
      setStatus('错误: ' + error.message)
      setLoading(false)
    }
  }

  // AI训练工作流步骤1：过滤特殊样本
  const handleFilterSamples = async () => {
    try {
      setTrainingLoading(true)
      setCurrentTrainingTask('filter_special_samples')
      const res = await axios.post(`${API_BASE}/api/training/filter-special-samples`, {
        sample_count: 300
      })

      if (res.data.success) {
        setTrainingStatus('过滤任务已启动')
      }
    } catch (error: any) {
      setTrainingStatus('错误: ' + error.message)
      setTrainingLoading(false)
    }
  }

  // AI训练工作流步骤2：提取特征向量
  const handleExtractFeatures = async () => {
    try {
      setTrainingLoading(true)
      setCurrentTrainingTask('extract_features')
      const res = await axios.post(`${API_BASE}/api/training/extract-features`)

      if (res.data.success) {
        setTrainingStatus('特征提取任务已启动')
      }
    } catch (error: any) {
      setTrainingStatus('错误: ' + error.message)
      setTrainingLoading(false)
    }
  }

  // AI训练工作流步骤3：K-means聚类
  const handleClusterSamples = async () => {
    try {
      setTrainingLoading(true)
      setCurrentTrainingTask('cluster_samples')
      const res = await axios.post(`${API_BASE}/api/training/cluster-samples`)

      if (res.data.success) {
        setTrainingStatus('聚类任务已启动')
      }
    } catch (error: any) {
      setTrainingStatus('错误: ' + error.message)
      setTrainingLoading(false)
    }
  }

  // AI训练工作流步骤4：AI提取模式
  const handleExtractPatterns = async () => {
    try {
      setTrainingLoading(true)
      setCurrentTrainingTask('extract_ai_patterns')
      const res = await axios.post(`${API_BASE}/api/training/extract-ai-patterns`)

      if (res.data.success) {
        setTrainingStatus('AI模式提取任务已启动')
      }
    } catch (error: any) {
      setTrainingStatus('错误: ' + error.message)
      setTrainingLoading(false)
    }
  }

  // 模式验证
  const handleValidatePatterns = async () => {
    try {
      setTrainingLoading(true)
      setCurrentTrainingTask('validate_patterns')
      const res = await axios.post(`${API_BASE}/api/training/validate-patterns`)

      if (res.data.success) {
        setTrainingStatus('模式验证任务已启动')
      }
    } catch (error: any) {
      setTrainingStatus('错误: ' + error.message)
      setTrainingLoading(false)
    }
  }

  return (
    <div className="bg-white rounded-lg shadow-md p-6">
      <h2 className="text-2xl font-bold mb-6 text-green-600">📊 区域2：模式分析与训练</h2>

      {/* 说明文字 */}
      <div className="mb-6 p-4 bg-gray-50 rounded-lg border-l-4 border-gray-400">
        <p className="text-sm text-gray-700">
          <strong>功能说明：</strong>本区域用于识别股票上涨模式。包含两种方式：
        </p>
        <ul className="text-sm text-gray-600 mt-2 ml-4 space-y-1">
          <li>• <strong>方式1 (经典分析)</strong>：使用AI直接分析历史上涨案例，提取经典模式</li>
          <li>• <strong>方式2 (AI训练流程)</strong>：过滤→特征提取→聚类→AI分析，发现非经典的特殊模式</li>
          <li>• <strong>模式验证</strong>：用历史数据验证模式的有效性 (预测准确率)</li>
        </ul>
      </div>

      {/* 方式1: 经典模式分析 */}
      <div className="mb-6 p-5 bg-gradient-to-r from-green-50 to-green-100 rounded-lg border border-green-300">
        <div className="flex items-center justify-between mb-3">
          <div>
            <h3 className="text-lg font-bold text-green-800 flex items-center gap-2">
              🎯 方式1：经典模式分析
            </h3>
            <p className="text-xs text-gray-600 mt-1">直接使用AI分析2000个历史上涨案例，提取共性模式</p>
          </div>
          <button
            onClick={handleAnalyze}
            disabled={loading}
            className={`px-6 py-3 rounded-lg font-semibold text-white transition-all ${
              loading
                ? 'bg-gray-400 cursor-not-allowed'
                : 'bg-green-600 hover:bg-green-700 hover:shadow-lg'
            }`}
          >
            {loading ? '分析中...' : '开始分析'}
          </button>
        </div>

        {/* 状态显示 */}
        {status && (
          <div className="mt-3 p-3 bg-white rounded border border-green-200">
            <p className="text-sm text-gray-700">{status}</p>
            {loading && progress > 0 && (
              <div className="mt-2 w-full bg-gray-200 rounded-full h-2">
                <div
                  className="bg-green-600 h-2 rounded-full transition-all"
                  style={{ width: `${progress}%` }}
                />
              </div>
            )}
          </div>
        )}
      </div>

      {/* 方式2: AI训练工作流 */}
      <div className="mb-6 p-5 bg-gradient-to-r from-blue-50 to-blue-100 rounded-lg border border-blue-300">
        <div className="mb-4">
          <h3 className="text-lg font-bold text-blue-800 flex items-center gap-2">
            🤖 方式2：AI模式训练工作流
          </h3>
          <p className="text-xs text-gray-600 mt-1">
            4步流程：发现经典分析无法识别的特殊上涨模式（需按顺序执行）
          </p>
        </div>

        <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
          {/* 步骤1 */}
          <div className="bg-white p-4 rounded-lg border border-blue-200">
            <div className="flex items-start justify-between mb-2">
              <div>
                <h4 className="font-semibold text-blue-700 text-sm">步骤1：过滤特殊样本</h4>
                <p className="text-xs text-gray-500 mt-1">排除匹配经典模式的样本</p>
              </div>
              {stepResults.filter && (
                <span className="text-xs bg-green-100 text-green-700 px-2 py-1 rounded">✓ 已完成</span>
              )}
            </div>
            <button
              onClick={handleFilterSamples}
              disabled={trainingLoading}
              className={`w-full mt-2 px-4 py-2 rounded-lg font-semibold text-white text-sm ${
                trainingLoading
                  ? 'bg-gray-400 cursor-not-allowed'
                  : 'bg-blue-600 hover:bg-blue-700'
              }`}
            >
              {trainingLoading && currentTrainingTask === 'filter_special_samples' ? '处理中...' : '开始过滤'}
            </button>
            {stepResults.filter && (
              <p className="text-xs text-gray-600 mt-2">
                结果: 特殊样本 {stepResults.filter.count} 个
              </p>
            )}
          </div>

          {/* 步骤2 */}
          <div className="bg-white p-4 rounded-lg border border-blue-200">
            <div className="flex items-start justify-between mb-2">
              <div>
                <h4 className="font-semibold text-blue-700 text-sm">步骤2：提取特征向量</h4>
                <p className="text-xs text-gray-500 mt-1">计算波动率、成交量等数值特征</p>
              </div>
              {stepResults.extract && (
                <span className="text-xs bg-green-100 text-green-700 px-2 py-1 rounded">✓ 已完成</span>
              )}
            </div>
            <button
              onClick={handleExtractFeatures}
              disabled={trainingLoading}
              className={`w-full mt-2 px-4 py-2 rounded-lg font-semibold text-white text-sm ${
                trainingLoading
                  ? 'bg-gray-400 cursor-not-allowed'
                  : 'bg-blue-600 hover:bg-blue-700'
              }`}
            >
              {trainingLoading && currentTrainingTask === 'extract_features' ? '处理中...' : '开始提取'}
            </button>
          </div>

          {/* 步骤3 */}
          <div className="bg-white p-4 rounded-lg border border-blue-200">
            <div className="flex items-start justify-between mb-2">
              <div>
                <h4 className="font-semibold text-blue-700 text-sm">步骤3：K-means聚类</h4>
                <p className="text-xs text-gray-500 mt-1">将相似样本归类成簇</p>
              </div>
              {stepResults.cluster && (
                <span className="text-xs bg-green-100 text-green-700 px-2 py-1 rounded">✓ 已完成</span>
              )}
            </div>
            <button
              onClick={handleClusterSamples}
              disabled={trainingLoading}
              className={`w-full mt-2 px-4 py-2 rounded-lg font-semibold text-white text-sm ${
                trainingLoading
                  ? 'bg-gray-400 cursor-not-allowed'
                  : 'bg-blue-600 hover:bg-blue-700'
              }`}
            >
              {trainingLoading && currentTrainingTask === 'cluster_samples' ? '处理中...' : '开始聚类'}
            </button>
          </div>

          {/* 步骤4 */}
          <div className="bg-white p-4 rounded-lg border border-blue-200">
            <div className="flex items-start justify-between mb-2">
              <div>
                <h4 className="font-semibold text-blue-700 text-sm">步骤4：AI提取模式</h4>
                <p className="text-xs text-gray-500 mt-1">分析各簇并总结上涨模式</p>
              </div>
              {stepResults.patterns && (
                <span className="text-xs bg-green-100 text-green-700 px-2 py-1 rounded">✓ 已完成</span>
              )}
            </div>
            <button
              onClick={handleExtractPatterns}
              disabled={trainingLoading}
              className={`w-full mt-2 px-4 py-2 rounded-lg font-semibold text-white text-sm ${
                trainingLoading
                  ? 'bg-gray-400 cursor-not-allowed'
                  : 'bg-blue-600 hover:bg-blue-700'
              }`}
            >
              {trainingLoading && currentTrainingTask === 'extract_ai_patterns' ? '分析中...' : '开始提取'}
            </button>
            {stepResults.patterns && stepResults.patterns.patterns && (
              <p className="text-xs text-gray-600 mt-2">
                结果: 发现 {stepResults.patterns.patterns.length} 个新模式
              </p>
            )}
          </div>
        </div>

        {/* 工作流状态 */}
        {trainingStatus && (
          <div className="mt-4 p-3 bg-white rounded border border-blue-200">
            <p className="text-sm text-gray-700">{trainingStatus}</p>
            {trainingLoading && trainingProgress > 0 && (
              <div className="mt-2 w-full bg-gray-200 rounded-full h-2">
                <div
                  className="bg-blue-600 h-2 rounded-full transition-all"
                  style={{ width: `${trainingProgress}%` }}
                />
              </div>
            )}
          </div>
        )}
      </div>

      {/* 模式验证区域 */}
      <div className="mb-6 p-5 bg-gradient-to-r from-purple-50 to-purple-100 rounded-lg border border-purple-300">
        <div className="flex items-center justify-between mb-3">
          <div>
            <h3 className="text-lg font-bold text-purple-800 flex items-center gap-2">
              ✅ 模式验证
            </h3>
            <p className="text-xs text-gray-600 mt-1">
              使用历史数据验证模式有效性 (聚类降维法：2000样本→12簇→60代表→AI批量匹配)
            </p>
          </div>
          <button
            onClick={handleValidatePatterns}
            disabled={trainingLoading}
            className={`px-6 py-3 rounded-lg font-semibold text-white transition-all ${
              trainingLoading
                ? 'bg-gray-400 cursor-not-allowed'
                : 'bg-purple-600 hover:bg-purple-700 hover:shadow-lg'
            }`}
          >
            {trainingLoading && currentTrainingTask === 'validate_patterns' ? '验证中...' : '开始验证'}
          </button>
        </div>

        {/* 验证结果 */}
        {stepResults.validation && stepResults.validation.data && (
          <div className="mt-4 p-4 bg-white rounded border border-purple-200">
            <h4 className="font-semibold text-purple-700 mb-3">验证结果摘要</h4>
            <div className="grid grid-cols-3 gap-4 mb-3 text-center">
              <div className="p-2 bg-purple-50 rounded">
                <p className="text-xs text-gray-600">总快照数</p>
                <p className="text-lg font-bold text-purple-700">
                  {stepResults.validation.data.metadata.total_snapshots}
                </p>
              </div>
              <div className="p-2 bg-purple-50 rounded">
                <p className="text-xs text-gray-600">聚类数</p>
                <p className="text-lg font-bold text-purple-700">
                  {stepResults.validation.data.metadata.n_clusters}
                </p>
              </div>
              <div className="p-2 bg-purple-50 rounded">
                <p className="text-xs text-gray-600">代表样本</p>
                <p className="text-lg font-bold text-purple-700">
                  {stepResults.validation.data.metadata.n_representatives}
                </p>
              </div>
            </div>

            <div className="space-y-2 max-h-60 overflow-y-auto">
              {stepResults.validation.data.validation_summary.map((result: any, idx: number) => (
                <div
                  key={idx}
                  className={`p-3 rounded border ${result.is_valid ? 'bg-green-50 border-green-300' : 'bg-red-50 border-red-300'}`}
                >
                  <div className="flex justify-between items-center">
                    <h5 className="font-semibold text-sm">{result.pattern_name}</h5>
                    <span className={`text-xs px-3 py-1 rounded font-bold ${result.is_valid ? 'bg-green-200 text-green-800' : 'bg-red-200 text-red-800'}`}>
                      {result.is_valid ? '✓ 有效' : '✗ 无效'}
                    </span>
                  </div>
                  <div className="grid grid-cols-3 gap-2 mt-2 text-xs text-gray-700">
                    <div>
                      <span className="text-gray-500">匹配样本:</span> <strong>{result.total_matches}</strong>
                    </div>
                    <div>
                      <span className="text-gray-500">准确率:</span> <strong className={result.success_rate >= 0.4 ? 'text-green-600' : 'text-red-600'}>
                        {(result.success_rate * 100).toFixed(1)}%
                      </strong>
                    </div>
                    <div>
                      <span className="text-gray-500">平均涨幅:</span> <strong>{(result.avg_rise * 100).toFixed(2)}%</strong>
                    </div>
                  </div>
                </div>
              ))}
            </div>
          </div>
        )}
      </div>

      {/* 已识别模式列表 (折叠式) */}
      {patterns.length > 0 && (
        <div className="mt-6 p-5 bg-gray-50 rounded-lg border border-gray-300">
          <h3 className="text-lg font-bold mb-3 text-gray-800">📋 已识别的上涨模式 ({patterns.length})</h3>
          <div className="space-y-3 max-h-96 overflow-y-auto">
            {patterns.map((pattern, idx) => (
              <details key={idx} className="bg-white p-4 rounded-lg border border-gray-200">
                <summary className="font-semibold text-green-700 cursor-pointer hover:text-green-800">
                  {pattern.pattern_name}
                </summary>
                <p className="text-sm text-gray-600 mt-2">{pattern.description}</p>
                {pattern.characteristics && pattern.characteristics.length > 0 && (
                  <div className="mt-2">
                    <p className="text-xs font-semibold text-gray-700">关键特征:</p>
                    <ul className="text-xs text-gray-600 ml-4 mt-1 space-y-1">
                      {pattern.characteristics.map((char, i) => (
                        <li key={i}>• {char}</li>
                      ))}
                    </ul>
                  </div>
                )}
              </details>
            ))}
          </div>
        </div>
      )}

      {/* 底部说明 */}
      <div className="mt-6 p-4 bg-blue-50 rounded-lg border border-blue-200">
        <p className="text-xs text-gray-700">
          <strong>💡 使用建议：</strong>
        </p>
        <ul className="text-xs text-gray-600 mt-2 ml-4 space-y-1">
          <li>• <strong>首次使用</strong>：先运行"方式1"快速获得经典模式</li>
          <li>• <strong>深度分析</strong>：再运行"方式2"的4个步骤 (按顺序)，发现特殊模式</li>
          <li>• <strong>验证模式</strong>：最后运行"模式验证"，查看各模式的历史准确率</li>
          <li>• <strong>费用参考</strong>：方式1约$0.10-0.20 | 方式2约$0.20-0.30 | 验证约$0.02</li>
        </ul>
      </div>
    </div>
  )
}
