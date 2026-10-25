/* Field-scoped, coarse keyboard dynamics. Raw key/code/value never leave this browser. */
(() => {
  'use strict';
  const telemetry = window.ParticipantTelemetry;
  if (!telemetry) return;
  const schema = 'keyboard-1.0';
  let sequence = 0;
  let nextPressId = 0;
  let queue = [];
  let flushing = false;
  const activePresses = new Map(); // event.code is in-memory pairing state only.

  const context = (field) => {
    const root = document.querySelector('#session-main');
    const section = root?.querySelector('[data-section-number]');
    const activityNodes = root ? [...root.querySelectorAll('[data-teaching-activity-number]')] : [];
    const activity = root?.querySelector('.composer[data-teaching-activity-number]') || activityNodes[activityNodes.length - 1];
    return {
      section_number: section ? Number(section.dataset.sectionNumber) : null,
      teaching_activity_number: activity?.dataset.teachingActivityNumber ? Number(activity.dataset.teachingActivityNumber) : null,
      surface: field.id === 'learner-text' ? 'TUTOR_RESPONSE' : 'ASSESSMENT_RESPONSE',
    };
  };
  const keyClass = (key) => {
    if (key === ' ') return 'SPACE';
    if (key === 'Enter') return 'ENTER';
    if (key === 'Backspace') return 'BACKSPACE';
    if (key === 'Delete') return 'DELETE';
    if (key === 'Tab') return 'TAB';
    if (/^Arrow/.test(key)) return 'ARROW';
    if (['Alt', 'AltGraph', 'Control', 'Meta', 'Shift'].includes(key)) return 'MODIFIER';
    if (key.length === 1) {
      if (/^\d$/u.test(key)) return 'DIGIT';
      if (/^\p{L}$/u.test(key)) return 'CHAR';
      return 'PUNCTUATION';
    }
    return 'OTHER';
  };
  const post = (body, beacon = false) => {
    const text = JSON.stringify(body);
    if (beacon && navigator.sendBeacon && text.length < 60000) {
      return navigator.sendBeacon('/session/telemetry/keyboard', new Blob([text], { type: 'application/json' }));
    }
    return fetch('/session/telemetry/keyboard', { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: text, keepalive: beacon })
      .then((response) => response.ok).catch(() => false);
  };
  const flush = (beacon = false) => {
    if (flushing || !queue.length) return;
    flushing = true;
    const events = queue.splice(0, 100);
    Promise.resolve(post({
      browser_run_id: telemetry.runId, batch_id: crypto.randomUUID(), run_metadata: telemetry.metadata, events,
    }, beacon)).then((ok) => { if (!ok && !beacon) queue.unshift(...events); })
      .finally(() => { flushing = false; if (queue.length && !beacon) setTimeout(flush, 250); });
  };
  const capture = (event, field) => {
    const pairingKey = event.code; // never serialized
    let pressId = activePresses.get(pairingKey);
    if (event.type === 'keydown' && !event.repeat) {
      pressId = ++nextPressId;
      activePresses.set(pairingKey, pressId);
    }
    // A keyup without a locally observed non-repeat keydown is discarded: no invented press.
    if (!pressId) return;
    if (event.type === 'keyup') activePresses.delete(pairingKey);
    const c = context(field);
    queue.push({
      telemetry_schema_version: schema, browser_run_id: telemetry.runId, client_sequence: ++sequence,
      event_type: event.type === 'keydown' ? 'KEYDOWN' : 'KEYUP', press_id: pressId,
      client_event_at_utc_ms: Date.now(), client_performance_ms: performance.now(),
      performance_time_origin_ms: telemetry.performanceTimeOrigin, section_number: c.section_number,
      teaching_activity_number: c.teaching_activity_number, surface: c.surface, key_class: keyClass(event.key),
      flags: { repeat: event.repeat, is_composing: event.isComposing, ctrl: event.ctrlKey, alt: event.altKey, shift: event.shiftKey, meta: event.metaKey },
    });
    if (queue.length >= 100) flush();
  };
  const attach = () => document.querySelectorAll('#learner-text, #assessment-response').forEach((field) => {
    if (field.dataset.keyboardDynamicsAttached) return;
    field.dataset.keyboardDynamicsAttached = 'true';
    field.addEventListener('keydown', (event) => capture(event, field));
    field.addEventListener('keyup', (event) => capture(event, field));
  });
  telemetry.onRender(attach);
  addEventListener('DOMContentLoaded', attach);
  addEventListener('pagehide', () => flush(true));
  setInterval(flush, 5000);
})();
