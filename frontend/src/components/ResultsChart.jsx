import { useEffect, useState } from 'react';
import { LineChart, Line, BarChart, Bar, XAxis, YAxis, CartesianGrid, Tooltip, Legend, ResponsiveContainer, ComposedChart } from 'recharts';
import { getBenchmarkResults, getBenchmarkResultsCSV } from '../api/client';
import { Download, RefreshCw } from 'lucide-react';

export const ResultsChart = () => {
  const [results, setResults] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);
  const [chartType, setChartType] = useState('bar');

  const fetchResults = async () => {
    try {
      const data = await getBenchmarkResults();
      setResults(data);
      setError(null);
    } catch (err) {
      setError('Failed to fetch results');
      console.error(err);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchResults();
    const interval = setInterval(fetchResults, 30000); // Refresh every 30 seconds
    return () => clearInterval(interval);
  }, []);

  const handleDownloadCSV = async () => {
    try {
      const blob = await getBenchmarkResultsCSV();
      const url = window.URL.createObjectURL(blob);
      const link = document.createElement('a');
      link.href = url;
      link.setAttribute('download', `benchmark-results-${new Date().toISOString()}.csv`);
      document.body.appendChild(link);
      link.click();
      link.parentNode.removeChild(link);
    } catch (err) {
      console.error('Error downloading CSV:', err);
    }
  };

  if (loading) {
    return <div className="card text-center py-8">Loading results...</div>;
  }

  if (results.length === 0) {
    return (
      <div className="card text-center py-12">
        <div className="text-gray-500 text-lg">No results yet. Run a benchmark first!</div>
      </div>
    );
  }

  // Prepare data for charts
  const chartData = results.map(result => ({
    algorithm: result.algorithm?.split('_').join(' ') || 'Unknown',
    time_ms: parseFloat(result.time_ms).toFixed(2),
    throughput_mbps: parseFloat(result.throughput_mbps || 0).toFixed(2),
    ops_per_sec: parseInt(result.ops_per_sec || 0),
  }));

  // Calculate statistics
  const stats = {
    fastest: chartData.reduce((min, curr) => parseFloat(curr.time_ms) < parseFloat(min.time_ms) ? curr : min),
    slowest: chartData.reduce((max, curr) => parseFloat(curr.time_ms) > parseFloat(max.time_ms) ? curr : max),
    average: (chartData.reduce((sum, curr) => sum + parseFloat(curr.time_ms), 0) / chartData.length).toFixed(2),
    total: chartData.length,
  };

  return (
    <div className="space-y-6">
      <div className="card">
        <div className="flex justify-between items-center mb-6">
          <h2 className="text-2xl font-bold text-primary">Benchmark Results</h2>
          <div className="flex gap-2">
            <button
              onClick={fetchResults}
              className="btn-outline flex items-center gap-2"
            >
              <RefreshCw size={18} />
              Refresh
            </button>
            <button
              onClick={handleDownloadCSV}
              className="btn-primary flex items-center gap-2"
            >
              <Download size={18} />
              Export CSV
            </button>
          </div>
        </div>

        {error && (
          <div className="mb-4 p-4 bg-red-100 border-l-4 border-red-500 text-red-700">
            {error}
          </div>
        )}

        {/* Statistics */}
        <div className="grid grid-cols-4 gap-4 mb-6">
          <div className="bg-gradient-to-br from-blue-50 to-blue-100 p-4 rounded-lg">
            <div className="text-sm text-gray-600">Fastest</div>
            <div className="text-2xl font-bold text-primary">{stats.fastest.time_ms}ms</div>
            <div className="text-xs text-gray-600">{stats.fastest.algorithm}</div>
          </div>
          <div className="bg-gradient-to-br from-red-50 to-red-100 p-4 rounded-lg">
            <div className="text-sm text-gray-600">Slowest</div>
            <div className="text-2xl font-bold text-red-600">{stats.slowest.time_ms}ms</div>
            <div className="text-xs text-gray-600">{stats.slowest.algorithm}</div>
          </div>
          <div className="bg-gradient-to-br from-green-50 to-green-100 p-4 rounded-lg">
            <div className="text-sm text-gray-600">Average</div>
            <div className="text-2xl font-bold text-green-600">{stats.average}ms</div>
            <div className="text-xs text-gray-600">All algorithms</div>
          </div>
          <div className="bg-gradient-to-br from-purple-50 to-purple-100 p-4 rounded-lg">
            <div className="text-sm text-gray-600">Total Tests</div>
            <div className="text-2xl font-bold text-purple-600">{stats.total}</div>
            <div className="text-xs text-gray-600">Completed</div>
          </div>
        </div>

        {/* Chart Type Toggle */}
        <div className="flex gap-2 mb-6">
          <button
            onClick={() => setChartType('bar')}
            className={`px-4 py-2 rounded-lg font-semibold transition-all ${
              chartType === 'bar'
                ? 'bg-primary text-white'
                : 'bg-gray-100 text-gray-800 hover:bg-gray-200'
            }`}
          >
            Execution Time
          </button>
          <button
            onClick={() => setChartType('throughput')}
            className={`px-4 py-2 rounded-lg font-semibold transition-all ${
              chartType === 'throughput'
                ? 'bg-primary text-white'
                : 'bg-gray-100 text-gray-800 hover:bg-gray-200'
            }`}
          >
            Throughput
          </button>
          <button
            onClick={() => setChartType('combined')}
            className={`px-4 py-2 rounded-lg font-semibold transition-all ${
              chartType === 'combined'
                ? 'bg-primary text-white'
                : 'bg-gray-100 text-gray-800 hover:bg-gray-200'
            }`}
          >
            Combined
          </button>
        </div>

        {/* Charts */}
        {chartType === 'bar' && (
          <ResponsiveContainer width="100%" height={300}>
            <BarChart data={chartData}>
              <CartesianGrid strokeDasharray="3 3" />
              <XAxis dataKey="algorithm" />
              <YAxis label={{ value: 'Time (ms)', angle: -90, position: 'insideLeft' }} />
              <Tooltip />
              <Bar dataKey="time_ms" fill="#2E86AB" radius={[8, 8, 0, 0]} />
            </BarChart>
          </ResponsiveContainer>
        )}

        {chartType === 'throughput' && (
          <ResponsiveContainer width="100%" height={300}>
            <LineChart data={chartData}>
              <CartesianGrid strokeDasharray="3 3" />
              <XAxis dataKey="algorithm" />
              <YAxis label={{ value: 'Throughput (MB/s)', angle: -90, position: 'insideLeft' }} />
              <Tooltip />
              <Line
                type="monotone"
                dataKey="throughput_mbps"
                stroke="#A23B72"
                strokeWidth={2}
                dot={{ r: 6 }}
              />
            </LineChart>
          </ResponsiveContainer>
        )}

        {chartType === 'combined' && (
          <ResponsiveContainer width="100%" height={300}>
            <ComposedChart data={chartData}>
              <CartesianGrid strokeDasharray="3 3" />
              <XAxis dataKey="algorithm" />
              <YAxis yAxisId="left" label={{ value: 'Time (ms)', angle: -90, position: 'insideLeft' }} />
              <YAxis yAxisId="right" orientation="right" label={{ value: 'Throughput (MB/s)', angle: 90, position: 'insideRight' }} />
              <Tooltip />
              <Legend />
              <Bar yAxisId="left" dataKey="time_ms" fill="#2E86AB" name="Execution Time (ms)" />
              <Line yAxisId="right" type="monotone" dataKey="throughput_mbps" stroke="#A23B72" name="Throughput (MB/s)" />
            </ComposedChart>
          </ResponsiveContainer>
        )}
      </div>

      {/* Results Table */}
      <div className="card">
        <h3 className="text-xl font-bold mb-4 text-primary">Detailed Results</h3>
        <div className="overflow-x-auto">
          <table className="w-full text-sm">
            <thead className="bg-gray-100 border-b-2 border-gray-300">
              <tr>
                <th className="px-4 py-2 text-left">Algorithm</th>
                <th className="px-4 py-2 text-right">Time (ms)</th>
                <th className="px-4 py-2 text-right">Throughput (MB/s)</th>
                <th className="px-4 py-2 text-right">Ops/Sec</th>
              </tr>
            </thead>
            <tbody>
              {chartData.map((row, idx) => (
                <tr key={idx} className="border-b border-gray-200 hover:bg-gray-50">
                  <td className="px-4 py-3 font-semibold text-gray-900">{row.algorithm}</td>
                  <td className="px-4 py-3 text-right font-mono text-primary">{row.time_ms}</td>
                  <td className="px-4 py-3 text-right font-mono text-secondary">{row.throughput_mbps}</td>
                  <td className="px-4 py-3 text-right font-mono">{row.ops_per_sec.toLocaleString()}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </div>
    </div>
  );
};
