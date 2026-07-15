/* ============================================
   STACKBUILD — JavaScript
   ============================================ */

document.addEventListener('DOMContentLoaded', () => {
    initNavbar();
    initScrollAnimations();
    initSmoothScroll();
    initCountUp();
    initParallaxOrbs();
});

/* ---------- Navbar ---------- */
function initNavbar() {
    const navbar = document.getElementById('navbar');
    const hamburger = document.getElementById('nav-hamburger');
    const mobileNav = document.getElementById('nav-mobile');

    window.addEventListener('scroll', () => {
        if (window.scrollY > 60) {
            navbar.classList.add('scrolled');
        } else {
            navbar.classList.remove('scrolled');
        }
    }, { passive: true });

    if (hamburger && mobileNav) {
        hamburger.addEventListener('click', () => {
            hamburger.classList.toggle('active');
            mobileNav.classList.toggle('active');
            document.body.style.overflow = mobileNav.classList.contains('active') ? 'hidden' : '';
        });

        mobileNav.querySelectorAll('a').forEach(link => {
            link.addEventListener('click', () => {
                hamburger.classList.remove('active');
                mobileNav.classList.remove('active');
                document.body.style.overflow = '';
            });
        });
    }
}

/* ---------- Scroll Animations (IntersectionObserver) ---------- */
function initScrollAnimations() {
    const observer = new IntersectionObserver((entries) => {
        entries.forEach(entry => {
            if (entry.isIntersecting) {
                entry.target.classList.add('visible');
                observer.unobserve(entry.target);
            }
        });
    }, { rootMargin: '0px 0px -60px 0px', threshold: 0.1 });

    // Process steps
    document.querySelectorAll('.process-step').forEach((el, i) => {
        el.style.transitionDelay = `${i * 0.12}s`;
        observer.observe(el);
    });

    // Service cards (stagger)
    const servicesGrid = document.querySelector('.services-grid');
    if (servicesGrid) {
        servicesGrid.classList.add('stagger');
        observer.observe(servicesGrid);
    }

    // Why cards (stagger)
    const whyGrid = document.querySelector('.why-grid');
    if (whyGrid) {
        whyGrid.classList.add('stagger');
        observer.observe(whyGrid);
    }

    // Project cards
    document.querySelectorAll('.project-card').forEach((el, i) => {
        el.classList.add('animate-in');
        el.style.transitionDelay = `${i * 0.1}s`;
        observer.observe(el);
    });

    // Testimonial cards
    const testGrid = document.querySelector('.testimonials-grid');
    if (testGrid) {
        testGrid.classList.add('stagger');
        observer.observe(testGrid);
    }

    // Section headers
    document.querySelectorAll('.section-header').forEach(el => {
        el.classList.add('animate-in');
        observer.observe(el);
    });

    // CTA sections
    document.querySelectorAll('.cta-content').forEach(el => {
        el.classList.add('animate-in');
        observer.observe(el);
    });

    // Community section pieces
    document.querySelectorAll('.community-content, .community-cards').forEach(el => {
        el.classList.add('animate-in');
        observer.observe(el);
    });
}

/* ---------- Smooth Scroll ---------- */
function initSmoothScroll() {
    document.querySelectorAll('a[href^="#"]').forEach(anchor => {
        anchor.addEventListener('click', function (e) {
            const href = this.getAttribute('href');
            if (href === '#') return;
            e.preventDefault();
            const target = document.querySelector(href);
            if (target) {
                const navH = document.getElementById('navbar')?.offsetHeight || 72;
                window.scrollTo({
                    top: target.getBoundingClientRect().top + window.scrollY - navH - 20,
                    behavior: 'smooth'
                });
            }
        });
    });
}

/* ---------- Count-Up Animation for Stats ---------- */
function initCountUp() {
    const statNumbers = document.querySelectorAll('.stat-number[data-target]');
    if (!statNumbers.length) return;

    const observer = new IntersectionObserver((entries) => {
        entries.forEach(entry => {
            if (entry.isIntersecting) {
                const el = entry.target;
                const target = parseInt(el.getAttribute('data-target'), 10);
                animateNumber(el, 0, target, 1800);
                observer.unobserve(el);
            }
        });
    }, { threshold: 0.5 });

    statNumbers.forEach(el => observer.observe(el));
}

function animateNumber(el, start, end, duration) {
    const startTime = performance.now();
    const easeOutQuart = t => 1 - Math.pow(1 - t, 4);

    function update(currentTime) {
        const elapsed = currentTime - startTime;
        const progress = Math.min(elapsed / duration, 1);
        const easedProgress = easeOutQuart(progress);
        const current = Math.round(start + (end - start) * easedProgress);
        el.textContent = current;
        if (progress < 1) requestAnimationFrame(update);
    }
    requestAnimationFrame(update);
}

/* ---------- Parallax Orbs on Mouse Move ---------- */
function initParallaxOrbs() {
    const orbs = document.querySelectorAll('.hero-orb');
    if (!orbs.length) return;

    let ticking = false;
    window.addEventListener('mousemove', (e) => {
        if (ticking) return;
        ticking = true;
        requestAnimationFrame(() => {
            const x = (e.clientX / window.innerWidth - 0.5) * 2;
            const y = (e.clientY / window.innerHeight - 0.5) * 2;
            orbs.forEach((orb, i) => {
                const speed = (i + 1) * 10;
                orb.style.transform = `translate(${x * speed}px, ${y * speed}px)`;
            });
            ticking = false;
        });
    }, { passive: true });
}
