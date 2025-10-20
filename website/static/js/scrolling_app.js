document.addEventListener('DOMContentLoaded', function () {
  const targets = document.querySelectorAll('.section.hidden');
  console.log('scroll targets:', targets.length, Array.from(targets));

  if (!targets.length) {
    console.warn('No .section.hidden elements found');
    return;
  }

  if (!('IntersectionObserver' in window)) {
    console.warn('IntersectionObserver not supported, revealing all sections');
    targets.forEach(el => {
      el.classList.add('show');
      el.classList.remove('hidden');
    });
    return;
  }

  // Small delay so browser paints .hidden styles first
  setTimeout(() => {
    const io = new IntersectionObserver((entries) => {
      entries.forEach(entry => {
        if (entry.isIntersecting) {
          console.log('Revealing section:', entry.target);
          const el = entry.target;
          
          // Add .show (starts transition), remove .hidden after transition completes
          el.classList.add('show');
          
          // Remove .hidden after transition duration (1s from CSS)
          setTimeout(() => {
            el.classList.remove('hidden');
          }, 1000);
          
          io.unobserve(el);
        }
      });
    }, { 
      threshold: 0.1,
      rootMargin: '0px 0px -50px 0px'
    });

    targets.forEach(el => io.observe(el));
    console.log('IntersectionObserver attached to', targets.length, 'sections');
  }, 100);
});

