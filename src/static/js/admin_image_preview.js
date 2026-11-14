/* Drives ImagePreviewInput: Preview opens the full image in a modal, Upload proxies to the
   hidden file input, Remove toggles the clear checkbox. Widgets marked data-crop="square"
   route a freshly picked file through a square cropper before it reaches the input. The
   modal shells are built on first use, so the widget needs no template hook. */
(function () {
    'use strict';

    const OUTPUT_MAX = 1024;
    let previewModal = null;
    let cropModal = null;
    const baselines = new WeakMap();

    function build(id, html) {
        const el = document.createElement('dialog');
        el.className = 'admin-dialog';
        el.id = id;
        el.innerHTML = html;
        document.body.appendChild(el);
        return el;
    }

    function previewShell() {
        if (previewModal) return previewModal;
        previewModal = build('imagePreviewModal',
            '<div class="admin-dialog-header"><h5>Image preview</h5>' +
            '<button type="button" class="admin-dialog-close" data-dialog-close aria-label="Close">' +
            '<span class="material-symbols-outlined">close</span></button></div>' +
            '<div class="admin-dialog-body admin-dialog-image"><img alt=""></div>');
        return previewModal;
    }

    function cropShell() {
        if (cropModal) return cropModal;
        cropModal = build('imageCropModal',
            '<div class="admin-dialog-header"><h5>Crop image</h5>' +
            '<button type="button" class="admin-dialog-close" data-dialog-close aria-label="Close">' +
            '<span class="material-symbols-outlined">close</span></button></div>' +
            '<div class="admin-dialog-body">' +
            '<div class="image-crop-stage"><img alt="" draggable="false"></div>' +
            '<input type="range" class="image-crop-zoom" min="1" max="4" step="0.01" value="1">' +
            '<p class="image-crop-hint">Drag to reposition, slide to zoom.</p>' +
            '</div>' +
            '<div class="admin-dialog-actions">' +
            '<button type="button" class="seoto-btn image-crop-cancel">Cancel</button>' +
            '<button type="button" class="seoto-btn seoto-btn--primary image-crop-apply">Apply crop</button>' +
            '</div>');
        return cropModal;
    }

    function openPreview(url) {
        if (!url) return;
        const el = previewShell();
        el.querySelector('.admin-dialog-body img').src = url;
        el.showModal();
    }

    function status(widget, text) {
        const slot = widget.querySelector('.image-preview-status');
        if (slot) slot.textContent = text;
    }

    function showThumb(widget, url) {
        widget.querySelectorAll('.image-preview-trigger').forEach(function (el) {
            el.hidden = false;
            el.dataset.imageUrl = url;
        });
        const thumb = widget.querySelector('.image-preview-thumb');
        if (thumb) thumb.src = url;
    }

    /* The state the widget was rendered in, so a cancelled crop can fall back to it
       rather than keep showing a thumbnail whose file the cancel just discarded. */
    function baseline(widget) {
        if (!baselines.has(widget)) {
            const thumb = widget.querySelector('.image-preview-thumb');
            baselines.set(widget, {
                url: thumb.dataset.imageUrl || '',
                src: thumb.getAttribute('src') || '',
                hidden: thumb.hidden,
            });
        }
        return baselines.get(widget);
    }

    function restore(widget) {
        const base = baseline(widget);
        widget.querySelectorAll('.image-preview-trigger').forEach(function (el) {
            el.hidden = base.hidden;
            el.dataset.imageUrl = base.url;
        });
        const thumb = widget.querySelector('.image-preview-thumb');
        if (thumb) thumb.setAttribute('src', base.src);
    }

    function setFile(input, file) {
        const bucket = new DataTransfer();
        bucket.items.add(file);
        input.files = bucket.files;
    }

    /* A square viewport over an image positioned by translate+scale: the crop is whatever
       the viewport covers, so the source rect is just the inverse transform of its corner. */
    function cropper(file, onDone, onCancel) {
        const el = cropShell();
        const stage = el.querySelector('.image-crop-stage');
        const img = el.querySelector('.image-crop-stage img');
        const zoom = el.querySelector('.image-crop-zoom');
        const url = URL.createObjectURL(file);
        const state = {scale: 1, base: 1, x: 0, y: 0, size: 0};
        let drag = null;
        let applied = false;

        function clamp() {
            const w = img.naturalWidth * state.scale;
            const h = img.naturalHeight * state.scale;
            state.x = Math.min(0, Math.max(state.size - w, state.x));
            state.y = Math.min(0, Math.max(state.size - h, state.y));
        }

        function paint() {
            clamp();
            img.style.transform =
                'translate(' + state.x + 'px,' + state.y + 'px) scale(' + state.scale + ')';
        }

        function onPointerDown(event) {
            drag = {x: event.clientX - state.x, y: event.clientY - state.y};
            stage.setPointerCapture(event.pointerId);
        }

        function onPointerMove(event) {
            if (!drag) return;
            state.x = event.clientX - drag.x;
            state.y = event.clientY - drag.y;
            paint();
        }

        function onPointerUp() {
            drag = null;
        }

        function onZoom() {
            const previous = state.scale;
            state.scale = state.base * parseFloat(zoom.value);
            // Keep the viewport centre fixed while the image grows around it.
            const ratio = state.scale / previous;
            state.x = state.size / 2 - (state.size / 2 - state.x) * ratio;
            state.y = state.size / 2 - (state.size / 2 - state.y) * ratio;
            paint();
        }

        function teardown() {
            stage.removeEventListener('pointerdown', onPointerDown);
            stage.removeEventListener('pointermove', onPointerMove);
            stage.removeEventListener('pointerup', onPointerUp);
            zoom.removeEventListener('input', onZoom);
            el.querySelector('.image-crop-apply').removeEventListener('click', apply);
            el.removeEventListener('close', teardown);
            URL.revokeObjectURL(url);
            if (!applied) onCancel();
        }

        function apply() {
            applied = true;
            const side = Math.min(OUTPUT_MAX, Math.round(state.size / state.scale));
            const canvas = document.createElement('canvas');
            canvas.width = canvas.height = side;
            canvas.getContext('2d').drawImage(
                img,
                -state.x / state.scale, -state.y / state.scale,
                state.size / state.scale, state.size / state.scale,
                0, 0, side, side
            );

            const type = file.type === 'image/png' ? 'image/png' : 'image/jpeg';
            canvas.toBlob(function (blob) {
                onDone(new File([blob], file.name, {type: type, lastModified: Date.now()}));
                el.close();
            }, type, 0.92);
        }

        img.onload = function () {
            state.size = stage.clientWidth;
            state.base = state.size / Math.min(img.naturalWidth, img.naturalHeight);
            state.scale = state.base;
            state.x = (state.size - img.naturalWidth * state.scale) / 2;
            state.y = (state.size - img.naturalHeight * state.scale) / 2;
            zoom.value = '1';
            paint();
        };
        img.src = url;

        stage.addEventListener('pointerdown', onPointerDown);
        stage.addEventListener('pointermove', onPointerMove);
        stage.addEventListener('pointerup', onPointerUp);
        zoom.addEventListener('input', onZoom);
        el.querySelector('.image-crop-apply').addEventListener('click', apply);
        el.addEventListener('close', teardown);
        el.showModal();
        // The stage has no width until it is on screen, so size a cached image once it is.
        if (img.complete && img.naturalWidth) img.onload();
    }

    document.addEventListener('click', function (event) {
        const button = event.target.closest(
            '.image-preview-trigger, .image-preview-upload, .image-preview-remove, .image-crop-cancel'
        );
        const dialog = event.target.closest('dialog.admin-dialog');
        if (dialog && (event.target.closest('[data-dialog-close]') || event.target === dialog)) {
            dialog.close();
            return;
        }
        if (!button) return;
        event.preventDefault();

        if (button.classList.contains('image-crop-cancel')) {
            cropShell().close();
            return;
        }

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
        baseline(widget);
        const file = input.files && input.files[0];
        if (!file) {
            status(widget, '');
            return;
        }

        function accept(chosen) {
            status(widget, 'New image selected');
            showThumb(widget, URL.createObjectURL(chosen));
        }

        if (widget.dataset.crop === 'square' && file.type.startsWith('image/')) {
            cropper(file, function (cropped) {
                setFile(input, cropped);
                accept(cropped);
            }, function () {
                input.value = '';
                status(widget, '');
                restore(widget);
            });
            return;
        }
        accept(file);
    });
})();
