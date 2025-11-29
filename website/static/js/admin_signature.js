// Admin Signature Pad
document.addEventListener('DOMContentLoaded', function() {
    const canvas = document.getElementById('admin-signature-pad');
    const clearBtn = document.getElementById('clear-admin-sig');
    const hiddenInput = document.querySelector('input[name="wtn_admin_signature"]') || document.querySelector('textarea[name="wtn_admin_signature"]');
    
    if (!canvas || !hiddenInput) {
        console.log('Canvas or hidden input not found');
        return;
    }
    
    console.log('Admin signature canvas initialized');
    
    const ctx = canvas.getContext('2d');
    let drawing = false;
    let hasSignature = false;
    
    // Check if there's already a signature
    if (hiddenInput.value && hiddenInput.value.startsWith('data:image')) {
        const img = new Image();
        img.onload = function() {
            ctx.drawImage(img, 0, 0, canvas.width, canvas.height);
            hasSignature = true;
        };
        img.src = hiddenInput.value;
    }
    
    // Drawing functions
    function startDrawing(e) {
        drawing = true;
        const rect = canvas.getBoundingClientRect();
        const x = (e.clientX || e.touches[0].clientX) - rect.left;
        const y = (e.clientY || e.touches[0].clientY) - rect.top;
        ctx.beginPath();
        ctx.moveTo(x, y);
        hasSignature = true;
    }
    
    function draw(e) {
        if (!drawing) return;
        e.preventDefault();
        const rect = canvas.getBoundingClientRect();
        const x = (e.clientX || e.touches[0].clientX) - rect.left;
        const y = (e.clientY || e.touches[0].clientY) - rect.top;
        ctx.lineTo(x, y);
        ctx.strokeStyle = '#000';
        ctx.lineWidth = 2;
        ctx.lineCap = 'round';
        ctx.lineJoin = 'round';
        ctx.stroke();
        
        // Save to hidden input immediately on each stroke
        hiddenInput.value = canvas.toDataURL('image/png');
    }
    
    function stopDrawing() {
        drawing = false;
        // Save one final time when done
        if (hasSignature) {
            hiddenInput.value = canvas.toDataURL('image/png');
        }
    }
    
    // Mouse events
    canvas.addEventListener('mousedown', startDrawing);
    canvas.addEventListener('mousemove', draw);
    canvas.addEventListener('mouseup', stopDrawing);
    canvas.addEventListener('mouseout', stopDrawing);
    
    // Touch events
    canvas.addEventListener('touchstart', function(e) {
        e.preventDefault();
        startDrawing(e);
    });
    canvas.addEventListener('touchmove', function(e) {
        e.preventDefault();
        draw(e);
    });
    canvas.addEventListener('touchend', function(e) {
        e.preventDefault();
        stopDrawing();
    });
    
    // Clear button
    clearBtn.addEventListener('click', function() {
        ctx.clearRect(0, 0, canvas.width, canvas.height);
        hiddenInput.value = '';
        hasSignature = false;
    });
    
    // Auto-check the "approved" checkbox when signing
    const approvedCheckbox = document.querySelector('input[name="wtn_admin_approved"]');
    if (approvedCheckbox) {
        canvas.addEventListener('mouseup', function() {
            if (hasSignature && !approvedCheckbox.checked) {
                approvedCheckbox.checked = true;
            }
        });
        canvas.addEventListener('touchend', function() {
            if (hasSignature && !approvedCheckbox.checked) {
                approvedCheckbox.checked = true;
            }
        });
    }
});
