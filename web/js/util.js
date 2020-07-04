export function isOverflown(element) {
  return element.scrollHeight > element.clientHeight || element.scrollWidth > element.clientWidth;
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

export function coverArtString(title) {

  let nameOfSong = "";
  // The maximum length before we start truncating
  const maxLength = 50;

  if (title.length > maxLength) {
    // Name = longTitleTooLongToBeAGoodAltTex...
    nameOfSong = title.substr(0, maxLength) + "\u2026";
  } else {
    // Name = shortTitle
    nameOfSong = title;
  }

  return 'Cover art for ' + nameOfSong;
}