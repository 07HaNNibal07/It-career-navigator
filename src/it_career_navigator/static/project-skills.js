// Each project form owns its selection and submits ordinary hidden form fields.
document.querySelectorAll('.project-skill-picker').forEach((picker) => {
  const query = picker.querySelector('.project-skill-query');
  const results = picker.querySelector('.project-skill-results');
  const selected = picker.querySelector('.project-selected-skills');
  const status = picker.querySelector('.project-skill-status');
  let timer;
  let controller;
  let revision = 0;
  query.removeAttribute('name');

  const normalize = (name) => name.trim().toLocaleLowerCase();
  const hasSkill = (name) => [...selected.children].some(
    (chip) => normalize(chip.dataset.name) === normalize(name)
  );
  function close() {
    results.hidden = true;
    query.setAttribute('aria-expanded', 'false');
  }
  function resetSearch() {
    revision += 1;
    clearTimeout(timer);
    controller?.abort();
    results.replaceChildren();
    close();
  }
  function wireChip(chip) {
    chip.querySelector('button').addEventListener('click', () => {
      chip.remove();
      status.textContent = 'Навык убран из проекта.';
      query.focus();
    });
  }
  selected.querySelectorAll('.project-skill-chip').forEach(wireChip);

  function add(name, id = null) {
    name = name.trim();
    if (!name) return;
    if (hasSkill(name)) {
      status.textContent = 'Этот навык уже выбран.';
    } else if (selected.children.length >= 100) {
      status.textContent = 'Можно выбрать не более 100 навыков.';
      return;
    } else {
      const chip = document.createElement('span');
      chip.className = 'project-skill-chip';
      chip.dataset.name = name;
      const label = document.createElement('span');
      label.textContent = name;
      const input = document.createElement('input');
      input.type = 'hidden';
      input.name = id === null ? 'skill_names' : 'skill_ids';
      input.value = id === null ? name : String(id);
      const remove = document.createElement('button');
      remove.type = 'button';
      remove.textContent = '×';
      remove.setAttribute('aria-label', `Убрать ${name}`);
      chip.append(label, input, remove);
      wireChip(chip);
      selected.append(chip);
      status.textContent = `Выбран навык ${name}.`;
    }
    query.value = '';
    resetSearch();
    query.focus();
  }

  function option(label, action) {
    const button = document.createElement('button');
    button.type = 'button';
    button.textContent = label;
    button.addEventListener('click', action);
    results.append(button);
  }

  query.addEventListener('input', () => {
    resetSearch();
    status.textContent = '';
    const text = query.value.trim();
    if (!text) return;
    const currentRevision = revision;
    timer = setTimeout(async () => {
      controller = new AbortController();
      try {
        const response = await fetch(`/profile/skills/search?query=${encodeURIComponent(text)}`, {
          signal: controller.signal,
        });
        if (!response.ok) throw new Error('Search unavailable');
        const skills = await response.json();
        if (revision !== currentRevision) return;
        results.replaceChildren();
        skills.filter((skill) => !hasSkill(skill.name)).forEach((skill) => {
          option(skill.name, () => add(skill.name, skill.id));
        });
        if (!skills.some((skill) => normalize(skill.name) === normalize(text)) && !hasSkill(text)) {
          option(`＋ Добавить «${text}»`, () => add(text));
        }
        if (!results.children.length) status.textContent = 'Совпадающие навыки уже выбраны.';
        results.hidden = results.children.length === 0;
        query.setAttribute('aria-expanded', String(!results.hidden));
      } catch (error) {
        if (error.name !== 'AbortError' && revision === currentRevision) {
          status.textContent = 'Поиск временно недоступен. Нажми Enter, чтобы добавить название вручную.';
        }
      }
    }, 180);
  });

  query.addEventListener('keydown', (event) => {
    if (event.key === 'Enter') {
      event.preventDefault();
      add(query.value);
    } else if (event.key === 'ArrowDown' && !results.hidden) {
      event.preventDefault();
      results.querySelector('button')?.focus();
    } else if (event.key === 'Escape') {
      resetSearch();
    }
  });
  results.addEventListener('keydown', (event) => {
    const buttons = [...results.querySelectorAll('button')];
    const index = buttons.indexOf(document.activeElement);
    if (event.key === 'ArrowDown' || event.key === 'ArrowUp') {
      event.preventDefault();
      const next = index + (event.key === 'ArrowDown' ? 1 : -1);
      if (next < 0) query.focus();
      else buttons[Math.min(next, buttons.length - 1)]?.focus();
    } else if (event.key === 'Escape') {
      close();
      query.focus();
    }
  });
  picker.addEventListener('focusout', (event) => {
    if (!picker.contains(event.relatedTarget)) close();
  });
  document.addEventListener('click', (event) => {
    if (!picker.contains(event.target)) close();
  });
  picker.closest('form').addEventListener('submit', (event) => {
    if (query.value.trim()) add(query.value);
    if (query.value.trim()) event.preventDefault();
  });
});
