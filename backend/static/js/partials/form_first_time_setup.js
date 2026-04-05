// Toggle Zabbix auth fields
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

// Toggle map provider fields
const mapRadios = document.querySelectorAll('input[name="map_provider"]');
const fieldGoogle = document.getElementById('field_google');
const fieldMapbox = document.getElementById('field_mapbox');

function updateMapFields() {
    const selected = document.querySelector('input[name="map_provider"]:checked');
    if (!selected) return;
    fieldGoogle.classList.toggle('hidden', selected.value !== 'google');
    fieldMapbox.classList.toggle('hidden', selected.value !== 'mapbox');
}

mapRadios.forEach(radio => radio.addEventListener('change', updateMapFields));
updateMapFields();
