const $ = (selector, root = document) => root.querySelector(selector);
const $$ = (selector, root = document) => [...root.querySelectorAll(selector)];

$$('[data-year]').forEach((node) => { node.textContent = new Date().getFullYear(); });

const menuButton = $('.menu-toggle');
const siteNav = $('#site-nav');
if (menuButton && siteNav) {
  menuButton.addEventListener('click', () => {
    const isOpen = menuButton.getAttribute('aria-expanded') === 'true';
    menuButton.setAttribute('aria-expanded', String(!isOpen));
    siteNav.classList.toggle('open', !isOpen);
    document.body.classList.toggle('menu-open', !isOpen);
  });
  $$('a', siteNav).forEach((link) => link.addEventListener('click', () => {
    menuButton.setAttribute('aria-expanded', 'false');
    siteNav.classList.remove('open');
    document.body.classList.remove('menu-open');
  }));
}

const header = $('[data-header]');
const syncHeader = () => header?.classList.toggle('scrolled', window.scrollY > 24);
syncHeader();
window.addEventListener('scroll', syncHeader, { passive: true });

const scrollSections = $$('[data-scroll-section]');
const scrollLinks = $$('[data-scroll-link]');
let scrollSectionFrame = 0;
function syncCurrentSection() {
  scrollSectionFrame = 0;
  if (!scrollSections.length || !scrollLinks.length) return;
  const marker = Math.min(window.innerHeight * .42, 420);
  let current = scrollSections[0].dataset.scrollSection;
  scrollSections.forEach((section) => {
    if (section.getBoundingClientRect().top <= marker) current = section.dataset.scrollSection;
  });
  if (window.innerHeight + window.scrollY >= document.documentElement.scrollHeight - 8) {
    current = scrollSections[scrollSections.length - 1].dataset.scrollSection;
  }
  document.body.dataset.currentSection = current;
  scrollLinks.forEach((link) => {
    const isCurrent = link.dataset.scrollLink === current;
    link.classList.toggle('is-current', isCurrent);
    if (isCurrent) link.setAttribute('aria-current', 'location');
    else link.removeAttribute('aria-current');
  });
}
function requestSectionSync() {
  if (scrollSectionFrame) return;
  scrollSectionFrame = requestAnimationFrame(syncCurrentSection);
}
syncCurrentSection();
window.addEventListener('scroll', requestSectionSync, { passive: true });
window.addEventListener('resize', requestSectionSync);

const reducedMotion = window.matchMedia('(prefers-reduced-motion: reduce)').matches;
const counters = $$('[data-count]');
function animateCounter(node) {
  const target = Number(node.dataset.count || 0);
  if (reducedMotion) { node.textContent = target; return; }
  const started = performance.now();
  const duration = 900;
  function frame(now) {
    const progress = Math.min((now - started) / duration, 1);
    const eased = 1 - Math.pow(1 - progress, 3);
    node.textContent = Math.round(target * eased);
    if (progress < 1) requestAnimationFrame(frame);
  }
  requestAnimationFrame(frame);
}
if (counters.length) {
  if (reducedMotion) {
    counters.forEach((counter) => { counter.textContent = counter.dataset.count; });
  } else if ('IntersectionObserver' in window) {
    const counterObserver = new IntersectionObserver((entries) => {
      entries.forEach((entry) => {
        if (!entry.isIntersecting) return;
        animateCounter(entry.target);
        counterObserver.unobserve(entry.target);
      });
    }, { threshold: 0.55 });
    counters.forEach((counter) => counterObserver.observe(counter));
  } else {
    counters.forEach(animateCounter);
  }
}

const fallbackLabels = {
  fabric: '포신한 직물의 감촉',
  organize: '정갈한 일상의 여백',
  outdoor: '든든한 밖의 시간'
};
const won = (value) => `${Number(value || 0).toLocaleString('ko-KR')}원`;
const productCard = (product, featured = false) => {
  const discountRate = Number(product.discountRate || 0);
  const salePrice = product.salePrice ?? product.price;
  const hasDiscount = discountRate > 0 && Number(product.productPrice) > Number(salePrice);
  const priceLabel = hasDiscount
    ? `${discountRate}% 할인, 판매가 ${won(salePrice)}, 정상가 ${won(product.productPrice)}`
    : `판매가 ${won(salePrice)}`;
  return `
  <article class="product-card ${featured ? 'featured' : ''}">
    <a class="product-visual ${product.category}" href="${product.url}" target="_blank" rel="noopener" aria-label="${product.name} 쿠팡에서 보기">
      ${product.image ? `<img src="${product.image}" alt="${product.name}" loading="lazy">` : `<span>${fallbackLabels[product.category] || '일상을 위한 물건'}</span>`}
      <em>${product.categoryLabel}</em>
    </a>
    <div class="product-info">
      <p>${product.categoryLabel}</p><h3>${product.name}</h3>${product.option ? `<small class="product-option">${product.option}</small>` : ''}<span>${product.tagline}</span>
      <div class="product-price" aria-label="${priceLabel}">
        <div class="price-main">${hasDiscount ? `<span>${discountRate}%</span>` : ''}<strong>${won(salePrice)}</strong></div>
        ${hasDiscount ? `<del>${won(product.productPrice)}</del>` : ''}
      </div>
      <div class="product-actions">
        <a class="button product-buy" href="${product.url}" target="_blank" rel="noopener noreferrer">쿠팡에서 구매 <span aria-hidden="true">↗</span></a>
        <button type="button" class="cart-add" data-cart-add data-name="${product.name}" data-price="${salePrice}" data-url="${product.url}">담기</button>
      </div>
    </div>
  </article>`;
};

async function renderProducts() {
  const containers = $$('[data-product-list]');
  if (!containers.length) return;
  try {
    const response = await fetch('products.json');
    if (!response.ok) throw new Error('products.json');
    const { products } = await response.json();
    containers.forEach((container) => {
      const filtered = container.dataset.category ? products.filter((item) => item.category === container.dataset.category) : products;
      const limit = Number(container.dataset.limit || filtered.length);
      const curated = filtered.slice(0, limit);
      container.innerHTML = curated.map((item, index) => productCard(item, index === 0 && !container.dataset.category)).join('');
    });
  } catch {
    containers.forEach((container) => { container.innerHTML = '<p class="empty-note">제품을 준비하고 있어요.</p>'; });
  }
}

async function renderStories() {
  const containers = $$('[data-story-list]');
  if (!containers.length) return;
  try {
    const response = await fetch('story/posts.json');
    if (!response.ok) throw new Error('posts.json');
    const posts = await response.json();
    containers.forEach((container) => {
      const limit = Number(container.dataset.limit || posts.length);
      container.innerHTML = posts.slice(0, limit).map((post) => `
        <article class="story-card"><p>${post.tags?.[0] || 'LIVING NOTE'} · ${post.date}</p>
        <h3><a href="story/${post.url}">${post.title}</a></h3><span>${post.summary}</span>
        <a class="text-link" href="story/${post.url}">읽어보기 <span aria-hidden="true">→</span></a></article>`).join('');
    });
  } catch {
    containers.forEach((container) => { container.innerHTML = '<p class="empty-note">생활 이야기를 준비하고 있어요.</p>'; });
  }
}
renderProducts();
renderStories();
