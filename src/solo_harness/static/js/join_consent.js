/* Join flow: Welcome -> Student details -> Error Detection introduction -> Study overview -> How the learning works -> consent
   acknowledgement -> POST /join.
   Nothing is submitted (and no session is created) until the student has entered a University ID AND acknowledged
   the study information. The consent dialog and the form field names are unchanged. */
(function () {
  'use strict';
  var modal = document.getElementById('consent-modal');
  var ack = document.getElementById('consent-ack');
  var confirmButton = document.getElementById('consent-confirm');
  var cancelButton = document.getElementById('consent-cancel');
  var closeButton = document.getElementById('consent-close');
  var welcomeStep = document.getElementById('welcome-step');
  var startButton = document.getElementById('start-details');
  var backButton = document.getElementById('back-to-welcome');
  var detailsStep = document.getElementById('id-entry');
  var introStep = document.getElementById('intro-step');
  var overviewStep = document.getElementById('overview-step');
  var structureStep = document.getElementById('structure-step');
  var openConsentButton = document.getElementById('open-consent');
  var backToDetails = document.getElementById('back-to-details');
  var introContinue = document.getElementById('intro-continue');
  var backToIntro = document.getElementById('back-to-intro');
  var overviewContinue = document.getElementById('overview-continue');
  var backToOverview = document.getElementById('back-to-overview');
  var idInput = document.getElementById('participant-code');
  var idError = document.getElementById('participant-code-error');
  var form = document.getElementById('join-form');
  var body = document.getElementById('consent-body');
  var title = document.getElementById('consent-title');
  if (!modal || !ack || !confirmButton || !welcomeStep || !detailsStep || !introStep || !overviewStep || !structureStep || !introContinue || !overviewContinue || !openConsentButton || !form || !idInput) return;

  var acknowledged = false;
  var sync = function () { confirmButton.disabled = !ack.checked; };

  var steps = { welcome: welcomeStep, details: detailsStep, intro: introStep, overview: overviewStep, structure: structureStep };
  var showStep = function (name) {
    Object.keys(steps).forEach(function (key) { steps[key].hidden = key !== name; });
    var target = steps[name].querySelector('h1, h2');
    if (target) target.focus();
    if (name === 'details') idInput.focus();
  };

  var show = function () {
    if (typeof modal.showModal === 'function') modal.showModal(); else modal.setAttribute('open', '');
    if (body) body.scrollTop = 0;
    if (title) title.focus();
  };
  var hide = function () {
    if (typeof modal.close === 'function') modal.close(); else { modal.removeAttribute('open'); onClosed(); }
  };
  var onClosed = function () {
    if (acknowledged) return;
    ack.checked = false; sync(); // closing without acknowledging leaves nothing recorded
  };

  var ageInput = document.getElementById('participant-age');
  var genderInput = document.getElementById('participant-gender');
  var educationInput = document.getElementById('participant-education');
  var check = function (input, ok) {
    if (!input) return true;
    var err = document.getElementById(input.id + '-error');
    if (err) err.hidden = ok;
    input.setAttribute('aria-invalid', ok ? 'false' : 'true');
    return ok;
  };
  var ageOk = function () {
    var v = ageInput ? ageInput.value.trim() : '';
    var n = Number(v);
    return v !== '' && /^\d+$/.test(v) && n >= 5 && n <= 120;
  };
  var idValid = function () { return check(idInput, idInput.value.trim() !== ''); };
  // Validates every demographics field (all shown), returning the first invalid input or null.
  var firstInvalid = function () {
    var results = [
      [idInput, idValid()],
      [ageInput, check(ageInput, ageOk())],
      [genderInput, check(genderInput, !genderInput || genderInput.value !== '')],
      [educationInput, check(educationInput, !educationInput || educationInput.value !== '')]
    ];
    for (var i = 0; i < results.length; i++) if (!results[i][1]) return results[i][0];
    return null;
  };

  startButton.addEventListener('click', function () { showStep('details'); });
  if (backButton) backButton.addEventListener('click', function () { showStep('welcome'); });
  if (backToDetails) backToDetails.addEventListener('click', function () { showStep('details'); });
  introContinue.addEventListener('click', function () { showStep('overview'); });
  if (backToIntro) backToIntro.addEventListener('click', function () { showStep('intro'); });
  overviewContinue.addEventListener('click', function () { showStep('structure'); });
  if (backToOverview) backToOverview.addEventListener('click', function () { showStep('overview'); });
  openConsentButton.addEventListener('click', show); // consent opens only from the last information step's Continue
  idInput.addEventListener('input', function () { if (idError && !idError.hidden) idValid(); });
  if (ageInput) ageInput.addEventListener('input', function () { var e = document.getElementById('participant-age-error'); if (e && !e.hidden) check(ageInput, ageOk()); });
  [genderInput, educationInput].forEach(function (el) { if (el) el.addEventListener('change', function () { check(el, el.value !== ''); }); });
  ack.addEventListener('change', sync);

  // Continue on the details step: validate the ID and move to the introduction. The real submit only happens
  // after the consent acknowledgement (the form is submitted programmatically from the consent confirm button).
  form.addEventListener('submit', function (event) {
    if (acknowledged && ack.checked) return; // acknowledged: let the normal POST /join proceed
    event.preventDefault();
    var bad = firstInvalid();
    if (bad) { bad.focus(); return; }
    showStep('intro');
  });

  confirmButton.addEventListener('click', function () {
    if (!ack.checked) return;
    acknowledged = true;
    hide();
    if (typeof form.requestSubmit === 'function') form.requestSubmit(); else form.submit();
  });
  [cancelButton, closeButton].forEach(function (button) { if (button) button.addEventListener('click', hide); });
  modal.addEventListener('close', onClosed); // also covers the Escape key
  sync();
})();
