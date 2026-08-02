import re

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
        """Assert against the dropzone's own tag — a match elsewhere in the page
        would otherwise hide a regression here."""
        tag = re.search(r'<div[^>]*id="logo-drop"[^>]*>', self.html)
        self.assertIsNotNone(tag, 'logo dropzone element not found')
        self.assertIn('role="button"', tag.group(0))
        self.assertIn('tabindex="0"', tag.group(0))
        self.assertIn('aria-label=', tag.group(0))

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


class InvoiceCopyTests(TestCase):
    """Blank fields must be omitted rather than replaced with copy the user never typed."""

    def setUp(self):
        self.html = self.client.get(reverse('generate_invoice')).content.decode()

    def test_document_title_is_editable(self):
        self.assertIn('id="wordmark"', self.html)
        self.assertIn('${v.wordmark}', self.html)
        self.assertNotIn('<h1>INVOICE</h1>', self.html)

    def test_no_invented_copy_is_substituted_for_blank_fields(self):
        for invented in (
            "'Professional Services'",
            "'Your Business'",
            "'Client'",
            "|| 'Thank you for your patronage!'",
        ):
            with self.subTest(invented=invented):
                self.assertNotIn(invented, self.html)


class EmailNormalisationTests(TestCase):
    """A pasted mail link must print as the bare address, not 'mailto:someone@example.com'."""

    def setUp(self):
        self.html = self.client.get(reverse('generate_invoice')).content.decode()

    def test_cleaner_exists(self):
        self.assertIn('function cleanEmail(', self.html)
        self.assertIn("replace(/^mailto:/i, '')", self.html)

    def test_both_email_fields_normalise_on_change(self):
        self.assertEqual(self.html.count('onchange="normalizeEmailField(this)"'), 2)

    def test_generated_invoice_cleans_both_addresses(self):
        self.assertIn("fromEmail: cleanEmail(g('from-email'))", self.html)
        self.assertIn("toEmail: cleanEmail(g('to-email'))", self.html)


class InvoiceTemplateStoreTests(TestCase):
    def setUp(self):
        self.html = self.client.get(reverse('generate_invoice')).content.decode()

    def test_template_bar_is_present(self):
        for marker in (
            'id="tpl-select"',
            'id="tpl-apply"',
            'id="tpl-save-new"',
            'id="tpl-update"',
            'id="tpl-default"',
            'id="tpl-delete"',
            'id="tpl-status"',
        ):
            with self.subTest(marker=marker):
                self.assertIn(marker, self.html)

    def test_storage_keys_are_versioned(self):
        self.assertIn("TPL_KEY = 'seoto.invoice.templates.v1'", self.html)
        self.assertIn("TPL_DEFAULT_KEY = 'seoto.invoice.defaultTemplate.v1'", self.html)

    def test_template_carries_the_repeated_fields(self):
        for field in ('wordmark', 'from-name', 'from-email', 'from-phone', 'from-location',
                      'inv-desc', 'currency', 'tax-rate', 'bank-name', 'acc-name',
                      'acc-num', 'momo', 'notes'):
            with self.subTest(field=field):
                self.assertIn("'%s'" % field, self.html)

    def test_template_excludes_client_number_and_dates(self):
        """These change every invoice, so applying a template must not touch them."""
        block = self.html.split('const TPL_FIELDS = {')[1].split('};')[0]
        for excluded in ('to-name', 'to-email', 'to-location', 'inv-num', 'inv-date', 'due-date'):
            with self.subTest(excluded=excluded):
                self.assertNotIn(excluded, block)

    def test_quota_failure_is_handled(self):
        self.assertIn('function tplCommit(', self.html)
        self.assertIn('There isn’t enough browser storage left', self.html)
