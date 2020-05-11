$('#uploadSelectFile').on('change', function () {
    //get the file name
    var fileName = $(this).val().replace('C:\\fakepath\\', " ");
    //replace the "Choose a file" label
    $(this).next('.custom-file-label').html(fileName);
});
$('a.a-submit, button.btn-submit').on('click', function (event) {
    $(event.target).closest('form').submit();
});


// ----------------------
// ------ Playlist ------
// ----------------------

var pl_item_template = $(".playlist-item-template");
var pl_id_element = $(".playlist-item-id");
var pl_index_element = $(".playlist-item-index");
var pl_title_element = $(".playlist-item-title");
var pl_artist_element = $(".playlist-item-artist");
var pl_thumb_element = $(".playlist-item-thumbnail");
var pl_type_element = $(".playlist-item-type");
var pl_path_element = $(".playlist-item-path");

var pl_tag_edit_element = $(".playlist-item-edit");

var notag_element = $(".library-item-notag"); // these elements are shared with library
var tag_element = $(".library-item-tag");

var add_tag_modal = $("#addTagModal");

var playlist_loading = $("#playlist-loading");
var playlist_table = $("#playlist-table");
var playlist_empty = $("#playlist-empty");
var playlist_expand = $("#playlist-expand");

var playlist_ver = 0;
var playlist_current_index = 0;

var playlist_range_from = 0;
var playlist_range_to = 0;

var last_volume = 0;

var playing = false;
var playPauseBtn = $("#play-pause-btn");

var playModeBtns = {
    'one-shot': $('#one-shot-mode-btn'),
    random: $('#random-mode-btn'),
    repeat: $('#repeat-mode-btn'),
    autoplay: $('#autoplay-mode-btn')
};
var playModeIcon = {
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
            }
        },
    });
    if (refresh) {
        location.reload()
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

    var item_copy = pl_item_template.clone();
    item_copy.attr("id", "playlist-item-" + item.index);
    item_copy.addClass("playlist-item").removeClass("d-none");

    var tags = item_copy.find(".playlist-item-tags");
    tags.empty();

    var tag_edit_copy = pl_tag_edit_element.clone();
    tag_edit_copy.click(function () {
        addTagModalShow(item.id, item.title, item.tags);
    });
    tag_edit_copy.appendTo(tags);

    if (item.tags.length > 0) {
        item.tags.forEach(function (tag_tuple) {
            tag_copy = tag_element.clone();
            tag_copy.html(tag_tuple[0]);
            tag_copy.addClass("badge-" + tag_tuple[1]);
            tag_copy.appendTo(tags);
        });
    } else {
        tag_copy = notag_element.clone();
        tag_copy.appendTo(tags);
    }

    item_copy.appendTo(playlist_table);
}

function displayPlaylist(data) {
    playlist_table.animate({ opacity: 0 }, 200, function () {
        playlist_loading.hide();
        $(".playlist-item").remove();
        var items = data.items;
        var length = data.length;
        var start_from = data.start_from;
        playlist_range_from = start_from;
        playlist_range_to = start_from + items.length - 1;

        if (items.length < length && start_from > 0) {
            _from = start_from - 5;
            _from = _from > 0 ? _from : 0;
            _to = start_from - 1;
            if (_to > 0) {
                insertExpandPrompt(_from, start_from + length - 1, _from, _to);
            }
        }

        items.forEach(
            function (item) {
                addPlaylistItem(item);
            }
        );

        if (items.length < length && start_from + items.length < length) {
            _from = start_from + items.length;
            _to = start_from + items.length - 1 + 10;
            _to = _to < length - 1 ? _to : length - 1;
            if (start_from + items.length < _to) {
                insertExpandPrompt(start_from, _to, _from, _to);
            }
        }

        displayActiveItem(data.current_index);
        bindPlaylistEvent();
        playlist_table.animate({ opacity: 1 }, 200);
    });
}

function displayActiveItem(current_index) {
    $(".playlist-item").removeClass("table-active");
    $("#playlist-item-" + current_index).addClass("table-active");
}

