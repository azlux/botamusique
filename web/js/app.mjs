import 'jquery/src/jquery.js';
import 'jquery-migrate/src/migrate.js';
import Popper from 'popper.js/dist/esm/popper.js';
import {
  Modal,
  Toast,
  Tooltip,
} from 'bootstrap/js/src/index.js';

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

import NProgress from 'nprogress/nprogress.js';
import axios from 'axios/lib/axios.js';

axios.defaults.onDownloadProgress = (e) => {
  NProgress.set(Math.floor(e.loaded * 1.0) / e.total);
};

// Add a request interceptor
axios.interceptors.request.use((config) => {
  NProgress.start();

  return config;
}, (error) => {
  console.error(error);

  return Promise.reject(error);
});

// Add a response interceptor
axios.interceptors.response.use((response) => {
  NProgress.done();

  console.debug(response.data);

  return response;
}, (error) => {
  console.error(error);

  return Promise.reject(error);
});

// Old Application Code
//import './main.mjs';

// New application code
import Theme from './components/theme.mjs';
import MusicPlaylist from './components/playlist.mjs';
import MusicLibrary from './components/library.mjs';
import {limitChars} from './lib/text.mjs';

const musicPlaylist = new MusicPlaylist(axios);
const musicLibrary = new MusicLibrary(axios);

const playModeBtns = {
  'one-shot': document.getElementById('one-shot-mode-btn'),
  'random': document.getElementById('random-mode-btn'),
  'repeat': document.getElementById('repeat-mode-btn'),
  'autoplay': document.getElementById('autoplay-mode-btn'),
};

const filters = {
  file: document.getElementById('filter-type-file'),
  url: document.getElementById('filter-type-url'),
  radio: document.getElementById('filter-type-radio'),
};

var playlistTable;
var playlistItemTemplate;
var libraryGroup;
var libraryItemTemplate;

document.addEventListener('DOMContentLoaded', async () => {
  playlistTable = document.getElementById('playlist-table');
  playlistItemTemplate = document.querySelector('.playlist-item-template');
  libraryGroup = document.getElementById('library-group');
  libraryItemTemplate = document.getElementById('library-item');
  const musicUrlInput = document.getElementById('music-url-input');
  const radioUrlInput = document.getElementById('radio-url-input');
  const playPauseBtn = document.getElementById('play-pause-btn');
  const fastForwardBtn = document.getElementById('fast-forward-btn');
  const volumePopoverBtn = document.getElementById('volume-popover-btn');
  const volumePopoverDiv = document.getElementById('volume-popover');
  const volumeSlider = document.getElementById('volume-slider');

  let volume_popover_instance = null;
  let volume_popover_show = false;
  let volume_update_timer;

  /**
   * Initialize components
   */
  Theme.init();

  // Replace any existing <i> tags with <svg> and set up a MutationObserver to
  // continue doing this as the DOM changes.
  dom.watch();

  updatePlaylist();
  updateLibrary();

  /**
   * Catch user events
   */
  // Swap theme
  document.getElementById('theme-switch-btn').addEventListener('click', async () => {
    Theme.swap();
  });

  // Play/pause
  playPauseBtn.addEventListener('click', async () => {
    musicPlaylist.playPause();
  });

  // Fast-forward
  fastForwardBtn.addEventListener('click', async () => {
    musicPlaylist.next();
  });

  // Playlist modes
  for (const playMode in playModeBtns) {
    playModeBtns[playMode].addEventListener('click', async () => {
      musicPlaylist.changePlayMode(playMode);
    });
  }

  // Add to playlist
  document.getElementById('add-to-playlist-btn').addEventListener('click', async () => {
    const data = await getFilters();
    data.action = 'add';

    console.debug(data);

    musicPlaylist.addItem(data);

    updatePlaylist();
  });

  // Volume popover
  volumePopoverBtn.addEventListener('click', async (e) => {
    e.stopPropagation();

    // Show/hide popover
    if (!volume_popover_show) {
      volume_popover_instance = new Popper(volumePopoverBtn, volumePopoverDiv, {
        placement: 'top',
        modifiers: {
          offset: {
            offset: '0, 8',
          },
        },
      });

      volumePopoverDiv.setAttribute('data-show', '');
    } else {
      volumePopoverDiv.removeAttribute('data-show');

      if (volume_popover_instance) {
        volume_popover_instance.destroy();
        volume_popover_instance = null;
      }
    }

    // Change internal popover state
    volume_popover_show = !volume_popover_show;

    document.addEventListener('click', async () => {
      volumePopoverDiv.removeAttribute('data-show');

      if (volume_popover_instance) {
        volume_popover_instance.destroy();
        volume_popover_instance = null;
        volume_popover_show = !volume_popover_show;
      }
    }, { once: true });
  });

  // ?
  volumePopoverBtn.addEventListener('click', async (e) => {
    e.stopPropagation();
  });

  // Send volume request update
  volumeSlider.addEventListener('change', async () => {
    window.clearTimeout(volume_update_timer);

    volume_update_timer = window.setTimeout(() => {
      musicPlaylist.setVolume(volumeSlider.value);
    }, 500); // delay in milliseconds
  });

  // Turn volume down one level
  document.getElementById('volume-down-btn').addEventListener('click', async () => {
    musicPlaylist.volumeDown();
  });

  // Turn volume up one level
  document.getElementById('volume-up-btn').addEventListener('click', async () => {
    musicPlaylist.volumeUp();
  });

  // Clear playlist
  document.getElementById('clear-playlist-btn').addEventListener('click', async () => {
    musicPlaylist.clear();
  });

  // Rescan local music files
  document.getElementById('library-rescan-btn').addEventListener('click', async () => {
    musicLibrary.rescan();

    //updateResults();
  });

  // Download music files
  document.getElementById('library-download-btn').addEventListener('click', async () => {
    const cond = await getFilters();

    /*download_id.val();
    download_type.val(cond.type);
    download_dir.val(cond.dir);
    download_tags.val(cond.tags);
    download_keywords.val(cond.keywords);
    download_form.submit();*/
  });

  // Delete selected music files
  document.getElementById('library-delete-btn').addEventListener('click', async () => {
    const data = await getFilters();
    data.action = 'delete';

    console.debug(data);

    musicLibrary.removeItems(data);

    updatePlaylist();
    //updateResults();
  });

  // Add music URL
  document.getElementById('add-music-url').querySelector('button').addEventListener('click', async () => {
    musicLibrary.addMusicByURL(musicUrlInput.value).then(() => {
      musicUrlInput.value = '';
    });
  });

  // Add music Radio
  document.getElementById('add-radio-url').querySelector('button').addEventListener('click', async () => {
    musicLibrary.addRadioByURL(radioUrlInput.value).then(() => {
      radioUrlInput.value = '';
    });
  });

  /**
   * Recurring events (reduce as much as possible)
   */
  // Todo: configurable delay
  /*setInterval(() => {
    // See if server has been updated by another client
    if (musicPlaylist.checkForUpdate()) {
      updatePlaylist();
    }
  }, 5000);*/
});

