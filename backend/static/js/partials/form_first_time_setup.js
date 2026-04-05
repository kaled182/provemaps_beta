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

/* ── expose globally (used by inline onchange) ── */
window.previewLogo = previewLogo;

/* ── Initial render ── */
goTo(1);
