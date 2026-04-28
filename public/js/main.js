(async () => {
  const grid = document.getElementById('grid');
  const status = document.getElementById('status');

  function formatPrice(price) {
    if (price == null) return null;
    return price.toLocaleString('ko-KR') + '원';
  }

  function makeCard(deal) {
    const card = document.createElement('div');
    card.className = 'card';
    card.addEventListener('click', () => {
      const target = deal.purchase_url || deal.original_url;
      if (target) window.open(target, '_blank', 'noopener');
    });

    // 썸네일
    if (deal.thumbnail) {
      const img = document.createElement('img');
      img.className = 'card-thumb';
      img.src = deal.thumbnail;
      img.alt = deal.title;
      img.loading = 'lazy';
      img.onerror = () => img.replaceWith(placeholder());
      card.appendChild(img);
    } else {
      card.appendChild(placeholder());
    }

    // 본문
    const body = document.createElement('div');
    body.className = 'card-body';

    const title = document.createElement('div');
    title.className = 'card-title';
    title.textContent = deal.title;
    body.appendChild(title);

    const priceEl = document.createElement('div');
    const formatted = formatPrice(deal.price);
    if (formatted) {
      priceEl.className = 'card-price';
      priceEl.textContent = formatted;
    } else {
      priceEl.className = 'card-price unknown';
      priceEl.textContent = '가격 미상';
    }
    body.appendChild(priceEl);

    if (deal.store_name) {
      const store = document.createElement('span');
      store.className = 'card-store';
      store.textContent = deal.store_name;
      body.appendChild(store);
    }

    card.appendChild(body);
    return card;
  }

  function placeholder() {
    const div = document.createElement('div');
    div.className = 'card-thumb-placeholder';
    div.textContent = '🛒';
    return div;
  }

  try {
    const resp = await fetch('./data/deals.json');
    if (!resp.ok) throw new Error(`HTTP ${resp.status}`);
    const deals = await resp.json();

    status.style.display = 'none';

    if (deals.length === 0) {
      status.style.display = '';
      status.textContent = '현재 핫딜이 없습니다.';
      return;
    }

    const fragment = document.createDocumentFragment();
    for (const deal of deals) {
      fragment.appendChild(makeCard(deal));
    }
    grid.appendChild(fragment);
  } catch (e) {
    status.className = 'status error';
    status.textContent = `데이터를 불러올 수 없습니다: ${e.message}`;
  }
})();
