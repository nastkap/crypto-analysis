# ECIES Crypto Benchmark - Frontend

Professional React 18 frontend for the ECIES Cryptographic Benchmark System running on Kubernetes.

## Features

✨ **Modern UI**
- React 18 with hooks and functional components
- Tailwind CSS for responsive design
- Gradient colors (primary: #2E86AB, secondary: #A23B72)

📊 **Interactive Dashboard**
- Real-time system status monitoring
- Benchmark execution control
- Performance result visualization with Recharts
- CSV export functionality

🎨 **Components**
- `Navbar` - Navigation with routing
- `SystemStatus` - Live K8s pod monitoring
- `BenchmarkForm` - Test configuration and submission
- `ResultsChart` - Multi-view result analysis

🛣️ **Pages**
- **Dashboard** - System overview and quick start
- **Run Benchmark** - Execute performance tests
- **Results** - Analyze and export metrics
- **Settings** - Configuration and system info

🔌 **API Integration**
- Axios-based HTTP client
- Environment-based API URL configuration
- Automatic proxy to backend in development

## Project Structure

```
frontend/
├── src/
│   ├── components/           # React components
│   │   ├── Navbar.jsx
│   │   ├── SystemStatus.jsx
│   │   ├── BenchmarkForm.jsx
│   │   ├── ResultsChart.jsx
│   │   └── index.js
│   ├── pages/               # Page components
│   │   ├── Dashboard.jsx
│   │   ├── BenchmarkPage.jsx
│   │   ├── ResultsPage.jsx
│   │   ├── SettingsPage.jsx
│   │   └── index.js
│   ├── api/                 # API client
│   │   └── client.js
│   ├── App.jsx              # Main app with routing
│   ├── main.jsx             # Entry point
│   └── index.css            # Global styles + Tailwind
├── public/                  # Static assets
├── Dockerfile              # Multi-stage Docker build
├── vite.config.js          # Vite + proxy config
├── tailwind.config.js      # Tailwind customization
├── postcss.config.js       # PostCSS for Tailwind
├── package.json            # Dependencies
└── README.md              # This file
```

## Quick Start

### Development

1. **Install dependencies**
   ```bash
   npm install
   ```

2. **Start development server**
   ```bash
   npm run dev
   ```
   - Frontend: http://localhost:3000
   - API proxy to backend: http://localhost:8000/api

3. **Build for production**
   ```bash
   npm run build
   ```

4. **Preview production build**
   ```bash
   npm run preview
   ```

### Docker

1. **Build image**
   ```bash
   docker build -t crypto-frontend:1.0.0 .
   ```

2. **Run container**
   ```bash
   docker run -p 3000:3000 crypto-frontend:1.0.0
   ```

## Environment Configuration

Create `.env.local` in the project root:

```env
VITE_API_URL=http://localhost:8000
```

For production, update `vite.config.js` proxy configuration or set the correct API URL.

## Dependencies

- **React 18.2.0** - UI library
- **Vite 5.0.0** - Build tool (fast!)
- **Tailwind CSS 3.4.0** - Utility-first styling
- **Recharts 2.10.0** - React charting library
- **Axios 1.6.2** - HTTP client
- **React Router 6.20.0** - Client-side routing
- **Lucide React 0.294.0** - Icon library
- **Zustand 4.4.0** - State management (optional)

## API Endpoints Used

| Endpoint | Method | Purpose |
|----------|--------|---------|
| `/api/status` | GET | System status |
| `/api/k8s/pods` | GET | Kubernetes pods information |
| `/api/benchmark/run` | POST | Start new benchmark |
| `/api/benchmark/{id}` | GET | Get benchmark status |
| `/api/results` | GET | Get all benchmark results |
| `/api/results/download` | GET | Download results as CSV |
| `/api/health` | GET | Health check |

## Development Tips

### Adding a New Component

1. Create `src/components/MyComponent.jsx`
2. Export in `src/components/index.js`
3. Import: `import { MyComponent } from '../components'`

### Adding a New Page

1. Create `src/pages/MyPage.jsx`
2. Export in `src/pages/index.js`
3. Add route in `src/App.jsx`

### Styling with Tailwind

- Responsive: `md:grid-cols-3`, `lg:flex-row`
- Custom colors: `text-primary`, `bg-secondary`
- Custom components: `btn-primary`, `card`, `input-field`

See `src/index.css` for custom component definitions.

### API Calls

```javascript
import { getSystemStatus, runBenchmark } from '../api/client';

// In component
const data = await getSystemStatus();
const result = await runBenchmark({ size: 1024, iterations: 10 });
```

## Kubernetes Deployment

Frontend will be deployed with:
- Deployment manifest (frontend-deployment.yaml)
- Service manifest (frontend-service.yaml)
- Exposed via Ingress at `/` path

Example K8s Service configuration:
```yaml
kind: Service
apiVersion: v1
metadata:
  name: frontend
  namespace: crypto-perf
spec:
  type: ClusterIP
  selector:
    app: frontend
  ports:
    - protocol: TCP
      port: 3000
      targetPort: 3000
```

## Build Output

The production build creates a `dist/` folder with:
- Optimized JavaScript bundles
- CSS optimized with PurgeCSS
- Assets with content hashes
- ~150-200KB gzipped

## Browser Support

- Chrome/Edge 90+
- Firefox 88+
- Safari 14+
- Mobile browsers (iOS Safari 12+, Chrome Mobile)

## Troubleshooting

### API calls failing
- Check if backend is running: `curl http://localhost:8000/health`
- Update `VITE_API_URL` in `.env.local`
- Check browser console for CORS errors

### Styling not applying
- Restart dev server after changing `tailwind.config.js`
- Clear browser cache (Ctrl+Shift+Delete)

### Build fails
- Delete `node_modules` and `package-lock.json`, then `npm install`
- Check Node.js version: `node -v` (requires 16+)

## Next Steps

- Add dark mode theme support
- Implement real-time WebSocket updates
- Add result comparison view
- Create custom benchmark templates
- Add performance metrics export (PDF, PNG)

## License

MIT - See LICENSE file for details
