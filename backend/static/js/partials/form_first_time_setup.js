/* ──────────────────────────────────────────────
   First-Time Setup — Multi-Step Wizard
   ────────────────────────────────────────────── */

const TOTAL_STEPS = 6;
let currentStep = 1;

/* ── DOM refs ── */
const panels      = () => document.querySelectorAll('.step-panel');
const circles     = () => document.querySelectorAll('.step-circle');
const labels      = () => document.querySelectorAll('.step-label');
const connectors  = () => document.querySelectorAll('.step-connector');
const dots        = () => document.querySelectorAll('.dot');
const btnPrev     = document.getElementById('btn-prev');
const btnNext     = document.getElementById('btn-next');
const btnSubmit   = document.getElementById('btn-submit');

/* ══════════════════════════════════════════════
   STEP NAVIGATION
══════════════════════════════════════════════ */

function goTo(step) {
  const prev = currentStep;
  currentStep = Math.max(1, Math.min(TOTAL_STEPS, step));

  updatePanels();
  updateProgressBar(prev);
  updateDots();
  updateButtons();

  if (currentStep === TOTAL_STEPS) populateSummary();
}

function updatePanels() {
  panels().forEach(p => {
    const n = parseInt(p.dataset.panel, 10);
    p.classList.toggle('hidden', n !== currentStep);
  });
}

function updateProgressBar(prevStep) {
  circles().forEach((circle, i) => {
    const step = i + 1;
    const label = labels()[i];

    if (step < currentStep) {
      // completed
      circle.className = circle.className
        .replace(/border-\S+/g, '')
        .replace(/bg-\S+/g, '')
        .replace(/text-\S+/g, '')
        .trim();
      circle.classList.add(
        'border-emerald-500', 'bg-emerald-600', 'text-white',
        'step-circle', 'w-10', 'h-10', 'rounded-full', 'flex',
        'items-center', 'justify-center', 'border-2', 'transition-all', 'duration-300'
      );
      label.className = label.className.replace(/text-\S+/g, '').trim();
      label.classList.add('text-emerald-400', 'text-xs', 'font-medium', 'transition-colors', 'duration-300', 'step-label');
    } else if (step === currentStep) {
      // active
      circle.className = circle.className
        .replace(/border-\S+/g, '')
        .replace(/bg-\S+/g, '')
        .replace(/text-\S+/g, '')
        .trim();
      circle.classList.add(
        'border-blue-500', 'bg-blue-600', 'text-white',
        'step-circle', 'w-10', 'h-10', 'rounded-full', 'flex',
        'items-center', 'justify-center', 'border-2', 'transition-all', 'duration-300'
      );
      label.className = label.className.replace(/text-\S+/g, '').trim();
      label.classList.add('text-blue-400', 'text-xs', 'font-medium', 'transition-colors', 'duration-300', 'step-label');
    } else {
      // pending
      circle.className = circle.className
        .replace(/border-\S+/g, '')
        .replace(/bg-\S+/g, '')
        .replace(/text-\S+/g, '')
        .trim();
      circle.classList.add(
        'border-gray-600', 'bg-gray-800', 'text-gray-400',
        'step-circle', 'w-10', 'h-10', 'rounded-full', 'flex',
        'items-center', 'justify-center', 'border-2', 'transition-all', 'duration-300'
      );
      label.className = label.className.replace(/text-\S+/g, '').trim();
      label.classList.add('text-gray-500', 'text-xs', 'font-medium', 'transition-colors', 'duration-300', 'step-label');
    }
  });

  connectors().forEach(conn => {
    const afterStep = parseInt(conn.dataset.after, 10);
    if (afterStep < currentStep) {
      conn.classList.remove('bg-gray-700');
      conn.classList.add('bg-emerald-500');
    } else {
      conn.classList.remove('bg-emerald-500');
      conn.classList.add('bg-gray-700');
    }
  });
}

function updateDots() {
  dots().forEach(dot => {
    const n = parseInt(dot.dataset.dot, 10);
    dot.classList.remove('bg-blue-500', 'bg-gray-600', 'w-4', 'w-2');
    if (n === currentStep) {
      dot.classList.add('bg-blue-500', 'w-4');
    } else {
      dot.classList.add('bg-gray-600', 'w-2');
    }
  });
}

