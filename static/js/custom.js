$('#uploadSelectFile').on('change', function () {
    //get the file name
    let fileName = $(this).val().replace('C:\\fakepath\\', " ");
    //replace the "Choose a file" label
    $(this).next('.custom-file-label').html(fileName);
});


// ----------------------
// ------ Playlist ------
// ----------------------

const pl_item_template = $(".playlist-item-template");
const pl_id_element = $(".playlist-item-id");
const pl_index_element = $(".playlist-item-index");
const pl_title_element = $(".playlist-item-title");
const pl_artist_element = $(".playlist-item-artist");
const pl_thumb_element = $(".playlist-item-thumbnail");
const pl_type_element = $(".playlist-item-type");
const pl_path_element = $(".playlist-item-path");

const pl_tag_edit_element = $(".playlist-item-edit");

const notag_element = $(".library-item-notag"); // these elements are shared with library
const tag_element = $(".library-item-tag");

const add_tag_modal = $("#addTagModal");

const playlist_loading = $("#playlist-loading");
const playlist_table = $("#playlist-table");
const playlist_empty = $("#playlist-empty");
const playlist_expand = $(".playlist-expand");

let playlist_items = null;

let playlist_ver = 0;
let playlist_current_index = 0;

let playlist_range_from = 0;
let playlist_range_to = 0;

let last_volume = 0;

let playing = false;

const playPauseBtn = $('#play-pause-btn');
const fastForwardBtn = $('#fast-forward-btn');

const playModeBtns = {
    'one-shot': $('#one-shot-mode-btn'),
    random: $('#random-mode-btn'),
    repeat: $('#repeat-mode-btn'),
    autoplay: $('#autoplay-mode-btn')
};
const playModeIcon = {
    'one-shot': 'fa-tasks',
    random: 'fa-random',
    repeat: 'fa-redo',
    autoplay: 'fa-robot'
};

function request(_url, _data, refresh = false) {
    console.log(_data);
    $.ajax({
        type: 'POST',
        url: _url,
        data: _data,
        statusCode: {
            200: function (data) {
                if (data.ver !== playlist_ver) {
                    checkForPlaylistUpdate();
                }
                updateControls(data.empty, data.play, data.mode, data.volume);
                updatePlayerPlayhead(data.playhead);
            },
            403: function (){
                location.reload(true);
            }
        },
    });
    if (refresh) {
        location.reload(true)
    }
}

function addPlaylistItem(item) {
    pl_id_element.val(item.id);
    pl_index_element.html(item.index + 1);
    pl_title_element.html(item.title);
    pl_artist_element.html(item.artist);
    pl_thumb_element.attr("src", item.thumbnail);
    pl_type_element.html(item.type);
    pl_path_element.html(item.path);

    let item_copy = pl_item_template.clone();
    item_copy.attr("id", "playlist-item-" + item.index);
    item_copy.addClass("playlist-item").removeClass("d-none");

    let tags = item_copy.find(".playlist-item-tags");
    tags.empty();

    let tag_edit_copy = pl_tag_edit_element.clone();
    tag_edit_copy.click(function () {
        addTagModalShow(item.id, item.title, item.tags);
    });
    tag_edit_copy.appendTo(tags);

    if (item.tags.length > 0) {
        item.tags.forEach(function (tag_tuple) {
            let tag_copy = tag_element.clone();
            tag_copy.html(tag_tuple[0]);
            tag_copy.addClass("badge-" + tag_tuple[1]);
            tag_copy.appendTo(tags);
        });
    } else {
        let tag_copy = notag_element.clone();
        tag_copy.appendTo(tags);
    }

    item_copy.appendTo(playlist_table);
}

