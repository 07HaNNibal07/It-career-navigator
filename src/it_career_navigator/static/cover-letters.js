document.querySelectorAll('form[data-generating]').forEach((form) => {
  const button = form.querySelector('button[type="submit"]');
  button.dataset.originalLabel = button.textContent;
  form.addEventListener('submit', () => {
    button.disabled = true;
    button.textContent = 'Готовим черновик…';
  });
});

const editor = document.querySelector('#letter-text');
const reviewed = document.querySelector('#letter-reviewed');
const copy = document.querySelector('#copy-letter');
const status = document.querySelector('#copy-status');
if (editor && reviewed && copy) {
  reviewed.addEventListener('change', () => { copy.disabled = !reviewed.checked; });
  editor.addEventListener('input', () => {
    reviewed.checked = false;
    copy.disabled = true;
    status.textContent = '';
  });
  copy.addEventListener('click', async () => {
    try {
      await navigator.clipboard.writeText(editor.value);
      status.textContent = 'Текст скопирован. Если ты редактировал(а) его, не забудь сохранить изменения.';
    } catch {
      editor.focus();
      editor.select();
      status.textContent = 'Текст выделен. Нажми Ctrl+C или используй команду копирования на устройстве.';
    }
  });
}
// Back/forward cache can restore a previously disabled generation button.
window.addEventListener('pageshow', () => {
  document.querySelectorAll('form[data-generating] button').forEach((button) => {
    button.disabled = false;
    button.textContent = button.dataset.originalLabel;
  });
});