function insertExpandPrompt(real_from, real_to, display_from, display_to) {
    var expand_copy = playlist_expand.clone();
    playlist_expand.removeClass('d-none');
    if (display_from !== display_to) {
        expand_copy.find(".playlist-expand-item-range").html((display_from + 1) + "~" + (display_to + 1));
    } else {
        expand_copy.find(".playlist-expand-item-range").html(display_from);
    }

    expand_copy.addClass('playlist-item');
    expand_copy.appendTo(playlist_table);
    expand_copy.click(function () {
        playlist_range_from = real_from;
        playlist_range_to = real_to;
        checkForPlaylistUpdate();
    });
}

function updatePlaylist() {
    playlist_table.animate({ opacity: 0 }, 200, function () {
        playlist_empty.addClass('d-none');
        playlist_loading.show();
        playlist_table.find(".playlist-item").css("opacity", 0);
        data = {};
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
                    if ((data.current_index > playlist_range_to || data.current_index < playlist_range_from)
                        && data.current_index !== -1) {
                        playlist_range_from = 0;
                        playlist_range_to = 0;
                        updatePlaylist();
                    } else {
                        playlist_current_index = data.current_index;
                        displayActiveItem(data.current_index);
                    }
                }
                updateControls(data.empty, data.play, data.mode, data.volume);
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
    if (empty) {
        playPauseBtn.prop("disabled", true);
    } else {
        playPauseBtn.prop("disabled", false);
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

    if (volume != last_volume) {
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

// Check the version of playlist to see if update is needed.
setInterval(checkForPlaylistUpdate, 3000);


// ----------------------
// --- THEME SWITCHER ---
// ----------------------
function themeInit() {
    var theme = localStorage.getItem("theme");
    if (theme !== null) {
        setPageTheme(theme);
    }
}

function switchTheme() {
    var theme = localStorage.getItem("theme");
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

var filters = {
    file: $('#filter-type-file'),
    url: $('#filter-type-url'),
    radio: $('#filter-type-radio'),
};
var filter_dir = $("#filter-dir");
var filter_keywords = $("#filter-keywords");

function setFilterType(event, type) {
    event.preventDefault();

    if (filters[type].hasClass('active')) {
        filters[type].removeClass('active btn-primary').addClass('btn-secondary');
        filters[type].find('input[type=radio]').removeAttr('checked');
    } else {
        filters[type].removeClass('btn-secondary').addClass('active btn-primary');
        filters[type].find('input[type=radio]').attr('checked', 'checked');
    }

    updateResults();
}

// Bind Event
var _tag = null;
$(".filter-tag").click(function (e) {
    var tag = $(e.currentTarget);
    _tag = tag;
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

var item_template = $("#library-item");

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
            var id = $(e.currentTarget).parent().parent().find(".library-item-id").val();
            //window.open('/download?id=' + id);
            downloadId(id);
        }
    );

    $(".library-item-add-next").unbind().click(
        function (e) {
            var id = $(e.currentTarget).parent().parent().find(".library-item-id").val();
            request('post', {
                'add_item_next': id
            });
        }
    );

    $(".library-item-add-bottom").unbind().click(
        function (e) {
            var id = $(e.currentTarget).parent().parent().find(".library-item-id").val();
            request('post', {
                'add_item_bottom': id
            });
        }
    );
}

var lib_group = $("#library-group");
var id_element = $(".library-item-id");
var title_element = $(".library-item-title");
var artist_element = $(".library-item-artist");
var thumb_element = $(".library-item-thumb");
var type_element = $(".library-item-type");
var path_element = $(".library-item-path");

var tag_edit_element = $(".library-item-edit");
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

    var item_copy = item_template.clone();
    item_copy.addClass("library-item-active");

    var tags = item_copy.find(".library-item-tags");
    tags.empty();

    var tag_edit_copy = tag_edit_element.clone();
    tag_edit_copy.click(function () {
        addTagModalShow(item.id, item.title, item.tags);
    });
    tag_edit_copy.appendTo(tags);

    if (item.tags.length > 0) {
        item.tags.forEach(function (tag_tuple) {
            tag_copy = tag_element.clone();
            tag_copy.html(tag_tuple[0]);
            tag_copy.addClass("badge-" + tag_tuple[1]);
            tag_copy.appendTo(tags);
        });
    } else {
        tag_copy = notag_element.clone();
        tag_copy.appendTo(tags);
    }

    item_copy.appendTo(lib_group);
    item_copy.show();
}

function getFilters(dest_page = 1) {
    var tags = $(".tag-clicked");
    var tags_list = [];
    tags.each(function (index, tag) {
        tags_list.push(tag.innerHTML);
    });

    filter_types = [];
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

var lib_loading = $("#library-item-loading");
var lib_empty = $("#library-item-empty");
var active_page = 1;

function updateResults(dest_page = 1) {
    active_page = dest_page;
    data = getFilters(dest_page);
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
                }
            }
        });

        $(".library-item-active").remove();
        lib_empty.hide();
        lib_loading.show();
        lib_group.animate({ opacity: 1 }, 200);
    });
}