function displayPlaylist(data) {
    playlist_table.animate({ opacity: 0 }, 200, function () {
        playlist_loading.hide();
        $(".playlist-item").remove();
        let items = data.items;
        playlist_items = items;
        let length = data.length;
        let start_from = data.start_from;
        playlist_range_from = start_from;
        playlist_range_to = start_from + items.length - 1;

        if (items.length < length && start_from > 0) {
            let _from = start_from - 5;
            _from = _from > 0 ? _from : 0;
            let _to = start_from - 1;
            if (_to > 0) {
                insertExpandPrompt(_from, start_from + length - 1, _from, _to, length);
            }
        }

        items.forEach(
            function (item) {
                addPlaylistItem(item);
            }
        );

        if (items.length < length && start_from + items.length < length) {
            let _from = start_from + items.length;
            let _to = start_from + items.length - 1 + 10;
            _to = _to < length - 1 ? _to : length - 1;
            if (start_from + items.length < _to) {
                insertExpandPrompt(start_from, _to, _from, _to, length);
            }
        }

        displayActiveItem(data.current_index);
        updatePlayerInfo(items[data.current_index - data.start_from]);
        bindPlaylistEvent();
        playlist_table.animate({ opacity: 1 }, 200);
    });
}

function displayActiveItem(current_index) {
    $(".playlist-item").removeClass("table-active");
    $("#playlist-item-" + current_index).addClass("table-active");
}

function insertExpandPrompt(real_from, real_to, display_from, display_to, total_length) {
    let expand_copy = playlist_expand.clone();
    expand_copy.addClass('playlist-item');
    expand_copy.removeClass('d-none');
    if (display_from !== display_to) {
        expand_copy.find(".playlist-expand-item-range").html((display_from + 1) + "~" + (display_to + 1)
            + " of " + (total_length) + " items");
    } else {
        expand_copy.find(".playlist-expand-item-range").html(display_from + " of " + (total_length) + " items");
    }

    expand_copy.addClass('playlist-item');
    expand_copy.appendTo(playlist_table);
    expand_copy.click(function () {
        playlist_range_from = real_from;
        playlist_range_to = real_to;
        updatePlaylist();
    });
}

function updatePlaylist() {
    playlist_table.animate({ opacity: 0 }, 200, function () {
        playlist_empty.addClass('d-none');
        playlist_loading.show();
        playlist_table.find(".playlist-item").css("opacity", 0);
        let data = {};
        if (!(playlist_range_from === 0 && playlist_range_to === 0)) {
            data = {
                range_from: playlist_range_from,
                range_to: playlist_range_to
            };
        }
        $.ajax({
            type: 'GET',
            url: 'playlist',
            data: data,
            statusCode: {
                200: displayPlaylist,
                204: function () {
                    playlist_loading.hide();
                    playlist_empty.removeClass('d-none');
                    $(".playlist-item").remove();
                }
            }
        });
        playlist_table.animate({ opacity: 1 }, 200);
    });
}

function checkForPlaylistUpdate() {
    $.ajax({
        type: 'POST',
        url: 'post',
        statusCode: {
            200: function (data) {
                if (data.ver !== playlist_ver) {
                    playlist_ver = data.ver;
                    playlist_range_from = 0;
                    playlist_range_to = 0;
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
                if (!data.empty){
                    updatePlayerPlayhead(data.playhead);
                }
            }
        }
    });
}

function bindPlaylistEvent() {
    $(".playlist-item-play").unbind().click(
        function (e) {
            request('post', {
                'play_music': ($(e.currentTarget).parent().parent().parent().find(".playlist-item-index").html() - 1)
            });
        }
    );
    $(".playlist-item-trash").unbind().click(
        function (e) {
            request('post', {
                'delete_music': ($(e.currentTarget).parent().parent().parent().find(".playlist-item-index").html() - 1)
            });
        }
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
        } else {
            playing = false;
            playPauseBtn.find('[data-fa-i2svg]').removeClass('fa-pause').addClass('fa-play');
        }
    }

    for (const otherMode of Object.values(playModeBtns)) {
        otherMode.removeClass('active');
    }
    playModeBtns[mode].addClass('active');

    let playModeIndicator = $('#modeIndicator');
    for (const icon_class of Object.values(playModeIcon)) {
        playModeIndicator.removeClass(icon_class);
    }
    playModeIndicator.addClass(playModeIcon[mode]);

    if (volume !== last_volume) {
        last_volume = volume;
        if (volume > 1) {
            document.getElementById("volume-slider").value = 1;
        } else if (volume < 0) {
            document.getElementById("volume-slider").value = 0;
        } else {
            document.getElementById("volume-slider").value = volume;
        }
    }
}