/**
 * Load playlist state and items.
 */
async function updatePlaylist() {
  musicPlaylist.getItems().then(response => {
    response.data.items.forEach(item => {
      // Clone playlist item template
      const playlistItem = playlistItemTemplate.cloneNode(true);

      // Set new element's ID
      playlistItem.id = 'playlist-item-' + item.index;

      // Update item class
      playlistItem.classList.add('playlist-item');

      // Remove Bootstrap display:none class
      playlistItem.classList.remove('d-none');

      // Create DocumentFragment
      const fragment = document.createDocumentFragment();
      fragment.appendChild(playlistItem);

      // Append item to DOM
      playlistTable.appendChild(fragment);
    });
  });
}

/**
 * Load library state and items.
 */
async function updateLibrary() {
  musicLibrary.getItems(1, ['file', 'url', 'radio']).then(response => {
    response.data.items.forEach(item => {
      const libraryItem = libraryItemTemplate.cloneNode(true);

      // Update item attributes
      libraryItem.querySelector('.library-item-id').value = item.id;
      libraryItem.querySelector('.library-item-title').innerHTML = item.artist;
      libraryItem.querySelector('.library-item-artist').innerHTML = (item.artist ? '- ' + item.artist : '');
      libraryItem.querySelector('.library-item-thumb').setAttribute('src', item.thumb);
      libraryItem.querySelector('.library-item-thumb').setAttribute('alt', limitChars(item.title));
      libraryItem.querySelector('.library-item-type').innerHTML = '[' + item.type + ']';
      libraryItem.querySelector('.library-item-path').innerHTML = item.path;

      // Update item styling
      libraryItem.classList.add('library-active-item');
      libraryItem.style.removeProperty('display');

      // Create DocumentFragment
      const fragment = document.createDocumentFragment();
      fragment.appendChild(libraryItem);

      // Append item to DOM
      libraryGroup.appendChild(fragment);
    });
  });
}

/**
 * Get active library filters
 *
 * @param {number} [page = 1] Page filter.
 * @returns {object} Formatted filters object.
 */
async function getFilters(page = 1) {
  // Build list of active tags
  const tags = [];
  document.querySelectorAll('.tag-clicked').forEach(tag => {
    tags.push(tag);
  });

  // Build a list of active library item types
  const types = [];
  for (const filter in filters) {
    if (filters[filter].classList.contains('active')) {
      types.push(filter);
    }
  }

  return {
    type: types.join(','),
    dir: document.getElementById('filter-dir').value,
    tags: tags.join(','),
    keywords: document.getElementById('filter-keywords').value,
    page: page,
  };
}
