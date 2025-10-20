// Accessible FAQ expand/collapse using event delegation
(function(){
  function setCollapsedState(item, collapsed){
    const faqA = item.querySelector('.faq-a');
    const btn = item.querySelector('.faq-q');
    if(!faqA || !btn) return;
    btn.setAttribute('aria-expanded', (!collapsed).toString());
    if(!collapsed){
      item.classList.add('open');
      faqA.style.maxHeight = faqA.scrollHeight + 'px';
      faqA.style.opacity = '1';
    } else {
      faqA.style.maxHeight = '0';
      faqA.style.opacity = '0';
      item.classList.remove('open');
    }
  }

  function onToggle(target){
    const btn = target.closest('.faq-q');
    if(!btn) return false;
    const item = btn.closest('.faq-item');
    if(!item) return false;
    const expanded = btn.getAttribute('aria-expanded') === 'true';
    setCollapsedState(item, expanded); // pass collapsed = expanded to toggle
    return true;
  }

  function init(){
    console.log('FAQ: initializing');
    // initialize all items from aria-expanded attribute
    document.querySelectorAll('.faq-item').forEach(item => {
      const btn = item.querySelector('.faq-q');
      const faqA = item.querySelector('.faq-a');
      if(!btn || !faqA) return;
      btn.style.cursor = 'pointer';
      const expanded = btn.getAttribute('aria-expanded') === 'true';
      if(expanded){
        item.classList.add('open');
        faqA.style.maxHeight = faqA.scrollHeight + 'px';
        faqA.style.opacity = '1';
      } else {
        faqA.style.maxHeight = '0';
        faqA.style.opacity = '0';
      }
    });

    // Use event delegation for clicks
    document.addEventListener('click', function(e){
      const toggled = onToggle(e.target);
      if(toggled) e.preventDefault();
    });

    // keyboard support (Enter/Space) via keydown on document
    document.addEventListener('keydown', function(e){
      // only handle Space/Enter when focus is on a .faq-q
      const active = document.activeElement;
      if(!active) return;
      if(active.classList && active.classList.contains('faq-q')){
        if(e.key === 'Enter' || e.key === ' ' || e.key === 'Spacebar'){
          e.preventDefault();
          onToggle(active);
        }
      }
    });
  }

  if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', init);
  } else {
    init();
  }
})();
