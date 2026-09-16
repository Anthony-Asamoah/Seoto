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
        const el = document.createElement('div');
        el.className = 'modal fade';
        el.id = id;
        el.tabIndex = -1;
        el.innerHTML = html;
        document.body.appendChild(el);
        return el;
    }

    function previewShell() {
        if (previewModal) return previewModal;
        previewModal = build('imagePreviewModal',
            '<div class="modal-dialog modal-lg modal-dialog-centered">' +
            '<div class="modal-content">' +
            '<div class="modal-header"><h5 class="modal-title">Image preview</h5>' +
            '<button type="button" class="btn-close" data-bs-dismiss="modal" aria-label="Close"></button></div>' +
            '<div class="modal-body text-center"><img alt="" class="img-fluid"></div>' +
            '</div></div>');
        return previewModal;
    }

    function cropShell() {
        if (cropModal) return cropModal;
        cropModal = build('imageCropModal',
            '<div class="modal-dialog modal-dialog-centered">' +
            '<div class="modal-content">' +
            '<div class="modal-header"><h5 class="modal-title">Crop image</h5>' +
            '<button type="button" class="btn-close" data-bs-dismiss="modal" aria-label="Close"></button></div>' +
            '<div class="modal-body">' +
            '<div class="image-crop-stage"><img alt="" draggable="false"></div>' +
            '<input type="range" class="form-range image-crop-zoom" min="1" max="4" step="0.01" value="1">' +
            '<p class="image-crop-hint">Drag to reposition, slide to zoom.</p>' +
            '</div>' +
            '<div class="modal-footer">' +
            '<button type="button" class="btn btn-outline-secondary image-crop-cancel">Cancel</button>' +
            '<button type="button" class="btn btn-primary image-crop-apply">Apply crop</button>' +
            '</div></div></div>');
        return cropModal;
    }

    function openPreview(url) {
        if (!url) return;
        const el = previewShell();
        el.querySelector('.modal-body img').src = url;

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
            el.removeEventListener('hidden.bs.modal', teardown);
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
                hide();
            }, type, 0.92);
        }

        function hide() {
            if (window.bootstrap && window.bootstrap.Modal) {
                window.bootstrap.Modal.getOrCreateInstance(el).hide();
            } else {
                teardown();
            }
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
        el.addEventListener('hidden.bs.modal', teardown);

        if (window.bootstrap && window.bootstrap.Modal) {
            const instance = window.bootstrap.Modal.getOrCreateInstance(el);
            instance.show();
            // The stage has no width until it is laid out, so size once it is on screen.
            el.addEventListener('shown.bs.modal', function once() {
                el.removeEventListener('shown.bs.modal', once);
                if (img.complete) img.onload();
            });
        } else {
            applied = true;  // No bootstrap: take the file uncropped rather than lose it.
            onDone(file);
            teardown();
        }
    }

    document.addEventListener('click', function (event) {
        const button = event.target.closest(
            '.image-preview-trigger, .image-preview-upload, .image-preview-remove, .image-crop-cancel'
        );
        if (!button) return;
        event.preventDefault();

        if (button.classList.contains('image-crop-cancel')) {
            window.bootstrap.Modal.getOrCreateInstance(cropShell()).hide();
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
