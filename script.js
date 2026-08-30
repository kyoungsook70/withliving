const contactForm = document.querySelector('#contact-form');
if (contactForm) {
  contactForm.addEventListener('submit', (event) => {
    event.preventDefault();
    const data = new FormData(contactForm);
    const subject = encodeURIComponent(`[NEXGEN] ${data.get('type')} - ${data.get('name')}`);
    const body = encodeURIComponent(`이름 / 담당자명: ${data.get('name')}\n이메일: ${data.get('email')}\n문의 유형: ${data.get('type')}\n\n${data.get('message')}`);
    window.location.href = `mailto:withnexgen@gmail.com?subject=${subject}&body=${body}`;
  });
}

const year = document.querySelector('#year');
if (year) year.textContent = new Date().getFullYear();

const menuToggle = document.querySelector('.menu-toggle');
const siteNav = document.querySelector('.site-nav');

const closeMenu = () => {
  if (!menuToggle || !siteNav) return;
  document.body.classList.remove('menu-open');
  menuToggle.setAttribute('aria-expanded', 'false');
  menuToggle.setAttribute('aria-label', '메뉴 열기');
};

if (menuToggle && siteNav) {
  menuToggle.addEventListener('click', () => {
    const isOpen = !document.body.classList.contains('menu-open');
    document.body.classList.toggle('menu-open', isOpen);
    menuToggle.setAttribute('aria-expanded', String(isOpen));
    menuToggle.setAttribute('aria-label', isOpen ? '메뉴 닫기' : '메뉴 열기');
  });
  siteNav.addEventListener('click', (event) => {
    if (event.target.closest('a')) closeMenu();
  });
  document.addEventListener('keydown', (event) => {
    if (event.key === 'Escape') closeMenu();
  });
}

const sectionNavItems = Array.from(document.querySelectorAll('.site-nav a[href^="#"]'))
  .map((link) => ({ link, section: document.querySelector(link.getAttribute('href')) }))
  .filter((item) => item.section);

if (sectionNavItems.length) {
  let ticking = false;

  const updateActiveSection = () => {
    const marker = window.scrollY + window.innerHeight * 0.38;
    let activeItem = null;

    sectionNavItems.forEach((item) => {
      if (item.section.offsetTop <= marker) activeItem = item;
    });

    sectionNavItems.forEach((item) => {
      const isActive = item === activeItem;
      item.link.classList.toggle('is-active', isActive);
      if (isActive) item.link.setAttribute('aria-current', 'location');
      else item.link.removeAttribute('aria-current');
    });

    ticking = false;
  };

  const scheduleActiveSectionUpdate = () => {
    if (ticking) return;
    ticking = true;
    window.requestAnimationFrame(updateActiveSection);
  };

  window.addEventListener('scroll', scheduleActiveSectionUpdate, { passive: true });
  window.addEventListener('resize', scheduleActiveSectionUpdate);
  updateActiveSection();
}

const productTargets = document.querySelectorAll('[data-products-limit]');

const formatPrice = (price) => `${new Intl.NumberFormat('ko-KR').format(price)}원`;

const createProductCard = (product, index, options = {}) => {
  const card = document.createElement('article');
  card.className = `store-product-card card${options.featured ? ' store-product-featured' : ''}`;

  const media = document.createElement('div');
  media.className = 'store-product-media';

  const image = document.createElement('img');
  image.src = product.image;
  image.alt = product.name;
  image.loading = index < 3 ? 'eager' : 'lazy';
  image.decoding = 'async';
  image.referrerPolicy = 'no-referrer';
  media.append(image);

  const body = document.createElement('div');
  body.className = 'store-product-body';

  const meta = document.createElement('p');
  meta.className = 'card-meta';
  meta.textContent = options.featured ? "SELLER'S PICK · EGF CREAM" : `NEXGEN · ${String(index + 1).padStart(2, '0')}`;

  const name = document.createElement('h3');
  name.textContent = product.name;

  const tagline = document.createElement('p');
  tagline.className = 'store-product-tagline';
  tagline.textContent = product.tagline || '내 피부 루틴에 맞는 제품';

  const foot = document.createElement('div');
  foot.className = 'store-product-foot';

  const price = document.createElement('div');
  price.className = 'store-product-price';

  if (product.discountRate > 0 && product.regularPrice > product.price) {
    const regular = document.createElement('del');
    regular.className = 'store-product-regular';
    regular.textContent = formatPrice(product.regularPrice);

    const discount = document.createElement('span');
    discount.className = 'store-product-discount';
    discount.textContent = `${product.discountRate}%`;
    price.append(regular, discount);
  }

  const sale = document.createElement('strong');
  sale.textContent = formatPrice(product.price);
  price.append(sale);

  const buy = document.createElement('a');
  buy.href = product.url;
  if (options.directBuy) {
    buy.textContent = '스마트스토어에서 구매 ↗';
    buy.target = '_blank';
    buy.rel = 'noopener';
    buy.setAttribute('aria-label', `${product.name} 스마트스토어에서 구매`);
  } else {
    buy.textContent = '장바구니 담기';
    buy.setAttribute('data-cart-add', '');
    buy.setAttribute('data-name', product.name);
    buy.setAttribute('data-price', String(product.price));
    buy.setAttribute('data-url', product.url);
    buy.setAttribute('aria-label', `${product.name} 장바구니에 담기`);
  }

  foot.append(price, buy);
  body.append(meta, name, tagline, foot);
  card.append(media, body);
  return card;
};

