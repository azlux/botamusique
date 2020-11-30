import {isString} from "./type.mjs";

export function isOverflown(element) {
  return element.scrollHeight > element.clientHeight || element.scrollWidth > element.clientWidth;
}

export function hash(string) {
  if (!isString(string)) return 0;
  let hash = 0;
  if (string.length === 0) {
    return hash;
  }
  for (let i = 0; i < string.length; i++) {
    const char = string.charCodeAt(i);
    hash = ((hash<<5)-hash)+char;
    hash = hash & hash; // Convert to 32bit integer
  }
  return hash;
}

export function getColor(string) {
  const num = hash(string) % 8;

  switch (num) {
    case 0:
      return 'primary';
    case 1:
      return 'secondary';
    case 2:
      return 'success';
    case 3:
      return 'danger';
    case 4:
      return 'warning';
    case 5:
      return 'info';
    case 6:
      return 'light';
    case 7:
      return 'dark';
  }
}

export function setProgressBar(bar, progress, text = '') {
  const progPos = (-1 * (1 - progress) * bar.scrollWidth).toString();
  const progStr = (progress * 100).toString();
  bar.setAttribute('aria-valuenow', progStr);
  bar.style.transform = 'translateX(' + progPos + 'px)';
  bar.textContent = text;
}

export function secondsToStr(seconds) {
  seconds = Math.floor(seconds);
  const mins = Math.floor(seconds / 60);
  const secs = seconds % 60;
  return ('00' + mins).slice(-2) + ':' + ('00' + secs).slice(-2);
}