function togglePlayPause() {
    if (playing) {
        request('post', {action: 'pause'});
    } else {
        request('post', {action: 'resume'});
    }
}

function changePlayMode(mode) {
    request('post', {action: mode});
}


// ----------------------
// --- THEME SWITCHER ---
// ----------------------
function themeInit() {
    let theme = localStorage.getItem("theme");
    if (theme !== null) {
        setPageTheme(theme);
    }
}

function switchTheme() {
    let theme = localStorage.getItem("theme");
    if (theme === "light" || theme === null) {
        setPageTheme("dark");
        localStorage.setItem("theme", "dark");
    } else {
        setPageTheme("light");
        localStorage.setItem("theme", "light");
    }
}

function setPageTheme(theme) {
    if (theme === "light")
        document.getElementById("pagestyle").setAttribute("href", "static/css/bootstrap.min.css");
    else if (theme === "dark")
        document.getElementById("pagestyle").setAttribute("href", "static/css/bootstrap.darkly.min.css");
}

// ---------------------
// ------ Browser ------
// ---------------------

let filters = {
    file: $('#filter-type-file'),
    url: $('#filter-type-url'),
    radio: $('#filter-type-radio'),
};
let filter_dir = $("#filter-dir");
let filter_keywords = $("#filter-keywords");

function setFilterType(event, type) {
    event.preventDefault();

    if (filters[type].hasClass('active')) {
        filters[type].removeClass('active btn-primary').addClass('btn-secondary');
        filters[type].find('input[type=radio]').removeAttr('checked');
    } else {
        filters[type].removeClass('btn-secondary').addClass('active btn-primary');
        filters[type].find('input[type=radio]').attr('checked', 'checked');
    }

    if (type === 'file') {
        filter_dir.prop('disabled', !filters['file'].hasClass('active'));
    }

    updateResults();
}

// Bind Event
$(".filter-tag").click(function (e) {
    let tag = $(e.currentTarget);
    if (!tag.hasClass('tag-clicked')) {
        tag.addClass('tag-clicked');
        tag.removeClass('tag-unclicked');
    } else {
        tag.addClass('tag-unclicked');
        tag.removeClass('tag-clicked');
    }
    updateResults();
});

filter_dir.change(function () { updateResults() });
filter_keywords.change(function () { updateResults() });

let item_template = $("#library-item");

function bindLibraryResultEvent() {
    $(".library-thumb-col").unbind().hover(
        function (e) { $(e.currentTarget).find(".library-thumb-grp").addClass("library-thumb-grp-hover"); },
        function (e) { $(e.currentTarget).find(".library-thumb-grp").removeClass("library-thumb-grp-hover"); }
    );

    $(".library-info-title").unbind().hover(
        function (e) { $(e.currentTarget).parent().find(".library-thumb-grp").addClass("library-thumb-grp-hover"); },
        function (e) { $(e.currentTarget).parent().find(".library-thumb-grp").removeClass("library-thumb-grp-hover"); }
    );

    $(".library-item-play").unbind().click(
        function (e) {
            request('post', {
                'add_item_at_once': $(e.currentTarget).parent().parent().parent().find(".library-item-id").val()
            });
        }
    );

    $(".library-item-trash").unbind().click(
        function (e) {
            request('post', {
                'delete_item_from_library': $(e.currentTarget).parent().parent().find(".library-item-id").val()
            });
            updateResults(active_page);
        }
    );

    $(".library-item-download").unbind().click(
        function (e) {
            let id = $(e.currentTarget).parent().parent().find(".library-item-id").val();
            //window.open('/download?id=' + id);
            downloadId(id);
        }
    );

    $(".library-item-add-next").unbind().click(
        function (e) {
            let id = $(e.currentTarget).parent().parent().find(".library-item-id").val();
            request('post', {
                'add_item_next': id
            });
        }
    );

    $(".library-item-add-bottom").unbind().click(
        function (e) {
            let id = $(e.currentTarget).parent().parent().find(".library-item-id").val();
            request('post', {
                'add_item_bottom': id
            });
        }
    );
}

