export function isOverflown(element) {
  return element.scrollHeight > element.clientHeight || element.scrollWidth > element.clientWidth;
}

export function setProgressBar(bar, progress, text='') {
  const progStr = (progress*100).toString();
  bar.setAttribute('aria-valuenow', progStr);
  bar.style.width = progStr + '%';
  bar.textContent = text;
}

export function secondsToStr(seconds) {
  seconds = Math.floor(seconds);
  const mins = Math.floor(seconds / 60);
  const secs = seconds % 60;
  return ('00' + mins).slice(-2) + ':' + ('00' + secs).slice(-2);
}
