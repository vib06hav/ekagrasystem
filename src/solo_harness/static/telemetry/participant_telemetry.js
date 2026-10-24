/* Local rrweb recorder. It intentionally captures no custom keyboard telemetry. */
(() => {
  'use strict';
  const schema = '1.0';
  const rrwebVersion = '2.1.7';
  const runId = crypto.randomUUID();
  const origin = performance.timeOrigin;
  const started = Date.now();
  const metadata = {
    browser_run_id: runId,
    page_path: location.pathname,
    recording_started_client_utc_ms: started,
    performance_time_origin_ms: origin,
    initial_performance_ms: performance.now(),
    telemetry_schema_version: schema,
    rrweb_version: rrwebVersion,
  };
  let rrSequence = 0;
  let uiSequence = 0;
  let rrQueue = [];
  let uiQueue = [];
  let flushing = false;
  let wasProcessing = false;
  const seen = new Set();
  const renderObservers = [];

  const context = () => {
    const root = document.querySelector('#session-main');
    const section = root?.querySelector('[data-section-number]');
    return {
      section_number: section ? Number(section.dataset.sectionNumber) : null,
      teaching_activity_number: section?.dataset.teachingActivityNumber ? Number(section.dataset.teachingActivityNumber) : null,
    };
  };
  const enqueueUi = (eventType, surface, payload = {}) => {
    const c = context();
    uiQueue.push({
      event_type: eventType, surface, payload, browser_run_id: runId,
      client_sequence: ++uiSequence, client_event_at_utc_ms: Date.now(),
      client_performance_ms: performance.now(), performance_time_origin_ms: origin,
      section_number: c.section_number, teaching_activity_number: c.teaching_activity_number,
    });
    if (uiQueue.length >= 20) flush();
  };
  const post = (url, body, beacon = false) => {
    const text = JSON.stringify(body);
    if (beacon && navigator.sendBeacon && text.length < 60000) {
      return navigator.sendBeacon(url, new Blob([text], { type: 'application/json' }));
    }
    return fetch(url, { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: text, keepalive: beacon })
      .then((response) => response.ok).catch(() => false);
  };
  const flush = (beacon = false) => {
    if (flushing || (!rrQueue.length && !uiQueue.length)) return;
    flushing = true;
    const rr = rrQueue.splice(0, 100);
    const ui = uiQueue.splice(0, 50);
    const work = [];
    if (rr.length) work.push(Promise.resolve(post('/session/telemetry/rrweb', {
      telemetry_schema_version: schema, browser_run_id: runId, batch_id: crypto.randomUUID(), run_metadata: metadata, events: rr,
    }, beacon)).then((ok) => { if (!ok && !beacon) rrQueue.unshift(...rr); }));
    if (ui.length) work.push(Promise.resolve(post('/session/telemetry/ui-events', { events: ui }, beacon))
      .then((ok) => { if (!ok && !beacon) uiQueue.unshift(...ui); }));
    Promise.all(work).finally(() => { flushing = false; if ((rrQueue.length || uiQueue.length) && !beacon) setTimeout(flush, 250); });
  };
  const rendered = (key, type, surface, payload) => {
    if (seen.has(key)) return;
    seen.add(key);
    enqueueUi(type, surface, payload);
  };
  const observeRender = () => requestAnimationFrame(() => {
    const root = document.querySelector('#session-main');
    if (!root) return;
    const section = root.querySelector('[data-section-number]');
    const number = section?.dataset.sectionNumber || 'terminal';
    rendered(`session:${number}`, 'SESSION_PAGE_RENDERED', 'session');
    if (section) rendered(`section:${number}:${section.dataset.telemetryMode || ''}`, 'SECTION_RENDERED', 'section');
    const activityNodes = [...root.querySelectorAll('[data-teaching-activity-number]')];
    const activity = root.querySelector('.composer[data-teaching-activity-number]') || activityNodes[activityNodes.length - 1];
    if (activity) rendered(`activity:${number}:${activity.dataset.teachingActivityNumber}`, 'TEACHING_ACTIVITY_RENDERED', 'teaching');
    const processing = root.querySelector('[data-processing-kind]');
    if (processing && !wasProcessing) enqueueUi('PROCESSING_SHOWN', 'processing', { kind: processing.dataset.processingKind });
    if (!processing && wasProcessing) enqueueUi('PROCESSING_HIDDEN', 'session');
    wasProcessing = Boolean(processing);
    root.querySelectorAll('[data-tutor-message-sequence]').forEach((node) => rendered(
      `tutor:${number}:${activity?.dataset.teachingActivityNumber || ''}:${node.dataset.tutorMessageSequence}`, 'TUTOR_MESSAGE_RENDERED', 'teaching', { message_sequence: Number(node.dataset.tutorMessageSequence) },
    ));
    if (root.querySelector('[data-telemetry-surface="assessment"]')) rendered(`assessment:${number}:${activity?.dataset.teachingActivityNumber || ''}`, 'ASSESSMENT_RENDERED', 'assessment');
    if (root.querySelector('[data-assessment-completed-marker]')) rendered(`assessment-marker:${number}:${activity?.dataset.teachingActivityNumber || ''}`, 'ASSESSMENT_COMPLETED_MARKER_RENDERED', 'section');
    if (root.querySelector('[data-generation-error]')) rendered(`error:${number}`, 'GENERATION_ERROR_RENDERED', 'error');
    if (root.querySelector('[data-section-complete]')) rendered(`complete:${number}`, 'SECTION_COMPLETE_RENDERED', 'section_complete');
    if (root.querySelector('[data-completed-section-review]')) rendered(`review:${number}`, 'COMPLETED_SECTION_REVIEW_OPENED', 'review');
    if (root.querySelector('[data-study-complete]')) rendered('study-complete', 'STUDY_COMPLETE_RENDERED', 'study_complete');
    renderObservers.forEach((observer) => observer());
  });
  const clickEvent = (event) => {
    const button = event.target.closest('button');
    if (!button) return;
    const form = button.closest('form');
    const action = form?.getAttribute('hx-post') || form?.getAttribute('action') || '';
    const events = {
      '/session/actions/begin': ['BEGIN_CLICKED', 'teaching'],
      '/session/actions/tutor-message': ['TUTOR_RESPONSE_SUBMIT_CLICKED', 'teaching'],
      '/session/actions/assessment-response': ['ASSESSMENT_RESPONSE_SUBMIT_CLICKED', 'assessment'],
      '/session/actions/retry': ['RETRY_CLICKED', 'error'],
      '/session/actions/next': ['NEXT_CLICKED', 'section_complete'],
      '/session/actions/finish': ['FINISH_CLICKED', 'section_complete'],
    };
    if (events[action]) enqueueUi(...events[action]);
  };
  document.addEventListener('click', clickEvent, true);
  window.ParticipantTelemetry = {
    runId, performanceTimeOrigin: origin, metadata,
    observeRender, flush,
    onRender(observer) { renderObservers.push(observer); },
  };
  if (window.rrwebRecord?.record) {
    window.rrwebRecord.record({
      emit: (rrwebEvent) => {
        rrQueue.push({ telemetry_schema_version: schema, browser_run_id: runId, sequence: ++rrSequence,
          client_emit_utc_ms: Date.now(), client_performance_ms: performance.now(), rrweb_event: rrwebEvent });
        if (rrQueue.length >= 100) flush();
      },
      maskAllInputs: true,
      sampling: { input: 'all' },
      maskTextSelector: '.message.learner',
      recordCanvas: false,
      recordCrossOriginIframes: false,
    });
  }
  setInterval(flush, 5000);
  addEventListener('pagehide', () => flush(true));
  addEventListener('DOMContentLoaded', observeRender);
})();