const lib_group = $("#library-group");
const id_element = $(".library-item-id");
const title_element = $(".library-item-title");
const artist_element = $(".library-item-artist");
const thumb_element = $(".library-item-thumb");
const type_element = $(".library-item-type");
const path_element = $(".library-item-path");

const tag_edit_element = $(".library-item-edit");
//var notag_element = $(".library-item-notag");
//var tag_element = $(".library-item-tag");

//var add_tag_modal = $("#addTagModal");

function addResultItem(item) {
    id_element.val(item.id);
    title_element.html(item.title);
    artist_element.html(item.artist ? ("- " + item.artist) : "");
    thumb_element.attr("src", item.thumb);
    type_element.html("[" + item.type + "]");
    path_element.html(item.path);

    let item_copy = item_template.clone();
    item_copy.addClass("library-item-active");

    let tags = item_copy.find(".library-item-tags");
    tags.empty();

    let tag_edit_copy = tag_edit_element.clone();
    tag_edit_copy.click(function () {
        addTagModalShow(item.id, item.title, item.tags);
    });
    tag_edit_copy.appendTo(tags);

    if (item.tags.length > 0) {
        item.tags.forEach(function (tag_tuple) {
            let tag_copy = tag_element.clone();
            tag_copy.html(tag_tuple[0]);
            tag_copy.addClass("badge-" + tag_tuple[1]);
            tag_copy.appendTo(tags);
        });
    } else {
        let tag_copy = notag_element.clone();
        tag_copy.appendTo(tags);
    }

    item_copy.appendTo(lib_group);
    item_copy.show();
}

function getFilters(dest_page = 1) {
    let tags = $(".tag-clicked");
    let tags_list = [];
    tags.each(function (index, tag) {
        tags_list.push(tag.innerHTML);
    });

    let filter_types = [];
    for (const filter in filters) {
        if (filters[filter].hasClass('active')) {
            filter_types.push(filter);
        }
    }

    return {
        type: filter_types.join(','),
        dir: filter_dir.val(),
        tags: tags_list.join(","),
        keywords: filter_keywords.val(),
        page: dest_page
    };
}

let lib_loading = $("#library-item-loading");
let lib_empty = $("#library-item-empty");
let active_page = 1;

function updateResults(dest_page = 1) {
    active_page = dest_page;
    let data = getFilters(dest_page);
    data.action = "query";

    lib_group.animate({ opacity: 0 }, 200, function () {
        $.ajax({
            type: 'POST',
            url: 'library',
            data: data,
            statusCode: {
                200: processResults,
                204: function () {
                    lib_loading.hide();
                    lib_empty.show();
                    page_ul.empty();
                },
                403: function () {
                    location.reload(true);
                }
            }
        });

        $(".library-item-active").remove();
        lib_empty.hide();
        lib_loading.show();
        lib_group.animate({ opacity: 1 }, 200);
    });
}

const download_form = $("#download-form");
const download_id = download_form.find("input[name='id']");
const download_type = download_form.find("input[name='type']");
const download_dir = download_form.find("input[name='dir']");
const download_tags = download_form.find("input[name='tags']");
const download_keywords = download_form.find("input[name='keywords']");

function addAllResults() {
    let data = getFilters();
    data.action = "add";

    console.log(data);

    $.ajax({
        type: 'POST',
        url: 'library',
        data: data
    });

    checkForPlaylistUpdate();
}

function deleteAllResults() {
    let data = getFilters();
    data.action = "delete";

    console.log(data);

    $.ajax({
        type: 'POST',
        url: 'library',
        data: data
    });

    checkForPlaylistUpdate();
    updateResults();
}

