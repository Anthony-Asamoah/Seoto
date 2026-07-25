from django.test import TestCase
from django.urls import reverse


class GenerateInvoiceViewTests(TestCase):
    def setUp(self):
        self.url = reverse('generate_invoice')

    def test_page_renders(self):
        response = self.client.get(self.url)
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, 'generate_invoice/index.html')


class LogoUploadMarkupTests(TestCase):
    """The invoice builder is a single self-contained template, so the logo feature is
    asserted through the markup and client-side config it ships."""

    def setUp(self):
        self.html = self.client.get(reverse('generate_invoice')).content.decode()

    def test_upload_controls_are_present(self):
        for marker in (
            'id="logo-drop"',
            'id="logo-input"',
            'id="logo-preview-wrap"',
            'id="logo-actions"',
        ):
            with self.subTest(marker=marker):
                self.assertIn(marker, self.html)

    def test_dropzone_is_keyboard_reachable(self):
        self.assertIn('role="button"', self.html)
        self.assertIn('tabindex="0"', self.html)

    def test_upload_is_constrained_to_images_under_2mb(self):
        self.assertIn('accept="image/png,image/jpeg,image/svg+xml,image/webp,image/gif"', self.html)
        self.assertIn('LOGO_MAX_BYTES = 2097152', self.html)

    def test_placement_options_are_offered(self):
        self.assertIn('id="place-grid"', self.html)
        for placement in ("'header-left'", "'header-right'", "'letterhead'"):
            with self.subTest(placement=placement):
                self.assertIn(placement, self.html)

    def test_size_options_are_offered(self):
        self.assertIn('id="logo-size-seg"', self.html)
        for size in ("sm: {label: 'Small'", "md: {label: 'Medium'", "lg: {label: 'Large'"):
            with self.subTest(size=size):
                self.assertIn(size, self.html)

    def test_contrast_plate_control_is_present(self):
        self.assertIn('id="logo-plate-toggle"', self.html)
        self.assertIn('function contrastRatio(', self.html)
        self.assertIn('function analyzeLogo(', self.html)

    def test_generated_invoice_styles_cover_every_placement(self):
        for rule in ('.logo-wrap{', '.hr .logo-wrap{', '.logo-plate{', '.lh{'):
            with self.subTest(rule=rule):
                self.assertIn(rule, self.html)
