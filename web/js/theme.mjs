export default class {
    /**
     * @property {boolean} dark Interal state for dark theme activation.
     * @private
     */
    static #dark = false;

    /**
     * Inialize the theme class.
     */
    static init() {
      // Check LocalStorage for dark theme selection
      if (localStorage.getItem('darkTheme') === 'true') {
        // Update page theme
        this.set(true);
      }
    }

    /**
     * Set page theme and update local storage variable.
     *
     * @param {boolean} dark Whether to activate dark theme.
     */
    static set(dark = false) {
      // Swap CSS to selected theme
      document.getElementById('pagestyle')
          .setAttribute('href', 'static/css/' + (dark ? 'dark' : 'main') + '.css');

      // Update local storage
      localStorage.setItem('darkTheme', dark);

      // Update internal state
      this.#dark = dark;
    }

    /**
     * Swap page theme.
     */
    static swap() {
      this.set(!this.#dark);
    }
}
