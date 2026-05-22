import { BenchmarkForm, SystemStatus } from '../components';
import { useState } from 'react';

export const BenchmarkPage = () => {
  const [benchmarkHistory, setBenchmarkHistory] = useState([]);

  const handleBenchmarkStarted = (result) => {
    setBenchmarkHistory(prev => [result, ...prev]);
  };

  return (
    <div className="space-y-8">
      {/* Header */}
      <div className="bg-gradient-to-r from-primary to-secondary text-white p-8 rounded-lg shadow-lg">
        <h1 className="text-4xl font-bold mb-2">Run Benchmark</h1>
        <p className="text-lg opacity-90">Configure and execute cryptographic performance tests</p>
      </div>

      {/* Main Content */}
      <div className="grid grid-cols-1 lg:grid-cols-3 gap-8">
        {/* Form */}
        <div className="lg:col-span-2">
          <BenchmarkForm onBenchmarkStarted={handleBenchmarkStarted} />
        </div>

        {/* System Status */}
        <div>
          <SystemStatus />
        </div>
      </div>

      {/* History */}
      {benchmarkHistory.length > 0 && (
        <div className="card">
          <h2 className="text-2xl font-bold text-primary mb-6">Recent Benchmarks</h2>
          <div className="space-y-3">
            {benchmarkHistory.map((benchmark, idx) => (
              <div key={idx} className="p-4 bg-gray-50 rounded-lg border border-gray-200 hover:border-primary transition-all">
                <div className="flex justify-between items-start">
                  <div>
                    <div className="font-semibold text-gray-900">Benchmark #{benchmarkHistory.length - idx}</div>
                    <div className="text-sm text-gray-600 mt-1">
                      ID: <code className="bg-gray-100 px-2 py-1 rounded">{benchmark.benchmark_id}</code>
                    </div>
                    <div className="text-sm text-gray-600">
                      Status: <span className="font-semibold">{benchmark.status}</span>
                    </div>
                  </div>
                  <span className={`px-3 py-1 rounded-full text-sm font-semibold ${
                    benchmark.status === 'running'
                      ? 'bg-blue-100 text-blue-800'
                      : benchmark.status === 'completed'
                      ? 'bg-green-100 text-green-800'
                      : 'bg-gray-100 text-gray-800'
                  }`}>
                    {benchmark.status}
                  </span>
                </div>
              </div>
            ))}
          </div>
        </div>
      )}

      {/* Info */}
      <div className="card bg-blue-50 border-l-4 border-primary">
        <h3 className="font-bold text-primary mb-3">ℹ️ Benchmark Configuration Tips</h3>
        <ul className="text-sm text-gray-700 space-y-2">
          <li>• <strong>Small sizes (1-1KB):</strong> Quick tests, good for rapid iteration</li>
          <li>• <strong>Medium sizes (1-10MB):</strong> Realistic workloads, best for comparison</li>
          <li>• <strong>Large sizes (100MB):</strong> Stress tests, check memory/CPU limits</li>
          <li>• <strong>Iterations:</strong> Higher iterations = more accurate average, but longer execution</li>
          <li>• <strong>All Nodes:</strong> Recommended for fair comparison across all implementations</li>
        </ul>
      </div>
    </div>
  );
};
