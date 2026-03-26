/**
 * HealthGuard UI Animations -- Performance-optimized
 * Uses CSS classes instead of inline styles, consolidated IntersectionObserver,
 * respects prefers-reduced-motion.
 */
(function () {
  'use strict';

  var prefersReducedMotion = window.matchMedia('(prefers-reduced-motion: reduce)').matches;

  /**
   * Scroll-reveal: fade-in cards and stat-cards when they enter the viewport.
   * Uses a single IntersectionObserver for all revealable elements.
   */
  function initScrollReveal() {
    if (prefersReducedMotion) return;

    var observer = new IntersectionObserver(function (entries) {
      entries.forEach(function (entry) {
        if (entry.isIntersecting) {
          entry.target.classList.add('revealed');
          observer.unobserve(entry.target);
        }
      });
    }, { threshold: 0.1, rootMargin: '0px 0px -50px 0px' });

    document.querySelectorAll('.card, .stat-card').forEach(function (el) {
      el.classList.add('reveal-on-scroll');
      observer.observe(el);
    });
  }

  /**
   * Staggered grid reveal: children of .stats-grid and .grid-auto
   * animate in with increasing delay.
   */
  function initStaggeredReveal() {
    if (prefersReducedMotion) return;

    var observer = new IntersectionObserver(function (entries) {
      entries.forEach(function (entry) {
        if (entry.isIntersecting) {
          entry.target.classList.add('stagger-revealed');
          observer.unobserve(entry.target);
        }
      });
    }, { threshold: 0.1 });

    document.querySelectorAll('.stats-grid, .grid-auto').forEach(function (grid) {
      var children = grid.children;
      for (var i = 0; i < children.length; i++) {
        children[i].classList.add('stagger-child');
        children[i].style.transitionDelay = (i * 0.08) + 's';
      }
      observer.observe(grid);
    });
  }

  /**
   * Animate stat numbers counting up when they enter the viewport.
   */
  function initCountUp() {
    if (prefersReducedMotion) return;

    document.querySelectorAll('.stat-card-value').forEach(function (el) {
      var text = el.textContent.trim();
      var match = text.match(/^([\d,]+)/);
      if (match) {
        var target = parseInt(match[1].replace(/,/g, ''), 10);
        if (target > 0 && target < 1000000) {
          var suffix = text.replace(/^[\d,]+/, '');
          animateValue(el, 0, target, 1000, suffix);
        }
      }
    });
  }

  function animateValue(el, start, end, duration, suffix) {
    var startTime = performance.now();
    function update(currentTime) {
      var elapsed = currentTime - startTime;
      var progress = Math.min(elapsed / duration, 1);
      var easeOut = 1 - Math.pow(1 - progress, 3);
      var current = Math.floor(start + (end - start) * easeOut);
      el.textContent = current.toLocaleString() + suffix;
      if (progress < 1) {
        requestAnimationFrame(update);
      }
    }
    requestAnimationFrame(update);
  }

  /**
   * Progress bar animation when bars enter the viewport.
   */
  function initProgressBars() {
    if (prefersReducedMotion) return;

    var observer = new IntersectionObserver(function (entries) {
      entries.forEach(function (entry) {
        if (entry.isIntersecting) {
          var bar = entry.target;
          var targetWidth = bar.style.width;
          bar.style.width = '0%';
          bar.style.transition = 'width 0.8s ease-out';
          requestAnimationFrame(function () {
            bar.style.width = targetWidth;
          });
          observer.unobserve(bar);
        }
      });
    }, { threshold: 0.1 });

    document.querySelectorAll('[style*="width:"][style*="height: 100%"]').forEach(function (bar) {
      if (bar.parentElement && bar.parentElement.style.overflow === 'hidden') {
        observer.observe(bar);
      }
    });
  }

  /**
   * Navbar shadow on scroll -- uses requestAnimationFrame to avoid
   * expensive per-frame style recalculations.
   */
  function initNavbarShadow() {
    var navbar = document.querySelector('.navbar');
    if (!navbar) return;

    var ticking = false;
    var lastScrolled = false;

    window.addEventListener('scroll', function () {
      if (!ticking) {
        requestAnimationFrame(function () {
          var scrolled = window.scrollY > 10;
          if (scrolled !== lastScrolled) {
            navbar.style.boxShadow = scrolled
              ? '0 4px 12px rgba(0,0,0,0.1)'
              : 'var(--shadow-sm)';
            lastScrolled = scrolled;
          }
          ticking = false;
        });
        ticking = true;
      }
    }, { passive: true });
  }

  /**
   * Form submit loading spinner.
   */
  function initFormLoading() {
    document.querySelectorAll('form').forEach(function (form) {
      form.addEventListener('submit', function () {
        var btn = this.querySelector('button[type="submit"]');
        if (btn && !btn.disabled) {
          var originalText = btn.innerHTML;
          btn.innerHTML = '<span class="spinner-border spinner-border-sm me-2"></span>Loading...';
          btn.disabled = true;
          setTimeout(function () {
            btn.innerHTML = originalText;
            btn.disabled = false;
          }, 10000);
        }
      });
    });
  }

  /**
   * Debounced auto-submit for search inputs.
   */
  function initSearchAutoSubmit() {
    function debounce(func, wait) {
      var timeout;
      return function () {
        var args = arguments;
        var context = this;
        clearTimeout(timeout);
        timeout = setTimeout(function () { func.apply(context, args); }, wait);
      };
    }

    document.querySelectorAll('.search-box input[type="text"], .search-box input[type="search"]').forEach(function (input) {
      var form = input.closest('form');
      if (form) {
        input.addEventListener('input', debounce(function () {
          if (input.value.length >= 2 || input.value.length === 0) {
            form.submit();
          }
        }, 500));
      }
    });
  }

  /**
   * Mobile hamburger menu close on outside click.
   */
  function initMobileMenu() {
    document.addEventListener('click', function (e) {
      var navToggle = document.querySelector('.navbar-toggle');
      var navMenu = document.querySelector('.navbar-nav');
      if (navToggle && navMenu && !navToggle.contains(e.target) && !navMenu.contains(e.target)) {
        navMenu.classList.remove('active');
      }
    });
  }

  // Initialize all modules on DOMContentLoaded
  document.addEventListener('DOMContentLoaded', function () {
    initScrollReveal();
    initStaggeredReveal();
    initCountUp();
    initProgressBars();
    initNavbarShadow();
    initFormLoading();
    initSearchAutoSubmit();
    initMobileMenu();
  });
})();
