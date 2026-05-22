import { ResultsChart } from '../components';

export const ResultsPage = () => {
  return (
    <div className="space-y-8">
      {/* Header */}
      <div className="bg-gradient-to-r from-primary to-secondary text-white p-8 rounded-lg shadow-lg">
        <h1 className="text-4xl font-bold mb-2">Benchmark Results</h1>
        <p className="text-lg opacity-90">Analyze and compare cryptographic performance metrics</p>
      </div>

      {/* Results Chart */}
      <ResultsChart />

      {/* Interpretation Guide */}
      <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
        <div className="card">
          <h3 className="text-xl font-bold text-primary mb-4">📊 Metrics Explained</h3>
          <div className="space-y-3 text-sm text-gray-700">
            <div>
              <strong className="text-primary">Execution Time (ms)</strong>
              <p className="text-gray-600">Lower is better. Time taken to encrypt/decrypt data.</p>
            </div>
            <div>
              <strong className="text-secondary">Throughput (MB/s)</strong>
              <p className="text-gray-600">Higher is better. Data processed per second.</p>
            </div>
            <div>
              <strong>Ops/Sec</strong>
              <p className="text-gray-600">Higher is better. Number of operations completed per second.</p>
            </div>
          </div>
        </div>

        <div className="card">
          <h3 className="text-xl font-bold text-primary mb-4">💡 Performance Insights</h3>
          <div className="space-y-3 text-sm text-gray-700">
            <div>
              <strong className="text-primary">C++ vs Python</strong>
              <p className="text-gray-600">C++ libraries typically 2-3x faster due to native compilation.</p>
            </div>
            <div>
              <strong className="text-secondary">Data Size Impact</strong>
              <p className="text-gray-600">Larger data sizes may show different performance characteristics.</p>
            </div>
            <div>
              <strong>Library Comparison</strong>
              <p className="text-gray-600">Different implementations have varying optimization levels.</p>
            </div>
          </div>
        </div>
      </div>

      {/* Export Options */}
      <div className="card bg-green-50 border-l-4 border-green-500">
        <h3 className="font-bold text-green-700 mb-3">✓ Export & Share</h3>
        <p className="text-sm text-green-600 mb-4">Results are automatically saved to the database. You can:</p>
        <ul className="text-sm text-green-700 space-y-1">
          <li>• Export all results as CSV for analysis in Excel or R</li>
          <li>• Share individual benchmark IDs with colleagues</li>
          <li>• Track performance trends over time</li>
          <li>• Compare results across different configurations</li>
        </ul>
      </div>
    </div>
  );
};
