/**
 * Cognitive Graph - Entry Point
 * Initializes the Cognitive Graph component
 */

import { CognitiveGraph } from './components/CognitiveGraph.js';

// Initialize when DOM is ready
document.addEventListener('DOMContentLoaded', () => {
  initCognitiveGraph();
});

async function initCognitiveGraph() {
  console.log('[CognitiveGraph] Initializing...');

  try {
    // Initialize the Cognitive Graph component
    const cognitiveGraph = new CognitiveGraph();

    // Expose for debugging
    window.cg = cognitiveGraph;

    console.log('[CognitiveGraph] Initialized successfully');
  } catch (err) {
    console.error('[CognitiveGraph] Initialization failed:', err);
  }
}
