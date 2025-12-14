'use client'

import { useState, useEffect } from 'react'
import axios from 'axios'
import AnnotatedKLineChart from './AnnotatedKLineChart'

const API_BASE = 'http://localhost:8000'

interface Pattern {
  pattern_name: string
  description: string
  characteristics: string[]
  key_features?: string[]
  key_days?: string
  example_stock_code?: string
  kline_data?: any[]
  annotations?: any
}

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

interface VisualizationData {
  pattern_name: string
  pattern_description: string
  stock_code: string
  date_range: {
    start: string
    end: string
  }
  kline_data: KLineData[]
  annotations: Annotation[]
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

  // 各步骤完成状态和结果
  const [stepResults, setStepResults] = useState<any>({
    filter: null,
    extract: null,
    cluster: null,
    patterns: null,
    validation: null
  })

  // K线图可视化状态
  const [expandedPatterns, setExpandedPatterns] = useState<Set<string>>(new Set())
  const [visualizationData, setVisualizationData] = useState<Map<string, VisualizationData>>(new Map())
  const [loadingVisualizations, setLoadingVisualizations] = useState<Set<string>>(new Set())
  const [visualizationErrors, setVisualizationErrors] = useState<Map<string, string>>(new Map())

  // 加载所有已有的结果文件
  const loadExistingResults = async () => {
    try {
      // 尝试加载步骤1结果
      try {
        const r1 = await axios.get(`${API_BASE}/api/training/results/special-samples`)
        if (r1.data.success) {
          setStepResults((prev: any) => ({ ...prev, filter: r1.data }))
        }
      } catch (e) {}

      // 尝试加载步骤2结果
      try {
        const r2 = await axios.get(`${API_BASE}/api/training/results/feature-vectors`)
        if (r2.data.success) {
          setStepResults((prev: any) => ({ ...prev, extract: r2.data }))
        }
      } catch (e) {}

      // 尝试加载步骤3结果
      try {
        const r3 = await axios.get(`${API_BASE}/api/training/results/clustered-samples`)
        if (r3.data.success) {
          setStepResults((prev: any) => ({ ...prev, cluster: r3.data }))
        }
      } catch (e) {}

      // 尝试加载步骤4结果
      try {
        const r4 = await axios.get(`${API_BASE}/api/training/results/ai-patterns`)
        if (r4.data.success) {
          setStepResults((prev: any) => ({ ...prev, patterns: r4.data }))
        }
      } catch (e) {}

      // 尝试加载验证结果
      try {
        const r5 = await axios.get(`${API_BASE}/api/training/results/pattern-validation`)
        if (r5.data.success) {
          setStepResults((prev: any) => ({ ...prev, validation: r5.data }))
        }
      } catch (e) {}
    } catch (error) {
      console.error('Error loading existing results:', error)
    }
  }

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
          } else if (taskName === 'extract_features') {
            const resultRes = await axios.get(`${API_BASE}/api/training/results/feature-vectors`)
            setStepResults((prev: any) => ({ ...prev, extract: resultRes.data }))
          } else if (taskName === 'cluster_samples') {
            const resultRes = await axios.get(`${API_BASE}/api/training/results/clustered-samples`)
            setStepResults((prev: any) => ({ ...prev, cluster: resultRes.data }))
          } else if (taskName === 'extract_ai_patterns') {
            const resultRes = await axios.get(`${API_BASE}/api/training/results/ai-patterns`)
            setStepResults((prev: any) => ({ ...prev, patterns: resultRes.data }))
          } else if (taskName === 'validate_patterns') {
            const resultRes = await axios.get(`${API_BASE}/api/training/results/pattern-validation`)
            setStepResults((prev: any) => ({ ...prev, validation: resultRes.data }))
          } else if (taskName === 'merge_valid_patterns') {
            const resultRes = await axios.get(`${API_BASE}/api/training/results/merge-result`)
            setStepResults((prev: any) => ({ ...prev, merge: resultRes.data }))
            // Refresh the patterns list after merge
            fetchPatterns()
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

  // 组件初始化时加载已有结果
  useEffect(() => {
    loadExistingResults()
    fetchPatterns()
  }, [])

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

  const handleMergeValidPatterns = async () => {
    try {
      setTrainingLoading(true)
      setCurrentTrainingTask('merge_valid_patterns')
      const res = await axios.post(`${API_BASE}/api/training/merge-valid-patterns`)

      if (res.data.success) {
        setTrainingStatus('模式合并任务已启动')
      }
    } catch (error: any) {
      setTrainingStatus('错误: ' + error.message)
      setTrainingLoading(false)
    }
  }

  // 加载K线图可视化数据
  const loadVisualization = async (patternName: string) => {
    if (visualizationData.has(patternName)) {
      // 如果已经加载过，直接返回
      return
    }

    setLoadingVisualizations(prev => new Set(prev).add(patternName))
    // 清除之前的错误
    setVisualizationErrors(prev => {
      const newMap = new Map(prev)
      newMap.delete(patternName)
      return newMap
    })

    try {
      const res = await axios.get(`${API_BASE}/api/training/patterns/${encodeURIComponent(patternName)}/visualization`)

      if (res.data.success) {
        setVisualizationData(prev => new Map(prev).set(patternName, res.data.data))
      } else {
        setVisualizationErrors(prev => new Map(prev).set(patternName, res.data.message || '加载失败'))
      }
    } catch (error: any) {
      console.error('加载K线图失败:', error)
      const errorMsg = error.response?.data?.detail || error.message || '网络错误，请重试'
      setVisualizationErrors(prev => new Map(prev).set(patternName, errorMsg))
    } finally {
      setLoadingVisualizations(prev => {
        const newSet = new Set(prev)
        newSet.delete(patternName)
        return newSet
      })
    }
  }

  // 切换模式展开状态
  const togglePatternExpansion = (patternName: string) => {
    const newExpanded = new Set(expandedPatterns)
    if (newExpanded.has(patternName)) {
      newExpanded.delete(patternName)
    } else {
      newExpanded.add(patternName)
      // 展开时加载K线图数据
      loadVisualization(patternName)
    }
    setExpandedPatterns(newExpanded)
  }

  return (
    <div className="bg-white rounded-lg shadow-md p-6">
      <h2 className="text-2xl font-bold mb-6 text-green-600">📊 区域2：模式分析与训练</h2>

      {/* 说明文字 */}
      <div className="mb-6 p-4 bg-gradient-to-r from-yellow-50 to-orange-50 rounded-lg border-l-4 border-orange-400">
        <p className="text-sm text-gray-700">
          <strong>📌 重要说明：</strong>本区域提供<strong className="text-orange-600">两种互补的模式发现方法</strong>，建议都运行以获得全面的模式库：
        </p>
        <div className="mt-3 grid grid-cols-2 gap-4">
          <div className="p-3 bg-white rounded border border-green-200">
            <p className="font-semibold text-green-700 text-sm">🎯 经典K线形态识别</p>
            <p className="text-xs text-gray-600 mt-1">识别人眼可见的K线图形态（如"V型反转"、"放量突破"）</p>
          </div>
          <div className="p-3 bg-white rounded border border-blue-200">
            <p className="font-semibold text-blue-700 text-sm">🤖 AI数值特征挖掘</p>
            <p className="text-xs text-gray-600 mt-1">发现隐藏在数值中的规律（如"低波动震荡"、"温和放量"）</p>
          </div>
        </div>
      </div>

      {/* 经典K线形态识别 */}
      <div className="mb-6 p-5 bg-gradient-to-r from-green-50 to-green-100 rounded-lg border border-green-300">
        <div className="flex items-center justify-between mb-3">
          <div>
            <h3 className="text-lg font-bold text-green-800 flex items-center gap-2">
              🎯 经典K线形态识别
            </h3>
            <p className="text-xs text-gray-600 mt-1">AI分析2000个历史上涨案例的K线图 → 提取共性形态模式 → 输出带K线形态说明的经典模式</p>
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

      {/* AI数值特征挖掘 */}
      <div className="mb-6 p-5 bg-gradient-to-r from-blue-50 to-blue-100 rounded-lg border border-blue-300">
        <div className="mb-4">
          <h3 className="text-lg font-bold text-blue-800 flex items-center gap-2">
            🤖 AI数值特征挖掘工作流
          </h3>
          <p className="text-xs text-gray-600 mt-1">
            4步流程：过滤特殊样本 → 计算数值特征 → 聚类分组 → AI提取模式（需按顺序执行）
          </p>
        </div>

        <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
          {/* 步骤1 */}
          <div className="bg-white p-4 rounded-lg border border-blue-200">
            <div className="flex items-start justify-between mb-2">
              <div>
                <h4 className="font-semibold text-blue-700 text-sm">步骤1：过滤特殊样本</h4>
                <p className="text-xs text-gray-500 mt-1">从数据库随机抽取2000个上涨样本 → AI判断是否匹配经典模式 → 过滤出不匹配的特殊样本</p>
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
              <p className="text-xs text-gray-600 mt-2 bg-blue-50 p-2 rounded">
                ✓ 特殊样本: <strong>{stepResults.filter.count}</strong> 个
              </p>
            )}
          </div>

          {/* 步骤2 */}
          <div className="bg-white p-4 rounded-lg border border-blue-200">
            <div className="flex items-start justify-between mb-2">
              <div>
                <h4 className="font-semibold text-blue-700 text-sm">步骤2：提取特征向量</h4>
                <p className="text-xs text-gray-500 mt-1">读取步骤1的特殊样本K线数据 → 计算8个数值特征(波动率、成交量趋势、最大回撤等) → 转换为特征向量</p>
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
            {stepResults.extract && (
              <p className="text-xs text-gray-600 mt-2 bg-blue-50 p-2 rounded">
                ✓ 特征向量: <strong>{stepResults.extract.count}</strong> 个
              </p>
            )}
          </div>

          {/* 步骤3 */}
          <div className="bg-white p-4 rounded-lg border border-blue-200">
            <div className="flex items-start justify-between mb-2">
              <div>
                <h4 className="font-semibold text-blue-700 text-sm">步骤3：K-means聚类</h4>
                <p className="text-xs text-gray-500 mt-1">读取步骤2的特征向量 → 使用K-means算法聚类 → 将相似样本分成若干簇(自动确定簇数)</p>
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
            {stepResults.cluster && (
              <p className="text-xs text-gray-600 mt-2 bg-blue-50 p-2 rounded">
                ✓ 聚类数: <strong>{stepResults.cluster.n_clusters}</strong> 簇
              </p>
            )}
          </div>

          {/* 步骤4 */}
          <div className="bg-white p-4 rounded-lg border border-blue-200">
            <div className="flex items-start justify-between mb-2">
              <div>
                <h4 className="font-semibold text-blue-700 text-sm">步骤4：AI提取模式</h4>
                <p className="text-xs text-gray-500 mt-1">读取步骤3的聚类结果 → AI分析每个簇的K线数据 → 总结共性特征并命名模式 → 输出最终模式列表</p>
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
            {stepResults.patterns && stepResults.patterns.data && stepResults.patterns.data.patterns && (
              <p className="text-xs text-gray-600 mt-2 bg-blue-50 p-2 rounded">
                ✓ 新模式: <strong>{stepResults.patterns.data.patterns.length}</strong> 个
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

        {/* AI发现的新模式列表 */}
        {stepResults.patterns && stepResults.patterns.data && stepResults.patterns.data.patterns && (
          <div className="mt-4 p-4 bg-white rounded border border-blue-300">
            <h4 className="font-semibold text-blue-800 mb-3 flex items-center gap-2">
              🔍 AI数值特征模式 ({stepResults.patterns.data.patterns.length}个)
            </h4>
            <p className="text-xs text-gray-600 mb-2">这些模式基于波动率、成交量趋势等数值特征，与K线形态模式互补</p>
            <div className="space-y-3 max-h-80 overflow-y-auto">
              {stepResults.patterns.data.patterns.map((pattern: any, idx: number) => (
                <details key={idx} className="bg-blue-50 p-3 rounded border border-blue-200">
                  <summary className="font-semibold text-blue-700 cursor-pointer hover:text-blue-900 text-sm">
                    {pattern.pattern_name}
                  </summary>
                  <p className="text-xs text-gray-700 mt-2 leading-relaxed">{pattern.description}</p>
                  {pattern.key_features && pattern.key_features.length > 0 && (
                    <div className="mt-2">
                      <p className="text-xs font-semibold text-gray-700">关键特征:</p>
                      <ul className="text-xs text-gray-600 ml-4 mt-1 space-y-1">
                        {pattern.key_features.map((feat: string, i: number) => (
                          <li key={i}>• {feat}</li>
                        ))}
                      </ul>
                    </div>
                  )}
                  <div className="mt-2 text-xs text-gray-500">
                    样本数: {pattern.sample_count} | 来源: 聚类{pattern.cluster_id}
                  </div>
                </details>
              ))}
            </div>
          </div>
        )}
      </div>

      {/* 模式验证区域 */}
      <div className="mb-6 p-5 bg-gradient-to-r from-purple-50 to-purple-100 rounded-lg border border-purple-300">
        <div className="flex items-center justify-between mb-3">
          <div>
            <h3 className="text-lg font-bold text-purple-800 flex items-center gap-2">
              ✅ 步骤5：AI模式验证
            </h3>
            <p className="text-xs text-gray-600 mt-1">
              使用历史数据验证步骤4生成的AI模式有效性 (聚类降维法：2000样本→12簇→60代表→AI批量匹配)
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

      {/* 步骤6：合并有效模式 */}
      <div className="mb-6 p-5 bg-gradient-to-r from-emerald-50 to-emerald-100 rounded-lg border border-emerald-300">
        <div className="flex items-center justify-between mb-3">
          <div>
            <h3 className="text-lg font-bold text-emerald-800 flex items-center gap-2">
              💾 步骤6：合并有效模式到数据库
            </h3>
            <p className="text-xs text-gray-600 mt-1">
              将验证通过的模式(准确率≥45%)合并到数据库，同时淘汰低效模式(准确率&lt;40%，设置为不活跃)
            </p>
          </div>
          <button
            onClick={handleMergeValidPatterns}
            disabled={trainingLoading}
            className={`px-6 py-3 rounded-lg font-semibold text-white transition-all ${
              trainingLoading
                ? 'bg-gray-400 cursor-not-allowed'
                : 'bg-emerald-600 hover:bg-emerald-700 hover:shadow-lg'
            }`}
          >
            {trainingLoading && currentTrainingTask === 'merge_valid_patterns' ? '合并中...' : '开始合并'}
          </button>
        </div>

        {/* 合并结果 */}
        {stepResults.merge && stepResults.merge.data && (
          <div className="mt-4 p-4 bg-white rounded border border-emerald-200">
            <h4 className="font-semibold text-emerald-700 mb-3">合并结果摘要</h4>
            <div className="grid grid-cols-2 gap-4 mb-3 text-center">
              <div className="p-3 bg-emerald-50 rounded">
                <p className="text-xs text-gray-600">已合并模式</p>
                <p className="text-2xl font-bold text-emerald-700">
                  {stepResults.merge.data.merged_count || 0}
                </p>
              </div>
              <div className="p-3 bg-orange-50 rounded">
                <p className="text-xs text-gray-600">已淘汰模式</p>
                <p className="text-2xl font-bold text-orange-700">
                  {stepResults.merge.data.deactivated_count || 0}
                </p>
              </div>
            </div>
            {stepResults.merge.data.merged_patterns && stepResults.merge.data.merged_patterns.length > 0 && (
              <div className="mt-3">
                <p className="text-xs font-semibold text-gray-700 mb-2">已合并的模式:</p>
                <div className="flex flex-wrap gap-2">
                  {stepResults.merge.data.merged_patterns.map((name: string, idx: number) => (
                    <span key={idx} className="px-2 py-1 bg-emerald-100 text-emerald-700 rounded text-xs">
                      ✓ {name}
                    </span>
                  ))}
                </div>
              </div>
            )}
            {stepResults.merge.data.deactivated_patterns && stepResults.merge.data.deactivated_patterns.length > 0 && (
              <div className="mt-3">
                <p className="text-xs font-semibold text-gray-700 mb-2">已淘汰的模式:</p>
                <div className="flex flex-wrap gap-2">
                  {stepResults.merge.data.deactivated_patterns.map((name: string, idx: number) => (
                    <span key={idx} className="px-2 py-1 bg-orange-100 text-orange-700 rounded text-xs">
                      ✗ {name}
                    </span>
                  ))}
                </div>
              </div>
            )}
          </div>
        )}
      </div>

      {/* 模式库总览 */}
      <div className="mt-6 p-5 bg-gradient-to-r from-gray-50 to-gray-100 rounded-lg border border-gray-300">
        <h3 className="text-xl font-bold mb-4 text-gray-800">📚 完整模式库</h3>

        {/* K线形态模式 */}
        {patterns.length > 0 && (
          <div className="mb-6 p-4 bg-white rounded-lg border border-green-300">
            <div className="flex items-center gap-2 mb-3">
              <span className="px-3 py-1 bg-green-100 text-green-700 rounded-full text-xs font-semibold">来源: 经典K线形态识别</span>
              <h4 className="text-lg font-bold text-green-700">🎯 K线形态模式 ({patterns.length}个)</h4>
            </div>
            <p className="text-xs text-gray-600 mb-3">基于K线图视觉形态的传统技术分析模式</p>
          <div className="space-y-3 max-h-96 overflow-y-auto">
            {patterns.map((pattern, idx) => (
              <div key={idx} className="bg-white p-4 rounded-lg border border-gray-200">
                <div
                  className="font-semibold text-green-700 cursor-pointer hover:text-green-800 flex items-center justify-between"
                  onClick={() => togglePatternExpansion(pattern.pattern_name)}
                >
                  <span>{pattern.pattern_name}</span>
                  <span className="text-sm text-gray-500">
                    {expandedPatterns.has(pattern.pattern_name) ? '▼' : '▶'}
                  </span>
                </div>

                {expandedPatterns.has(pattern.pattern_name) && (
                  <>
                    <p className="text-sm text-gray-600 mt-2">{pattern.description}</p>

                    {/* 量化指标卡片 */}
                    {(pattern.key_days || pattern.example_stock_code || (pattern.key_features && pattern.key_features.length > 0)) && (
                      <div className="mt-4 bg-amber-50 rounded-lg p-4 border-2 border-amber-200">
                        <h3 className="text-sm font-semibold text-amber-900 mb-3 flex items-center gap-2">
                          <span>📊</span> 量化指标
                        </h3>
                        <div className="grid grid-cols-2 gap-3">
                          {pattern.key_days && (
                            <div className="bg-white rounded p-3 border border-amber-200">
                              <div className="text-xs text-gray-600">关键时间段</div>
                              <div className="text-lg font-bold text-purple-600">{pattern.key_days}</div>
                            </div>
                          )}
                          {pattern.example_stock_code && (
                            <div className="bg-white rounded p-3 border border-amber-200">
                              <div className="text-xs text-gray-600">示例股票</div>
                              <div className="text-lg font-bold text-blue-600">{pattern.example_stock_code}</div>
                            </div>
                          )}
                          {pattern.key_features && pattern.key_features.map((feature, i) => (
                            <div key={i} className="bg-white rounded p-3 border border-amber-200">
                              <div className="text-xs text-gray-600">关键特征 {i + 1}</div>
                              <div className="text-sm font-semibold text-green-600">{feature}</div>
                            </div>
                          ))}
                        </div>
                      </div>
                    )}

                    {/* 核心特征网格 */}
                    {pattern.characteristics && pattern.characteristics.length > 0 && (
                      <div className="mt-4">
                        <h3 className="text-sm font-semibold text-gray-800 mb-3">核心特征</h3>
                        <div className="grid grid-cols-2 gap-3">
                          {pattern.characteristics.map((char, i) => (
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
                    )}

                    {/* K线图可视化（带标注） */}
                    <div className="mt-4">
                      <h3 className="text-sm font-semibold text-gray-800 mb-3">典型案例K线图</h3>
                      {pattern.kline_data && pattern.kline_data.length > 0 ? (
                        <div className="bg-gray-50 rounded-lg p-4 border border-gray-200">
                          <AnnotatedKLineChart
                            data={pattern.kline_data}
                            annotations={pattern.annotations}
                          />
                        </div>
                      ) : (
                        <div className="bg-gray-50 rounded-lg p-8 border border-gray-200 text-center">
                          <div className="text-gray-400 text-4xl mb-2">📊</div>
                          <p className="text-gray-500 text-sm">暂无K线数据</p>
                          <p className="text-gray-400 text-xs mt-1">请先获取股票行情数据</p>
                        </div>
                      )}
                    </div>
                  </>
                )}
              </div>
            ))}
          </div>
          </div>
        )}

        {/* AI数值特征模式 */}
        {stepResults.patterns && stepResults.patterns.data && stepResults.patterns.data.patterns && stepResults.patterns.data.patterns.length > 0 && (
          <div className="p-4 bg-white rounded-lg border border-blue-300">
            <div className="flex items-center gap-2 mb-3">
              <span className="px-3 py-1 bg-blue-100 text-blue-700 rounded-full text-xs font-semibold">来源: AI数值特征挖掘</span>
              <h4 className="text-lg font-bold text-blue-700">🔍 AI数值特征模式 ({stepResults.patterns.data.patterns.length}个)</h4>
            </div>
            <p className="text-xs text-gray-600 mb-3">基于波动率、成交量趋势等数值特征的隐藏规律</p>
            <div className="space-y-3 max-h-96 overflow-y-auto">
              {stepResults.patterns.data.patterns.map((pattern: any, idx: number) => (
                <div key={idx} className="bg-white p-4 rounded-lg border border-gray-200">
                  <div
                    className="font-semibold text-blue-700 cursor-pointer hover:text-blue-800 flex items-center justify-between"
                    onClick={() => togglePatternExpansion(pattern.pattern_name)}
                  >
                    <span>{pattern.pattern_name}</span>
                    <span className="text-sm text-gray-500">
                      {expandedPatterns.has(pattern.pattern_name) ? '▼' : '▶'}
                    </span>
                  </div>

                  {expandedPatterns.has(pattern.pattern_name) && (() => {
                    // 从数据库查找完整的模式数据
                    const dbPattern = patterns.find(p => p.pattern_name === pattern.pattern_name)

                    return (
                      <>
                        <p className="text-sm text-gray-600 mt-2">{pattern.description}</p>

                        {/* 量化指标（如果有） */}
                        {dbPattern && (dbPattern.key_days || dbPattern.example_stock_code || (dbPattern.key_features && dbPattern.key_features.length > 0)) && (
                          <div className="mt-4 bg-amber-50 rounded-lg p-4 border-2 border-amber-200">
                            <h3 className="text-sm font-semibold text-amber-900 mb-3 flex items-center gap-2">
                              <span>📊</span> 量化指标
                            </h3>
                            <div className="grid grid-cols-2 gap-3">
                              {dbPattern.key_days && (
                                <div className="bg-white rounded p-3 border border-amber-200">
                                  <div className="text-xs text-gray-600">关键时间段</div>
                                  <div className="text-lg font-bold text-purple-600">{dbPattern.key_days}</div>
                                </div>
                              )}
                              {pattern.sample_count && (
                                <div className="bg-white rounded p-3 border border-amber-200">
                                  <div className="text-xs text-gray-600">训练样本数</div>
                                  <div className="text-lg font-bold text-blue-600">{pattern.sample_count}</div>
                                </div>
                              )}
                              {dbPattern.key_features && dbPattern.key_features.map((feature: string, i: number) => (
                                <div key={i} className="bg-white rounded p-3 border border-amber-200">
                                  <div className="text-xs text-gray-600">关键特征 {i + 1}</div>
                                  <div className="text-sm font-semibold text-green-600">{feature}</div>
                                </div>
                              ))}
                            </div>
                          </div>
                        )}

                        {/* 核心特征（match_rules） */}
                        {pattern.match_rules && pattern.match_rules.length > 0 && (
                          <div className="mt-4">
                            <h3 className="text-sm font-semibold text-gray-800 mb-3">核心特征</h3>
                            <div className="grid grid-cols-2 gap-3">
                              {pattern.match_rules.map((rule: string, i: number) => (
                                <div
                                  key={i}
                                  className="flex items-start gap-2 bg-purple-50 rounded-lg p-3 border border-purple-200"
                                >
                                  <span className="text-purple-600 font-bold">✓</span>
                                  <span className="text-sm text-gray-700 font-medium">{rule}</span>
                                </div>
                              ))}
                            </div>
                          </div>
                        )}

                        {/* K线图（带标注） */}
                        {dbPattern && dbPattern.kline_data && dbPattern.kline_data.length > 0 && (
                          <div className="mt-4">
                            <h3 className="text-sm font-semibold text-gray-800 mb-3">典型案例K线图</h3>
                            <div className="bg-gray-50 rounded-lg p-4 border border-gray-200">
                              <AnnotatedKLineChart
                                data={dbPattern.kline_data}
                                annotations={dbPattern.annotations}
                              />
                            </div>
                          </div>
                        )}
                      </>
                    )
                  })()}
                </div>
              ))}
            </div>
          </div>
        )}

        {/* 空状态提示 */}
        {patterns.length === 0 && (!stepResults.patterns || !stepResults.patterns.data || !stepResults.patterns.data.patterns || stepResults.patterns.data.patterns.length === 0) && (
          <div className="p-8 text-center bg-white rounded-lg border border-gray-200">
            <p className="text-gray-500 text-sm">暂无已识别的模式</p>
            <p className="text-gray-400 text-xs mt-1">请运行上方的"经典K线形态识别"或"AI数值特征挖掘"来发现模式</p>
          </div>
        )}
      </div>

      {/* 底部说明 */}
      <div className="mt-6 p-4 bg-blue-50 rounded-lg border border-blue-200">
        <p className="text-xs text-gray-700">
          <strong>💡 使用建议：</strong>
        </p>
        <ul className="text-xs text-gray-600 mt-2 ml-4 space-y-1">
          <li>• <strong>建立完整模式库</strong>：建议两种方法都运行，获得互补的模式组合</li>
          <li>• <strong>K线形态识别</strong>：点击"开始分析"按钮，快速获得3-5个传统K线形态模式</li>
          <li>• <strong>AI数值特征挖掘</strong>：依次运行4个步骤，发现2-5个基于数值特征的隐藏规律</li>
          <li>• <strong>模式验证</strong>：运行"开始验证"，用历史数据检查经典模式的准确率</li>
          <li>• <strong>费用参考</strong>：K线形态识别约$0.10-0.20 | AI数值挖掘约$0.20-0.30 | 验证约$0.02</li>
        </ul>
      </div>
    </div>
  )
}

// 简化的K线图组件 (SVG版本 - 参考page.tsx实现)
function SimpleKLineChart({ data, annotations }: { data: KLineData[], annotations: Annotation[] }) {
  const [hoveredIndex, setHoveredIndex] = useState<number | null>(null)

  if (!data || data.length === 0) {
    return <div className="text-center text-gray-500 py-8">暂无K线数据</div>
  }

  const maxHigh = Math.max(...data.map(d => d.high))
  const minLow = Math.min(...data.map(d => d.low))
  const priceRange = maxHigh - minLow
  const padding = priceRange * 0.15
  const maxVolume = Math.max(...data.map(d => d.volume))

  const getY = (price: number) => {
    return ((maxHigh + padding - price) / (priceRange + 2 * padding)) * 180
  }

  const containerWidth = 1000
  const leftMargin = 50
  const rightMargin = 80
  const chartWidth = containerWidth - leftMargin - rightMargin
  const xScale = chartWidth / data.length
  const candleWidth = Math.max(3, Math.min(8, xScale * 0.6))
  const totalWidth = containerWidth

  return (
    <div className="relative">
      {/* K线图 */}
      <svg width={totalWidth} height="250" viewBox={`0 0 ${totalWidth} 250`} className="overflow-visible">
        {/* 价格网格线 */}
        {[0, 1, 2, 3, 4].map((i) => {
          const price = maxHigh + padding - (priceRange + 2 * padding) * (i / 4)
          return (
            <g key={i}>
              <line
                x1={leftMargin}
                y1={i * 45}
                x2={totalWidth - rightMargin}
                y2={i * 45}
                stroke="#e5e7eb"
                strokeWidth="1"
              />
              <text x="10" y={i * 45 + 5} fontSize="10" fill="#6b7280">
                {price.toFixed(2)}
              </text>
            </g>
          )
        })}

        {/* K线蜡烛 */}
        {data.map((candle, index) => {
          const x = leftMargin + index * xScale
          const isRise = candle.close >= candle.open

          return (
            <g key={index}>
              {/* 影线 */}
              <line
                x1={x}
                y1={getY(candle.high)}
                x2={x}
                y2={getY(candle.low)}
                stroke={isRise ? '#ef4444' : '#22c55e'}
                strokeWidth="1.5"
              />
              {/* 实体 - 红涨绿跌 */}
              <rect
                x={x - candleWidth / 2}
                y={getY(Math.max(candle.open, candle.close))}
                width={candleWidth}
                height={Math.max(2, Math.abs(getY(candle.close) - getY(candle.open)))}
                fill={isRise ? '#ffffff' : '#22c55e'}
                stroke={isRise ? '#ef4444' : '#22c55e'}
                strokeWidth={isRise ? 1.5 : 0}
                onMouseEnter={() => setHoveredIndex(index)}
                onMouseLeave={() => setHoveredIndex(null)}
                className="cursor-pointer hover:opacity-80 transition-opacity"
              />

              {/* 日期标签 */}
              {index % 5 === 0 && (
                <text
                  x={x}
                  y="205"
                  fill="#6b7280"
                  fontSize="9"
                  textAnchor="middle"
                >
                  {candle.date.slice(5)}
                </text>
              )}
            </g>
          )
        })}

        {/* 标注点 */}
        {annotations && annotations.map((ann, idx) => {
          const dataIndex = data.findIndex(d => d.date === ann.date)
          if (dataIndex === -1) return null

          const x = leftMargin + dataIndex * xScale
          const y = getY(ann.price)

          const colors: Record<string, string> = {
            high: '#ef4444',
            low: '#22c55e',
            volume: '#f59e0b',
            breakout: '#8b5cf6',
            consolidation: '#6366f1'
          }

          return (
            <g key={idx}>
              <circle cx={x} cy={y} r="4" fill={colors[ann.type] || '#3b82f6'} />
              <text
                x={x + 8}
                y={y - 8}
                fontSize="10"
                fontWeight="bold"
                fill={colors[ann.type] || '#3b82f6'}
              >
                {ann.label}
              </text>
            </g>
          )
        })}
      </svg>

      {/* 成交量图 */}
      <svg width={totalWidth} height="80" viewBox={`0 0 ${totalWidth} 80`}>
        {data.map((candle, index) => {
          const x = leftMargin + index * xScale
          const height = (candle.volume / maxVolume) * 60
          const isRise = candle.close >= candle.open

          return (
            <rect
              key={index}
              x={x - candleWidth / 2}
              y={60 - height}
              width={candleWidth}
              height={height}
              fill={isRise ? '#fca5a5' : '#86efac'}
              opacity={0.7}
              className="cursor-pointer hover:opacity-100 transition-opacity"
              onMouseEnter={() => setHoveredIndex(index)}
              onMouseLeave={() => setHoveredIndex(null)}
            />
          )
        })}
      </svg>

      {/* 悬浮信息 */}
      {hoveredIndex !== null && (
        <div className="absolute top-0 left-0 bg-gray-900 text-white text-xs rounded px-3 py-2 pointer-events-none shadow-lg z-10">
          <div className="font-bold mb-1">{data[hoveredIndex].date}</div>
          <div>开: ¥{data[hoveredIndex].open.toFixed(2)}</div>
          <div>收: ¥{data[hoveredIndex].close.toFixed(2)}</div>
          <div>高: ¥{data[hoveredIndex].high.toFixed(2)}</div>
          <div>低: ¥{data[hoveredIndex].low.toFixed(2)}</div>
          <div className="mt-1 pt-1 border-t border-gray-700">
            量: {data[hoveredIndex].volume.toLocaleString()}
          </div>
        </div>
      )}
    </div>
  )
}
