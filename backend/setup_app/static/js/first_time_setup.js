/* ────────────────────────────────────────────────────────────────
   First-time Setup Wizard
   Wait for DOM to be ready before executing
──────────────────────────────────────────────────────────────── */
document.addEventListener('DOMContentLoaded', function() {

/* ────────────────────────────────────────────────────────────────
   Wizard state
──────────────────────────────────────────────────────────────── */
let currentStep = 1;
const totalSteps = 6;
let direction = 'forward';

/* ────────────────────────────────────────────────────────────────
   Auth-type toggle (Zabbix step)
──────────────────────────────────────────────────────────────── */
function toggleAuthFields(type) {
    const tokenField  = document.getElementById('tokenField');
    const loginFields = document.getElementById('loginFields');

    if (type === 'token') {
        tokenField.classList.remove('hidden');
        loginFields.classList.add('hidden');
        tokenField.querySelector('input').required = true;
        loginFields.querySelectorAll('input').forEach(i => i.required = false);
    } else {
        tokenField.classList.add('hidden');
        loginFields.classList.remove('hidden');
        tokenField.querySelector('input').required = false;
        loginFields.querySelectorAll('input').forEach(i => i.required = true);
    }
}

/* ────────────────────────────────────────────────────────────────
   Logo upload & preview
──────────────────────────────────────────────────────────────── */
const logoInput    = document.getElementById('logoInput');
const uploadArea   = document.getElementById('uploadArea');
const previewArea  = document.getElementById('previewArea');
const logoPreview  = document.getElementById('logoPreview');
const logoNameEl   = document.getElementById('logoName');
const removeLogoBtn = document.getElementById('removeLogo');

logoInput.addEventListener('change', function (e) {
    const file = e.target.files[0];
    if (!file) return;

    if (file.size > 2 * 1024 * 1024) {
        alert('File too large! Maximum size is 2 MB.');
        logoInput.value = '';
        return;
    }
    if (!file.type.match('image/png')) {
        alert('Please upload a PNG image.');
        logoInput.value = '';
        return;
    }

    const reader = new FileReader();
    reader.onload = function (ev) {
        logoPreview.src   = ev.target.result;
        logoNameEl.textContent = file.name;
        uploadArea.classList.add('hidden');
        previewArea.classList.remove('hidden');
    };
    reader.readAsDataURL(file);
});

removeLogoBtn.addEventListener('click', function () {
    logoInput.value        = '';
    logoPreview.src        = '';
    logoNameEl.textContent = '';
    uploadArea.classList.remove('hidden');
    previewArea.classList.add('hidden');
});

/* ────────────────────────────────────────────────────────────────
   Progress bar
──────────────────────────────────────────────────────────────── */
function updateProgress() {
    const pct = (currentStep / totalSteps) * 100;
    document.getElementById('progressBar').style.width = pct + '%';
}

/* ────────────────────────────────────────────────────────────────
   Step indicator circles
──────────────────────────────────────────────────────────────── */
function updateStepIndicators() {
    document.querySelectorAll('.step-item').forEach((item, idx) => {
        const n = idx + 1;
        item.classList.remove('active', 'completed');
        if (n < currentStep)      item.classList.add('completed');
        else if (n === currentStep) item.classList.add('active');
    });
}

/* ────────────────────────────────────────────────────────────────
   Show a step with slide animation
──────────────────────────────────────────────────────────────── */
function showStep(step) {
    const animClass = direction === 'forward' ? 'fade-in-right' : 'fade-in-left';

    document.querySelectorAll('.wizard-step').forEach((el, idx) => {
        if (idx + 1 === step) {
            el.classList.add('active');
            el.classList.remove('fade-in-right', 'fade-in-left');
            void el.offsetWidth; // force reflow to re-trigger animation
            el.classList.add(animClass);
        } else {
            el.classList.remove('active', 'fade-in-right', 'fade-in-left');
        }
    });

    // Show / hide navigation buttons
    const prevBtn   = document.getElementById('prevBtn');
    const nextBtn   = document.getElementById('nextBtn');
    const submitBtn = document.getElementById('submitBtn');

    prevBtn.style.display   = step === 1          ? 'none' : 'inline-flex';
    nextBtn.style.display   = step === totalSteps ? 'none' : 'inline-flex';
    submitBtn.style.display = step === totalSteps ? 'inline-flex' : 'none';

    updateProgress();
    updateStepIndicators();
}

/* ────────────────────────────────────────────────────────────────
   Validate visible required fields in the current step
──────────────────────────────────────────────────────────────── */
function validateCurrentStep() {
    const stepEl = document.querySelector(`.wizard-step[data-step="${currentStep}"]`);
    const fields = stepEl.querySelectorAll('input[required]:not([type="hidden"])');

    for (const field of fields) {
        // Skip inputs that are visually hidden (inside a collapsed section)
        if (field.offsetParent === null) continue;

        if (!field.value.trim()) {
            field.focus();
            field.classList.add('field-error');
            setTimeout(() => field.classList.remove('field-error'), 2000);
            return false;
        }
    }
    return true;
}

/* ────────────────────────────────────────────────────────────────
   Navigation
──────────────────────────────────────────────────────────────── */
document.getElementById('nextBtn').addEventListener('click', function () {
    if (validateCurrentStep() && currentStep < totalSteps) {
        direction = 'forward';
        currentStep++;
        showStep(currentStep);
        console.log('Moved to step ' + currentStep);
    }
});

document.getElementById('prevBtn').addEventListener('click', function () {
    if (currentStep > 1) {
        direction = 'backward';
        currentStep--;
        showStep(currentStep);
    }
});

document.getElementById('setupForm').addEventListener('submit', function (e) {
    if (!validateCurrentStep()) {
        e.preventDefault();
    }
});

/* Keyboard shortcuts */
document.addEventListener('keydown', function (e) {
    if (e.key === 'ArrowRight' && currentStep < totalSteps) {
        document.getElementById('nextBtn').click();
    } else if (e.key === 'ArrowLeft' && currentStep > 1) {
        document.getElementById('prevBtn').click();
    }
});

/* ────────────────────────────────────────────────────────────────
   Init
──────────────────────────────────────────────────────────────── */
toggleAuthFields('token');
showStep(1);

console.log('First-time setup wizard initialized');

}); // End DOMContentLoaded