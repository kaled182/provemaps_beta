    const authRadios = document.querySelectorAll('input[name="auth_type"]');
    const tokenField = document.getElementById('token_field');
    const loginFields = document.getElementById('login_fields');

    authRadios.forEach(radio => {
        radio.addEventListener('change', () => {
            if (radio.value === 'token') {
                tokenField.classList.remove('hidden');
                loginFields.classList.add('hidden');
            } else {
                tokenField.classList.add('hidden');
                loginFields.classList.remove('hidden');
            }
        });
    });