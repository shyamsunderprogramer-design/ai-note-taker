/**
 * Vite config for the ANT web app.
 *
 * The current dev source is a single-file monolith at the repo root:
 *   - index.html (entry)
 *   - app.js    (monolithic, ~340KB, ~9200 lines)
 *   - style.css (single stylesheet, ~188KB)
 *
 * The parallel `js/` and `css/` sub-folders hold a modular refactor
 * (ES-module main entry that imports from core/state.js, etc.) that
 * is NOT yet wired up to index.html. Migrating to that modular setup
 * is a separate refactor tracked separately from this config.
 *
 * Vite currently treats index.html as a multi-page app: the static HTML
 * pages alongside it (caption-overlay.html, cognitive-graph.html, …)
 * are also entry points and get copied to dist/ with their assets.
 *
 * `base: '/'` because the app is served at the root path on Vercel
 * and packaged into Electron at the apps/web/ root.
 */

import { defineConfig } from 'vite';
import { resolve } from 'path';

export default defineConfig({
  root: '.',
  base: '/',
  build: {
    outDir: 'dist',
    emptyOutDir: true,
    // The dev index.html, app.js, and style.css are plain non-module
    // files; Vite's default minifier is fine.
    rollupOptions: {
      input: {
        // Multi-page entry. Any *.html at the root becomes a route.
        index: resolve(__dirname, 'index.html'),
        caption_overlay: resolve(__dirname, 'caption-overlay.html'),
        cognitive_graph: resolve(__dirname, 'cognitive-graph.html'),
        interview_overlay: resolve(__dirname, 'interview-overlay.html'),
        interview_simulator: resolve(__dirname, 'interview-simulator.html'),
        job_tracker: resolve(__dirname, 'job-tracker.html'),
        overlay: resolve(__dirname, 'overlay.html'),
        pre_interview: resolve(__dirname, 'pre-interview.html'),
        resume_review: resolve(__dirname, 'resume-review.html'),
        resume_review_v2: resolve(__dirname, 'resume-review-v2.html'),
        signin: resolve(__dirname, 'signin.html'),
        splash: resolve(__dirname, 'splash.html'),
        study_plan: resolve(__dirname, 'study-plan.html'),
        analytics_dashboard: resolve(__dirname, 'analytics-dashboard.html'),
      },
    },
  },
  server: {
    port: 5173,
    // Vite dev server proxies /api to the FastAPI backend on :8000.
    proxy: {
      '/api': {
        target: 'http://localhost:8000',
        changeOrigin: true,
        rewrite: (path) => path.replace(/^\/api/, ''),
      },
      '/health': 'http://localhost:8000',
      '/docs': 'http://localhost:8000',
      '/openapi.json': 'http://localhost:8000',
    },
  },
});
