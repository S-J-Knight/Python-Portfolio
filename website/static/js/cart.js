document.addEventListener('DOMContentLoaded', function() {
    var updateBtns = document.getElementsByClassName('update-cart');
    console.log('Number of update-cart buttons:', updateBtns.length); // Debug line

    for (let i = 0; i < updateBtns.length; i++) {
        updateBtns[i].addEventListener('click', function(){
            var productId = this.dataset.product;
            var action = this.dataset.action;
            console.log('productId:', productId, 'Action:', action);

            console.log('User:', user);
            if (user === 'AnonymousUser') {
                console.log('User is not authenticated');
            } else {
                updateUserOrder(productId, action);
            }
        });
    }
});

function updateUserOrder(productId, action){
	console.log('User is authenticated, sending data...')

		var url = '/update_item/'

		fetch(url, {
			method:'POST',
			headers:{
				'Content-Type':'application/json',
				'X-CSRFToken':csrftoken,
			}, 
			body:JSON.stringify({'productId':productId, 'action':action})
		})
		.then((response) => {
		   return response.json();
		})
		.then((data) => {
		    location.reload()
		});
}

// Add this script to your template
document.addEventListener('DOMContentLoaded', function() {
    var checkbox = document.getElementById('use-last-address');
    var shippingInfo = document.getElementById('shipping-info');
    if (checkbox && shippingInfo) {
        checkbox.addEventListener('change', function() {
            shippingInfo.style.display = this.checked ? 'none' : 'block';
        });
        // Initial state
        shippingInfo.style.display = checkbox.checked ? 'none' : 'block';
    }
    var saveShipping = document.getElementById('save-shipping-info') ? document.getElementById('save-shipping-info').checked : false;
    shippingInfo.save = saveShipping;
});

