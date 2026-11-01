/* Consent gate for the landing page: Continue opens the consent modal; the ID form appears only after acknowledgement. */
(function () {
  'use strict';
  var modal = document.getElementById('consent-modal');
  var openButton = document.getElementById('open-consent');
  var ack = document.getElementById('consent-ack');
  var confirmButton = document.getElementById('consent-confirm');
  var cancelButton = document.getElementById('consent-cancel');
  var closeButton = document.getElementById('consent-close');
  var beginBox = document.getElementById('begin-box');
  var entryBox = document.getElementById('id-entry');
  var idInput = document.getElementById('participant-code');
  var form = document.getElementById('join-form');
  var body = document.getElementById('consent-body');
  var title = document.getElementById('consent-title');
  if (!modal || !openButton || !ack || !confirmButton || !beginBox || !entryBox || !form) return;

  var acknowledged = false;
  var sync = function () { confirmButton.disabled = !ack.checked; };
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
  var reveal = function () {
    beginBox.hidden = true;
    entryBox.hidden = false;
    if (idInput) idInput.focus();
  };

  openButton.addEventListener('click', show);
  ack.addEventListener('change', sync);
  confirmButton.addEventListener('click', function () {
    if (!ack.checked) return;
    acknowledged = true;
    hide();
    reveal();
  });
  [cancelButton, closeButton].forEach(function (button) { if (button) button.addEventListener('click', hide); });
  modal.addEventListener('close', onClosed); // also covers the Escape key
  form.addEventListener('submit', function (event) {
    if (!acknowledged || !ack.checked) { event.preventDefault(); entryBox.hidden = true; beginBox.hidden = false; acknowledged = false; show(); }
  });
  sync();
})();
