const currency = new Intl.NumberFormat('en-IN', {
  style: 'currency',
  currency: 'INR',
  maximumFractionDigits: 0,
});

const escapeHtml = (value) => String(value).replace(/[&<>"']/g, (character) => ({
  '&': '&amp;',
  '<': '&lt;',
  '>': '&gt;',
  '"': '&quot;',
  "'": '&#39;',
}[character]));

async function request(path, options = {}) {
  const response = await fetch(path, {
    credentials: 'same-origin',
    ...options,
    headers: {
      ...(options.body ? { 'Content-Type': 'application/json' } : {}),
      ...options.headers,
    },
  });
  const result = await response.json();
  if (!response.ok) throw new Error(result.error || 'Something went wrong.');
  return result;
}

function notify(message, isError = false) {
  let toast = document.querySelector('.site-toast');
  if (!toast) {
    toast = document.createElement('div');
    toast.className = 'site-toast';
    toast.setAttribute('role', 'status');
    document.body.append(toast);
  }
  toast.textContent = message;
  toast.classList.toggle('is-error', isError);
  toast.classList.add('is-visible');
  window.clearTimeout(notify.timeout);
  notify.timeout = window.setTimeout(() => toast.classList.remove('is-visible'), 2800);
}

function productCard(product) {
  const discount = Math.round((1 - product.price_cents / product.original_price_cents) * 100);
  const filledStars = Math.round(product.rating);
  const stars = '★'.repeat(filledStars) + '☆'.repeat(5 - filledStars);
  return `<article class="product-card">
    <div class="product-media">
      <span class="badge-discount">-${discount}%</span>
      <img src="${escapeHtml(product.image_path)}" alt="${escapeHtml(product.name)}" loading="lazy" decoding="async" />
    </div>
    <div class="product-body">
      <span class="product-cat">${escapeHtml(product.category)}</span>
      <h3>${escapeHtml(product.name)}</h3>
      <div class="rating"><span class="stars" aria-label="${product.rating} out of 5">${stars}</span> ${product.rating} (${product.review_count})</div>
      <div class="price-row">
        <span class="price">${currency.format(product.price_cents / 100)}</span>
        <span class="price-old">${currency.format(product.original_price_cents / 100)}</span>
      </div>
      <button class="btn btn-primary btn-sm" type="button" data-add-to-cart="${escapeHtml(product.id)}">Add to Cart</button>
    </div>
  </article>`;
}

async function loadProducts() {
  const grid = document.querySelector('.product-grid, .featured-grid');
  if (!grid) return;
  try {
    const { products } = await request('/api/products');
    grid.dataset.allProducts = JSON.stringify(products);
    if (grid.classList.contains('featured-grid')) {
      grid.innerHTML = products.slice(0, 3).map(productCard).join('');
    } else {
      renderProductResults(grid, products);
    }
  } catch (error) {
    notify(error.message, true);
  }
}

function renderProductResults(grid, products) {
  const selectedCategory = document.querySelector('.filter-btn.active')?.dataset.category || 'All';
  const searchTerm = document.querySelector('[data-product-search]')?.value.trim().toLowerCase() || '';
  const visible = products.filter((product) =>
    (selectedCategory === 'All' || product.category === selectedCategory)
    && `${product.name} ${product.category} ${product.description}`.toLowerCase().includes(searchTerm),
  );
  grid.innerHTML = visible.length
    ? visible.map(productCard).join('')
    : '<div class="empty-state"><h3>No products found</h3><p>Try a different search or category.</p></div>';
}

async function loadCart() {
  try {
    const cart = await request('/api/cart');
    document.querySelectorAll('.cart-chip span').forEach((count) => {
      count.textContent = String(cart.item_count);
      count.setAttribute('aria-label', `${cart.item_count} items in cart`);
    });
    renderCart(cart);
  } catch (error) {
    notify(error.message, true);
  }
}

function renderCart(cart) {
  const list = document.querySelector('.cart-list');
  const summary = document.querySelector('.summary-card');
  if (!list || !summary) return;
  if (!cart.items.length) {
    list.innerHTML = '<div class="empty-state"><h3>Your cart is empty</h3><p>Find something useful for your everyday.</p><a class="btn btn-primary" href="Products.html">Browse products</a></div>';
  } else {
    list.innerHTML = cart.items.map((item) => `<article class="cart-item" data-cart-item="${escapeHtml(item.id)}">
      <div class="cart-thumb"><img src="${escapeHtml(item.image_path)}" alt="" loading="lazy" decoding="async" /></div>
      <div class="cart-info"><h3>${escapeHtml(item.name)}</h3><p class="meta">${escapeHtml(item.category)}</p>
        <div class="qty-control">
          <button type="button" data-cart-action="decrease" data-product-id="${escapeHtml(item.id)}" aria-label="Decrease ${escapeHtml(item.name)} quantity">−</button>
          <span>${item.quantity}</span>
          <button type="button" data-cart-action="increase" data-product-id="${escapeHtml(item.id)}" aria-label="Increase ${escapeHtml(item.name)} quantity">+</button>
        </div>
      </div>
      <div class="cart-price"><div class="amount">${currency.format(item.price_cents * item.quantity / 100)}</div>
        <button class="remove-link" type="button" data-cart-action="remove" data-product-id="${escapeHtml(item.id)}">Remove</button>
      </div>
    </article>`).join('');
  }
  summary.innerHTML = `<h2>Order Summary</h2>
    <div class="summary-row"><span>Subtotal (${cart.item_count} items)</span><span>${currency.format(cart.total_cents / 100)}</span></div>
    <div class="summary-row"><span>Shipping</span><span>Free</span></div>
    <div class="summary-row total"><span>Total</span><span>${currency.format(cart.total_cents / 100)}</span></div>
    <button class="btn btn-primary btn-block" type="button" data-checkout ${cart.items.length ? '' : 'disabled'}>Proceed to Checkout</button>
    <a class="btn btn-ghost btn-block" href="Products.html" style="margin-top:0.65rem;">Continue Shopping</a>
    <p class="promo-note">Secure checkout. Free shipping on every order.</p>`;
}