const renderProducts = async () => {
  if (!productTargets.length) return;

  try {
    const response = await fetch('products.json', { cache: 'no-store' });
    if (!response.ok) throw new Error(`HTTP ${response.status}`);

    const data = await response.json();
    if (!Array.isArray(data.products)) throw new Error('제품 데이터 형식이 올바르지 않습니다.');

    const productCount = document.querySelector('#product-count');
    const productDate = document.querySelector('#product-date');
    if (productCount) productCount.textContent = data.products.length;
    if (productDate) productDate.textContent = String(data.collectedAt || '').replaceAll('-', '.') || 'UPDATED';

    productTargets.forEach((target) => {
      if (target.dataset.productsLayout === 'curated') {
        const featuredName = '넥스젠 레이저시술후 재생크림 피부과 EGF 재생크림';
        const featured = data.products.find((product) => product.name === featuredName);
        if (!featured) throw new Error('대표 제품을 찾을 수 없습니다.');

        const recommendations = data.products
          .filter((product) => product !== featured)
          .slice(0, 6);
        const fragment = document.createDocumentFragment();
        fragment.append(createProductCard(featured, 0, { featured: true, directBuy: true }));

        const grid = document.createElement('div');
        grid.className = 'curated-product-grid';
        recommendations.forEach((product, index) => {
          grid.append(createProductCard(product, index, { directBuy: true }));
        });
        fragment.append(grid);

        const more = document.createElement('a');
        more.className = 'curated-products-more';
        more.href = 'https://smartstore.naver.com/withnexgen';
        more.target = '_blank';
        more.rel = 'noopener';
        more.textContent = '전체 제품 보기 ↗';
        fragment.append(more);
        target.replaceChildren(fragment);
        return;
      }

      const limitValue = target.dataset.productsLimit;
      const products = limitValue === 'all'
        ? data.products
        : data.products.slice(0, Number(limitValue));
      const fragment = document.createDocumentFragment();
      products.forEach((product, index) => fragment.append(createProductCard(product, index)));
      target.replaceChildren(fragment);
    });
  } catch (error) {
    productTargets.forEach((target) => {
      const message = document.createElement('p');
      message.className = 'product-loading';
      message.textContent = '제품 정보를 불러오지 못했습니다. 잠시 후 다시 확인해 주세요.';
      target.replaceChildren(message);
    });
    console.error('NEXGEN product loading failed:', error);
  }
};

renderProducts();

const latestStories = document.querySelector('[data-posts-source]');

const formatStoryDate = (value) => {
  const date = new Date(`${value}T00:00:00`);
  if (Number.isNaN(date.getTime())) return value || '';
  return new Intl.DateTimeFormat('ko-KR', {
    year: 'numeric',
    month: '2-digit',
    day: '2-digit',
  }).format(date).replaceAll(' ', '');
};

const createStoryCard = (post) => {
  const article = document.createElement('article');
  article.className = 'story-card card';
  const link = document.createElement('a');
  link.href = post.url
    ? `story/${post.url}`
    : `story/post.html?id=${encodeURIComponent(post.id || '')}`;

  const meta = document.createElement('p');
  meta.className = 'card-meta';
  meta.textContent = formatStoryDate(post.date);

  const title = document.createElement('h3');
  title.textContent = post.title || '(제목 없음)';

  const summary = document.createElement('p');
  summary.textContent = post.summary || '';

  const arrow = document.createElement('span');
  arrow.className = 'story-arrow';
  arrow.setAttribute('aria-hidden', 'true');
  arrow.textContent = '↗';

  link.append(meta, title, summary, arrow);
  article.append(link);
  return article;
};

const renderLatestStories = async () => {
  if (!latestStories) return;
  try {
    const response = await fetch(latestStories.dataset.postsSource, { cache: 'no-store' });
    if (!response.ok) throw new Error(`HTTP ${response.status}`);
    const posts = await response.json();
    if (!Array.isArray(posts)) throw new Error('블로그 데이터 형식이 올바르지 않습니다.');
    const fragment = document.createDocumentFragment();
    posts
      .slice()
      .sort((a, b) => String(b.date || '').localeCompare(String(a.date || '')))
      .slice(0, 3)
      .forEach((post) => fragment.append(createStoryCard(post)));
    latestStories.replaceChildren(fragment);
  } catch (error) {
    const message = document.createElement('p');
    message.className = 'blog-message';
    message.textContent = '이야기를 불러오지 못했습니다. 잠시 후 다시 확인해 주세요.';
    latestStories.replaceChildren(message);
    console.error('NEXGEN story loading failed:', error);
  }
};

renderLatestStories();
