$('#uploadSelectFile').on('change', function() {
  // get the file name
  const fileName = $(this).val().replace('C:\\fakepath\\', ' ');
  // replace the "Choose a file" label
  $(this).next('.custom-file-label').html(fileName);
});


// ----------------------
// ------ Playlist ------
// ----------------------

const pl_item_template = $('.playlist-item-template');
const pl_id_element = $('.playlist-item-id');
const pl_index_element = $('.playlist-item-index');
const pl_title_element = $('.playlist-item-title');
const pl_artist_element = $('.playlist-item-artist');
const pl_thumb_element = $('.playlist-item-thumbnail');
const pl_type_element = $('.playlist-item-type');
const pl_path_element = $('.playlist-item-path');

const pl_tag_edit_element = $('.playlist-item-edit');

const notag_element = $('.library-item-notag'); // these elements are shared with library
const tag_element = $('.library-item-tag');

const addTagModal = new Modal(document.getElementById('addTagModal'));

const playlist_loading = $('#playlist-loading');
const playlist_table = $('#playlist-table');
const playlist_empty = $('#playlist-empty');
const playlist_expand = $('.playlist-expand');

let playlist_items = null;

let playlist_ver = 0;
let playlist_current_index = 0;

let playlist_range_from = 0;
let playlist_range_to = 0;

let last_volume = 0;

let playing = false;

const playModeBtns = {
  'one-shot': $('#one-shot-mode-btn'),
  'random': $('#random-mode-btn'),
  'repeat': $('#repeat-mode-btn'),
  'autoplay': $('#autoplay-mode-btn'),
};

const playModeIcon = {
  'one-shot': 'fa-tasks',
  'random': 'fa-random',
  'repeat': 'fa-redo',
  'autoplay': 'fa-robot',
};

function request(_url, _data, refresh = false) {
  console.log(_data);
  $.ajax({
    type: 'POST',
    url: _url,
    data: _data,
    statusCode: {
      200: function(data) {
        if (data.ver !== playlist_ver) {
          checkForPlaylistUpdate();
        }
        updateControls(data.empty, data.play, data.mode, data.volume);
        updatePlayerPlayhead(data.playhead);
      },
      403: function() {
        location.reload(true);
      },
    },
  });
  if (refresh) {
    location.reload(true);
  }
}

function displayPlaylist(data) {
  playlist_table.animate({
    opacity: 0,
  }, 200, function() {
    playlist_loading.hide();
    $('.playlist-item').remove();
    const items = data.items;
    const length = data.length;
    if (items.length === 0) {
      playlist_empty.removeClass('d-none');
      playlist_table.animate({opacity: 1}, 200);
      return;
    }
    playlist_items = {};
    for (const i in items) {
      playlist_items[items[i].index] = items[i];
    }
    const start_from = data.start_from;
    playlist_range_from = start_from;
    playlist_range_to = start_from + items.length - 1;

    if (items.length < length && start_from > 0) {
      let _from = start_from - 5;
      _from = _from > 0 ? _from : 0;
      const _to = start_from - 1;
      if (_to > 0) {
        insertExpandPrompt(_from, start_from + length - 1, _from, _to, length);
      }
    }

    items.forEach(
        function(item) {
          addPlaylistItem(item);
        },
    );

    if (items.length < length && start_from + items.length < length) {
      const _from = start_from + items.length;
      let _to = start_from + items.length - 1 + 10;
      _to = _to < length - 1 ? _to : length - 1;
      if (start_from + items.length < _to) {
        insertExpandPrompt(start_from, _to, _from, _to, length);
      }
    }

    displayActiveItem(data.current_index);
    updatePlayerInfo(playlist_items[data.current_index]);
    bindPlaylistEvent();
    playlist_table.animate({opacity: 1}, 200);
  });
}

function displayActiveItem(current_index) {
  $('.playlist-item').removeClass('table-active');
  $('#playlist-item-' + current_index).addClass('table-active');
}

