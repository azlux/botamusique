/**
 * Library state and backend interface library
 */
export default class {
  /**
   * @member {object} #axios Axios HTTP request library instance.
   */
  #axios;

  constructor(axios) {
    this.#axios = axios;
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
  async getItems(page = 1, type = [], dir = '', tags = [], keywords = '') {
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
  async addMusicByURL(url) {
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
  async addRadioByURL(url) {
    return this.#axios.post('post', {
      add_radio: url,
    });
  }
}
