/* Manual light/dark toggle. Stores an explicit choice; with none, the system preference applies. */
(function () {
  var KEY = 'ekagra-theme', root = document.documentElement, mq = window.matchMedia('(prefers-color-scheme: dark)'), memory = null;
  function stored() {
    try { var v = localStorage.getItem(KEY); if (v === 'light' || v === 'dark') return v; } catch (e) {}
    return memory;
  }
  function effective() { return stored() || (mq.matches ? 'dark' : 'light'); }
  function sync() {
    var mode = effective();
    document.querySelectorAll('[data-theme-toggle]').forEach(function (button) {
      var label = mode === 'dark' ? 'Switch to light mode' : 'Switch to dark mode';
      button.setAttribute('data-mode', mode); button.setAttribute('aria-label', label); button.setAttribute('title', label);
    });
  }
  function apply() {
    var choice = stored();
    if (choice) root.setAttribute('data-theme', choice); else root.removeAttribute('data-theme');
    sync();
  }
  document.addEventListener('click', function (event) {
    var button = event.target.closest && event.target.closest('[data-theme-toggle]');
    if (!button) return;
    var next = effective() === 'dark' ? 'light' : 'dark';
    memory = next;
    try { localStorage.setItem(KEY, next); } catch (e) {}
    apply();
  });
  if (mq.addEventListener) mq.addEventListener('change', sync);
  var initial = stored(); if (initial) root.setAttribute('data-theme', initial);
  document.addEventListener('DOMContentLoaded', sync);
})();