function insertExpandPrompt(real_from, real_to, display_from, display_to, total_length) {
  const expand_copy = playlist_expand.clone();
  expand_copy.addClass('playlist-item');
  expand_copy.removeClass('d-none');
  if (display_from !== display_to) {
    expand_copy.find('.playlist-expand-item-range').html((display_from + 1) + '~' + (display_to + 1) +
      ' of ' + (total_length) + ' items');
  } else {
    expand_copy.find('.playlist-expand-item-range').html(display_from + ' of ' + (total_length) + ' items');
  }

  expand_copy.addClass('playlist-item');
  expand_copy.appendTo(playlist_table);
  expand_copy.click(function() {
    playlist_range_from = real_from;
    playlist_range_to = real_to;
    updatePlaylist();
  });
}

function updatePlaylist() {
  playlist_table.animate({
    opacity: 0,
  }, 200, function() {
    playlist_empty.addClass('d-none');
    playlist_loading.show();
    playlist_table.find('.playlist-item').css('opacity', 0);
    let data = {};
    if (!(playlist_range_from === 0 && playlist_range_to === 0)) {
      data = {
        range_from: playlist_range_from,
        range_to: playlist_range_to,
      };
    }
    $.ajax({
      type: 'GET',
      url: 'playlist',
      data: data,
      statusCode: {
        200: displayPlaylist,
      },
    });
    playlist_table.animate({
      opacity: 1,
    }, 200);
  });
}

function bindPlaylistEvent() {
  $('.playlist-item-play').unbind().click(
      function(e) {
        request('post', {
          'play_music': ($(e.currentTarget).parent().parent().parent().find('.playlist-item-index').html() - 1),
        });
      },
  );
  $('.playlist-item-trash').unbind().click(
      function(e) {
        request('post', {
          'delete_music': ($(e.currentTarget).parent().parent().parent().find('.playlist-item-index').html() - 1),
        });
      },
  );
}

function updateControls(empty, play, mode, volume) {
  updatePlayerControls(play, empty);
  if (empty) {
    playPauseBtn.prop('disabled', true);
    fastForwardBtn.prop('disabled', true);
  } else {
    playPauseBtn.prop('disabled', false);
    fastForwardBtn.prop('disabled', false);
    if (play) {
      playing = true;
      playPauseBtn.find('[data-fa-i2svg]').removeClass('fa-play').addClass('fa-pause');
      // PR #180: Since this button changes behavior dynamically, we change its
      // ARIA labels in JS instead of only adding them statically in the HTML
      playPauseBtn.attr('aria-label', 'Pause');
    } else {
      playing = false;
      playPauseBtn.find('[data-fa-i2svg]').removeClass('fa-pause').addClass('fa-play');
      // PR #180: Since this button changes behavior dynamically, we change its
      // ARIA labels in JS instead of only adding them statically in the HTML
      playPauseBtn.attr('aria-label', 'Play');
    }
  }

  for (const otherMode of Object.values(playModeBtns)) {
    otherMode.removeClass('active');
  }
  playModeBtns[mode].addClass('active');

  const playModeIndicator = $('#modeIndicator');
  for (const icon_class of Object.values(playModeIcon)) {
    playModeIndicator.removeClass(icon_class);
  }
  playModeIndicator.addClass(playModeIcon[mode]);

  if (volume !== last_volume) {
    last_volume = volume;
    if (volume > 1) {
      volumeSlider.value = 1;
    } else if (volume < 0) {
      volumeSlider.value = 0;
    } else {
      volumeSlider.value = volume;
    }
  }
}


// ---------------------
// ------ Browser ------
// ---------------------

const filter_keywords = $('#filter-keywords');

filter_dir.change(function() {
  updateResults();
});
filter_keywords.change(function() {
  updateResults();
});

const item_template = $('#library-item');

