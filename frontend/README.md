# Frontend

React + TypeScript + Vite frontend for the AD password reset application.

```bash
npm ci
npm run dev
npm run lint
npm run build
npm audit
```

The development server runs on port 5001 and proxies `/api` to the backend on port 5002. The production application serves the generated `dist` directory from Flask.

See the repository-level README for security and deployment requirements.