function updateButtons() {
  btnPrev.disabled = currentStep === 1;

  if (currentStep === TOTAL_STEPS) {
    btnNext.classList.add('hidden');
    btnSubmit.classList.remove('hidden');
  } else {
    btnNext.classList.remove('hidden');
    btnSubmit.classList.add('hidden');
  }
}

/* ── Button listeners ── */
btnPrev.addEventListener('click', () => goTo(currentStep - 1));
btnNext.addEventListener('click', () => goTo(currentStep + 1));

/* ══════════════════════════════════════════════
   SUMMARY (step 6)
══════════════════════════════════════════════ */

function populateSummary() {
  const company   = document.getElementById('company_name')?.value || '—';
  const zabbixUrl = document.getElementById('zabbix_url')?.value   || '—';

  const mapChecked = document.querySelector('input[name="map_provider"]:checked');
  const mapLabels  = { osm: 'OpenStreetMap', mapbox: 'Mapbox', google: 'Google Maps' };
  const mapText    = mapChecked ? (mapLabels[mapChecked.value] || mapChecked.value) : '—';

  const dbHost = document.querySelector('input[name="db_host"]')?.value || '';
  const dbName = document.querySelector('input[name="db_name"]')?.value || '';
  const dbText = dbHost && dbName ? `${dbName} @ ${dbHost}` : (dbHost || dbName || '—');

  const el = id => document.getElementById(id);
  if (el('summary-company')) el('summary-company').textContent = company;
  if (el('summary-zabbix'))  el('summary-zabbix').textContent  = zabbixUrl;
  if (el('summary-map'))     el('summary-map').textContent     = mapText;
  if (el('summary-db'))      el('summary-db').textContent      = dbText;
}

/* ══════════════════════════════════════════════
   AUTH TYPE CARDS (Zabbix — step 2)
══════════════════════════════════════════════ */

const authOptions = document.querySelectorAll('.auth-option');
const fieldToken  = document.getElementById('field_token');
const fieldLogin  = document.getElementById('field_login');

function applyAuthStyle(selected) {
  authOptions.forEach(opt => {
    const radio = opt.querySelector('input[type="radio"]');
    const indicator = opt.querySelector('.radio-indicator');
    const isSelected = radio === selected;

    opt.classList.toggle('border-blue-500', isSelected);
    opt.classList.toggle('bg-blue-500/10',  isSelected);
    opt.classList.toggle('border-gray-600', !isSelected);
    opt.classList.toggle('bg-gray-800',     !isSelected);

    if (indicator) {
      if (isSelected) {
        indicator.classList.add('border-blue-500', 'bg-blue-500');
        indicator.innerHTML = '<div class="w-2 h-2 rounded-full bg-white"></div>';
      } else {
        indicator.classList.remove('border-blue-500', 'bg-blue-500');
        indicator.innerHTML = '';
      }
    }
  });

  const isToken = selected && selected.value === 'token';
  if (fieldToken) fieldToken.classList.toggle('hidden', !isToken);
  if (fieldLogin) fieldLogin.classList.toggle('hidden', isToken);
}

authOptions.forEach(opt => {
  opt.addEventListener('click', () => {
    const radio = opt.querySelector('input[type="radio"]');
    if (radio) {
      radio.checked = true;
      applyAuthStyle(radio);
    }
  });
});

// init
const checkedAuth = document.querySelector('input[name="auth_type"]:checked');
if (checkedAuth) applyAuthStyle(checkedAuth);

/* ══════════════════════════════════════════════
   MAP PROVIDER CARDS (step 3)
══════════════════════════════════════════════ */

const mapOptions       = document.querySelectorAll('.map-option');
const fieldMapboxToken = document.getElementById('field_mapbox_token');
const fieldGoogleKey   = document.getElementById('field_google_key');