function bindLibraryResultEvent() {
  $('.library-thumb-col').unbind().hover(
      function(e) {
        $(e.currentTarget).find('.library-thumb-grp').addClass('library-thumb-grp-hover');
      },
      function(e) {
        $(e.currentTarget).find('.library-thumb-grp').removeClass('library-thumb-grp-hover');
      },
  );

  $('.library-info-title').unbind().hover(
      function(e) {
        $(e.currentTarget).parent().find('.library-thumb-grp').addClass('library-thumb-grp-hover');
      },
      function(e) {
        $(e.currentTarget).parent().find('.library-thumb-grp').removeClass('library-thumb-grp-hover');
      },
  );

  $('.library-item-play').unbind().click(
      function(e) {
        request('post', {
          'add_item_at_once': $(e.currentTarget).parent().parent().parent().find('.library-item-id').val(),
        });
      },
  );

  $('.library-item-trash').unbind().click(
      function(e) {
        request('post', {
          'delete_item_from_library': $(e.currentTarget).parent().parent().find('.library-item-id').val(),
        });
        updateResults(active_page);
      },
  );

  $('.library-item-download').unbind().click(
      function(e) {
        const id = $(e.currentTarget).parent().parent().find('.library-item-id').val();
        // window.open('/download?id=' + id);
        downloadId(id);
      },
  );

  $('.library-item-add-next').unbind().click(
      function(e) {
        const id = $(e.currentTarget).parent().parent().find('.library-item-id').val();
        request('post', {
          'add_item_next': id,
        });
      },
  );

  $('.library-item-add-bottom').unbind().click(
      function(e) {
        const id = $(e.currentTarget).parent().parent().find('.library-item-id').val();
        request('post', {
          'add_item_bottom': id,
        });
      },
  );
}

const lib_filter_tag_group = $('#filter-tags');
const lib_filter_tag_element = $('.filter-tag');

const lib_group = $('#library-group');
const id_element = $('.library-item-id');
const title_element = $('.library-item-title');
const artist_element = $('.library-item-artist');
const thumb_element = $('.library-item-thumb');
const type_element = $('.library-item-type');
const path_element = $('.library-item-path');

const tag_edit_element = $('.library-item-edit');
// var notag_element = $(".library-item-notag");
// var tag_element = $(".library-item-tag");

const library_tags = [];

function updateLibraryControls() {
  $.ajax({
    type: 'GET',
    url: 'library/info',
    statusCode: {
      200: displayLibraryControls,
      403: function() {
        location.reload(true);
      },
    },
  });
}

function displayLibraryControls(data) {
  $('#maxUploadFileSize').val(data.max_upload_file_size);
  if (data.upload_enabled) {
    $('#uploadDisabled').val('false');
    $('#upload').show();
  } else {
    $('#uploadDisabled').val('true');
    $('#upload').hide();
  }

  if (data.delete_allowed) {
    $('#deleteAllowed').val('true');
    $('.library-delete').show();
  } else {
    $('#uploadDisabled').val('false');
    $('.library-delete').hide();
  }

  const select = $('#filter-dir');
  const dataList = $('#upload-target-dirs');
  select.find('option').remove();
  dataList.find('option').remove();
  if (data.dirs.length > 0) {
    console.log(data.dirs);
    data.dirs.forEach(function(dir) {
      $('<option value="' + dir + '">' + dir + '</option>').appendTo(select);
      $('<option value="' + dir + '">').appendTo(dataList);
    });
  }

  // ----- Tag filters -----
  const tags = [];
  const tags_dict = {};
  $('.filter-tag').each(function(i, tag_element) {
    tags_dict[tag_element.innerHTML] = tag_element;
    tags.push(tag_element.innerHTML);
  });
  if (data.tags.length > 0) {
    for (const tag of data.tags) {
      if (tags.includes(tag)) {
        const index = tags.indexOf(tag);
        tags.splice(index, 1);
      } else {
        const tag_copy = lib_filter_tag_element.clone();
        tag_copy.html(tag);
        tag_copy.addClass('badge-' + getColor(tag));
        tag_copy.appendTo(lib_filter_tag_group);
        // Bind Event
        tag_copy.click(function(e) {
          const tag = $(e.currentTarget);
          if (!tag.hasClass('tag-clicked')) {
            tag.addClass('tag-clicked');
            tag.removeClass('tag-unclicked');
          } else {
            tag.addClass('tag-unclicked');
            tag.removeClass('tag-clicked');
          }
          updateResults();
        });
      }
    }
    for (const tag of tags) {
      tags_dict[tag].remove();
    }
  } else {
    $('.filter-tag').remove();
  }
}

