import 'jquery/src/jquery.js';
import 'jquery-migrate/src/migrate.js';
import Popper from 'popper.js/dist/esm/popper.js';
/*import {
  Modal,
  Toast,
  Tooltip,
} from 'bootstrap/js/src/index.js';*/
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
var filterDir;

document.addEventListener('DOMContentLoaded', async () => {
  playlistTable = document.getElementById('playlist-table');
  playlistItemTemplate = document.querySelector('.playlist-item-template');
  libraryGroup = document.getElementById('library-group');
  libraryItemTemplate = document.getElementById('library-item');
  filterDir = document.getElementById('filter-dir');
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

    await musicPlaylist.addItem(data);

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

  // Library filters
  for (const filter in filters) {
    filters[filter].addEventListener('click', e => {
      e.preventDefault();

      setFilterType(filter);
    });
  }

  // Rescan local music files
  document.getElementById('library-rescan-btn').addEventListener('click', async () => {
    await musicLibrary.rescan();

    //updateResults();
  });

  // Download music files
  document.getElementById('library-download-btn').addEventListener('click', async () => {
    //const cond = await getFilters();

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

    await musicLibrary.removeItems(data);

    updatePlaylist();
    //updateResults();
  });

  // Add music URL
  document.getElementById('add-music-url').querySelector('button').addEventListener('click', async () => {
    await musicLibrary.addMusicByURL(musicUrlInput.value);

    musicUrlInput.value = '';
  });

  // Add music Radio
  document.getElementById('add-radio-url').querySelector('button').addEventListener('click', async () => {
    await musicLibrary.addRadioByURL(radioUrlInput.value);

    radioUrlInput.value = '';
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
    if (data.current_index !== playlist_current_index) {
      if (data.current_index !== -1) {
        if ((data.current_index > playlist_range_to || data.current_index < playlist_range_from)) {
          playlist_range_from = 0;
          playlist_range_to = 0;
          updatePlaylist();
        } else {
          playlist_current_index = data.current_index;
          updatePlayerInfo(playlist_items[data.current_index]);
          displayActiveItem(data.current_index);
        }
      }
    }
    updateControls(data.empty, data.play, data.mode, data.volume);
    if (!data.empty) {
      updatePlayerPlayhead(data.playhead);
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

      // Update item attributes
      playlistItem.querySelector('.playlist-item-id').value = item.id;
      playlistItem.querySelector('.playlist-item-index').innerHTML = item.index + 1;
      playlistItem.querySelector('.playlist-item-title').innerHTML = item.title;
      playlistItem.querySelector('.playlist-item-artist').innerHTML = item.arist;
      playlistItem.querySelector('.playlist-item-thumbnail').setAttribute('src', item.thumbnail);
      playlistItem.querySelector('.playlist-item-thumbnail').setAttribute('alt', limitChars(item.title));
      playlistItem.querySelector('.playlist-item-type').innerHTML = item.type;
      playlistItem.querySelector('.playlist-item-path').innerHTML = item.path;

      // Update item ID
      playlistItem.id = 'playlist-item-' + item.index;

      // Update item class
      playlistItem.classList.add('playlist-item');

      // Update item tags
      /*const tags = item_copy.find('.playlist-item-tags');
      tags.empty();

      const tag_edit_copy = pl_tag_edit_element.clone();
      tag_edit_copy.click(function() {
        addTagModalShow(item.id, item.title, item.tags);
      });
      tag_edit_copy.appendTo(tags);

      if (item.tags.length > 0) {
        item.tags.forEach(function(tag_tuple) {
          const tag_copy = tag_element.clone();
          tag_copy.html(tag_tuple[0]);
          tag_copy.addClass('badge-' + tag_tuple[1]);
          tag_copy.appendTo(tags);
        });
      } else {
        const tag_copy = notag_element.clone();
        tag_copy.appendTo(tags);
      }*/

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

      // Update item tags
      /*const tags = item_copy.find('.library-item-tags');
      tags.empty();

      const tag_edit_copy = tag_edit_element.clone();
      tag_edit_copy.click(function() {
        addTagModalShow(item.id, item.title, item.tags);
      });
      tag_edit_copy.appendTo(tags);

      if (item.tags.length > 0) {
        item.tags.forEach(function(tag_tuple) {
          const tag_copy = tag_element.clone();
          tag_copy.html(tag_tuple[0]);
          tag_copy.addClass('badge-' + tag_tuple[1]);
          tag_copy.appendTo(tags);
        });
      } else {
        const tag_copy = notag_element.clone();
        tag_copy.appendTo(tags);
      }*/

      // Bind events
      /*libraryItem.querySelector('.library-thumb-col').addEventListener('hover', () => {
        function (e) {
          $(e.currentTarget).find('.library-thumb-grp').addClass('library-thumb-grp-hover');
        },
        function (e) {
          $(e.currentTarget).find('.library-thumb-grp').removeClass('library-thumb-grp-hover');
        },
      });

      $('.library-info-title').unbind().hover(
        function (e) {
          $(e.currentTarget).parent().find('.library-thumb-grp').addClass('library-thumb-grp-hover');
        },
        function (e) {
          $(e.currentTarget).parent().find('.library-thumb-grp').removeClass('library-thumb-grp-hover');
        },
      );

      $('.library-item-play').unbind().click(
        function (e) {
          request('post', {
            'add_item_at_once': $(e.currentTarget).parent().parent().parent().find('.library-item-id').val(),
          });
        },
      );

      $('.library-item-trash').unbind().click(
        function (e) {
          request('post', {
            'delete_item_from_library': $(e.currentTarget).parent().parent().find('.library-item-id').val(),
          });
          updateResults(active_page);
        },
      );

      $('.library-item-download').unbind().click(
        function (e) {
          const id = $(e.currentTarget).parent().parent().find('.library-item-id').val();
          // window.open('/download?id=' + id);
          downloadId(id);
        },
      );

      $('.library-item-add-next').unbind().click(
        function (e) {
          const id = $(e.currentTarget).parent().parent().find('.library-item-id').val();
          request('post', {
            'add_item_next': id,
          });
        },
      );

      $('.library-item-add-bottom').unbind().click(
        function (e) {
          const id = $(e.currentTarget).parent().parent().find('.library-item-id').val();
          request('post', {
            'add_item_bottom': id,
          });
        },
      );*/

      // Remove display style property (showing element)
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
    dir: filterDir.value,
    tags: tags.join(','),
    keywords: document.getElementById('filter-keywords').value,
    page: page,
  };
}

/**
 * Set active filter.
 *
 * @param {string} type Filter type.
 */
async function setFilterType(type) {
  if (filters[type].classList.contains('active')) {
    filters[type].classList.remove('active');
    filters[type].classList.remove('btn-primary');
    filters[type].classList.add('btn-secondary');
    filters[type].querySelector('input[type=checkbox]').checked = false;
  } else {
    filters[type].classList.remove('btn-secondary');
    filters[type].classList.add('active');
    filters[type].classList.add('btn-primary');
    filters[type].querySelector('input[type=checkbox]').checked = true;
  }

  if (type === 'file') {
    filterDir.disabled = !filters['file'].classList.contains('active');
  }

  //updateResults();
}
