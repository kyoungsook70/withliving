# 위드리빙 — 생활을 더 편안하게

방석, 쿠션, 티슈케이스, 자전거 자물쇠, 선반 매트 등 일상을 편안하게 만드는 생활용품 브랜드 웹사이트입니다. 제품을 소개하고, 구매 버튼을 통해 쿠팡로 연결합니다.

## 1단계 범위

- Beauty Meets Science 사이트의 정적 HTML 구조와 반응형 CSS, JavaScript 구조 복제
- 영상 스크럽, 장바구니, 제품 JSON, 블로그, SEO·AEO·GEO 스킬 보존
- 위드리빙 브랜드 기준과 디자인 방향 확정
- 실제 쿠팡 링크·사진·가격은 확인 후 2단계에서 교체

## 로컬에서 보기

빌드 과정은 없습니다. 제품 JSON을 정상적으로 불러오려면 프로젝트 폴더에서 아래 명령으로 로컬 서버를 실행한 뒤 `http://localhost:8000`에 접속합니다.

```bash
python3 -m http.server 8000
```

## 파일 구성

- `index.html` — 홈 콘텐츠와 대표 제품
- `about.html` — 위드리빙 브랜드 이야기
- `products.html` — 전체 제품 목록 페이지
- `products.json` — 제품명, 가격, 이미지, 구매 링크 데이터
- `story/index.html` — 블로그 글 목록
- `story/post.html` — 블로그 글 상세
- `story/posts.json` — 홈과 블로그가 함께 읽는 글 데이터
- `story/admin.html` — 블로그 글 관리 도구
- `styles.css` — 반응형 디자인과 애니메이션
- `script.js` — 제품·최신 글 표시, 모바일 메뉴와 이메일 문의 기능

새 제품은 `products.json`에, 새 글은 `story/posts.json`에 같은 형식으로 추가하면 관련 페이지에 자동으로 반영됩니다. 쿠팡 주소, 이메일, SNS, 사업자 정보는 실제 정보를 받은 후 반영합니다.