const lib_loading = $('#library-item-loading');
const lib_empty = $('#library-item-empty');
let active_page = 1;

function updateResults(dest_page = 1) {
  active_page = dest_page;
  const data = getFilters(dest_page);
  data.action = 'query';

  console.debug(data);

  lib_group.animate({
    opacity: 0,
  }, 200, function() {
    $.ajax({
      type: 'POST',
      url: 'library',
      data: data,
      statusCode: {
        200: processResults,
        403: function() {
          location.reload(true);
        },
      },
    });

    $('.library-item-active').remove();
    lib_empty.hide();
    lib_loading.show();
    lib_group.animate({
      opacity: 1,
    }, 200);
  });

  updateLibraryControls();
}

const download_form = $('#download-form');
const download_id = download_form.find('input[name=\'id\']');
const download_type = download_form.find('input[name=\'type\']');
const download_dir = download_form.find('input[name=\'dir\']');
const download_tags = download_form.find('input[name=\'tags\']');
const download_keywords = download_form.find('input[name=\'keywords\']');

function downloadId(id) {
  download_id.attr('value', id);
  download_type.attr('value', '');
  download_dir.attr('value', '');
  download_tags.attr('value', '');
  download_keywords.attr('value', '');
  download_form.submit();
}

const page_ul = $('#library-page-ul');
const page_li = $('.library-page-li');
const page_no = $('.library-page-no');

function processResults(data) {
  lib_group.animate({
    opacity: 0,
  }, 200, function() {
    lib_loading.hide();
    const total_pages = data.total_pages;
    const active_page = data.active_page;
    const items = data.items;
    if (items.length === 0) {
      lib_loading.hide();
      lib_empty.show();
      page_ul.empty();
      lib_group.animate({opacity: 1}, 200);
      return;
    }
    items.forEach(
        function(item) {
          addResultItem(item);
          bindLibraryResultEvent();
        },
    );

    page_ul.empty();
    page_li.removeClass('active').empty();

    let i = 1;
    let page_li_copy;
    let page_no_copy;

    if (total_pages > 25) {
      i = (active_page - 12 >= 1) ? active_page - 12 : 1;
      const _i = total_pages - 23;
      i = (i < _i) ? i : _i;
      page_li_copy = page_li.clone();
      page_no_copy = page_no.clone();
      page_no_copy.html('&laquo;');

      page_no_copy.click(function(e) {
        updateResults(1);
      });

      page_no_copy.appendTo(page_li_copy);
      page_li_copy.appendTo(page_ul);
    }

    const limit = i + 24;
    for (; i <= total_pages && i <= limit; i++) {
      page_li_copy = page_li.clone();
      page_no_copy = page_no.clone();
      page_no_copy.html(i.toString());
      if (active_page === i) {
        page_li_copy.addClass('active');
      } else {
        page_no_copy.click(function(e) {
          const _page_no = $(e.currentTarget).html();
          updateResults(_page_no);
        });
      }
      page_no_copy.appendTo(page_li_copy);
      page_li_copy.appendTo(page_ul);
    }

    if (limit < total_pages) {
      page_li_copy = page_li.clone();
      page_no_copy = page_no.clone();
      page_no_copy.html('&raquo;');

      page_no_copy.click(function(e) {
        updateResults(total_pages);
      });

      page_no_copy.appendTo(page_li_copy);
      page_li_copy.appendTo(page_ul);
    }
    lib_group.animate({opacity: 1}, 200);
  });
}

// ---------------------
// ------ Tagging ------
// ---------------------

