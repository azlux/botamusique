// eslint-disable-next-line no-unused-vars
import {$, jQuery} from 'jquery/src/jquery';
import 'jquery-migrate/src/migrate';
import 'popper.js';
import 'bootstrap/js/src/index';

// Old application code
import './main.mjs';

// New application code
import Theme from './theme.mjs';

import {library, dom} from '@fortawesome/fontawesome-svg-core/index.es';
import {fas} from '@fortawesome/free-solid-svg-icons/index.es';
import {far} from '@fortawesome/free-regular-svg-icons/index.es';
import {fab} from '@fortawesome/free-brands-svg-icons/index.es';
library.add(fas, far, fab);

document.addEventListener('DOMContentLoaded', () => {
  Theme.init();

  // This is required to seach DOM and convert i tags to SVG
  dom.i2svg();

  document.getElementById('theme-switch-btn').addEventListener('click', () => {
    Theme.swap();
  });
});