function applyMapStyle(selected) {
  mapOptions.forEach(opt => {
    const radio = opt.querySelector('input[type="radio"]');
    const indicator = opt.querySelector('.map-radio-indicator');
    const isSelected = radio === selected;

    // colour: osm → green, others → blue
    const isOsm = radio && radio.value === 'osm';
    const activeColor = isOsm ? 'green' : 'blue';

    opt.classList.toggle(`border-${activeColor}-500`, isSelected);
    opt.classList.toggle(`bg-${activeColor}-500/10`,  isSelected);
    opt.classList.toggle('border-gray-600', !isSelected);
    opt.classList.toggle('bg-gray-800',     !isSelected);

    if (indicator) {
      if (isSelected) {
        indicator.classList.add(`border-${activeColor}-500`, `bg-${activeColor}-500`);
        indicator.innerHTML = '<div class="w-2.5 h-2.5 rounded-full bg-white"></div>';
      } else {
        indicator.classList.remove(
          'border-green-500', 'bg-green-500',
          'border-blue-500',  'bg-blue-500'
        );
        indicator.innerHTML = '';
      }
    }
  });

  const val = selected ? selected.value : 'osm';
  if (fieldMapboxToken) fieldMapboxToken.classList.toggle('hidden', val !== 'mapbox');
  if (fieldGoogleKey)   fieldGoogleKey.classList.toggle('hidden',   val !== 'google');
}

mapOptions.forEach(opt => {
  opt.addEventListener('click', () => {
    const radio = opt.querySelector('input[type="radio"]');
    if (radio) {
      radio.checked = true;
      applyMapStyle(radio);
    }
  });
});

// init
const checkedMap = document.querySelector('input[name="map_provider"]:checked');
applyMapStyle(checkedMap || null);

/* ══════════════════════════════════════════════
   LOGO PREVIEW
══════════════════════════════════════════════ */

function previewLogo(input) {
  const preview = document.getElementById('logo-preview');
  const labelEl = document.getElementById('logo-label');
  if (input.files && input.files[0]) {
    const reader = new FileReader();
    reader.onload = e => {
      if (preview) {
        preview.src = e.target.result;
        preview.classList.remove('hidden');
      }
      if (labelEl) labelEl.textContent = input.files[0].name;
    };
    reader.readAsDataURL(input.files[0]);
  }
}

/* ══════════════════════════════════════════════
   PASSWORD STRENGTH INDICATOR (step 4)
══════════════════════════════════════════════ */

function checkPasswordStrength(value) {
  const bars  = [1, 2, 3, 4].map(i => document.getElementById(`bar-${i}`));
  const label = document.getElementById('strength-label');
  if (!bars[0] || !label) return;

  const checks = [
    value.length >= 12,
    /[A-Z]/.test(value) && /[a-z]/.test(value),
    /[0-9]/.test(value),
    /[^A-Za-z0-9]/.test(value),
  ];
  const score = checks.filter(Boolean).length;

  const colors = ['bg-red-500', 'bg-orange-500', 'bg-yellow-500', 'bg-emerald-500'];
  const msgs   = [
    '<span class="text-red-400">Muito fraca</span>',
    '<span class="text-orange-400">Fraca — adicione números e símbolos</span>',
    '<span class="text-yellow-400">Razoável — adicione um símbolo especial</span>',
    '<span class="text-emerald-400 font-medium">Forte ✓</span>',
  ];

  bars.forEach((bar, i) => {
    bar.className = 'h-1.5 flex-1 rounded-full transition-colors duration-300 ';
    bar.className += i < score ? colors[score - 1] : 'bg-gray-700';
  });

  label.innerHTML = value.length === 0
    ? '<span class="text-gray-500">Mínimo: 12 caracteres · maiúscula · minúscula · número · símbolo</span>'
    : msgs[score - 1] || msgs[0];
}

