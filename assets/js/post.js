/* Post reading affordances: contents rail, code chrome, figure zoom.
   No dependencies. Every enhancement degrades to the unscripted page. */
(function () {
  'use strict';

  var body = document.querySelector('.post-body');
  if (!body) return;

  var reduceMotion = window.matchMedia('(prefers-reduced-motion: reduce)').matches;

  /* ---- 1. contents: one inline list, mirrored into a fixed rail ---- */

  function slug(text) {
    return text.trim().toLowerCase().replace(/[^\w]+/g, '-').replace(/(^-|-$)/g, '');
  }

  function buildContents() {
    var headings = [].slice.call(body.querySelectorAll('h2, h3'));
    var majors = headings.filter(function (h) { return h.tagName === 'H2'; });
    if (majors.length < 3) return null;

    headings.forEach(function (h) {
      if (!h.id) h.id = slug(h.textContent);
    });

    // kramdown's `{:toc}` already emits #markdown-toc for some posts; reuse it
    // as the inline copy so we never render two lists of the same thing.
    var inline = document.getElementById('markdown-toc');
    if (!inline) {
      inline = document.createElement('ul');
      inline.id = 'markdown-toc';
      headings.forEach(function (h) {
        var li = document.createElement('li');
        if (h.tagName === 'H3') li.className = 'toc-sub';
        var a = document.createElement('a');
        a.href = '#' + h.id;
        a.textContent = h.textContent;
        li.appendChild(a);
        inline.appendChild(li);
      });
      body.insertBefore(inline, body.firstChild);
    }

    var rail = document.createElement('nav');
    rail.className = 'toc-rail';
    rail.setAttribute('aria-label', 'On this page');
    var title = document.createElement('p');
    title.className = 'toc-title';
    title.textContent = 'On this page';
    var list = document.createElement('ul');
    headings.forEach(function (h) {
      var li = document.createElement('li');
      if (h.tagName === 'H3') li.className = 'toc-sub';
      var a = document.createElement('a');
      a.href = '#' + h.id;
      a.textContent = h.textContent;
      li.appendChild(a);
      list.appendChild(li);
    });
    rail.appendChild(title);
    rail.appendChild(list);
    var article = body.closest('.post') || body.parentNode;
    article.appendChild(rail);

    return { headings: headings, rail: rail };
  }

  function spy(contents) {
    if (!contents) return;
    var links = {};
    [].forEach.call(contents.rail.querySelectorAll('a'), function (a) {
      links[a.getAttribute('href').slice(1)] = a;
    });
    var current = null;

    function mark() {
      // The active section is the last heading whose top has passed the
      // reading line a third of the way down the viewport.
      var line = window.innerHeight / 3;
      var active = contents.headings[0];
      for (var i = 0; i < contents.headings.length; i++) {
        if (contents.headings[i].getBoundingClientRect().top <= line) {
          active = contents.headings[i];
        } else break;
      }
      if (active === current) return;
      if (current && links[current.id]) links[current.id].removeAttribute('aria-current');
      current = active;
      if (links[current.id]) links[current.id].setAttribute('aria-current', 'true');
    }

    var ticking = false;
    function onScroll() {
      if (ticking) return;
      ticking = true;
      window.requestAnimationFrame(function () { mark(); ticking = false; });
    }
    window.addEventListener('scroll', onScroll, { passive: true });
    window.addEventListener('resize', onScroll, { passive: true });
    mark();
  }

  spy(buildContents());

  /* ---- 1b. anchor links, so a section can be linked to ---- */

  [].forEach.call(body.querySelectorAll('h2, h3'), function (h) {
    if (!h.id) h.id = slug(h.textContent);
    if (h.querySelector('.h-anchor')) return;
    var a = document.createElement('a');
    a.className = 'h-anchor';
    a.href = '#' + h.id;
    a.textContent = '#';
    a.setAttribute('aria-label', 'Link to this section');
    h.appendChild(a);
  });

  /* ---- 2. code blocks: language label + copy ---- */

  var LANG_NAMES = {
    js: 'javascript', ts: 'typescript', py: 'python', rb: 'ruby',
    sh: 'shell', bash: 'shell', console: 'shell', yml: 'yaml',
    plaintext: 'text', md: 'markdown'
  };

  [].forEach.call(body.querySelectorAll('div.highlighter-rouge, pre'), function (block) {
    if (block.closest('.code-block')) return;

    var pre = block.tagName === 'PRE' ? block : block.querySelector('pre');
    if (!pre) return;

    var match = /(?:^|\s)language-([\w+#-]+)/.exec(block.className);
    var lang = match ? match[1].toLowerCase() : '';
    lang = LANG_NAMES[lang] || lang;

    var wrap = document.createElement('div');
    wrap.className = 'code-block';
    block.parentNode.insertBefore(wrap, block);

    var head = document.createElement('div');
    head.className = 'code-head';

    var label = document.createElement('span');
    label.className = 'code-lang';
    label.textContent = lang;
    head.appendChild(label);

    var button = document.createElement('button');
    button.type = 'button';
    button.className = 'code-copy';
    button.textContent = 'copy';
    button.setAttribute('aria-label', 'Copy code to clipboard');
    head.appendChild(button);

    wrap.appendChild(head);
    wrap.appendChild(block);

    button.addEventListener('click', function () {
      var code = pre.querySelector('code') || pre;
      var text = code.innerText.replace(/\n$/, '');
      var done = function (ok) {
        button.textContent = ok ? 'copied' : 'failed';
        button.classList.toggle('is-done', ok);
        setTimeout(function () {
          button.textContent = 'copy';
          button.classList.remove('is-done');
        }, 1600);
      };
      if (navigator.clipboard && navigator.clipboard.writeText) {
        navigator.clipboard.writeText(text).then(function () { done(true); }, function () { done(false); });
      } else {
        done(false);
      }
    });
  });

  /* ---- 3. figures: click a diagram to read it full size ---- */

  var zoomable = [].filter.call(body.querySelectorAll('img'), function (img) {
    return !img.classList.contains('hero');
  });
  if (!zoomable.length) return;

  var overlay = null;

  function closeZoom() {
    if (!overlay) return;
    overlay.remove();
    overlay = null;
    document.removeEventListener('keydown', onKey);
    document.body.style.removeProperty('overflow');
  }

  function onKey(event) {
    if (event.key === 'Escape') closeZoom();
  }

  zoomable.forEach(function (img) {
    img.classList.add('zoomable');
    img.setAttribute('role', 'button');
    img.setAttribute('tabindex', '0');
    var open = function () {
      closeZoom();
      overlay = document.createElement('div');
      overlay.className = 'zoom-overlay';
      if (reduceMotion) overlay.classList.add('no-motion');
      overlay.setAttribute('role', 'dialog');
      overlay.setAttribute('aria-modal', 'true');
      overlay.setAttribute('aria-label', img.alt || 'Figure');
      var big = document.createElement('img');
      big.src = img.currentSrc || img.src;
      big.alt = img.alt || '';
      overlay.appendChild(big);
      var caption = img.closest('figure') && img.closest('figure').querySelector('figcaption');
      if (caption) {
        var p = document.createElement('p');
        p.className = 'zoom-caption';
        p.textContent = caption.textContent;
        overlay.appendChild(p);
      }
      overlay.addEventListener('click', closeZoom);
      document.body.appendChild(overlay);
      document.body.style.overflow = 'hidden';
      document.addEventListener('keydown', onKey);
      overlay.focus();
    };
    img.addEventListener('click', open);
    img.addEventListener('keydown', function (event) {
      if (event.key === 'Enter' || event.key === ' ') {
        event.preventDefault();
        open();
      }
    });
  });
})();
