import { SystemStatus, BenchmarkForm } from '../components';
import { useState } from 'react';

export const Dashboard = () => {
  const [latestBenchmark, setLatestBenchmark] = useState(null);

  return (
    <div className="space-y-8">
      {/* Header */}
      <div className="bg-gradient-to-r from-primary to-secondary text-white p-8 rounded-lg shadow-lg">
        <h1 className="text-4xl font-bold mb-2">ECIES Crypto Benchmark System</h1>
        <p className="text-lg opacity-90">Compare cryptographic library performance in Kubernetes</p>
      </div>

      {/* Main Grid */}
      <div className="grid grid-cols-1 lg:grid-cols-3 gap-8">
        {/* Left Column - System Status */}
        <div className="lg:col-span-2">
          <SystemStatus />
        </div>

        {/* Right Column - Quick Start */}
        <div>
          <BenchmarkForm onBenchmarkStarted={setLatestBenchmark} />

          {latestBenchmark && (
            <div className="card mt-6 bg-green-50 border-l-4 border-green-500">
              <div className="text-sm text-green-700">
                <div className="font-semibold mb-2">✓ Benchmark Started!</div>
                <div className="text-xs">ID: {latestBenchmark.benchmark_id}</div>
                <div className="text-xs">Status: {latestBenchmark.status}</div>
              </div>
            </div>
          )}
        </div>
      </div>

      {/* Info Cards */}
      <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
        <div className="card border-l-4 border-primary">
          <h3 className="text-lg font-bold text-primary mb-2">📊 Performance Testing</h3>
          <p className="text-gray-600 text-sm">
            Run automated performance tests on multiple cryptographic libraries (Python, C++) to benchmark encryption/decryption speed and throughput.
          </p>
        </div>

        <div className="card border-l-4 border-secondary">
          <h3 className="text-lg font-bold text-secondary mb-2">🔒 Multiple Algorithms</h3>
          <p className="text-gray-600 text-sm">
            Test ECIES with various implementations: Python Cryptography, PyCryptodome, C++ OpenSSL, and C++ Crypto++.
          </p>
        </div>

        <div className="card border-l-4 border-purple-600">
          <h3 className="text-lg font-bold text-purple-600 mb-2">☸️ Kubernetes Ready</h3>
          <p className="text-gray-600 text-sm">
            Deployed on Kubernetes with resource limits, network policies, and advanced scheduling constraints for enterprise-grade reliability.
          </p>
        </div>
      </div>

      {/* Getting Started */}
      <div className="card">
        <h2 className="text-2xl font-bold text-primary mb-4">🚀 Getting Started</h2>
        <ol className="space-y-3 text-gray-700">
          <li className="flex items-start gap-3">
            <span className="flex-shrink-0 w-6 h-6 bg-primary text-white rounded-full flex items-center justify-center font-bold text-sm">1</span>
            <span><strong>Check System Status</strong> - Verify all pods are running on the left panel</span>
          </li>
          <li className="flex items-start gap-3">
            <span className="flex-shrink-0 w-6 h-6 bg-primary text-white rounded-full flex items-center justify-center font-bold text-sm">2</span>
            <span><strong>Configure Test</strong> - Select algorithm, data size, and iterations on the right</span>
          </li>
          <li className="flex items-start gap-3">
            <span className="flex-shrink-0 w-6 h-6 bg-primary text-white rounded-full flex items-center justify-center font-bold text-sm">3</span>
            <span><strong>Run Benchmark</strong> - Click "Start Benchmark" to begin testing</span>
          </li>
          <li className="flex items-start gap-3">
            <span className="flex-shrink-0 w-6 h-6 bg-primary text-white rounded-full flex items-center justify-center font-bold text-sm">4</span>
            <span><strong>View Results</strong> - Go to Results tab to see charts and export data</span>
          </li>
        </ol>
      </div>
    </div>
  );
};
