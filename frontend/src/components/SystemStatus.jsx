import { useEffect, useState } from 'react';
import { getK8sPods } from '../api/client';
import { Activity, Database, Server, AlertCircle } from 'lucide-react';

const StatusBadge = ({ status }) => {
  const statusConfig = {
    Running: { color: 'bg-green-100', textColor: 'text-green-800', icon: Activity },
    Pending: { color: 'bg-yellow-100', textColor: 'text-yellow-800', icon: AlertCircle },
    Failed: { color: 'bg-red-100', textColor: 'text-red-800', icon: AlertCircle },
    CrashLoopBackOff: { color: 'bg-red-100', textColor: 'text-red-800', icon: AlertCircle },
  };

  const config = statusConfig[status] || statusConfig.Pending;
  const Icon = config.icon;

  return (
    <span className={`inline-flex items-center gap-1 px-3 py-1 rounded-full text-sm font-semibold ${config.color} ${config.textColor}`}>
      <Icon size={14} />
      {status}
    </span>
  );
};

export const SystemStatus = () => {
  const [pods, setPods] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);

  useEffect(() => {
    const fetchPods = async () => {
      try {
        const data = await getK8sPods();
        setPods(data);
        setError(null);
      } catch (err) {
        setError('Failed to fetch system status');
        console.error(err);
      } finally {
        setLoading(false);
      }
    };

    fetchPods();
    const interval = setInterval(fetchPods, 10000); // Refresh every 10 seconds

    return () => clearInterval(interval);
  }, []);

  if (loading) {
    return <div className="text-center py-8">Loading system status...</div>;
  }

  const getIconForPod = (name) => {
    if (name.includes('postgres')) return Database;
    if (name.includes('redis')) return Server;
    return Activity;
  };

  return (
    <div className="card">
      <h2 className="text-2xl font-bold mb-6 text-primary">System Status</h2>

      {error && (
        <div className="mb-4 p-4 bg-red-100 border-l-4 border-red-500 text-red-700">
          {error}
        </div>
      )}

      <div className="space-y-3">
        {pods.map((pod) => {
          const Icon = getIconForPod(pod.name);
          return (
            <div key={pod.name} className="flex items-center justify-between p-4 bg-gray-50 rounded-lg hover:bg-gray-100 transition-all">
              <div className="flex items-center gap-3">
                <Icon size={20} className="text-primary" />
                <div>
                  <div className="font-semibold text-gray-900">{pod.name}</div>
                  <div className="text-sm text-gray-500">
                    CPU: {pod.cpu} | Memory: {pod.memory}
                  </div>
                </div>
              </div>
              <StatusBadge status={pod.status} />
            </div>
          );
        })}
      </div>

      <div className="mt-6 pt-6 border-t border-gray-200">
        <div className="grid grid-cols-3 gap-4 text-center">
          <div>
            <div className="text-2xl font-bold text-primary">{pods.filter(p => p.status === 'Running').length}</div>
            <div className="text-sm text-gray-600">Running</div>
          </div>
          <div>
            <div className="text-2xl font-bold text-yellow-600">{pods.filter(p => p.status === 'Pending').length}</div>
            <div className="text-sm text-gray-600">Pending</div>
          </div>
          <div>
            <div className="text-2xl font-bold text-red-600">{pods.filter(p => p.status === 'Failed').length}</div>
            <div className="text-sm text-gray-600">Failed</div>
          </div>
        </div>
      </div>
    </div>
  );
};
