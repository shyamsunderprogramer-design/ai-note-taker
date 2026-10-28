/* Shared connection lifecycle for the two desktop/browser overlays. */
(function () {
  window.createOverlayConnection = function ({ onStatus, onMessage }) {
    let socket = null;
    let timer = null;
    let stopped = false;
    let retries = 0;
    function stop() {
      stopped = true;
      clearTimeout(timer);
      const old = socket;
      socket = null;
      if (old) old.close();
    }
    function reconnect() {
      clearTimeout(timer);
      if (!stopped) timer = setTimeout(connect, Math.min(30000, 1000 * (2 ** Math.min(retries++, 5))));
    }
    function connect() {
      if (socket && socket.readyState < 2) return;
      stopped = false;
      clearTimeout(timer);
      let url;
      try {
        url = new URL(window.API_BASE.replace(/\/$/, '') + '/ws/transcribe');
        if (!['http:', 'https:'].includes(url.protocol)) throw new Error('Invalid backend URL');
        url.protocol = url.protocol === 'https:' ? 'wss:' : 'ws:';
        try {
          const token = localStorage.getItem('ainotetaker_auth_token');
          if (token) url.searchParams.set('token', token);
        } catch (_) { /* Storage can be unavailable in embedded contexts. */ }
        onStatus('connecting', 'Connecting…');
        socket = new WebSocket(url.toString());
      } catch (_) {
        onStatus('offline', 'Backend connection unavailable');
        return;
      }
      const current = socket;
      current.onmessage = (event) => {
        if (socket !== current) return;
        let data;
        try { data = JSON.parse(event.data); } catch (_) { return; }
        if (data.type === 'auth_error') {
          stop();
          onStatus('offline', 'Sign in to ANT, then reopen this window');
          return;
        }
        if (data.type === 'auth_ok') {
          retries = 0;
          onStatus('connected', 'Live');
        }
        onMessage(data);
      };
      current.onclose = (event) => {
        if (socket !== current || stopped) return;
        socket = null;
        if ([4001, 1008].includes(event.code)) {
          stopped = true;
          onStatus('offline', 'Sign in to ANT, then reopen this window');
          return;
        }
        onStatus('offline', 'Disconnected — reconnecting…');
        reconnect();
      };
      current.onerror = () => {
        if (socket === current) onStatus('offline', 'Connection interrupted');
      };
    }
    window.addEventListener('beforeunload', stop);
    return { connect, stop, get socket() { return socket; } };
  };
})();
