from django.contrib.auth.models import User
from django.test import TestCase
from django.urls import reverse

from domains.apps.rhymes.models import Rhyme
from domains.apps.rhymes.the_code import MAX_RHYMES_PER_SUFFIX, RhymeDB


class SuffixLengthTests(TestCase):
    def test_suffix_scales_with_word_length(self):
        # < 4 letters → 2, 4-5 → 3, >= 6 → 4
        self.assertEqual(RhymeDB._ideal_suffix_length('go'), 2)
        self.assertEqual(RhymeDB._ideal_suffix_length('cat'), 2)
        self.assertEqual(RhymeDB._ideal_suffix_length('time'), 3)
        self.assertEqual(RhymeDB._ideal_suffix_length('dream'), 3)
        self.assertEqual(RhymeDB._ideal_suffix_length('action'), 4)
        self.assertEqual(RhymeDB._ideal_suffix_length('celebration'), 4)

    def test_long_word_rhymes_on_four_letter_ending(self):
        # "action" should rhyme on "tion", not the broader "ion".
        result = RhymeDB('action').get_result()
        self.assertEqual(list(result.keys()), ['tion'])

    def test_short_word_rhymes_on_two_letter_ending(self):
        result = RhymeDB('cat').get_result()
        self.assertEqual(list(result.keys()), ['at'])

    def test_suffix_shortens_when_longer_ending_has_no_match(self):
        # "qzzz" has no real ending in the dictionary; the loop must fall back
        # without raising and simply yield no result rather than erroring.
        helper = RhymeDB('qzzz')
        self.assertIsInstance(helper.get_result(), dict)


class RhymeSelectionTests(TestCase):
    def test_result_is_capped(self):
        # "tion" matches thousands of entries; the page shows a usable slice.
        words = RhymeDB('action').get_result()['tion']
        self.assertEqual(len(words), MAX_RHYMES_PER_SUFFIX)

    def test_shortest_words_win_the_cap(self):
        # Short words are the familiar ones, so they must survive the cut.
        words = RhymeDB('time').get_result()['ime']
        for expected in ('Time', 'Chime', 'Crime', 'Lime'):
            self.assertIn(expected, words)

    def test_words_are_clean_titles(self):
        for word in RhymeDB('cat').get_result()['at']:
            self.assertEqual(word, word.strip())
            self.assertTrue(word.isalpha())
            self.assertTrue(word[0].isupper())

    def test_each_comma_separated_word_gets_its_own_group(self):
        result = RhymeDB('time, cat').get_result()
        self.assertEqual(sorted(result.keys()), ['at', 'ime'])


class GenerateFileContentTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(
            username='rhymer', email='rhymer@example.com', password='pw'
        )
        self.rhyme = Rhyme.create(
            rhyme='time',
            user=self.user,
            text='chime\ndime\nlime',
            word_count=3,
        )

    def test_content_is_friendly_not_technical(self):
        content = self.rhyme.generate_file_content()

        # Friendly framing
        self.assertIn('Rhymes for "time"', content)
        self.assertIn('Found 3 word(s) that rhyme.', content)
        self.assertIn('chime\ndime\nlime', content)

        # The old technical boilerplate should be gone
        self.assertNotIn('=' * 80, content)
        self.assertNotIn('RHYME DATABASE', content)
        self.assertNotIn('SEARCH QUERY', content)
        self.assertNotIn('Powered by Python & Wine', content)

        # No raw user identifiers leaking into the file
        self.assertNotIn(self.user.email, content)
        self.assertNotIn(self.user.username, content)


class SearchAjaxTests(TestCase):
    AJAX = {'HTTP_X_REQUESTED_WITH': 'XMLHttpRequest'}

    def test_ajax_search_returns_json_words(self):
        response = self.client.post(reverse('rhymes'), {'rhyme': 'time'}, **self.AJAX)

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response['Content-Type'], 'application/json')
        data = response.json()
        self.assertEqual(data['input'], 'time')
        self.assertIsInstance(data['words'], list)
        self.assertEqual(data['amount'], len(data['words']))

    def test_ajax_invalid_input_returns_error_json(self):
        response = self.client.post(reverse('rhymes'), {'rhyme': '123'}, **self.AJAX)

        self.assertEqual(response.status_code, 400)
        self.assertIn('error', response.json())

    def test_ajax_can_download_only_when_authenticated_with_results(self):
        anon = self.client.post(reverse('rhymes'), {'rhyme': 'time'}, **self.AJAX)
        self.assertFalse(anon.json()['can_download'])

        user = User.objects.create_user(username='u', email='u@example.com', password='pw')
        self.client.force_login(user)
        authed = self.client.post(reverse('rhymes'), {'rhyme': 'time'}, **self.AJAX)
        self.assertTrue(authed.json()['can_download'])

    def test_non_ajax_post_still_renders_html(self):
        response = self.client.post(reverse('rhymes'), {'rhyme': 'time'})

        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, 'rhymes/rhymes.html')