function generateDbPassword() {
  const upper   = 'ABCDEFGHJKLMNPQRSTUVWXYZ';   // sem I, O (confusos)
  const lower   = 'abcdefghjkmnpqrstuvwxyz';     // sem i, l, o
  const digits  = '23456789';                    // sem 0, 1
  const symbols = '!@#$%&*-_=+?';
  const all     = upper + lower + digits + symbols;

  const len = 64;
  const arr = new Uint32Array(len + 8);
  crypto.getRandomValues(arr);

  // Garante pelo menos 1 de cada categoria
  const pick = (charset, randIdx) => charset[arr[randIdx] % charset.length];
  let pass = [
    pick(upper,   0),
    pick(upper,   1),
    pick(lower,   2),
    pick(lower,   3),
    pick(digits,  4),
    pick(digits,  5),
    pick(symbols, 6),
    pick(symbols, 7),
  ];

  // Preenche o resto com chars aleatórios do conjunto completo
  for (let i = 8; i < len; i++) {
    pass.push(all[arr[i] % all.length]);
  }

  // Embaralha com Fisher-Yates usando mais entropia
  const shuffle = new Uint32Array(len);
  crypto.getRandomValues(shuffle);
  for (let i = len - 1; i > 0; i--) {
    const j = shuffle[i] % (i + 1);
    [pass[i], pass[j]] = [pass[j], pass[i]];
  }

  const password = pass.join('');
  const input = document.getElementById('db_password');
  if (input) {
    input.value = password;
    input.type = 'text';          // mostra para o usuário confirmar
    checkPasswordStrength(password);
  }
}

function copyDbPassword() {
  const input = document.getElementById('db_password');
  if (!input || !input.value) return;
  navigator.clipboard.writeText(input.value).then(() => {
    const btn = document.getElementById('btn-copy-pass');
    if (!btn) return;
    const orig = btn.innerHTML;
    btn.innerHTML = '<svg class="w-4 h-4 text-emerald-400" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M5 13l4 4L19 7"/></svg>';
    setTimeout(() => { btn.innerHTML = orig; }, 1500);
  });
}

function togglePasswordVisibility(inputId, btn) {
  const input = document.getElementById(inputId);
  if (!input) return;
  const isText = input.type === 'text';
  input.type = isText ? 'password' : 'text';
  const eyeOpen  = 'M15 12a3 3 0 11-6 0 3 3 0 016 0zM2.458 12C3.732 7.943 7.523 5 12 5c4.478 0 8.268 2.943 9.542 7-1.274 4.057-5.064 7-9.542 7-4.477 0-8.268-2.943-9.542-7z';
  const eyeClosed = 'M13.875 18.825A10.05 10.05 0 0112 19c-4.478 0-8.268-2.943-9.543-7a9.97 9.97 0 011.563-3.029m5.858.908a3 3 0 114.243 4.243M9.878 9.878l4.242 4.242M9.88 9.88l-3.29-3.29m7.532 7.532l3.29 3.29M3 3l3.59 3.59m0 0A9.953 9.953 0 0112 5c4.478 0 8.268 2.943 9.543 7a10.025 10.025 0 01-4.132 5.411m0 0L21 21';
  btn.querySelector('path:first-child').setAttribute('d', isText ? eyeOpen.split('z')[0] + 'z' : eyeClosed.split('m')[0]);
}

/* ── expose globally ── */
window.previewLogo = previewLogo;
window.checkPasswordStrength = checkPasswordStrength;
window.togglePasswordVisibility = togglePasswordVisibility;
window.generateDbPassword = generateDbPassword;
window.copyDbPassword = copyDbPassword;

/* ══════════════════════════════════════════════
   DOMAIN FIELD (step 5) — mostra e-mail se domínio preenchido
══════════════════════════════════════════════ */
const domainInput    = document.getElementById('domain_name');
const emailWrap      = document.getElementById('certbot-email-wrap');

if (domainInput && emailWrap) {
  domainInput.addEventListener('input', () => {
    emailWrap.classList.toggle('hidden', domainInput.value.trim() === '');
  });
}

/* ── Initial render ── */
(function () {
  const form = document.getElementById('setup-form');
  const errorStep = form && parseInt(form.dataset.errorStep, 10);
  goTo(errorStep > 0 ? errorStep : 1);

  // Auto-dismiss error toast after 8 s
  const toast = document.getElementById('setup-error-toast');
  if (toast) setTimeout(() => toast.remove(), 8000);
})();