function downloadAllResults() {
    let cond = getFilters();
    download_id.val();
    download_type.val(cond.type);
    download_dir.val(cond.dir);
    download_tags.val(cond.tags);
    download_keywords.val(cond.keywords);
    download_form.submit();
}

function downloadId(id) {
    download_id.attr("value", id);
    download_type.attr("value", "");
    download_dir.attr("value", "");
    download_tags.attr("value", "");
    download_keywords.attr("value", "");
    download_form.submit();
}

const page_ul = $("#library-page-ul");
const page_li = $(".library-page-li");
const page_no = $(".library-page-no");

function processResults(data) {
    lib_group.animate({ opacity: 0 }, 200, function () {
        lib_loading.hide();
        let total_pages = data.total_pages;
        let active_page = data.active_page;
        let items = data.items;
        items.forEach(
            function (item) {
                addResultItem(item);
                bindLibraryResultEvent();
            }
        );

        page_ul.empty();
        page_li.removeClass('active').empty();

        let i = 1;
        let page_li_copy;
        let page_no_copy;

        if (total_pages > 25) {
            i = (active_page - 12 >= 1) ? active_page - 12 : 1;
            let _i = total_pages - 23;
            i = (i < _i) ? i : _i;
            page_li_copy = page_li.clone();
            page_no_copy = page_no.clone();
            page_no_copy.html("&laquo;");

            page_no_copy.click(function (e) {
                updateResults(1);
            });

            page_no_copy.appendTo(page_li_copy);
            page_li_copy.appendTo(page_ul);
        }

        let limit = i + 24;
        for (; i <= total_pages && i <= limit; i++) {
            page_li_copy = page_li.clone();
            page_no_copy = page_no.clone();
            page_no_copy.html(i.toString());
            if (active_page === i) {
                page_li_copy.addClass("active");
            } else {
                page_no_copy.click(function (e) {
                    let _page_no = $(e.currentTarget).html();
                    updateResults(_page_no);
                });
            }
            page_no_copy.appendTo(page_li_copy);
            page_li_copy.appendTo(page_ul);
        }

        if (limit < total_pages) {
            page_li_copy = page_li.clone();
            page_no_copy = page_no.clone();
            page_no_copy.html("&raquo;");

            page_no_copy.click(function (e) {
                updateResults(total_pages);
            });

            page_no_copy.appendTo(page_li_copy);
            page_li_copy.appendTo(page_ul);
        }

        lib_group.animate({ opacity: 1 }, 200);
    });
}

// ---------------------
// ------ Tagging ------
// ---------------------

const add_tag_modal_title = $("#addTagModalTitle");
const add_tag_modal_item_id = $("#addTagModalItemId");
const add_tag_modal_tags = $("#addTagModalTags");
const add_tag_modal_input = $("#addTagModalInput");
const modal_tag = $(".modal-tag");
const modal_tag_text = $(".modal-tag-text");

function addTagModalShow(_id, _title, _tag_tuples) {
    add_tag_modal_title.html("Edit tags for " + _title);
    add_tag_modal_item_id.val(_id);
    add_tag_modal_tags.empty();
    _tag_tuples.forEach(function (tag_tuple) {
        modal_tag_text.html(tag_tuple[0]);
        let tag_copy = modal_tag.clone();
        let modal_tag_remove = tag_copy.find(".modal-tag-remove");
        modal_tag_remove.click(function (e) {
            $(e.currentTarget).parent().remove();
        });
        tag_copy.show();
        tag_copy.appendTo(add_tag_modal_tags);
        modal_tag_text.html("");
    });
    add_tag_modal.modal('show');
}

function addTagModalAdd() {
    let new_tags = add_tag_modal_input.val().split(",").map(function (str) { return str.trim() });
    new_tags.forEach(function (tag) {
        modal_tag_text.html(tag);
        let tag_copy = modal_tag.clone();
        let modal_tag_remove = tag_copy.find(".modal-tag-remove");
        modal_tag_remove.click(function (e) {
            $(e.currentTarget).parent().remove();
        });
        tag_copy.show();
        tag_copy.appendTo(add_tag_modal_tags);
        modal_tag_text.html("");
    });
    add_tag_modal_input.val("");
}

