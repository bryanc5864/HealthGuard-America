/**
 * HealthGuard America — Clinical Luxe Animations
 * Orchestrated reveals, tactile micro-interactions, atmospheric effects.
 * Respects prefers-reduced-motion throughout.
 */
(function () {
  'use strict';

  var prefersReducedMotion = window.matchMedia('(prefers-reduced-motion: reduce)').matches;

  /* ============================================
     Scroll Reveal — Staggered cascade
     ============================================ */
  function initScrollReveal() {
    if (prefersReducedMotion) return;

    var observer = new IntersectionObserver(function (entries) {
      entries.forEach(function (entry) {
        if (entry.isIntersecting) {
          entry.target.classList.add('revealed');
          observer.unobserve(entry.target);
        }
      });
    }, { threshold: 0.08, rootMargin: '0px 0px -40px 0px' });

    document.querySelectorAll('.card, .stat-card, .alert, .module-card').forEach(function (el) {
      el.classList.add('reveal-on-scroll');
      observer.observe(el);
    });
  }

  /* ============================================
     Staggered Grid Reveal — Children cascade in
     ============================================ */
  function initStaggeredReveal() {
    if (prefersReducedMotion) return;

    var observer = new IntersectionObserver(function (entries) {
      entries.forEach(function (entry) {
        if (entry.isIntersecting) {
          entry.target.classList.add('stagger-revealed');
          observer.unobserve(entry.target);
        }
      });
    }, { threshold: 0.08 });

    document.querySelectorAll('.stats-grid, .grid-auto, .portal-cards, .module-grid-3').forEach(function (grid) {
      var children = grid.children;
      for (var i = 0; i < children.length; i++) {
        children[i].classList.add('stagger-child');
        children[i].style.transitionDelay = (i * 0.07) + 's';
      }
      observer.observe(grid);
    });
  }

  /* ============================================
     Page Header Parallax — Subtle depth on scroll
     ============================================ */
  function initHeaderParallax() {
    if (prefersReducedMotion) return;

    var header = document.querySelector('.page-header');
    if (!header) return;

    var content = header.querySelector('.page-header-content');
    var headerHeight = header.offsetHeight;
    var ticking = false;

    window.addEventListener('scroll', function () {
      if (!ticking) {
        requestAnimationFrame(function () {
          var scrollY = window.scrollY;
          if (scrollY < headerHeight) {
            var ratio = scrollY / headerHeight;
            // Content fades and rises as you scroll past
            if (content) {
              content.style.opacity = 1 - ratio * 0.6;
              content.style.transform = 'translateY(' + (scrollY * 0.15) + 'px)';
            }
          }
          ticking = false;
        });
        ticking = true;
      }
    }, { passive: true });
  }

  /* ============================================
     Stat Counter — Animate numbers on reveal
     ============================================ */
  function initCountUp() {
    if (prefersReducedMotion) return;

    var observer = new IntersectionObserver(function (entries) {
      entries.forEach(function (entry) {
        if (entry.isIntersecting) {
          var el = entry.target;
          var text = el.textContent.trim();
          var match = text.match(/^[^\d]*([\d,]+)/);
          if (match) {
            var target = parseInt(match[1].replace(/,/g, ''), 10);
            if (target > 0 && target < 1000000) {
              var prefix = text.substring(0, text.indexOf(match[1]));
              var suffix = text.substring(text.indexOf(match[1]) + match[1].length);
              animateValue(el, 0, target, 1200, prefix, suffix);
            }
          }
          observer.unobserve(el);
        }
      });
    }, { threshold: 0.3 });

    document.querySelectorAll('.stat-card-value, .hero-stat-value').forEach(function (el) {
      observer.observe(el);
    });
  }

  function animateValue(el, start, end, duration, prefix, suffix) {
    var startTime = performance.now();
    function update(currentTime) {
      var elapsed = currentTime - startTime;
      var progress = Math.min(elapsed / duration, 1);
      // Smooth ease-out-expo
      var easeOut = 1 - Math.pow(2, -10 * progress);
      var current = Math.floor(start + (end - start) * easeOut);
      el.textContent = prefix + current.toLocaleString() + suffix;
      if (progress < 1) {
        requestAnimationFrame(update);
      }
    }
    requestAnimationFrame(update);
  }

  /* ============================================
     Progress Bars — Animate width on scroll
     ============================================ */
  function initProgressBars() {
    if (prefersReducedMotion) return;

    var observer = new IntersectionObserver(function (entries) {
      entries.forEach(function (entry) {
        if (entry.isIntersecting) {
          var bar = entry.target;
          var targetWidth = bar.style.width;
          bar.style.width = '0%';
          bar.style.transition = 'width 0.9s cubic-bezier(0.22, 1, 0.36, 1)';
          requestAnimationFrame(function () {
            requestAnimationFrame(function () {
              bar.style.width = targetWidth;
            });
          });
          observer.unobserve(bar);
        }
      });
    }, { threshold: 0.1 });

    document.querySelectorAll('.progress-bar, [class*="progress-bar"]').forEach(function (bar) {
      if (bar.style.width) {
        observer.observe(bar);
      }
    });

    // Also catch inline-styled progress bars
    document.querySelectorAll('[style*="width:"][style*="height: 100%"]').forEach(function (bar) {
      if (bar.parentElement && (bar.parentElement.classList.contains('progress') ||
          bar.parentElement.style.overflow === 'hidden')) {
        observer.observe(bar);
      }
    });
  }

  /* ============================================
     Navbar — Glass effect deepens on scroll
     ============================================ */
  function initNavbarScroll() {
    var navbar = document.querySelector('.navbar');
    if (!navbar || navbar.classList.contains('navbar-gov')) return;

    var ticking = false;
    var lastState = false;

    window.addEventListener('scroll', function () {
      if (!ticking) {
        requestAnimationFrame(function () {
          var scrolled = window.scrollY > 20;
          if (scrolled !== lastState) {
            if (scrolled) {
              navbar.classList.add('navbar--scrolled');
            } else {
              navbar.classList.remove('navbar--scrolled');
            }
            lastState = scrolled;
          }
          ticking = false;
        });
        ticking = true;
      }
    }, { passive: true });
  }

  /* ============================================
     Table Row Entrance — Cascade on scroll
     ============================================ */
  function initTableReveal() {
    if (prefersReducedMotion) return;

    var observer = new IntersectionObserver(function (entries) {
      entries.forEach(function (entry) {
        if (entry.isIntersecting) {
          var rows = entry.target.querySelectorAll('tbody tr');
          rows.forEach(function (row, i) {
            row.style.animationDelay = (i * 0.03) + 's';
            row.classList.add('tr-reveal');
          });
          observer.unobserve(entry.target);
        }
      });
    }, { threshold: 0.05 });

    document.querySelectorAll('.table').forEach(function (table) {
      observer.observe(table);
    });
  }

  /* ============================================
     Magnetic Buttons — Subtle follow on hover
     ============================================ */
  function initMagneticButtons() {
    if (prefersReducedMotion) return;

    document.querySelectorAll('.btn-lg, .btn-pricevision, .btn-drugwatch, .btn-foodscore, .portal-card').forEach(function (btn) {
      btn.addEventListener('mousemove', function (e) {
        var rect = btn.getBoundingClientRect();
        var x = e.clientX - rect.left - rect.width / 2;
        var y = e.clientY - rect.top - rect.height / 2;
        btn.style.transform = 'translate(' + (x * 0.08) + 'px, ' + (y * 0.08 - 2) + 'px)';
      });

      btn.addEventListener('mouseleave', function () {
        btn.style.transform = '';
      });
    });
  }

  /* ============================================
     Form Interactions — Focus glow & submit
     ============================================ */
  function initFormInteractions() {
    // Focus ring glow
    document.querySelectorAll('.form-control').forEach(function (input) {
      input.addEventListener('focus', function () {
        var parent = input.closest('.card, .form-group, form');
        if (parent) parent.classList.add('has-focus');
      });
      input.addEventListener('blur', function () {
        var parent = input.closest('.card, .form-group, form');
        if (parent) parent.classList.remove('has-focus');
      });
    });

    // Submit button loading state
    document.querySelectorAll('form').forEach(function (form) {
      form.addEventListener('submit', function () {
        var btn = this.querySelector('button[type="submit"], .btn[type="submit"]');
        if (btn && !btn.disabled) {
          btn.classList.add('btn--loading');
          btn.disabled = true;
          setTimeout(function () {
            btn.classList.remove('btn--loading');
            btn.disabled = false;
          }, 8000);
        }
      });
    });
  }

  /* ============================================
     Search Auto-Submit (debounced)
     ============================================ */
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

  /* ============================================
     Mobile Menu
     ============================================ */
  function initMobileMenu() {
    var toggle = document.querySelector('.navbar-toggle');
    var nav = document.querySelector('.navbar-nav');

    if (toggle && nav) {
      toggle.addEventListener('click', function (e) {
        e.stopPropagation();
        nav.classList.toggle('active');
      });
    }

    document.addEventListener('click', function (e) {
      if (nav && toggle && !toggle.contains(e.target) && !nav.contains(e.target)) {
        nav.classList.remove('active');
      }
    });
  }

  /* ============================================
     Tooltip Auto-Position
     ============================================ */
  function initTooltips() {
    document.querySelectorAll('.tooltip-wrapper').forEach(function (wrapper) {
      var tip = wrapper.querySelector('.tooltip-text');
      if (!tip) return;
      wrapper.addEventListener('mouseenter', function () {
        var rect = tip.getBoundingClientRect();
        if (rect.left < 8) tip.style.left = '0';
        if (rect.right > window.innerWidth - 8) tip.style.left = 'auto';
      });
    });
  }

  /* ============================================
     Badge Pulse — Draw attention to key badges
     ============================================ */
  function initBadgePulse() {
    if (prefersReducedMotion) return;
    document.querySelectorAll('.badge-success, .badge-danger').forEach(function (badge) {
      if (badge.closest('td') || badge.closest('.alert')) {
        badge.classList.add('badge--attention');
      }
    });
  }

  /* ============================================
     Initialize All
     ============================================ */
  document.addEventListener('DOMContentLoaded', function () {
    initScrollReveal();
    initStaggeredReveal();
    initHeaderParallax();
    initCountUp();
    initProgressBars();
    initNavbarScroll();
    initTableReveal();
    initMagneticButtons();
    initFormInteractions();
    initSearchAutoSubmit();
    initMobileMenu();
    initTooltips();
    initBadgePulse();
  });
})();
