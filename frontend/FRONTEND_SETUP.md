# Frontend Setup & Development Guide

Complete guide for React frontend development and deployment for the ECIES Crypto Benchmark System.

## Table of Contents

1. [Quick Start](#quick-start)
2. [Project Structure](#project-structure)
3. [Development](#development)
4. [Building & Deployment](#building--deployment)
5. [Docker & Kubernetes](#docker--kubernetes)
6. [API Integration](#api-integration)
7. [Troubleshooting](#troubleshooting)

---

## Quick Start

### Prerequisites

- Node.js 16+ (`node -v`)
- npm 7+ (`npm -v`)
- Backend running on `http://localhost:8000`

### Installation

```bash
cd frontend
npm install
```

### Development Server

```bash
npm run dev
```

- **Frontend**: http://localhost:3000
- **Backend API**: Proxied to http://localhost:8000/api
- **Hot Module Replacement**: Enabled (auto-reload on file changes)

### Production Build

```bash
npm run build
```

Output: `frontend/dist/` (ready to serve)

Preview production build:
```bash
npm run preview
```

---

## Project Structure

```
frontend/
│
├── src/
│   ├── components/              # Reusable React components
│   │   ├── Navbar.jsx          # Navigation bar with routing
│   │   ├── SystemStatus.jsx    # K8s pod status display
│   │   ├── BenchmarkForm.jsx   # Test configuration form
│   │   ├── ResultsChart.jsx    # Performance charts & table
│   │   └── index.js            # Component exports
│   │
│   ├── pages/                   # Page components (routes)
│   │   ├── Dashboard.jsx       # Home page with overview
│   │   ├── BenchmarkPage.jsx   # Run benchmark page
│   │   ├── ResultsPage.jsx     # View results page
│   │   ├── SettingsPage.jsx    # Configuration page
│   │   └── index.js            # Page exports
│   │
│   ├── api/                     # API communication
│   │   └── client.js           # Axios HTTP client with endpoints
│   │
│   ├── App.jsx                 # Main app with React Router
│   ├── main.jsx                # Application entry point
│   └── index.css               # Global styles + Tailwind imports
│
├── public/                      # Static assets
│   └── (empty - add images/icons here)
│
├── Dockerfile                   # Multi-stage Docker build
├── docker-compose.yml          # (root level - includes frontend service)
│
├── vite.config.js              # Build & dev server config
├── tailwind.config.js          # Tailwind CSS customization
├── postcss.config.js           # PostCSS plugins
│
├── package.json                # Dependencies & scripts
├── .gitignore                  # Git ignore rules
├── .env.example                # Environment template
└── README.md                   # Project README
```

---

## Development

### Creating Components

**Example**: Add new component `src/components/MetricsPanel.jsx`

```javascript
import { Activity } from 'lucide-react';

export const MetricsPanel = ({ metrics }) => {
  return (
    <div className="card">
      <h2 className="text-2xl font-bold text-primary flex items-center gap-2">
        <Activity size={24} />
        Metrics
      </h2>
      {/* Component content */}
    </div>
  );
};
```

Export in `src/components/index.js`:
```javascript
export { MetricsPanel } from './MetricsPanel';
```

Use in pages:
```javascript
import { MetricsPanel } from '../components';

export const Dashboard = () => {
  return <MetricsPanel metrics={data} />;
};
```

### Adding Routes

Edit `src/App.jsx`:

```javascript
import { BrowserRouter as Router, Routes, Route } from 'react-router-dom';
import { Dashboard, BenchmarkPage, ResultsPage, SettingsPage } from './pages';

function App() {
  return (
    <Router>
      <div className="min-h-screen bg-gray-50">
        <Navbar />
        <main className="max-w-7xl mx-auto px-4 py-8">
          <Routes>
            <Route path="/" element={<Dashboard />} />
            <Route path="/benchmark" element={<BenchmarkPage />} />
            <Route path="/results" element={<ResultsPage />} />
            <Route path="/settings" element={<SettingsPage />} />
            {/* Add new route */}
            <Route path="/mypage" element={<MyPage />} />
          </Routes>
        </main>
      </div>
    </Router>
  );
}
```

### Styling with Tailwind

Use utility classes directly:

```javascript
<div className="grid grid-cols-3 gap-4 p-6 bg-gradient-to-r from-primary to-secondary text-white rounded-lg">
  <h2 className="text-2xl font-bold">Title</h2>
  <button className="btn-primary">Click me</button>
</div>
```

**Custom component classes** (defined in `src/index.css`):
- `.btn-primary` - Primary button
- `.btn-secondary` - Secondary button  
- `.btn-outline` - Outline button
- `.card` - Card component
- `.input-field` - Input styling
- `.badge` - Badge component
- `.badge-success`, `.badge-danger`, etc. - Colored badges

**Responsive breakpoints**:
```javascript
<div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
  {/* 1 column mobile, 2 tablet, 3 desktop */}
</div>
```

**Colors**:
- Primary: `#2E86AB` (blue) - `text-primary`, `bg-primary`, `border-primary`
- Secondary: `#A23B72` (purple) - `text-secondary`, `bg-secondary`
- Standard: `text-red-600`, `bg-green-100`, `border-yellow-500`

---

## Building & Deployment

### Vite Build

```bash
npm run build
```

Creates optimized production build:
- ✅ Tree-shaked and minified
- ✅ CSS modules optimized with PurgeCSS
- ✅ Assets with content hashes
- ✅ Code splitting for large components
- **Size**: ~150-200KB gzipped

### Env Variables for Production

Create `.env.production`:

```env
VITE_API_URL=https://api.example.com
VITE_ENV=production
```

### Static Hosting

Any static hosting works (Nginx, Vercel, GitHub Pages, etc.):

```bash
# Serve dist directory
npm install -g serve
serve -s dist -l 3000
```

---

## Docker & Kubernetes

### Building Docker Image

```bash
# Build image
docker build -t crypto-frontend:1.0.0 .

# Run locally
docker run -p 3000:3000 \
  -e VITE_API_URL=http://localhost:8000 \
  crypto-frontend:1.0.0
```

### Kubernetes Deployment

Frontend deployed with:
- **Deployment** (2 replicas) - `k8s/frontend.yaml`
- **Service** (ClusterIP) - Included in `frontend.yaml`
- **Ingress routing** (path `/`) - `k8s/ingress.yaml`
- **NetworkPolicy** - `k8s/network-policy.yaml`

Deployment:

```bash
# From root directory
kubectl apply -k k8s/

# Or manual
kubectl apply -f k8s/frontend.yaml
```

Access:

```bash
# Via Minikube
minikube service frontend -n crypto-perf

# Via port-forward
kubectl port-forward -n crypto-perf svc/frontend 3000:3000

# Via Ingress (requires Ingress Controller)
http://localhost/
```

### Docker Compose

Frontend included in `docker-compose.yml`:

```bash
docker-compose up -d frontend

# Check logs
docker-compose logs -f frontend
```

---

## API Integration

### HTTP Client Setup

`src/api/client.js` provides Axios client with endpoints:

```javascript
import {
  getSystemStatus,
  getK8sPods,
  runBenchmark,
  getBenchmarkStatus,
  getBenchmarkResults,
  getBenchmarkResultsCSV,
  healthCheck,
} from '../api/client';
```

### Making API Calls

In components:

```javascript
import { useEffect, useState } from 'react';
import { getSystemStatus } from '../api/client';

export const MyComponent = () => {
  const [data, setData] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);

  useEffect(() => {
    const fetchData = async () => {
      try {
        const result = await getSystemStatus();
        setData(result);
        setError(null);
      } catch (err) {
        setError(err.message);
      } finally {
        setLoading(false);
      }
    };

    fetchData();
  }, []);

  if (loading) return <div>Loading...</div>;
  if (error) return <div>Error: {error}</div>;
  return <div>{JSON.stringify(data)}</div>;
};
```

### Adding New API Endpoints

Edit `src/api/client.js`:

```javascript
export const myNewEndpoint = async (params) => {
  try {
    const response = await apiClient.post('/my-endpoint', params);
    return response.data;
  } catch (error) {
    console.error('Error:', error);
    throw error;
  }
};
```

### Environment-Based API URL

Development proxy (Vite):
```javascript
// vite.config.js already configured
// /api → http://localhost:8000
```

Production override:
```bash
# .env.production
VITE_API_URL=https://api.prod.com
```

Access in code:
```javascript
const apiUrl = process.env.VITE_API_URL || 'http://localhost:8000';
```

---

## Troubleshooting

### API Calls Failing

**Issue**: `CORS error` or `Failed to fetch`

**Solutions**:

1. Check backend is running:
   ```bash
  curl http://localhost:8000/health
   ```

2. Update API URL:
   - Development: Check `vite.config.js` proxy
   - Production: Set `VITE_API_URL` env var

3. Check browser console (F12 → Console tab)

4. Verify backend CORS settings

### Styling Not Applied

**Issue**: Classes like `text-primary` not working

**Solutions**:

1. Restart dev server:
   ```bash
   npm run dev
   ```

2. Check `tailwind.config.js` is correct

3. Verify Tailwind imports in `src/index.css`:
   ```css
   @tailwind base;
   @tailwind components;
   @tailwind utilities;
   ```

4. Clear browser cache (Ctrl+Shift+Delete)

### Build Fails

**Issue**: `npm run build` errors

**Solutions**:

1. Clear dependencies:
   ```bash
   rm -rf node_modules package-lock.json
   npm install
   ```

2. Check Node.js version: `node -v` (need 16+)

3. Check for syntax errors in `src/`

4. Run build with verbose output:
   ```bash
   npm run build -- --debug
   ```

### Development Server Won't Start

**Issue**: `npm run dev` fails

**Solutions**:

1. Port 3000 already in use:
   ```bash
   # Find process on port 3000
   netstat -ano | findstr :3000  # Windows
   lsof -i :3000                  # macOS/Linux
   
   # Kill process or use different port
   ```

2. Backend not running - start it first

3. Check firewall settings

### Component Not Rendering

**Issue**: Component doesn't appear on page

**Solutions**:

1. Check React Router path matches
2. Verify component export in `index.js`
3. Import correctly: `import { MyComponent } from '../components'`
4. Check browser console for JavaScript errors
5. Verify component is used in JSX

---

## Next Steps

### Enhancement Ideas

- [ ] Add dark mode support
- [ ] Implement WebSocket for real-time updates
- [ ] Add result comparison view
- [ ] Create custom benchmark templates
- [ ] Export results as PDF/PNG
- [ ] Add user authentication
- [ ] Implement result caching
- [ ] Add performance metrics graphs
- [ ] Create API documentation UI

### Performance Optimization

```javascript
// Lazy load pages
import { lazy, Suspense } from 'react';

const Dashboard = lazy(() => import('./pages/Dashboard'));

// Use in routes
<Suspense fallback={<LoadingSpinner />}>
  <Routes>
    <Route path="/" element={<Dashboard />} />
  </Routes>
</Suspense>
```

### Testing

Set up testing with Vitest + React Testing Library:

```bash
npm install --save-dev vitest @testing-library/react @testing-library/jest-dom
```

---

## Additional Resources

- **React Docs**: https://react.dev
- **Vite Docs**: https://vitejs.dev
- **Tailwind CSS**: https://tailwindcss.com
- **Recharts**: https://recharts.org
- **Lucide Icons**: https://lucide.dev
- **Axios**: https://axios-http.com
- **React Router**: https://reactrouter.com

---

## License

MIT - See LICENSE file for details