function addTagModalSubmit() {
    let all_tags = $(".modal-tag-text");
    let tags = [];
    all_tags.each(function (i, element) {
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
            tags: tags.join(",")
        }
    });
    updateResults(active_page);
}

// ---------------------
// ------- Volume ------
// ---------------------

const volume_popover_btn = document.querySelector("#volume-popover-btn");
const volume_popover_div = document.querySelector("#volume-popover");
let volume_popover_instance = null;
let volume_popover_show = false;

volume_popover_btn.addEventListener('click', function(e){ e.stopPropagation(); })
volume_popover_div.addEventListener('click', function(e){ e.stopPropagation(); })

function toggleVolumePopover(){
    if (!volume_popover_show){
        volume_popover_instance = new Popper(volume_popover_btn, volume_popover_div, {
            placement: 'top',
            modifiers: {
                offset: { offset: '0, 8' }
            }
        } );
        volume_popover_div.setAttribute('data-show', '');
    } else {
        volume_popover_div.removeAttribute('data-show');
        if (volume_popover_instance){
            volume_popover_instance.destroy();
            volume_popover_instance = null;
        }
    }
    volume_popover_show = !volume_popover_show;

    document.addEventListener('click', function(){
        volume_popover_div.removeAttribute('data-show');
        if (volume_popover_instance){
            volume_popover_instance.destroy();
            volume_popover_instance = null;
            volume_popover_show = !volume_popover_show;
        }
    }, { once: true } );
}

let volume_update_timer;
function setVolumeDelayed(new_volume_value) {
    window.clearTimeout(volume_update_timer);
    volume_update_timer = window.setTimeout(function () {
        request('post', { action: 'volume_set_value', new_volume: new_volume_value });
    }, 500); // delay in milliseconds
}

// ---------------------
// ------- Upload ------
// ---------------------

const uploadModal = $("#uploadModal");

const uploadFileInput = document.getElementById("uploadSelectFile");
const uploadModalItem = document.getElementsByClassName("uploadItem")[0];
const uploadModalList = document.getElementById("uploadModalList");
const uploadTargetDir = document.getElementById("uploadTargetDir");
const uploadSuccessAlert = document.getElementById("uploadSuccessAlert");
const uploadSubmitBtn = document.getElementById("uploadSubmit");
const uploadCancelBtn = document.getElementById("uploadCancel");
const uploadCloseBtn = document.getElementById("uploadClose");

const maxFileSize = parseInt(document.getElementById("maxUploadFileSize").value);

let filesToProceed = [];
let filesProgressItem = {};
let runningXHR = null;

let areYouSureToCancelUploading = false;

uploadSubmitBtn.addEventListener("click", uploadStart);
uploadCancelBtn.addEventListener("click", uploadCancel)

function uploadStart(){
    uploadModalList.textContent = '';
    uploadSuccessAlert.style.display = 'none';
    uploadCancelBtn.style.display = 'none';
    uploadCloseBtn.style.display = 'block';
    areYouSureToCancelUploading = false;
    $(uploadCancelBtn).tooltip('hide');
    const file_list = uploadFileInput.files;

    if (file_list.length) {
        for (const file of file_list) {
            generateUploadProgressItem(file);
            if (file.size > maxFileSize) {
                setUploadError(file.name, 'File too large!')
                continue;
            } else if (!file.type.includes("audio")) {
                setUploadError(file.name, 'Unsupported media format!')
                continue;
            }

            filesToProceed.push(file);
        }

        uploadFileInput.value = '';
        uploadModal.modal("show");
        uploadNextFile();
    }
}

