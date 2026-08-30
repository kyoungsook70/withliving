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
const productCard = (product, featured = false) => `
  <article class="product-card ${featured ? 'featured' : ''}">
    <a class="product-visual ${product.category}" href="${product.url}" target="_blank" rel="noopener" aria-label="${product.name} 쿠팡에서 보기">
      ${product.image ? `<img src="${product.image}" alt="${product.name}" loading="lazy">` : `<span>${fallbackLabels[product.category] || '일상을 위한 물건'}</span>`}
      <em>${product.categoryLabel}</em>
    </a>
    <div class="product-info">
      <p>${product.categoryLabel}</p><h3>${product.name}</h3><span>${product.tagline}</span>
      <div class="product-actions">
        <a class="text-link" href="${product.url}" target="_blank" rel="noopener">쿠팡에서 가격 보기 <span aria-hidden="true">↗</span></a>
        <button type="button" class="cart-add" data-cart-add data-name="${product.name}" data-price="0" data-url="${product.url}">담기</button>
      </div>
    </div>
  </article>`;

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
      container.innerHTML = filtered.slice(0, limit).map((item, index) => productCard(item, index === 0 && !container.dataset.category)).join('');
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