const add_tag_modal_title = $('#addTagModalTitle');
const add_tag_modal_item_id = $('#addTagModalItemId');
const add_tag_modal_tags = $('#addTagModalTags');
const add_tag_modal_input = $('#addTagModalInput');
const modal_tag = $('.modal-tag');
const modal_tag_text = $('.modal-tag-text');

function addTagModalShow(_id, _title, _tag_tuples) {
  add_tag_modal_title.html(_title);
  add_tag_modal_item_id.val(_id);
  add_tag_modal_tags.empty();
  _tag_tuples.forEach(function(tag_tuple) {
    modal_tag_text.html(tag_tuple[0]);
    const tag_copy = modal_tag.clone();
    const modal_tag_remove = tag_copy.find('.modal-tag-remove');
    modal_tag_remove.click(function(e) {
      $(e.currentTarget).parent().remove();
    });
    tag_copy.show();
    tag_copy.appendTo(add_tag_modal_tags);
    modal_tag_text.html('');
  });
  addTagModal.show();
}

document.getElementById('addTagModalAddBtn').addEventListener('click', () => {
  const new_tags = add_tag_modal_input.val().split(',').map(function(str) {
    return str.trim();
  });
  new_tags.forEach(function(tag) {
    modal_tag_text.html(tag);
    const tag_copy = modal_tag.clone();
    const modal_tag_remove = tag_copy.find('.modal-tag-remove');
    modal_tag_remove.click(function(e) {
      $(e.currentTarget).parent().remove();
    });
    tag_copy.show();
    tag_copy.appendTo(add_tag_modal_tags);
    modal_tag_text.html('');
  });
  add_tag_modal_input.val('');
});

document.getElementById('addTagModalSubmit').addEventListener('click', () => {
  const all_tags = $('.modal-tag-text');
  const tags = [];
  all_tags.each(function(i, element) {
    if (element.innerHTML) {
      tags.push(element.innerHTML);
    }
  });

  $.ajax({
    type: 'POST',
    url: 'library',
    data: {
      action: 'edit_tags',
      id: add_tag_modal_item_id.val(),
      tags: tags.join(','),
    },
    complete: function() {
      updateResults(active_page);
    },
  });
});

// ---------------------
// ------- Upload ------
// ---------------------

const uploadModal = new Modal(document.getElementById('uploadModal'));

const uploadFileInput = document.getElementById('uploadSelectFile');
const uploadModalItem = document.getElementsByClassName('uploadItem')[0];
const uploadModalList = document.getElementById('uploadModalList');
const uploadTargetDir = document.getElementById('uploadTargetDir');
const uploadSuccessAlert = document.getElementById('uploadSuccessAlert');
const uploadSubmitBtn = document.getElementById('uploadSubmit');
const uploadCancelBtn = document.getElementById('uploadCancel');
const uploadCancelTooltip = new Tooltip(uploadCancelBtn);
const uploadCloseBtn = document.getElementById('uploadClose');

const maxFileSize = parseInt(document.getElementById('maxUploadFileSize').value);

let filesToProceed = [];
const filesProgressItem = {};
let runningXHR = null;

let areYouSureToCancelUploading = false;

uploadSubmitBtn.addEventListener('click', uploadStart);
uploadCancelBtn.addEventListener('click', uploadCancel);

function uploadStart() {
  uploadModalList.textContent = '';
  uploadSuccessAlert.style.display = 'none';
  uploadCancelBtn.style.display = 'none';
  uploadCloseBtn.style.display = 'block';
  areYouSureToCancelUploading = false;
  uploadCancelTooltip.hide();
  const file_list = uploadFileInput.files;

  if (file_list.length) {
    for (const file of file_list) {
      generateUploadProgressItem(file);
      if (file.size > maxFileSize) {
        setUploadError(file.name, 'File too large!');
        continue;
      } else if (!(file.type.includes('audio') || file.type.includes('video'))) {
        setUploadError(file.name, 'Unsupported media format!');
        continue;
      }

      filesToProceed.push(file);
    }

    uploadFileInput.value = '';
    uploadModal.show();
    uploadNextFile();
  }
}