function setUploadError(filename, error){
    let file_progress_item = filesProgressItem[filename];

    file_progress_item.title.classList.add("text-muted");
    file_progress_item.error.innerHTML += 'Error: ' + error;
    setProgressBar(file_progress_item.progress, 1);
    file_progress_item.progress.classList.add("bg-danger");
    file_progress_item.progress.classList.remove("progress-bar-animated");
}

function generateUploadProgressItem(file){
    let item_clone = uploadModalItem.cloneNode(true);
    let title = item_clone.querySelector(".uploadItemTitle");
    title.innerHTML = file.name;
    let error = item_clone.querySelector(".uploadItemError");
    let progress = item_clone.querySelector(".uploadProgress");
    item_clone.style.display = "block";

    let item = { title: title, error: error, progress: progress };
    filesProgressItem[file.name] = item;
    uploadModalList.appendChild(item_clone);

    return item;
}

function uploadNextFile(){
    uploadCancelBtn.style.display = 'block';
    uploadCloseBtn.style.display = 'none';

    let req = new XMLHttpRequest();
    let file = filesToProceed.shift();
    let file_progress_item = filesProgressItem[file.name];

    req.addEventListener("load", function(){
        if (this.status === 200) {
            setProgressBar(file_progress_item.progress, 1);
            file_progress_item.progress.classList.add("bg-success");
            file_progress_item.progress.classList.remove("progress-bar-animated");
        } else if (this.status === 400 || this.status === 403) {
            setUploadError(file.name, 'Illegal request!')
        } else if (this.status === 500) {
            setUploadError(file.name, 'Server internal error!')
        } else {
            if (this.responseText) {
                setUploadError(file.name, this.responseText)
            } else {
                setUploadError(file.name, 'Unknown error!')
            }
        }

        if (filesToProceed.length) {
            uploadNextFile();
        } else {
            uploadSuccessAlert.style.display = "block";
            runningXHR = null;

            uploadCancelBtn.style.display = 'none';
            uploadCloseBtn.style.display = 'block';

            request('post', {action : 'rescan'});
            updateResults();
        }
    });

    req.upload.addEventListener("progress", function(e){
        if (e.lengthComputable) {
            let percent = e.loaded / e.total;
            setProgressBar(file_progress_item.progress, percent, Math.floor(percent*100) + "%");
        }
    });

    let form = new FormData();
    form.append('file', file);
    form.append('targetdir', uploadTargetDir.value);

    req.open('POST', 'upload');
    req.withCredentials = true;
    req.send(form);

    file_progress_item.progress.classList.add("progress-bar-striped");
    file_progress_item.progress.classList.add("progress-bar-animated");

    runningXHR = req;
}

function uploadCancel(){
    if (!areYouSureToCancelUploading){
        $(uploadCancelBtn).tooltip('show');
    } else {
        $(uploadCancelBtn).tooltip('hide');
        uploadModal.modal('hide');
        runningXHR.abort()
        filesToProceed = [];
        uploadFileInput.value = '';
        request('post', {action : 'rescan'});
        updateResults();
    }

    areYouSureToCancelUploading = !areYouSureToCancelUploading;
}

// ---------------------
// ------  Player ------
// ---------------------

const player = document.getElementById("playerToast");
const playerArtwork = document.getElementById("playerArtwork");
const playerArtworkIdle = document.getElementById("playerArtworkIdle");
const playerTitle = document.getElementById("playerTitle");
const playerArtist = document.getElementById("playerArtist");
const playerBar = document.getElementById("playerBar");
const playerBarBox = document.getElementById("playerBarBox");
const playerPlayBtn = document.getElementById("playerPlayBtn");
const playerPauseBtn = document.getElementById("playerPauseBtn");
const playerSkipBtn = document.getElementById("playerSkipBtn");

let currentPlayingItem = null;

function togglePlayer() {
    $(player).toast("show");
}

function playerSetIdle(){
    playerArtwork.style.display ='none';
    playerArtworkIdle.style.display ='block';
    playerTitle.textContent = '-- IDLE --';
    playerArtist.textContent = '';
    setProgressBar(playerBar, 0);
}

