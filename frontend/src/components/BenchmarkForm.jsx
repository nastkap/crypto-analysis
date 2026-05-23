import { useState } from 'react';
import { runBenchmark } from '../api/client';
import { Play, Clock } from 'lucide-react';

export const BenchmarkForm = ({ onBenchmarkStarted }) => {
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState(null);
  const [success, setSuccess] = useState(null);

  const [formData, setFormData] = useState({
    algorithm: 'ECIES',
    size: 1024,
    iterations: 10,
    nodes: ['all'],
  });

  const sizes = [
    { label: '1 byte', value: 1 },
    { label: '1 KB', value: 1024 },
    { label: '1 MB', value: 1048576 },
    { label: '10 MB', value: 10485760 },
    { label: '100 MB', value: 104857600 },
  ];

  const handleInputChange = (e) => {
    const { name, value } = e.target;
    setFormData(prev => ({
      ...prev,
      [name]: name === 'iterations' ? parseInt(value) : (name === 'size' ? parseInt(value) : value),
    }));
  };

  const handleSizeClick = (size) => {
    setFormData(prev => ({
      ...prev,
      size: size,
    }));
  };

  const handleSubmit = async (e) => {
    e.preventDefault();
    setLoading(true);
    setError(null);
    setSuccess(null);

    try {
      const result = await runBenchmark(formData);
      setSuccess(`Benchmark started! ID: ${result.run_id || 'pending'}`);
      onBenchmarkStarted(result);
      
      // Reset form
      setFormData({
        algorithm: 'ECIES',
        size: 1024,
        iterations: 10,
        nodes: ['all'],
      });
    } catch (err) {
      setError(err.response?.data?.detail || err.response?.data?.error || 'Failed to start benchmark');
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="card">
      <h2 className="text-2xl font-bold mb-6 text-primary">Run Benchmark</h2>

      {error && (
        <div className="mb-4 p-4 bg-red-100 border-l-4 border-red-500 text-red-700">
          {error}
        </div>
      )}

      {success && (
        <div className="mb-4 p-4 bg-green-100 border-l-4 border-green-500 text-green-700">
          ✓ {success}
        </div>
      )}

      <form onSubmit={handleSubmit} className="space-y-6">
        {/* Algorithm */}
        <div>
          <label className="block text-sm font-semibold text-gray-700 mb-2">Algorithm</label>
          <select
            name="algorithm"
            value={formData.algorithm}
            onChange={handleInputChange}
            className="input-field"
          >
            <option value="ECIES">ECIES</option>
            <option value="RSA">RSA (future)</option>
            <option value="AES">AES (future)</option>
          </select>
        </div>

        {/* Data Size */}
        <div>
          <label className="block text-sm font-semibold text-gray-700 mb-3">Data Size</label>
          <div className="grid grid-cols-5 gap-2 mb-3">
            {sizes.map((size) => (
              <button
                key={size.value}
                type="button"
                onClick={() => handleSizeClick(size.value)}
                className={`py-2 rounded-lg font-semibold transition-all ${
                  formData.size === size.value
                    ? 'bg-primary text-white'
                    : 'bg-gray-100 text-gray-800 hover:bg-gray-200'
                }`}
              >
                {size.label}
              </button>
            ))}
          </div>
          <p className="text-sm text-gray-600">Selected: {formData.size.toLocaleString()} bytes</p>
        </div>

        {/* Iterations */}
        <div>
          <label className="block text-sm font-semibold text-gray-700 mb-2">Iterations</label>
          <input
            type="number"
            name="iterations"
            value={formData.iterations}
            onChange={handleInputChange}
            min="1"
            max="1000"
            className="input-field"
          />
        </div>

        {/* Nodes */}
        <div>
          <label className="block text-sm font-semibold text-gray-700 mb-3">Test Nodes</label>
          <div className="space-y-2">
            <label className="flex items-center gap-2 cursor-pointer">
              <input
                type="checkbox"
                checked={formData.nodes.includes('all')}
                onChange={(e) => {
                  if (e.target.checked) {
                    setFormData(prev => ({ ...prev, nodes: ['all'] }));
                  }
                }}
                className="w-4 h-4 accent-primary"
              />
              <span className="text-gray-700">All Nodes</span>
            </label>
          </div>
        </div>

        {/* Submit Button */}
        <button
          type="submit"
          disabled={loading}
          className="btn-primary w-full flex items-center justify-center gap-2 text-lg"
        >
          <Play size={20} />
          {loading ? 'Starting...' : 'Start Benchmark'}
        </button>
      </form>

      <div className="mt-6 pt-6 border-t border-gray-200 text-sm text-gray-600">
        <div className="flex items-center gap-2">
          <Clock size={16} />
          <span>Estimated duration: ~5-10 minutes depending on data size</span>
        </div>
      </div>
    </div>
  );
};
