const logoutBtn = document.getElementById('logout-btn');

const modalOverlay = document.getElementById('modal-overlay');
const modalTitle = document.getElementById('modal-title');
const modalMessage = document.getElementById('modal-message');
const modalExtra = document.getElementById('modal-extra');
const modalError = document.getElementById('modal-error');
const modalCancel = document.getElementById('modal-cancel');
const modalConfirm = document.getElementById('modal-confirm');

let modalResolve = null;
let modalVerifyInput = null;

function closeModal(result = false) {
  if (!modalOverlay) return;
  modalOverlay.classList.add('hidden');
  modalOverlay.setAttribute('aria-hidden', 'true');
  modalExtra.innerHTML = '';
  modalExtra.classList.add('hidden');
  modalError.classList.add('hidden');
  modalError.textContent = '';
  modalConfirm.disabled = false;
  modalConfirm.classList.remove('btn-danger');
  modalConfirm.classList.add('btn-primary');
  document.body.classList.remove('modal-open');
  if (modalResolve) {
    const resolve = modalResolve;
    modalResolve = null;
    resolve(result);
  }
}

function openModal(options) {
  return new Promise((resolve) => {
    modalResolve = resolve;
    modalTitle.textContent = options.title || 'Bevestigen';
    modalMessage.textContent = options.message || '';
    modalCancel.textContent = options.cancelText || 'Annuleren';
    modalConfirm.textContent = options.confirmText || 'Bevestigen';

    modalConfirm.classList.toggle('btn-danger', !!options.danger);
    modalConfirm.classList.toggle('btn-primary', !options.danger);

    modalExtra.innerHTML = '';
    modalExtra.classList.add('hidden');
    modalError.classList.add('hidden');
    modalVerifyInput = null;

    if (options.verifyValue) {
      modalExtra.classList.remove('hidden');
      modalExtra.innerHTML = `
        <label class="modal-verify-label">
          <span id="modal-verify-label-text"></span>
          <input type="text" id="modal-verify-input" class="modal-verify-input" autocomplete="off" spellcheck="false" placeholder="${options.verifyPlaceholder || ''}">
        </label>
      `;
      document.getElementById('modal-verify-label-text').innerHTML = options.verifyLabel || 'Typ ter bevestiging:';
      modalVerifyInput = document.getElementById('modal-verify-input');
      modalConfirm.disabled = true;
      modalVerifyInput.addEventListener('input', () => {
        modalConfirm.disabled = modalVerifyInput.value.trim() !== options.verifyValue;
        modalError.classList.add('hidden');
      });
      modalVerifyInput.addEventListener('keydown', (e) => {
        if (e.key === 'Enter' && !modalConfirm.disabled) {
          e.preventDefault();
          modalConfirm.click();
        }
      });
      setTimeout(() => modalVerifyInput.focus(), 50);
    }

    modalOverlay.classList.remove('hidden');
    modalOverlay.setAttribute('aria-hidden', 'false');
    document.body.classList.add('modal-open');
  });
}

if (modalCancel) {
  modalCancel.addEventListener('click', () => closeModal(false));
}

if (modalConfirm) {
  modalConfirm.addEventListener('click', () => {
    if (modalVerifyInput && modalVerifyInput.value.trim() === '') {
      modalError.textContent = 'Vul de verificatie in om door te gaan.';
      modalError.classList.remove('hidden');
      return;
    }
    closeModal(true);
  });
}

if (modalOverlay) {
  modalOverlay.addEventListener('click', (e) => {
    if (e.target === modalOverlay) closeModal(false);
  });
  document.addEventListener('keydown', (e) => {
    if (e.key === 'Escape' && !modalOverlay.classList.contains('hidden')) {
      closeModal(false);
    }
  });
}

window.showConfirm = function showConfirm(options) {
  return openModal({
    title: options.title,
    message: options.message,
    confirmText: options.confirmText || 'Bevestigen',
    cancelText: options.cancelText || 'Annuleren',
    danger: options.danger || false,
  });
};

window.showVerifyDelete = function showVerifyDelete(options) {
  return openModal({
    title: options.title || 'Verwijderen bevestigen',
    message: options.message,
    confirmText: options.confirmText || 'Permanent verwijderen',
    cancelText: options.cancelText || 'Annuleren',
    danger: true,
    verifyValue: options.verifyValue,
    verifyLabel: options.verifyLabel,
    verifyPlaceholder: options.verifyPlaceholder,
  });
};

window.showToast = function showToast(message, type = 'info') {
  const container = document.getElementById('toast-container');
  if (!container) return;
  const toast = document.createElement('div');
  toast.className = `toast toast-${type}`;
  toast.textContent = message;
  container.appendChild(toast);
  requestAnimationFrame(() => toast.classList.add('show'));
  setTimeout(() => {
    toast.classList.remove('show');
    setTimeout(() => toast.remove(), 300);
  }, 2500);
};

if (logoutBtn) {
  logoutBtn.addEventListener('click', async () => {
    const ok = await showConfirm({
      title: 'Uitloggen',
      message: 'Weet je zeker dat je wilt uitloggen?',
      confirmText: 'Uitloggen',
      cancelText: 'Annuleren',
    });
    if (!ok) return;
    const base = window.DB_BASE || '/db';
    await fetch(`${base}/api/logout`, { method: 'POST' });
    window.location.href = `${base}/login`;
  });
}
