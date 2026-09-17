import copy
import importlib.util
import json
import os
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

spec = importlib.util.spec_from_file_location('generator', Path(__file__).resolve().parents[1] / 'scripts/generate_daily_post.py')
g = importlib.util.module_from_spec(spec)
spec.loader.exec_module(g)


class PublicationTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.root = Path(self.tmp.name)
        self.story = self.root / 'story'
        self.story.mkdir()
        (self.story / 'posts.json').write_text('[]')
        (self.root / 'products.json').write_text(json.dumps({'storeUrl': 'https://shop.coupang.com/test', 'products': []}))
        self.patches = [patch.object(g, 'ROOT', self.root), patch.object(g, 'STORY', self.story), patch.object(g, 'pending_posts', return_value=[])]
        for p in self.patches: p.start()
        self.post = {'title': '가을철 옷장 습기는 어떻게 관리하나요?', 'slug': 'autumn-closet-moisture',
                     'description': '가을 옷장을 정리하기 전에 습기와 환기 상태를 먼저 살펴보세요. ' * 3,
                     'summary': '옷장 관리 기준', 'tags': ['가을', '정리', '습기'],
                     'intro': '이 문단은 옷장을 관리하는 구체적인 방법을 충분한 길이로 설명합니다.',
                     'sections': [{'heading': f'관리 순서 {i}', 'paragraphs': ['옷장 내부를 확인하고 옷 사이의 간격을 확보하는 관리 순서를 자세히 설명합니다.'] * 2, 'bullets': []} for i in range(3)],
                     'faq': [{'q': f'질문 {i}', 'a': '답변입니다.'} for i in range(3)],
                     'sources': [{'title': '공식 안내', 'url': 'https://example.org/guide'}],
                     'cta_text': '제품 보기', 'cta_url': 'https://shop.coupang.com/test'}

    def tearDown(self):
        for p in reversed(self.patches): p.stop()
        self.tmp.cleanup()

    def test_known_source_link_is_unwrapped_without_losing_source(self):
        self.post['intro'] += ' [공식 안내](https://example.org/guide)'
        cleaned = g.normalize_citations(self.post)
        self.assertNotIn('](', cleaned['intro'])
        self.assertEqual(cleaned['sources'], self.post['sources'])
        g.validate(cleaned)

    def test_unknown_link_still_rejected(self):
        self.post['intro'] += ' [다른 안내](https://example.org/unknown)'
        with self.assertRaises(SystemExit): g.validate(g.normalize_citations(self.post))

    def test_invalid_json_and_validation_error_recover(self):
        bad = copy.deepcopy(self.post)
        bad['intro'] += ' https://example.org/unknown'
        with patch.object(g, 'generate', side_effect=[ValueError('invalid json'), bad, self.post]) as generate:
            result = g.generate_valid_post('옷장')
            self.assertEqual(result['slug'], self.post['slug'])
            self.assertEqual(generate.call_count, 3)
            self.assertIn('URL', generate.call_args.args[1])

    def test_retries_are_bounded(self):
        with patch.object(g, 'generate', side_effect=ValueError('bad')) as generate:
            with self.assertRaises(ValueError): g.generate_valid_post('옷장')
            self.assertEqual(generate.call_count, 4)

    def test_pending_topic_is_skipped(self):
        (self.story / 'ideas.md').write_text('- [ ] 의자 방석의 크기는 어떻게 재나요?\n- [ ] 옷장 습기는 어떻게 관리하나요?\n')
        with patch.object(g, 'pending_posts', return_value=[{'title': '다른 제목', 'reserved_topics': ['의자 방석의 크기는 어떻게 재나요?']} ]):
            self.assertEqual(g.next_topic(), '옷장 습기는 어떻게 관리하나요?')

    def test_pending_slug_and_title_are_rejected(self):
        with patch.object(g, 'pending_posts', return_value=[{'title': self.post['title'] + ' | 위드리빙', 'url': self.post['slug'] + '.html'}]):
            with self.assertRaises(SystemExit): g.validate(self.post)

    def test_existing_day_never_calls_model(self):
        (self.story / 'posts.json').write_text('[{"date": "2026-09-17"}]')
        with patch('sys.argv', ['generate', '--date', '2026-09-17']), patch.object(g, 'generate') as generate:
            g.main()
            generate.assert_not_called()

    def test_similarity_ignores_brand_and_punctuation(self):
        self.assertTrue(g.similar_title('방석 크기는 어떻게 재나요? | 위드리빙', '방석 크기는 어떻게 재나요'))
        self.assertFalse(g.similar_title('방석 크기는 어떻게 재나요?', '가을 옷장 습기는 어떻게 관리하나요?'))


if __name__ == '__main__':
    unittest.main()
