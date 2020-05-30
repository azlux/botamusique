import Theme from './theme';

document.addEventListener('DOMContentLoaded', () => {
    Theme.init();

    document.getElementById('theme-switch-btn').addEventListener('click', () => {
        Theme.swap();
    });
});