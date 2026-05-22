import { useState } from 'react';
import { Settings, Info, Database } from 'lucide-react';

export const SettingsPage = () => {
  const [settings, setSettings] = useState({
    apiUrl: process.env.REACT_APP_API_URL || 'http://localhost:8000/api',
    autoRefresh: true,
    refreshInterval: 30,
    theme: 'light',
  });

  const [saved, setSaved] = useState(false);

  const handleInputChange = (e) => {
    const { name, value, type, checked } = e.target;
    setSettings(prev => ({
      ...prev,
      [name]: type === 'checkbox' ? checked : (name === 'refreshInterval' ? parseInt(value) : value),
    }));
    setSaved(false);
  };

  const handleSave = () => {
    localStorage.setItem('benchmarkSettings', JSON.stringify(settings));
    setSaved(true);
    setTimeout(() => setSaved(false), 3000);
  };

  return (
    <div className="space-y-8">
      {/* Header */}
      <div className="bg-gradient-to-r from-primary to-secondary text-white p-8 rounded-lg shadow-lg">
        <h1 className="text-4xl font-bold mb-2 flex items-center gap-3">
          <Settings size={40} />
          Settings
        </h1>
        <p className="text-lg opacity-90">Configure application preferences</p>
      </div>

      {/* API Configuration */}
      <div className="card">
        <h2 className="text-2xl font-bold text-primary mb-6 flex items-center gap-2">
          <Database size={24} />
          API Configuration
        </h2>

        <div className="space-y-6">
          <div>
            <label className="block text-sm font-semibold text-gray-700 mb-2">API URL</label>
            <input
              type="text"
              name="apiUrl"
              value={settings.apiUrl}
              onChange={handleInputChange}
              className="input-field font-mono text-sm"
              placeholder="http://localhost:8000/api"
            />
            <p className="text-xs text-gray-500 mt-2">
              ℹ️ Base URL for backend API requests. Should match your deployment configuration.
            </p>
          </div>

          <div className="bg-blue-50 border-l-4 border-blue-500 p-4 rounded">
            <p className="text-sm text-blue-700">
              <strong>Note:</strong> API URL is also configured in vite.config.js for development proxy.
            </p>
          </div>
        </div>
      </div>

      {/* UI Configuration */}
      <div className="card">
        <h2 className="text-2xl font-bold text-primary mb-6 flex items-center gap-2">
          <Info size={24} />
          Display Settings
        </h2>

        <div className="space-y-6">
          {/* Auto Refresh */}
          <div>
            <label className="flex items-center gap-3 cursor-pointer">
              <input
                type="checkbox"
                name="autoRefresh"
                checked={settings.autoRefresh}
                onChange={handleInputChange}
                className="w-5 h-5 accent-primary"
              />
              <span className="font-semibold text-gray-700">Enable Auto-Refresh</span>
            </label>
            <p className="text-xs text-gray-500 mt-2 ml-8">
              Automatically refresh system status and results at regular intervals
            </p>
          </div>

          {/* Refresh Interval */}
          {settings.autoRefresh && (
            <div>
              <label className="block text-sm font-semibold text-gray-700 mb-2">Refresh Interval (seconds)</label>
              <input
                type="number"
                name="refreshInterval"
                value={settings.refreshInterval}
                onChange={handleInputChange}
                min="5"
                max="300"
                step="5"
                className="input-field"
              />
              <p className="text-xs text-gray-500 mt-2">
                How often to automatically fetch new data (5-300 seconds)
              </p>
            </div>
          )}

          {/* Theme */}
          <div>
            <label className="block text-sm font-semibold text-gray-700 mb-2">Theme</label>
            <select
              name="theme"
              value={settings.theme}
              onChange={handleInputChange}
              className="input-field"
            >
              <option value="light">Light (default)</option>
              <option value="dark">Dark (coming soon)</option>
              <option value="auto">Auto (coming soon)</option>
            </select>
          </div>
        </div>
      </div>

      {/* System Information */}
      <div className="card bg-gray-50">
        <h2 className="text-2xl font-bold text-primary mb-6">System Information</h2>

        <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
          <div>
            <p className="text-sm text-gray-600">Application Version</p>
            <p className="text-lg font-bold text-gray-900">1.0.0</p>
          </div>
          <div>
            <p className="text-sm text-gray-600">Frontend Framework</p>
            <p className="text-lg font-bold text-gray-900">React 18 + Vite</p>
          </div>
          <div>
            <p className="text-sm text-gray-600">Backend</p>
            <p className="text-lg font-bold text-gray-900">Python Flask</p>
          </div>
          <div>
            <p className="text-sm text-gray-600">Deployment</p>
            <p className="text-lg font-bold text-gray-900">Kubernetes (Minikube)</p>
          </div>
        </div>
      </div>

      {/* Environment Info */}
      <div className="card bg-yellow-50 border-l-4 border-yellow-500">
        <h3 className="font-bold text-yellow-700 mb-3">⚙️ Environment Configuration</h3>
        <div className="text-sm text-yellow-700 font-mono space-y-1">
          <div>Node Env: <span className="text-yellow-600">{process.env.NODE_ENV || 'development'}</span></div>
          <div>API Base: <span className="text-yellow-600">{settings.apiUrl}</span></div>
          <div>Auto Refresh: <span className="text-yellow-600">{settings.autoRefresh ? 'Enabled' : 'Disabled'}</span></div>
        </div>
      </div>

      {/* Save Button */}
      <div className="flex gap-3">
        <button
          onClick={handleSave}
          className="btn-primary flex-1 text-lg"
        >
          {saved ? '✓ Saved!' : 'Save Settings'}
        </button>
        <button
          onClick={() => {
            localStorage.removeItem('benchmarkSettings');
            setSettings({
              apiUrl: 'http://localhost:8000/api',
              autoRefresh: true,
              refreshInterval: 30,
              theme: 'light',
            });
            setSaved(true);
          }}
          className="btn-outline flex-1 text-lg"
        >
          Reset to Defaults
        </button>
      </div>

      {/* Help */}
      <div className="card bg-blue-50 border-l-4 border-blue-500">
        <h3 className="font-bold text-blue-700 mb-3">❓ Need Help?</h3>
        <div className="text-sm text-blue-700 space-y-2">
          <p>📖 Read the documentation: <a href="#" className="underline hover:text-blue-900">k8s/GETTING_STARTED.md</a></p>
          <p>🐛 Report issues: <a href="#" className="underline hover:text-blue-900">GitHub Issues</a></p>
          <p>💬 Join community: <a href="#" className="underline hover:text-blue-900">GitHub Discussions</a></p>
        </div>
      </div>
    </div>
  );
};
