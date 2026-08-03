/* jazzmin's main.js opens only the nearest `li.has-treeview` above the active link, which
   is enough for its own flat menu but leaves our section level shut (see
   templates/admin/base_site.html). Walk the rest of the way up.

   The active link is resolved here rather than read off jazzmin's `.active` class: that
   class is added from a jQuery ready handler, and this file can execute before it runs. */
(function () {
    function activeLink() {
        var menu = document.getElementById('jazzy-navigation');
        if (!menu) {
            return null;
        }

        var current = menu.querySelector('a.nav-link.active');
        if (current) {
            return current;
        }

        var byPath = menu.querySelector('a[href="' + window.location.pathname + '"]');
        if (byPath) {
            return byPath;
        }

        // Fall back to the parent listing, so a change form still opens its branch.
        // Must be the last crumb of the whole trail, not the last `a` of each crumb.
        var crumbs = document.querySelectorAll('.breadcrumb a');
        if (!crumbs.length) {
            return null;
        }

        var href = crumbs[crumbs.length - 1].getAttribute('href');
        return href ? menu.querySelector('a[href="' + href + '"]') : null;
    }

    function openBranch() {
        var link = activeLink();
        if (!link) {
            return;
        }

        link.classList.add('active');

        var item = link.closest('li.nav-item.has-treeview');
        while (item) {
            item.classList.add('menu-is-opening', 'menu-open');
            var submenu = item.querySelector(':scope > ul');
            if (submenu) {
                submenu.style.display = 'block';
            }
            item = item.parentElement && item.parentElement.closest('li.nav-item.has-treeview');
        }
    }

    document.addEventListener('DOMContentLoaded', openBranch);
    window.addEventListener('load', openBranch);
})();
