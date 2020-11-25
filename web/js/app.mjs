import {library, dom} from '@fortawesome/fontawesome-svg-core/index.es.js';
import {
  faTimesCircle, faPlus, faCheck, faUpload, faTimes, faTrash, faPlay, faPause, faFastForward, faPlayCircle, faLightbulb,
  faTrashAlt, faDownload, faSyncAlt, faEdit, faVolumeUp, faVolumeDown, faRobot, faRedo, faRandom, faTasks
} from '@fortawesome/free-solid-svg-icons/index.es.js';
import {faFileAlt} from '@fortawesome/free-regular-svg-icons/index.es.js';

library.add(
  // Solid
  faTimesCircle, faPlus, faCheck, faUpload, faTimes, faTrash, faPlay, faPause, faFastForward, faPlayCircle, faLightbulb,
  faTrashAlt, faDownload, faSyncAlt, faEdit, faVolumeUp, faVolumeDown, faRobot, faRedo, faRandom, faTasks,
  // Regular
  faFileAlt
);

// Old application code
import './main.mjs';

// New application code
import Theme from './lib/theme.mjs';

document.addEventListener('DOMContentLoaded', () => {
  Theme.init();

  // Replace any existing <i> tags with <svg> and set up a MutationObserver to
  // continue doing this as the DOM changes.
  dom.watch();

  document.getElementById('theme-switch-btn').addEventListener('click', () => {
    Theme.swap();
  });
});

