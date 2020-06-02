import Theme from './theme';

import { library, dom } from '@fortawesome/fontawesome-svg-core/index.es';
import { fas } from '@fortawesome/free-solid-svg-icons/index.es';
import { far } from '@fortawesome/free-regular-svg-icons/index.es';
import { fab } from '@fortawesome/free-brands-svg-icons/index.es';
library.add(fas, far, fab);

document.addEventListener('DOMContentLoaded', () => {
    Theme.init();

    // FontAwesome
    dom.i2svg();

    document.getElementById('theme-switch-btn').addEventListener('click', () => {
        Theme.swap();
    });
});