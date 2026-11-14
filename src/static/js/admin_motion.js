document.addEventListener('click', function (event) {
    if (event.target.closest('[x-on\\:click="sidebarToggle()"]')) {
        document.documentElement.classList.add('seoto-motion');
    }
}, true);
