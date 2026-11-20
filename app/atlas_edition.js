
(() => {
  'use strict';
  const cover = document.getElementById('cover');
  if (cover && !document.body.classList.contains('edition-offline')) {
    // Keep bookmarks from the previous single-page edition working.
    function redirectLegacy() {
      const company = location.hash.match(/^#company-(002507|600298|688188|09992|US)(?:-|$)/);
      const topic = /^#(?:overview|business|forecast|valuation|updates|methods)(?:-|$)/;
      if (company) {
        const fragment = location.hash === '#company-' + company[1] ? '' : location.hash;
        location.replace('/atlas/company/' + company[1] + fragment);
      } else if (topic.test(location.hash)) {
        location.replace('/atlas/compare/' + location.hash);
      }
    }
    redirectLegacy();
    window.addEventListener('hashchange', redirectLegacy);
  }

  const progress = document.querySelector('.reading-progress');
  const stories = [...document.querySelectorAll('[data-story]')].map(article => ({
    article,
    sections: [...article.querySelectorAll('.story-content .segment')],
    toc: [...article.querySelectorAll('.company-outline a')],
  }));
  if (progress && stories.length) {
    let queued = false;
    function update() {
      const marker = Math.min(180, window.innerHeight * .22);
      const story = stories.find(({article}) => {
        const box = article.getBoundingClientRect();
        return box.top <= marker && box.bottom > marker;
      });
      if (!story) {
        progress.style.setProperty('--progress', 0);
        queued = false;
        return;
      }
      const box = story.article.getBoundingClientRect();
      const fraction = Math.max(0, Math.min(1, (marker - box.top) / box.height));
      progress.style.setProperty('--progress', fraction.toFixed(4));
      const current = story.sections.findLast(section => section.getBoundingClientRect().top < marker);
      for (const link of story.toc) {
        if (current && link.hash === '#' + current.id) link.setAttribute('aria-current', 'location');
        else link.removeAttribute('aria-current');
      }
      queued = false;
    }
    function queue() {
      if (queued) return;
      queued = true;
      requestAnimationFrame(update);
    }
    window.addEventListener('scroll', queue, {passive: true});
    window.addEventListener('resize', queue, {passive: true});
    queue();
  }

  const reduce = matchMedia('(prefers-reduced-motion: reduce)');
  for (const figure of document.querySelectorAll('[data-chart]')) {
    const chart = figure.querySelector('.chart');
    for (const button of figure.querySelectorAll('button[data-series]')) {
      button.addEventListener('click', () => {
        if (reduce.matches) return;
        chart.classList.remove('switching');
        requestAnimationFrame(() => requestAnimationFrame(() => {
          chart.classList.add('switching');
        }));
      });
    }
  }
})();
