from django.test import TestCase
from django.urls import reverse

from domains.apps.anagrams.the_code import AnagramSolver
from infrastructure.core.exceptions import InvalidInput


class AnagramSolverTests(TestCase):
    def test_finds_full_anagrams(self):
        solver = AnagramSolver('Listen')
        self.assertIn('silent', solver.get_exact())
        self.assertIn('enlist', solver.get_exact())
        self.assertNotIn('listen', [w for g in solver.get_groups() for w in g['words']])

    def test_groups_partials_longest_first(self):
        solver = AnagramSolver('listen')
        lengths = [group['length'] for group in solver.get_groups()]
        self.assertEqual(lengths, sorted(lengths, reverse=True))
        self.assertTrue(all(len(w) == g['length'] for g in solver.get_groups() for w in g['words']))

    def test_partials_only_use_available_letters(self):
        solver = AnagramSolver('listen')
        self.assertIn('tins', [w for g in solver.get_groups() for w in g['words']])
        self.assertNotIn('tests', [w for g in solver.get_groups() for w in g['words']])

    def test_whitespace_is_ignored(self):
        self.assertEqual(AnagramSolver(' li st en ').letters, 'listen')

    def test_rejects_non_letters(self):
        with self.assertRaises(InvalidInput):
            AnagramSolver('list3n')

    def test_rejects_blank(self):
        with self.assertRaises(InvalidInput):
            AnagramSolver('   ')

    def test_rejects_too_short_and_too_long(self):
        with self.assertRaises(InvalidInput):
            AnagramSolver('ab')
        with self.assertRaises(InvalidInput):
            AnagramSolver('a' * 16)

    def test_is_empty_for_unusable_letters(self):
        self.assertTrue(AnagramSolver('xzq').is_empty())


class AnagramViewTests(TestCase):
    def test_get_renders_page(self):
        response = self.client.get(reverse('anagrams'))
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, 'anagrams/anagrams.html')

    def test_post_renders_results(self):
        response = self.client.post(reverse('anagrams'), {'letters': 'listen'})
        self.assertEqual(response.status_code, 200)
        self.assertIn('silent', response.context['exact'])

    def test_ajax_post_returns_json(self):
        response = self.client.post(
            reverse('anagrams'), {'letters': 'listen'},
            headers={'x-requested-with': 'XMLHttpRequest'},
        )
        self.assertEqual(response.status_code, 200)
        payload = response.json()
        self.assertEqual(payload['input'], 'listen')
        self.assertIn('silent', payload['exact'])
        self.assertTrue(payload['amount'])

    def test_ajax_post_returns_400_on_bad_input(self):
        response = self.client.post(
            reverse('anagrams'), {'letters': '123'},
            headers={'x-requested-with': 'XMLHttpRequest'},
        )
        self.assertEqual(response.status_code, 400)
        self.assertIn('error', response.json())
