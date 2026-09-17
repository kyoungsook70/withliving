"""A successful merge is not publication: verify both index and static article."""
import argparse
import json
import time
import urllib.request
from pathlib import Path
from html import unescape

DOMAIN = 'https://www.withliving.kr'


def verify(post):
    headers = {'Cache-Control': 'no-cache'}
    stamp = str(int(time.time()))
    def fetch(path):
        req = urllib.request.Request(f'{DOMAIN}/{path}?publication_check={stamp}', headers=headers)
        with urllib.request.urlopen(req, timeout=20) as response:
            return response.read().decode()
    live = json.loads(fetch('story/posts.json'))
    if not any(p.get('url') == post['url'] and p['date'] == post['date'] and p['title'] == post['title'] for p in live):
        raise ValueError('운영 글 목록에 아직 반영되지 않았습니다.')
    page = unescape(fetch('story/' + post['url']))
    if post['title'] not in page or post['date'] not in page or '<article' not in page:
        raise ValueError('정적 글 페이지 제목·날짜·본문을 확인하지 못했습니다.')


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--date', required=True)
    args = parser.parse_args()
    posts = json.loads((Path(__file__).resolve().parents[1] / 'story/posts.json').read_text())
    post = next(p for p in posts if p['date'] == args.date)
    for attempt in range(20):
        try:
            verify(post)
            print(f"공개 확인 완료: {DOMAIN}/story/{post['url']}")
            return
        except (OSError, ValueError) as exc:
            print(f'공개 확인 {attempt + 1}/20: {exc}', flush=True)
            if attempt == 19:
                raise
            time.sleep(15)


if __name__ == '__main__':
    main()
