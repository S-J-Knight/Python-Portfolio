document.addEventListener('DOMContentLoaded', function () {
  // cart.js loaded marker
  console.log('cart.js loaded');

  // Helper: get CSRF token from cookies if not already defined
  function getCookie(name) {
    const value = `; ${document.cookie}`;
    const parts = value.split(`; ${name}=`);
    if (parts.length === 2) return parts.pop().split(';').shift();
    return null;
  }
  const CSRF = getCookie('csrftoken');

  // Global cart for guests (cookie-based)
  let cart = {};
  try {
    cart = JSON.parse(getCookie('cart') || '{}');
  } catch (_) {
    cart = {};
  }

  // prevent concurrent posts per button
  const inFlight = new WeakSet();

  // Click delegation so buttons added later still work
  document.addEventListener('click', async (e) => {
    const btn = e.target.closest('.update-cart');
    if (!btn) return;

    if (inFlight.has(btn)) return; // ignore double-click
    inFlight.add(btn);
    btn.disabled = true;

    const productId = btn.dataset.product;
    let action = btn.dataset.action;

    // read qty ...
    let qty = 1;
    const inputId = btn.dataset.qtyInput;
    if (inputId) {
      const el = document.getElementById(inputId);
      if (el) qty = parseInt(el.value, 10) || 0;   // allow 0
    } else {
      const near = btn.closest('article, tr, .actions, .product-details')?.querySelector('.qty-input');
      if (near) qty = parseInt(near.value, 10) || 0; // allow 0
    }

    // If qty <= 0, treat as "set to 0" which deletes the item
    if (qty <= 0) {
      action = 'set';
      qty = 0;
    }
    console.log('update-cart click ->', { productId, action, qty });

    const isGuest = (window.user || 'AnonymousUser') === 'AnonymousUser';

    try {
      if (isGuest) {
        if (!cart[productId]) cart[productId] = { quantity: 0 };
        if (action === 'add') cart[productId].quantity += qty;
        else if (action === 'remove') {
          cart[productId].quantity -= Math.max(1, qty);
          if (cart[productId].quantity <= 0) delete cart[productId];
        } else if (action === 'set') {
          if (qty <= 0) delete cart[productId];
          else cart[productId].quantity = qty;
        }
        document.cookie = 'cart=' + JSON.stringify(cart) + ';domain=;path=/';
        location.reload();
      } else {
        const url = '/store/update_item/';
        const payload = { productId, action, quantity: Number(qty) };
        console.log('POST', url, payload);
        const res = await fetch(url, {
          method: 'POST',
          headers: { 'Content-Type': 'application/json', 'X-CSRFToken': CSRF },
          body: JSON.stringify(payload),
        });
        const data = await res.json().catch(() => ({}));
        if (data.error) alert(data.error);
        location.reload();
      }
    } finally {
      btn.disabled = false;
      inFlight.delete(btn);
    }
  });

  // optional element example (guarded)
  const optionalElem = document.getElementById('some-id');
  if (optionalElem) {
    optionalElem.save = function () {
      // placeholder save method
    };
  }

  // Shipping info UI: guarded and inside the same DOMContentLoaded handler
  (function () {
    const checkbox = document.getElementById('use-last-address');
    const shippingInfo = document.getElementById('shipping-info');
    if (checkbox && shippingInfo) {
      checkbox.addEventListener('change', function () {
        shippingInfo.style.display = this.checked ? 'none' : 'block';
      });
      // Initial state
      shippingInfo.style.display = checkbox.checked ? 'none' : 'block';
    }
    const saveShippingElem = document.getElementById('save-shipping-info');
    const saveShipping = saveShippingElem ? saveShippingElem.checked : false;
    if (shippingInfo) {
      // attach a property safely
      shippingInfo.save = saveShipping;
    }
  })();

  // Helper: set quantity for a product (auth or guest)
  function sendSetQuantity(productId, qty) {
    const isGuest = (window.user || 'AnonymousUser') === 'AnonymousUser';
    qty = Number(qty || 0);

    if (isGuest) {
      if (qty <= 0) {
        delete cart[productId];
      } else {
        if (!cart[productId]) cart[productId] = { quantity: 0 };
        cart[productId].quantity = qty;
      }
      document.cookie = 'cart=' + JSON.stringify(cart) + ';domain=;path=/';
      location.reload();
      return;
    }

    fetch('/store/update_item/', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json', 'X-CSRFToken': CSRF },
      body: JSON.stringify({ productId, action: 'set', quantity: qty }),
    })
      .then((r) => r.json()).catch(() => ({}))
      .then((data) => {
        if (data && data.error) alert(data.error);
        location.reload();
      });
  }

  function productIdFromInput(input) {
    const cell = input.closest('.qty-cell');
    const refBtn = cell?.querySelector('.update-cart');
    return refBtn ? refBtn.dataset.product :
           (input.id && input.id.startsWith('qty-') ? input.id.replace('qty-', '') : null);
  }

  // Auto-apply when the number changes (skip if data-no-auto-submit is set)
  document.addEventListener('change', (e) => {
    const input = e.target.closest('.qty-input');
    if (!input) return;
    
    // Skip auto-submit for product detail page
    if (input.hasAttribute('data-no-auto-submit')) {
      console.log('Skipping auto-submit for input:', input.id);
      return;
    }
    
    const productId = productIdFromInput(input);
    if (!productId) return;
    let qty = parseInt(input.value, 10);
    if (isNaN(qty)) qty = 0; // 0 deletes
    sendSetQuantity(productId, qty);
  });

  // Pressing Enter applies immediately (0 deletes)
  document.addEventListener('keydown', (e) => {
    const input = e.target.closest('.qty-input');
    if (!input || e.key !== 'Enter') return;
    
    // Skip auto-submit for product detail page
    if (input.hasAttribute('data-no-auto-submit')) {
      console.log('Skipping auto-submit on Enter for input:', input.id);
      return;
    }
    
    e.preventDefault();
    const productId = productIdFromInput(input);
    if (!productId) return;
    let qty = parseInt(input.value, 10);
    if (isNaN(qty)) qty = 0;
    sendSetQuantity(productId, qty);
  });
}); // end DOMContentLoaded

