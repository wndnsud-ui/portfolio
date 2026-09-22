const system = document.querySelector('[data-hero-system]');

if (system) {
  const stages = [...system.querySelectorAll('[data-stage]')];
  const coordinates = system.querySelector('.system-coordinates');
  const status = system.querySelector('[data-system-status]');
  const messages = ['DEFINING THE PROBLEM', 'CONNECTING THE STRUCTURE', 'VALIDATING THE RESULT'];
  const reduceMotion = window.matchMedia('(prefers-reduced-motion: reduce)').matches;
  let activeStage = 0;
  let animationFrame;
  let cycle;

  const selectStage = (index) => {
    activeStage = index;
    stages.forEach((stage, stageIndex) => stage.classList.toggle('active', stageIndex === index));
    status.textContent = messages[index];
  };

  const updatePointer = (event) => {
    cancelAnimationFrame(animationFrame);
    animationFrame = requestAnimationFrame(() => {
      const bounds = system.getBoundingClientRect();
      const x = Math.max(0, Math.min(100, ((event.clientX - bounds.left) / bounds.width) * 100));
      const y = Math.max(0, Math.min(100, ((event.clientY - bounds.top) / bounds.height) * 100));
      system.style.setProperty('--pointer-x', `${x}%`);
      system.style.setProperty('--pointer-y', `${y}%`);
      coordinates.textContent = `X ${Math.round(x)} · Y ${Math.round(y)}`;
    });
  };

  const startCycle = () => {
    if (reduceMotion) return;
    clearInterval(cycle);
    cycle = setInterval(() => selectStage((activeStage + 1) % stages.length), 2200);
  };

  stages.forEach((stage, index) => {
    stage.addEventListener('pointerenter', () => selectStage(index));
    stage.addEventListener('click', () => {
      selectStage(index);
      startCycle();
    });
  });
  system.addEventListener('pointermove', updatePointer);
  system.addEventListener('pointerleave', () => {
    system.style.setProperty('--pointer-x', '50%');
    system.style.setProperty('--pointer-y', '50%');
    coordinates.textContent = 'X 50 · Y 50';
  });

  selectStage(0);
  startCycle();
}
