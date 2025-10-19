document.addEventListener('DOMContentLoaded', function () {
  console.log('cart.js loaded, UPDATE_ITEM_URL=', typeof UPDATE_ITEM_URL !== 'undefined' ? UPDATE_ITEM_URL : 'UNDEFINED', 'csrftoken=', typeof csrftoken !== 'undefined' ? csrftoken : 'UNDEFINED', 'user=', typeof user !== 'undefined' ? user : 'UNDEFINED');

  function getCookie(name) {
    const cookies = document.cookie ? document.cookie.split(';') : [];
    for (let i = 0; i < cookies.length; i++) {
      const cookie = cookies[i].trim();
      if (cookie.startsWith(name + '=')) return decodeURIComponent(cookie.substring(name.length + 1));
    }
    return null;
  }

  // ensure csrftoken is available
  const _csrftoken = (typeof csrftoken !== 'undefined' && csrftoken) ? csrftoken : getCookie('csrftoken');

  // load cart from cookie (guest)
  let cart = {};
  try {
    const raw = getCookie('cart');
    cart = raw ? JSON.parse(raw) : {};
  } catch (e) {
    cart = {};
  }
  // console.debug('Cart (cookie):', cart); // optional: keep as debug instead of duplicate console.log

  function setCartCookie() {
    document.cookie = 'cart=' + JSON.stringify(cart) + ';path=/';
  }

  function addCookieItem(productId, action) {
    if (!productId) return;
    if (!cart[productId]) {
      cart[productId] = { 'quantity': 0 };
    }
    if (action === 'add') {
      cart[productId].quantity = (cart[productId].quantity || 0) + 1;
    } else if (action === 'remove') {
      cart[productId].quantity = (cart[productId].quantity || 0) - 1;
      if (cart[productId].quantity <= 0) delete cart[productId];
    }
    setCartCookie();
    console.log('Updated cookie cart:', cart);
    location.reload();
  }

  function updateUserOrder(productId, action) {
    if (!productId) return;
    const url = (typeof UPDATE_ITEM_URL !== 'undefined') ? UPDATE_ITEM_URL : '/store/update_item/';
    fetch(url, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
        'X-CSRFToken': _csrftoken || ''
      },
      body: JSON.stringify({ productId: productId, action: action })
    })
      .then(res => res.json())
      .then(data => {
        console.log('updateUserOrder response', data);
        location.reload();
      })
      .catch(err => console.error('updateUserOrder error', err));
  }

  const updateBtns = document.getElementsByClassName('update-cart');
  console.log('Number of update-cart buttons:', updateBtns.length);

  for (let i = 0; i < updateBtns.length; i++) {
    const btn = updateBtns[i];
    if (!btn) continue;
    btn.addEventListener('click', function () {
      const productId = this.dataset.product;
      const action = this.dataset.action;
      console.log('Clicked update-cart:', productId, action);
      if (typeof user === 'undefined' || user === 'AnonymousUser') {
        addCookieItem(productId, action);
      } else {
        updateUserOrder(productId, action);
      }
    });
  }

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

}); // end DOMContentLoaded