function updatePlayerInfo(item){
    if (!item){
        playerSetIdle();
    }
    playerArtwork.style.display ='block';
    playerArtworkIdle.style.display ='none';
    currentPlayingItem = item;
    playerTitle.textContent = item.title;
    playerArtist.textContent = item.artist;
    playerArtwork.setAttribute("src", item.thumbnail);

    if (isOverflown(playerTitle)) {
        playerTitle.classList.add("scrolling")
    } else {
        playerTitle.classList.remove("scrolling")
    }

    if (isOverflown(playerArtist)) {
        playerArtist.classList.add("scrolling")
    } else {
        playerArtist.classList.remove("scrolling")
    }
}

function updatePlayerControls(play, empty) {
    if (empty) {
        playerSetIdle();
        playerPlayBtn.setAttribute("disabled", "");
        playerPauseBtn.setAttribute("disabled", "");
        playerSkipBtn.setAttribute("disabled", "");
    } else {
        playerPlayBtn.removeAttribute("disabled");
        playerPauseBtn.removeAttribute("disabled");
        playerSkipBtn.removeAttribute("disabled");
    }
    if (play) {
        playerPlayBtn.style.display ='none';
        playerPauseBtn.style.display = 'block';
    } else {
        playerPlayBtn.style.display = 'block';
        playerPauseBtn.style.display = 'none';
    }
}

let playhead_timer;
let player_playhead_position;
let playhead_dragging = false;
function updatePlayerPlayhead(playhead){
    if (!currentPlayingItem || playhead_dragging){
        return;
    }
    if (currentPlayingItem.duration !== 0 || currentPlayingItem.duration < playhead){
        playerBar.classList.remove("progress-bar-animated");
        clearInterval(playhead_timer);
        player_playhead_position = playhead;
        setProgressBar(playerBar, player_playhead_position / currentPlayingItem.duration, secondsToStr(player_playhead_position));
        if (playing) {
            playhead_timer = setInterval(function () {
                player_playhead_position += 0.1;
                setProgressBar(playerBar, player_playhead_position / currentPlayingItem.duration, secondsToStr(player_playhead_position));
            }, 100); // delay in milliseconds
        }
    } else {
        if (playing) {
            playerBar.classList.add("progress-bar-animated");
        } else {
            playerBar.classList.remove("progress-bar-animated");
        }
        setProgressBar(playerBar, 1);
    }
}

playerBarBox.addEventListener('mousedown', function () {
    if (currentPlayingItem && currentPlayingItem.duration > 0){
        playerBarBox.addEventListener('mousemove', playheadDragged);
        clearInterval(playhead_timer);
        playhead_dragging = true;
    }
});
playerBarBox.addEventListener('mouseup', function (event) {
    playerBarBox.removeEventListener('mousemove', playheadDragged);
    let percent = event.offsetX / playerBarBox.clientWidth;
    request('post', {move_playhead: percent * currentPlayingItem.duration});
    playhead_dragging = false;
});

function playheadDragged(event){
    let percent = event.offsetX / playerBarBox.clientWidth;
    setProgressBar(playerBar, percent, secondsToStr(percent * currentPlayingItem.duration));
}


// ---------------------
// -------  Util -------
// ---------------------

function isOverflown(element) {
  return element.scrollHeight > element.clientHeight || element.scrollWidth > element.clientWidth;
}

function setProgressBar(bar, progress, text="") {
    let prog_str = (progress*100).toString();
    bar.setAttribute("aria-valuenow", prog_str);
    bar.style.width = prog_str + "%";
    bar.textContent = text;
}

function secondsToStr(seconds) {
    seconds = Math.floor(seconds);
    let mins = Math.floor(seconds / 60);
    let secs = seconds % 60;
    return ("00" + mins).slice(-2) + ":" + ("00" + secs).slice(-2);
}


themeInit();
updateResults();
$(document).ready(updatePlaylist);

// Check the version of playlist to see if update is needed.
setInterval(checkForPlaylistUpdate, 3000);
