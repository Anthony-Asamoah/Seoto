/* Drives ImagePreviewInput: Preview opens the full image in a modal, Upload proxies to the
   hidden file input, Remove toggles the clear checkbox. The modal shell is built on first
   use, so the widget needs no template hook. */
(function () {
    'use strict';

    let modal = null;

    function shell() {
        if (modal) return modal;
        const el = document.createElement('div');
        el.className = 'modal fade';
        el.id = 'imagePreviewModal';
        el.tabIndex = -1;
        el.innerHTML =
            '<div class="modal-dialog modal-lg modal-dialog-centered">' +
            '<div class="modal-content">' +
            '<div class="modal-header"><h5 class="modal-title">Image preview</h5>' +
            '<button type="button" class="btn-close" data-bs-dismiss="modal" aria-label="Close"></button></div>' +
            '<div class="modal-body text-center"><img alt="" class="img-fluid"></div>' +
            '</div></div>';
        document.body.appendChild(el);
        modal = el;
        return el;
    }

    function openPreview(url) {
        const el = shell();
        const img = el.querySelector('.modal-body img');
        img.src = url;

        if (window.bootstrap && window.bootstrap.Modal) {
            window.bootstrap.Modal.getOrCreateInstance(el).show();
        } else {
            window.open(url, '_blank', 'noopener');
        }
    }

    function status(widget, text) {
        const slot = widget.querySelector('.image-preview-status');
        if (slot) slot.textContent = text;
    }

    document.addEventListener('click', function (event) {
        const button = event.target.closest(
            '.image-preview-trigger, .image-preview-upload, .image-preview-remove'
        );
        if (!button) return;
        event.preventDefault();

        const widget = button.closest('.image-preview-widget');

        if (button.classList.contains('image-preview-trigger')) {
            openPreview(button.dataset.imageUrl);
            return;
        }

        if (button.classList.contains('image-preview-upload')) {
            widget.querySelector('.image-preview-file').click();
            return;
        }

        const checkbox = document.getElementById(button.dataset.target);
        checkbox.checked = !checkbox.checked;
        button.classList.toggle('active', checkbox.checked);
        widget.classList.toggle('is-cleared', checkbox.checked);
        status(widget, checkbox.checked ? 'Removed on save' : '');
    });

    document.addEventListener('change', function (event) {
        const input = event.target;
        if (!input.classList.contains('image-preview-file')) return;

        const widget = input.closest('.image-preview-widget');
        const file = input.files && input.files[0];
        status(widget, file ? 'New image selected' : '');

        const thumb = widget.querySelector('.image-preview-thumb');
        if (file && thumb) thumb.src = URL.createObjectURL(file);
    });
})();