async function refreshHeader() {
  try {
    const { user } = await request('/api/auth/me');
    const accountLink = document.querySelector('.nav-actions .btn');
    if (!accountLink || !user) return;
    accountLink.href = '#sign-out';
    accountLink.textContent = 'Sign out';
    accountLink.addEventListener('click', async (event) => {
      event.preventDefault();
      await request('/api/auth/logout', { method: 'POST', body: '{}' });
      window.location.href = 'Home-Page.html';
    }, { once: true });
  } catch {
    // The page can still render when the API is temporarily unavailable.
  }
}

function wireForms() {
  const loginForm = document.querySelector('[data-login-form]');
  loginForm?.addEventListener('submit', async (event) => {
    event.preventDefault();
    const values = new FormData(loginForm);
    try {
      await request('/api/auth/login', {
        method: 'POST',
        body: JSON.stringify({ email: values.get('email'), password: values.get('password') }),
      });
      window.location.href = 'Home-Page.html';
    } catch (error) {
      notify(error.message, true);
    }
  });

  const registerForm = document.querySelector('[data-register-form]');
  registerForm?.addEventListener('submit', async (event) => {
    event.preventDefault();
    const values = new FormData(registerForm);
    if (values.get('password') !== values.get('confirm')) {
      notify('Passwords do not match.', true);
      return;
    }
    try {
      await request('/api/auth/register', {
        method: 'POST',
        body: JSON.stringify({
          fullName: values.get('fullname'),
          email: values.get('email'),
          phone: values.get('phone'),
          password: values.get('password'),
        }),
      });
      window.location.href = 'Home-Page.html';
    } catch (error) {
      notify(error.message, true);
    }
  });

  const contactForm = document.querySelector('[data-contact-form]');
  contactForm?.addEventListener('submit', async (event) => {
    event.preventDefault();
    const values = new FormData(contactForm);
    try {
      const result = await request('/api/contact', {
        method: 'POST',
        body: JSON.stringify(Object.fromEntries(values)),
      });
      contactForm.reset();
      notify(result.message);
    } catch (error) {
      notify(error.message, true);
    }
  });
}

document.addEventListener('click', async (event) => {
  const addButton = event.target.closest('[data-add-to-cart]');
  if (addButton) {
    try {
      await request('/api/cart/items', {
        method: 'POST',
        body: JSON.stringify({ productId: addButton.dataset.addToCart, quantity: 1 }),
      });
      await loadCart();
      notify('Added to your cart.');
    } catch (error) {
      notify(error.message, true);
    }
    return;
  }

  const cartButton = event.target.closest('[data-cart-action]');
  if (cartButton) {
    const item = cartButton.closest('[data-cart-item]');
    const currentQuantity = Number(item.querySelector('.qty-control span').textContent);
    const quantity = cartButton.dataset.cartAction === 'increase' ? currentQuantity + 1 : currentQuantity - 1;
    try {
      await request(`/api/cart/items/${encodeURIComponent(cartButton.dataset.productId)}`, {
        method: cartButton.dataset.cartAction === 'remove' ? 'DELETE' : 'PATCH',
        ...(cartButton.dataset.cartAction !== 'remove' ? { body: JSON.stringify({ quantity }) } : {}),
      });
      await loadCart();
    } catch (error) {
      notify(error.message, true);
    }
    return;
  }

  if (event.target.closest('[data-checkout]')) {
    try {
      const result = await request('/api/orders', { method: 'POST', body: '{}' });
      await loadCart();
      notify(`Order #${result.orderId} placed. Total ${currency.format(result.total_cents / 100)}.`);
    } catch (error) {
      if (error.message.includes('Sign in')) window.location.href = 'index.html';
      else notify(error.message, true);
    }
  }
});

document.querySelectorAll('.filter-btn').forEach((button) => {
  button.dataset.category = button.textContent.trim();
  button.addEventListener('click', () => {
    document.querySelector('.filter-btn.active')?.classList.remove('active');
    button.classList.add('active');
    const grid = document.querySelector('.product-grid');
    if (grid?.dataset.allProducts) renderProductResults(grid, JSON.parse(grid.dataset.allProducts));
  });
});

document.querySelector('[data-product-search]')?.addEventListener('input', () => {
  const grid = document.querySelector('.product-grid');
  if (grid?.dataset.allProducts) renderProductResults(grid, JSON.parse(grid.dataset.allProducts));
});

wireForms();
refreshHeader().finally(() => Promise.all([loadProducts(), loadCart()]));