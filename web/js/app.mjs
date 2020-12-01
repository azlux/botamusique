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

var playlistTable;
var playlistItemTemplate;
var libraryGroup;
var libraryItemTemplate;

document.addEventListener('DOMContentLoaded', () => {
  playlistTable = document.getElementById('playlist-table');
  playlistItemTemplate = document.querySelector('.playlist-item-template');
  libraryGroup = document.getElementById('library-group');
  libraryItemTemplate = document.getElementById('library-item');
  const musicUrlInput = document.getElementById('music-url-input');
  const radioUrlInput = document.getElementById('radio-url-input');

  /**
   * Initialize components
   */
  Theme.init();

  // Replace any existing <i> tags with <svg> and set up a MutationObserver to
  // continue doing this as the DOM changes.
  dom.watch();

  /**
   * Run component startups
   */
  updatePlaylist();
  updateLibrary();

  /**
   * Catch user events
   */
  document.getElementById('theme-switch-btn').addEventListener('click', () => {
    Theme.swap();
  });

  document.getElementById('add-music-url').querySelector('button').addEventListener('click', () => {
    musicLibrary.addMusicByURL(musicUrlInput.value).then(() => {
      musicUrlInput.value = '';
    });
  });

  document.getElementById('add-radio-url').querySelector('button').addEventListener('click', () => {
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