function setUploadError(filename, error) {
  const file_progress_item = filesProgressItem[filename];

  file_progress_item.title.classList.add('text-muted');
  file_progress_item.error.innerHTML += 'Error: ' + error;
  setProgressBar(file_progress_item.progress, 1);
  file_progress_item.progress.classList.add('bg-danger');
  file_progress_item.progress.classList.remove('progress-bar-animated');
}

function generateUploadProgressItem(file) {
  const item_clone = uploadModalItem.cloneNode(true);
  const title = item_clone.querySelector('.uploadItemTitle');
  title.innerHTML = file.name;
  const error = item_clone.querySelector('.uploadItemError');
  const progress = item_clone.querySelector('.uploadProgress');
  item_clone.style.display = 'block';

  const item = {
    title: title,
    error: error,
    progress: progress,
  };
  filesProgressItem[file.name] = item;
  uploadModalList.appendChild(item_clone);

  return item;
}

function uploadNextFile() {
  uploadCancelBtn.style.display = 'block';
  uploadCloseBtn.style.display = 'none';

  const req = new XMLHttpRequest();
  const file = filesToProceed.shift();
  const file_progress_item = filesProgressItem[file.name];

  req.addEventListener('load', function() {
    if (this.status === 200) {
      setProgressBar(file_progress_item.progress, 1);
      file_progress_item.progress.classList.add('bg-success');
      file_progress_item.progress.classList.remove('progress-bar-animated');
    } else if (this.status === 400 || this.status === 403) {
      setUploadError(file.name, 'Illegal request!');
    } else if (this.status === 500) {
      setUploadError(file.name, 'Server internal error!');
    } else {
      if (this.responseText) {
        setUploadError(file.name, this.responseText);
      } else {
        setUploadError(file.name, 'Unknown error!');
      }
    }

    if (filesToProceed.length) {
      uploadNextFile();
    } else {
      uploadSuccessAlert.style.display = 'block';
      runningXHR = null;

      uploadCancelBtn.style.display = 'none';
      uploadCloseBtn.style.display = 'block';

      request('post', {
        action: 'rescan',
      });
      updateResults();
    }
  });

  req.upload.addEventListener('progress', function(e) {
    if (e.lengthComputable) {
      const percent = e.loaded / e.total;
      setProgressBar(file_progress_item.progress, percent, Math.floor(percent * 100) + '%');
    }
  });

  const form = new FormData();
  form.append('file', file);
  form.append('targetdir', uploadTargetDir.value);

  req.open('POST', 'upload');
  req.withCredentials = true;
  req.send(form);

  file_progress_item.progress.classList.add('progress-bar-striped');
  file_progress_item.progress.classList.add('progress-bar-animated');

  runningXHR = req;
}

function uploadCancel() {
  if (!areYouSureToCancelUploading) {
    uploadCancelTooltip.show();
  } else {
    uploadCancelTooltip.hide();
    uploadModal.hide();
    runningXHR.abort();
    filesToProceed = [];
    uploadFileInput.value = '';
    request('post', {
      action: 'rescan',
    });
    updateResults();
  }

  areYouSureToCancelUploading = !areYouSureToCancelUploading;
}

// ---------------------
// ------  Player ------
// ---------------------

const player = new Toast(document.getElementById('playerToast'));
const playerArtwork = document.getElementById('playerArtwork');
const playerArtworkIdle = document.getElementById('playerArtworkIdle');
const playerTitle = document.getElementById('playerTitle');
const playerArtist = document.getElementById('playerArtist');
const playerBar = document.getElementById('playerBar');
const playerBarBox = document.getElementById('playerBarBox');
const playerPlayBtn = document.getElementById('playerPlayBtn');
const playerPauseBtn = document.getElementById('playerPauseBtn');
const playerSkipBtn = document.getElementById('playerSkipBtn');

let currentPlayingItem = null;

playerPlayBtn.addEventListener('click', () => {
  request('post', {action: 'resume'});
});

playerPauseBtn.addEventListener('click', () => {
  request('post', {action: 'pause'});
});

