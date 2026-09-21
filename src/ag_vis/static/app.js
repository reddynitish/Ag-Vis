const scene = document.querySelector('#scene');
const dialogue = document.querySelector('#dialogue');
const progress = document.querySelector('#progress');
const percent = document.querySelector('#percent');
const status = document.querySelector('#status');
const actionBadge = document.querySelector('#actionBadge');
const actionQueue = [];
let playing = false;
const MIN_ACTION_MS = 1350;

function render(state) {
  const amount = Math.max(0, Math.min(100, Math.round(state.progress * 100)));
  scene.dataset.phase = state.phase;
  scene.style.setProperty('--progress', state.progress);
  dialogue.textContent = state.message;
  progress.value = amount;
  progress.textContent = `${amount}%`;
  percent.textContent = `${amount}%`;
  status.textContent = state.status.toUpperCase();
  actionBadge.textContent = ({
    planning: 'DRAWING THE PLAN', researching: 'SURVEYING THE SITE',
    building: 'RAISING THE STRUCTURE', testing: 'INSPECTING THE BUILD',
    repairing: 'REPAIR CREW', blocked: 'WORK PAUSED', finished: 'BUILD COMPLETE'
  })[state.phase] || 'WORKING';
}

const wait = (milliseconds) => new Promise((resolve) => setTimeout(resolve, milliseconds));

async function playAction(state) {
  render(state);
  scene.classList.remove('acting');
  void scene.offsetWidth;
  scene.classList.add('acting');
  await wait(state.phase === 'finished' ? 2200 : MIN_ACTION_MS);
  scene.classList.remove('acting');
}

async function drainQueue() {
  if (playing) return;
  playing = true;
  while (actionQueue.length) {
    await playAction(actionQueue.shift());
  }
  playing = false;
}

function enqueue(state) {
  actionQueue.push(state);
  drainQueue();
}

fetch('/api/state').then((response) => response.json()).then(render);
const events = new EventSource('/api/events');
events.onmessage = (event) => enqueue(JSON.parse(event.data));
events.onerror = () => { status.textContent = 'RECONNECTING'; };
