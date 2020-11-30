/**
 * Player state and backend interface library
 */
export default class {
  /**
   * @member {object} #axios Axios HTTP request library instance.
   */
  #axios;

  /**
   * @member {number} playlist_version Playlist state version
   */
  playlist_version = 0;

  constructor(axios) {
    this.#axios = axios;
  }

  /**
   * Check if client playlist is up-to-date with current server version.
   *
   * @returns {boolean} True if playlist is not up-to-date and false if up-to-date.
   */
  async checkForPlaylistUpdate() {
    this.#axios.post('post').then(response => {
      // Do we need to update our playlist?
      if (response.data.ver != this.playlist_version) {
        this.playlist_version = response.data.ver;

        return true;
      }

      return false;
    });
  }

  /**
   * Get playlist items from server.
   *
   * @param {number} range_from Index of beginning item.
   * @param {number} range_to Index of ending item.
   * @returns {object} Axios response object.
   */
  async getPlaylistItems(range_from = 0, range_to = 0) {
    let data = {};

    if (!(range_from === 0 && range_to === 0)) {
      data = {
        range_from: range_from,
        range_to: range_to,
      };
    }

    return this.#axios.get('playlist', data);
  }

  /**
   * Get library items from server.
   *
   * @param {number} page
   * @param {Array} type
   * @param {string} dir
   * @param {Array} tags
   * @param {string} keywords
   * @returns {object} Axios response object.
   */
  async getLibraryItems(page = 1, type = [], dir = '', tags = [], keywords = '') {
    return this.#axios.post('library', {
      action: 'query',
      dir: dir,
      keywords: keywords,
      page: page,
      tags: tags.join(','),
      type: type.join(','),
    });
  }

  /**
   * Add music URL to library.
   *
   * @param {string} url HTTP(s) URL with any support service for youtube-dl (Python library).
   * @returns {Promise} Axios promise.
   */
  async addMusicURL(url) {
    return this.#axios.post('post', {
      add_url: url,
    });
  }

  /**
   * Add radio URL to library.
   *
   * @param {string} url HTTP(s) URL.
   * @returns {Promise} Axios promise.
   */
  async addRadioURL(url) {
    return this.#axios.post('post', {
      add_radio: url,
    });
  }
}