var download_form = $("#download-form");
var download_id = download_form.find("input[name='id']");
var download_type = download_form.find("input[name='type']");
var download_dir = download_form.find("input[name='dir']");
var download_tags = download_form.find("input[name='tags']");
var download_keywords = download_form.find("input[name='keywords']");

function addAllResults() {
    data = getFilters();
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
    data = getFilters();
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
    cond = getFilters();
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

var page_ul = $("#library-page-ul");
var page_li = $(".library-page-li");
var page_no = $(".library-page-no");

function processResults(data) {
    lib_group.animate({ opacity: 0 }, 200, function () {
        lib_loading.hide();
        total_pages = data.total_pages;
        active_page = data.active_page;
        items = data.items;
        items.forEach(
            function (item) {
                addResultItem(item);
                bindLibraryResultEvent();
            }
        );

        page_ul.empty();
        page_li.removeClass('active').empty();

        i = 1;
        var page_li_copy;
        var page_no_copy;

        if (total_pages > 25) {
            i = (active_page - 12 >= 1) ? active_page - 12 : 1;
            _i = total_pages - 23;
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

        limit = i + 24;
        for (; i <= total_pages && i <= limit; i++) {
            page_li_copy = page_li.clone();
            page_no_copy = page_no.clone();
            page_no_copy.html(i.toString());
            if (active_page === i) {
                page_li_copy.addClass("active");
            } else {
                page_no_copy.click(function (e) {
                    _page_no = $(e.currentTarget).html();
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

var add_tag_modal_title = $("#addTagModalTitle");
var add_tag_modal_item_id = $("#addTagModalItemId");
var add_tag_modal_tags = $("#addTagModalTags");
var add_tag_modal_input = $("#addTagModalInput");
var modal_tag = $(".modal-tag");
var modal_tag_text = $(".modal-tag-text");

function addTagModalShow(_id, _title, _tag_tuples) {
    add_tag_modal_title.html("Edit tags for " + _title);
    add_tag_modal_item_id.val(_id);
    add_tag_modal_tags.empty();
    _tag_tuples.forEach(function (tag_tuple) {
        modal_tag_text.html(tag_tuple[0]);
        var tag_copy = modal_tag.clone();
        var modal_tag_remove = tag_copy.find(".modal-tag-remove");
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
    new_tags = add_tag_modal_input.val().split(",").map(function (str) { return str.trim() });
    new_tags.forEach(function (tag) {
        modal_tag_text.html(tag);
        var tag_copy = modal_tag.clone();
        var modal_tag_remove = tag_copy.find(".modal-tag-remove");
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
    var all_tags = $(".modal-tag-text");
    tags = [];
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

var volume_update_timer;
function setVolumeDelayed(new_volume_value) {
    window.clearTimeout(volume_update_timer);
    volume_update_timer = window.setTimeout(function () {
        request('post', { action: 'volume_set_value', new_volume: new_volume_value });
    }, 500); // delay in milliseconds
}

themeInit();
updateResults();
$(document).ready(updatePlaylist);