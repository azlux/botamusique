/**
 * Player state and backend interface library
 */
export default class {
  /**
   * @member {object} #axios Axios HTTP request library instance.
   */
  #axios;

  /**
   * @member {number} version Playlist state version
   */
  version = 0;

  constructor(axios) {
    this.#axios = axios;
  }

  /**
   * Check if client playlist is up-to-date with current server version.
   *
   * @returns {boolean} True if playlist is not up-to-date and false if up-to-date.
   */
  async checkForUpdate() {
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
  async getItems(range_from = 0, range_to = 0) {
    let data = {};

    if (!(range_from === 0 && range_to === 0)) {
      data = {
        range_from: range_from,
        range_to: range_to,
      };
    }

    return this.#axios.get('playlist', data);
  }
}
