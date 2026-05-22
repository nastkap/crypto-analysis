import { Link } from 'react-router-dom';
import { Zap, BarChart3, Settings, Home } from 'lucide-react';

export const Navbar = () => {
  return (
    <nav className="bg-gradient-to-r from-primary to-secondary text-white shadow-lg">
      <div className="max-w-7xl mx-auto px-4 py-4">
        <div className="flex items-center justify-between">
          <Link to="/" className="flex items-center gap-2 text-2xl font-bold hover:opacity-80 transition-all">
            <Zap size={28} />
            <span>ECIES Benchmark</span>
          </Link>

          <div className="flex items-center gap-6">
            <Link to="/" className="flex items-center gap-2 hover:bg-white hover:bg-opacity-10 px-3 py-2 rounded-lg transition-all">
              <Home size={20} />
              <span>Dashboard</span>
            </Link>

            <Link to="/benchmark" className="flex items-center gap-2 hover:bg-white hover:bg-opacity-10 px-3 py-2 rounded-lg transition-all">
              <Zap size={20} />
              <span>Run Test</span>
            </Link>

            <Link to="/results" className="flex items-center gap-2 hover:bg-white hover:bg-opacity-10 px-3 py-2 rounded-lg transition-all">
              <BarChart3 size={20} />
              <span>Results</span>
            </Link>

            <Link to="/settings" className="flex items-center gap-2 hover:bg-white hover:bg-opacity-10 px-3 py-2 rounded-lg transition-all">
              <Settings size={20} />
              <span>Settings</span>
            </Link>
          </div>
        </div>
      </div>
    </nav>
  );
};
