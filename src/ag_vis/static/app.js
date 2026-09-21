const scene = document.querySelector('#scene');
const dialogue = document.querySelector('#dialogue');
const progress = document.querySelector('#progress');
const percent = document.querySelector('#percent');
const status = document.querySelector('#status');

function render(state) {
  const amount = Math.max(0, Math.min(100, Math.round(state.progress * 100)));
  scene.dataset.phase = state.phase;
  scene.style.setProperty('--progress', state.progress);
  dialogue.textContent = state.message;
  progress.value = amount;
  progress.textContent = `${amount}%`;
  percent.textContent = `${amount}%`;
  status.textContent = state.status.toUpperCase();
}

fetch('/api/state').then((response) => response.json()).then(render);
const events = new EventSource('/api/events');
events.onmessage = (event) => render(JSON.parse(event.data));
events.onerror = () => { status.textContent = 'RECONNECTING'; };
