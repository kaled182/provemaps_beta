const {
  showSuccessMessage,
  showErrorMessage,
  showConfirmDialog,
  showInfoMessage,
} = require('../modules/uiHelpers.js');

describe('routes_builder uiHelpers', () => {
  beforeEach(() => {
    document.body.innerHTML = '';
    jest.useFakeTimers();
  });

  afterEach(() => {
    jest.runOnlyPendingTimers();
    jest.useRealTimers();
  });

  test('showSuccessMessage renders toast with English defaults', () => {
    showSuccessMessage('Cable saved!');
    const toast = document.querySelector('.toast-card.toast-success');
    expect(toast).not.toBeNull();
    expect(toast.textContent).toContain('Success');
    expect(toast.textContent).toContain('Cable saved!');
  });

  test('showErrorMessage renders toast with English title and longer duration', () => {
    showErrorMessage('Failed to save');
    const toast = document.querySelector('.toast-card.toast-error');
    expect(toast).not.toBeNull();
    expect(toast.textContent).toContain('Error');
    expect(toast.textContent).toContain('Failed to save');
  });

  test('showInfoMessage renders toast with information title', () => {
    showInfoMessage('Heads up!');
    const toast = document.querySelector('.toast-card.toast-info');
    expect(toast).not.toBeNull();
    expect(toast.textContent).toContain('Information');
    expect(toast.textContent).toContain('Heads up!');
  });

  test('showConfirmDialog resolves true when confirm button clicked', async () => {
    const promise = showConfirmDialog({ description: 'Proceed?' });
    const confirmButton = document.querySelector('.confirm-buttons button[data-variant="primary"]');
    expect(confirmButton).not.toBeNull();
    expect(confirmButton.textContent).toBe('Confirm');
    confirmButton.click();
    await expect(promise).resolves.toBe(true);
  });

  test('showConfirmDialog resolves false when cancel button clicked', async () => {
    const promise = showConfirmDialog({ description: 'Proceed?' });
    const cancelButton = document.querySelector('.confirm-buttons button[data-variant="secondary"]');
    expect(cancelButton).not.toBeNull();
    expect(cancelButton.textContent).toBe('Cancel');
    cancelButton.click();
    await expect(promise).resolves.toBe(false);
  });
});
