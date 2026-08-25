/* KaTeX bootstrap. Loaded `defer` after katex + auto-render, so deferred
   script ordering guarantees renderMathInElement is already defined.

   kramdown has already turned every `$$…$$` in the markdown into `\[…\]`
   (display) or `\(…\)` (inline), so those are the only delimiters we look
   for — a bare `$$` in prose stays prose. */
(function () {
  'use strict';
  if (typeof renderMathInElement !== 'function') return;
  renderMathInElement(document.querySelector('.post-body') || document.body, {
    delimiters: [
      { left: '\\[', right: '\\]', display: true },
      { left: '\\(', right: '\\)', display: false }
    ],
    ignoredTags: ['script', 'noscript', 'style', 'textarea', 'pre', 'code', 'option'],
    ignoredClasses: ['chart'],
    throwOnError: false
  });
})();
