/**
 * HealthGuard UI Animations
 * Smooth transitions and micro-interactions
 */

document.addEventListener('DOMContentLoaded', function() {
    // Fade in cards on scroll
    const observerOptions = {
        threshold: 0.1,
        rootMargin: '0px 0px -50px 0px'
    };

    const observer = new IntersectionObserver((entries) => {
        entries.forEach(entry => {
            if (entry.isIntersecting) {
                entry.target.classList.add('animate-in');
                observer.unobserve(entry.target);
            }
        });
    }, observerOptions);

    // Observe cards and stat cards
    document.querySelectorAll('.card, .stat-card').forEach(el => {
        el.style.opacity = '0';
        el.style.transform = 'translateY(20px)';
        el.style.transition = 'opacity 0.4s ease, transform 0.4s ease';
        observer.observe(el);
    });

    // Add animate-in class styles
    const style = document.createElement('style');
    style.textContent = `
        .animate-in {
            opacity: 1 !important;
            transform: translateY(0) !important;
        }
    `;
    document.head.appendChild(style);

    // Smooth number counting for stat values
    document.querySelectorAll('.stat-card-value').forEach(el => {
        const text = el.textContent.trim();
        const match = text.match(/^([\d,]+)/);
        if (match) {
            const target = parseInt(match[1].replace(/,/g, ''));
            if (target > 0 && target < 1000000) {
                animateValue(el, 0, target, 1000, text);
            }
        }
    });

    // Button hover effects
    document.querySelectorAll('.btn').forEach(btn => {
        btn.addEventListener('mouseenter', function() {
            this.style.transform = 'translateY(-1px)';
        });
        btn.addEventListener('mouseleave', function() {
            this.style.transform = 'translateY(0)';
        });
    });
});

/**
 * Animate a number from start to end
 */
function animateValue(el, start, end, duration, originalText) {
    const suffix = originalText.replace(/^[\d,]+/, '');
    const startTime = performance.now();

    function update(currentTime) {
        const elapsed = currentTime - startTime;
        const progress = Math.min(elapsed / duration, 1);
        const easeOut = 1 - Math.pow(1 - progress, 3);
        const current = Math.floor(start + (end - start) * easeOut);
        el.textContent = current.toLocaleString() + suffix;

        if (progress < 1) {
            requestAnimationFrame(update);
        }
    }

    requestAnimationFrame(update);
}

/**
 * Loading spinner for forms
 */
document.querySelectorAll('form').forEach(form => {
    form.addEventListener('submit', function() {
        const btn = this.querySelector('button[type="submit"]');
        if (btn && !btn.disabled) {
            const originalText = btn.innerHTML;
            btn.innerHTML = '<span class="spinner-border spinner-border-sm me-2"></span>Loading...';
            btn.disabled = true;

            // Re-enable after 10s in case of error
            setTimeout(() => {
                btn.innerHTML = originalText;
                btn.disabled = false;
            }, 10000);
        }
    });
});
/**
 * Debounce helper - delays function execution until user stops typing
 */
function debounce(func, wait) {
    let timeout;
    return function executedFunction(...args) {
        const later = () => {
            clearTimeout(timeout);
            func(...args);
        };
        clearTimeout(timeout);
        timeout = setTimeout(later, wait);
    };
}

/**
 * Auto-submit search forms after debounce
 */
document.querySelectorAll('.search-box input[type="text"], .search-box input[type="search"]').forEach(input => {
    const form = input.closest('form');
    if (form) {
        input.addEventListener('input', debounce(function() {
            if (input.value.length >= 2 || input.value.length === 0) {
                form.submit();
            }
        }, 500));
    }
});

/**
 * Smooth page transitions
 */
document.querySelectorAll('a[href]:not([target="_blank"]):not([href^="#"]):not([href^="javascript"])').forEach(link => {
    link.addEventListener('click', function(e) {
        const href = this.getAttribute('href');
        if (href && href.startsWith('/') || href.startsWith(window.location.origin)) {
            document.body.style.opacity = '0.97';
            document.body.style.transition = 'opacity 0.15s ease';
        }
    });
});

/**
 * Mobile hamburger menu
 */
document.addEventListener('click', function(e) {
    const navToggle = document.querySelector('.navbar-toggle');
    const navMenu = document.querySelector('.navbar-nav');
    if (navToggle && navMenu && !navToggle.contains(e.target) && !navMenu.contains(e.target)) {
        navMenu.classList.remove('active');
    }
});

/**
 * Staggered card reveal on scroll
 */
document.querySelectorAll('.stats-grid, .grid-auto').forEach(grid => {
    const cards = grid.children;
    Array.from(cards).forEach((card, index) => {
        card.style.opacity = '0';
        card.style.transform = 'translateY(15px)';
        card.style.transition = `opacity 0.4s ease ${index * 0.08}s, transform 0.4s ease ${index * 0.08}s`;
    });

    const gridObserver = new IntersectionObserver((entries) => {
        entries.forEach(entry => {
            if (entry.isIntersecting) {
                Array.from(entry.target.children).forEach(card => {
                    card.style.opacity = '1';
                    card.style.transform = 'translateY(0)';
                });
                gridObserver.unobserve(entry.target);
            }
        });
    }, { threshold: 0.1 });

    gridObserver.observe(grid);
});

/**
 * Animate progress bars when they come into view
 */
const progressObserver = new IntersectionObserver((entries) => {
    entries.forEach(entry => {
        if (entry.isIntersecting) {
            const bar = entry.target;
            const targetWidth = bar.style.width;
            bar.style.width = '0%';
            bar.style.transition = 'width 0.8s ease-out';
            requestAnimationFrame(() => {
                bar.style.width = targetWidth;
            });
            progressObserver.unobserve(bar);
        }
    });
}, { threshold: 0.1 });

document.querySelectorAll('[style*="width:"][style*="height: 100%"]').forEach(bar => {
    if (bar.parentElement && bar.parentElement.style.overflow === 'hidden') {
        progressObserver.observe(bar);
    }
});

/**
 * Add shadow to navbar on scroll
 */
const navbar = document.querySelector('.navbar');
if (navbar) {
    window.addEventListener('scroll', function() {
        if (window.scrollY > 10) {
            navbar.style.boxShadow = '0 4px 12px rgba(0,0,0,0.1)';
        } else {
            navbar.style.boxShadow = 'var(--shadow-sm)';
        }
    }, { passive: true });
}
