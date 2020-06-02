// eslint-disable-next-line no-unused-vars
import {$, jQuery} from 'jquery/src/jquery';
import 'jquery-migrate/src/migrate';
import 'popper.js';
import 'bootstrap/js/src/index';
import {library, dom} from '@fortawesome/fontawesome-svg-core/index.es';
import {fas} from '@fortawesome/free-solid-svg-icons/index.es';
import {far} from '@fortawesome/free-regular-svg-icons/index.es';
library.add(fas, far);

// Old application code
import './main.mjs';

// New application code
import Theme from './theme.mjs';

document.addEventListener('DOMContentLoaded', () => {
  Theme.init();

  // Replace any existing <i> tags with <svg> and set up a MutationObserver to
  // continue doing this as the DOM changes.
  dom.watch();

  document.getElementById('theme-switch-btn').addEventListener('click', () => {
    Theme.swap();
  });
});

