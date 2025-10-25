const modal = document.getElementById('addDeviceModal');
const modalContent = document.getElementById('addDeviceModalContent');

function openModal() {
  modal.classList.remove('pointer-events-none');
  modal.classList.add('opacity-100');
  modalContent.classList.add('opacity-100', 'scale-100');
  modalContent.classList.remove('opacity-0', 'scale-95');
}

function closeModal() {
  modal.classList.remove('opacity-100');
  modal.classList.add('opacity-0');
  modalContent.classList.remove('opacity-100', 'scale-100');
  modalContent.classList.add('opacity-0', 'scale-95');
  setTimeout(() => modal.classList.add('pointer-events-none'), 300);
}

window.openModal = openModal;
window.closeModal = closeModal;

document.getElementById('addDeviceForm').addEventListener('submit', async (event) => {
  event.preventDefault();
  const formData = new FormData(event.currentTarget);
  const hostId = formData.get('device_name');

  try {
    const response = await fetch('/zabbix_api/api/add-device-from-zabbix/', {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
        'X-CSRFToken': document.querySelector('[name=csrfmiddlewaretoken]').value,
      },
      body: JSON.stringify({ hostid: hostId }),
    });

    const data = await response.json();
    if (response.ok) {
      alert(`Device added: ${data.device.name} (site: ${data.device.site})`);
      closeModal();
    } else {
      alert(`Error: ${data.error || 'Failed to add device'}`);
    }
  } catch (error) {
    console.error('Add device request failed:', error);
    alert('Network or server error.');
  }
});

modal.addEventListener('click', (event) => {
  if (event.target === modal) {
    closeModal();
  }
});
