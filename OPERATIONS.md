# 위드리빙 사이트 자동 운영

## 매일 오전 8시(KST)

`Daily WITH LIVING blog` GitHub Actions가 다음 작업을 실행합니다.

1. 미사용 글감이 5개 미만이면 기존 FAQ·제품·계절을 바탕으로 중복 없는 글감 10개를 보충합니다.
2. `story/ideas.md`의 첫 미사용 글감으로 `runday-seo` 규격의 글을 작성합니다.
3. 정적 HTML, `story/posts.json`, `sitemap.xml`, `feed.xml`, `llms.txt`를 함께 갱신합니다.
4. 13개 SEO·AEO·GEO 검사를 실행합니다.
5. 새 브랜치와 PR을 만들고 제목, 사람이 확인할 내용, 남은 글감 수를 PR 본문에 기록합니다.
6. 사람이 PR의 사실관계를 확인하고 Merge하면 Vercel이 자동 배포합니다.

## 매주 월요일 오전 9시(KST)

`Weekly WITH LIVING SEO audit` GitHub Actions가 사이트 전체에 13개 점검을 실행합니다. 사실관계를 바꾸지 않는 안전한 오류만 자동 수정하고, 전체 점검표와 수동 확인 항목을 담은 PR을 만듭니다.

## 사람이 직접 하는 확인

- 매일 발행 PR의 생활용품 사용·관리·제품 관련 사실과 출처 확인
- Merge 후 ChatGPT 또는 Perplexity URL 요약 확인
- Google Rich Results에서 FAQ·Breadcrumb 확인
- Google Search Console에서 새 글 색인 생성 요청
- 실제 휴대전화에서 주요 페이지와 새 글 확인
- Search Console 소유권 확인 화면 캡처 보관

## 배포 전 7가지

- [ ] 휴대전화에서 사이트 열기
- [ ] 첫 화면에서 3초 안에 생활용품 브랜드임을 이해할 수 있는지 확인
- [ ] 메뉴 5개가 모두 열리는지 확인
- [ ] 제품 카드가 공식 스마트스토어로 연결되는지 확인
- [ ] 블로그 글이 3편 이상 보이는지 확인
- [ ] 이메일·인스타그램 링크가 실제 계정인지 확인
- [ ] Search Console 소유권 확인 화면 캡처 보관