playerSkipBtn.addEventListener('click', () => {
  request('post', {action: 'next'});
});

document.getElementById('player-toast').addEventListener('click', () => {
  player.show();
});

function playerSetIdle() {
  playerArtwork.style.display = 'none';
  playerArtworkIdle.style.display = 'block';
  playerTitle.textContent = '-- IDLE --';
  playerArtist.textContent = '';
  setProgressBar(playerBar, 0);
  clearInterval(playhead_timer);
}

function updatePlayerInfo(item) {
  if (!item) {
    playerSetIdle();
    return;
  }
  playerArtwork.style.display = 'block';
  playerArtworkIdle.style.display = 'none';
  currentPlayingItem = item;
  playerTitle.textContent = item.title;
  playerArtist.textContent = item.artist;
  playerArtwork.setAttribute('src', item.thumbnail);
  playerArtwork.setAttribute('alt', limitChars(item.title));

  if (isOverflown(playerTitle)) {
    playerTitle.classList.add('scrolling');
  } else {
    playerTitle.classList.remove('scrolling');
  }

  if (isOverflown(playerArtist)) {
    playerArtist.classList.add('scrolling');
  } else {
    playerArtist.classList.remove('scrolling');
  }
}

function updatePlayerControls(play, empty) {
  if (empty) {
    playerSetIdle();
    playerPlayBtn.setAttribute('disabled', '');
    playerPauseBtn.setAttribute('disabled', '');
    playerSkipBtn.setAttribute('disabled', '');
  } else {
    playerPlayBtn.removeAttribute('disabled');
    playerPauseBtn.removeAttribute('disabled');
    playerSkipBtn.removeAttribute('disabled');
  }
  if (play) {
    playerPlayBtn.style.display = 'none';
    playerPauseBtn.style.display = 'block';
  } else {
    playerPlayBtn.style.display = 'block';
    playerPauseBtn.style.display = 'none';
  }
}

let playhead_timer;
let player_playhead_position;
let playhead_dragging = false;

function updatePlayerPlayhead(playhead) {
  if (!currentPlayingItem || playhead_dragging) {
    return;
  }
  if (currentPlayingItem.duration !== 0 || currentPlayingItem.duration < playhead) {
    playerBar.classList.remove('progress-bar-animated');
    clearInterval(playhead_timer);
    player_playhead_position = playhead;
    setProgressBar(playerBar, player_playhead_position / currentPlayingItem.duration, secondsToStr(player_playhead_position));
    if (playing) {
      playhead_timer = setInterval(function() {
        player_playhead_position += 0.3;
        setProgressBar(playerBar, player_playhead_position / currentPlayingItem.duration, secondsToStr(player_playhead_position));
      }, 300); // delay in milliseconds
    }
  } else {
    if (playing) {
      playerBar.classList.add('progress-bar-animated');
    } else {
      playerBar.classList.remove('progress-bar-animated');
    }
    setProgressBar(playerBar, 1);
  }
}

playerBarBox.addEventListener('mousedown', function() {
  if (currentPlayingItem && currentPlayingItem.duration > 0) {
    playerBarBox.addEventListener('mousemove', playheadDragged);
    clearInterval(playhead_timer);
    playhead_dragging = true;
  }
});

playerBarBox.addEventListener('mouseup', function(event) {
  playerBarBox.removeEventListener('mousemove', playheadDragged);
  const percent = (event.clientX - playerBarBox.getBoundingClientRect().x) / playerBarBox.clientWidth;
  request('post', {
    move_playhead: percent * currentPlayingItem.duration,
  });
  playhead_dragging = false;
});

function playheadDragged(event) {
  const percent = (event.clientX - playerBarBox.getBoundingClientRect().x) / playerBarBox.clientWidth;
  setProgressBar(playerBar, percent, secondsToStr(percent * currentPlayingItem.duration));
}

// -----------------------
// ----- Application -----
// -----------------------

document.addEventListener('DOMContentLoaded', () => {
  updateResults();
  updateLibraryControls();
});
