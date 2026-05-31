// GameHub Client — shared singleton for all game pages
(function () {
  'use strict';

  // ─── Sound Manager ───────────────────────────────────────────────────────
  const SoundManager = {
    _audio: {},

    init() {
      const sounds = ['move', 'capture', 'check', 'game_over', 'eat', 'win', 'lose', 'click'];
      sounds.forEach(name => {
        const audio = new Audio(`/static/sounds/${name}.mp3`);
        audio.preload = 'auto';
        this._audio[name] = audio;
      });
    },

    play(name) {
      const map = { eat: 'capture', click: 'move', win: 'check', lose: 'game_over' };
      const key = map[name] || name;
      const audio = this._audio[key];
      if (audio) {
        audio.currentTime = 0;
        audio.play().catch(() => {});
      }
    },
  };

  // ─── Player Manager ─────────────────────────────────────────────────────
  const PlayerManager = {
    _current: localStorage.getItem('gamehub_player') || 'Dad',

    get() { return this._current; },

    set(name) {
      this._current = name;
      localStorage.setItem('gamehub_player', name);
      if (window.socket && window.socket.connected) {
        window.socket.emit('login', name);
      }
    },
  };

  // ─── Online Status ────────────────────────────────────────────────────────
  let _onlineCount = 0;
  const _statusListeners = [];

  function onOnlineStatusChange(fn) {
    _statusListeners.push(fn);
    fn(_onlineCount);
  }

  function notifyStatus(count) {
    _onlineCount = count;
    _statusListeners.forEach(fn => fn(count));
  }

  // ─── Socket ──────────────────────────────────────────────────────────────
  function connectSocket() {
    if (window.socket) return window.socket;

    const socket = io(window.location.origin, { transports: ['websocket'] });
    window.socket = socket;

    socket.on('connect', () => {
      const indicator = document.getElementById('online-indicator');
      if (indicator) indicator.innerHTML = '<i class="fas fa-circle text-green-500"></i> Online';
      // Use server-authenticated player if available, fall back to localStorage
      const player = window.__PLAYER__ || PlayerManager.get();
      socket.emit('login', player);
    });

    socket.on('disconnect', () => {
      const indicator = document.getElementById('online-indicator');
      if (indicator) indicator.innerHTML = '<i class="fas fa-circle text-slate-300"></i> Offline';
    });

    socket.on('updateOnlineStatus', (users) => {
      const count = Array.isArray(users) ? users.length : 0;
      const indicator = document.getElementById('online-indicator');
      if (indicator) indicator.innerHTML = `<span class="text-xs text-slate-500">${count} online</span>`;
      notifyStatus(count);
    });

    return socket;
  }

  // ─── Public API ──────────────────────────────────────────────────────────
  window.GameHub = {
    init() {
      SoundManager.init();
      connectSocket();
    },

    playSound(name) { SoundManager.play(name); },

    getPlayer() { return PlayerManager.get(); },
    setPlayer(name) { PlayerManager.set(name); },

    onOnlineStatusChange,

    get onlineCount() { return _onlineCount; },
  };

  if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', () => window.GameHub.init());
  } else {
    window.GameHub.init();
  }
})();