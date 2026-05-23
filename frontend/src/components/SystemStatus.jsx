import { useEffect, useState } from 'react';
import { getSystemStatus } from '../api/client';
import { Activity, AlertCircle, CheckCircle2, XCircle } from 'lucide-react';

const StatusBadge = ({ status }) => {
  const statusConfig = {
    healthy: { color: 'bg-green-100', textColor: 'text-green-800', icon: CheckCircle2 },
    error: { color: 'bg-red-100', textColor: 'text-red-800', icon: XCircle },
    unknown: { color: 'bg-yellow-100', textColor: 'text-yellow-800', icon: AlertCircle },
  };

  const config = statusConfig[status] || statusConfig.unknown;
  const Icon = config.icon;

  return (
    <span className={`inline-flex items-center gap-1 px-3 py-1 rounded-full text-sm font-semibold ${config.color} ${config.textColor}`}>
      <Icon size={14} />
      {status}
    </span>
  );
};

export const SystemStatus = () => {
  const [status, setStatus] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);

  useEffect(() => {
    const fetchStatus = async () => {
      try {
        const data = await getSystemStatus();
        setStatus(data);
        setError(null);
      } catch (err) {
        setError('Failed to fetch system status');
        console.error(err);
      } finally {
        setLoading(false);
      }
    };

    fetchStatus();
    const interval = setInterval(fetchStatus, 10000);

    return () => clearInterval(interval);
  }, []);

  if (loading) {
    return <div className="text-center py-8">Loading system status...</div>;
  }

  const serviceStatus = status?.status === 'healthy' ? 'healthy' : 'error';
  const serviceName = status?.service || 'Benchmark Controller';

  return (
    <div className="card">
      <h2 className="text-2xl font-bold mb-6 text-primary">System Status</h2>

      {error && (
        <div className="mb-4 p-4 bg-red-100 border-l-4 border-red-500 text-red-700">
          {error}
        </div>
      )}

      <div className="flex items-center justify-between p-4 bg-gray-50 rounded-lg">
        <div className="flex items-center gap-3">
          <Activity size={20} className="text-primary" />
          <div>
            <div className="font-semibold text-gray-900">{serviceName}</div>
            <div className="text-sm text-gray-500">
              {status?.service ? `Health endpoint responded successfully` : 'Waiting for backend response'}
            </div>
          </div>
        </div>
        <StatusBadge status={serviceStatus} />
      </div>
    </div>
  );
};
