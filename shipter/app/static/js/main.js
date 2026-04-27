// Shipter Main JavaScript with Anime.js

document.addEventListener('DOMContentLoaded', function() {
    // Initialize anime.js background particles
    initBackgroundParticles();
    
    // Initialize UI animations
    initUIAnimations();
    
    // Initialize scroll reveal animations
    initScrollReveal();
    
    // Auto-dismiss flash messages after 5 seconds with anime.js
    const flashes = document.querySelectorAll('.flash');
    flashes.forEach((flash, index) => {
        setTimeout(() => {
            anime({
                targets: flash,
                opacity: 0,
                translateX: 100,
                duration: 400,
                easing: 'easeInQuad',
                complete: () => flash.remove()
            });
        }, 5000 + index * 500);
    });

    // Smooth scroll for anchor links with anime.js
    document.querySelectorAll('a[href^="#"]').forEach(anchor => {
        anchor.addEventListener('click', function(e) {
            e.preventDefault();
            const target = document.querySelector(this.getAttribute('href'));
            if (target) {
                anime({
                    targets: document.documentElement,
                    scrollTop: target.offsetTop - 72,
                    duration: 800,
                    easing: 'easeInOutQuad'
                });
            }
        });
    });

    // Form validation enhancement
    const forms = document.querySelectorAll('form[data-validate]');
    forms.forEach(form => {
        form.addEventListener('submit', function(e) {
            const inputs = form.querySelectorAll('[required]');
            let valid = true;
            
            inputs.forEach(input => {
                if (!input.value.trim()) {
                    valid = false;
                    input.classList.add('error');
                } else {
                    input.classList.remove('error');
                }
            });
            
            if (!valid) {
                e.preventDefault();
            }
        });
    });

    // Copy to clipboard functionality
    document.querySelectorAll('[data-copy]').forEach(btn => {
        btn.addEventListener('click', function() {
            const text = this.getAttribute('data-copy');
            navigator.clipboard.writeText(text).then(() => {
                const originalText = this.textContent;
                this.textContent = 'Скопировано!';
                
                // Animate button
                anime({
                    targets: this,
                    scale: [1, 1.1, 1],
                    duration: 300,
                    easing: 'easeOutQuad'
                });
                
                setTimeout(() => {
                    this.textContent = originalText;
                }, 2000);
            });
        });
    });

    // Confirm delete actions
    document.querySelectorAll('[data-confirm]').forEach(btn => {
        btn.addEventListener('click', function(e) {
            const message = this.getAttribute('data-confirm') || 'Вы уверены?';
            if (!confirm(message)) {
                e.preventDefault();
            }
        });
    });

    // Add ripple effect to buttons
    document.querySelectorAll('.btn').forEach(btn => {
        btn.addEventListener('click', function(e) {
            const rect = btn.getBoundingClientRect();
            const x = e.clientX - rect.left;
            const y = e.clientY - rect.top;
            
            const ripple = document.createElement('span');
            ripple.className = 'ripple';
            ripple.style.cssText = `
                position: absolute;
                background: rgba(255, 255, 255, 0.3);
                border-radius: 50%;
                transform: scale(0);
                left: ${x}px;
                top: ${y}px;
                width: 100px;
                height: 100px;
                margin-left: -50px;
                margin-top: -50px;
                pointer-events: none;
            `;
            
            btn.style.position = 'relative';
            btn.style.overflow = 'hidden';
            btn.appendChild(ripple);
            
            anime({
                targets: ripple,
                scale: 2,
                opacity: 0,
                duration: 600,
                easing: 'easeOutQuad',
                complete: () => ripple.remove()
            });
        });
    });

    console.log('Shipter initialized with Anime.js');
});

// Background Particles with Anime.js
function initBackgroundParticles() {
    const bg = document.querySelector('.animated-bg');
    if (!bg) return;
    
    // Clear existing particles
    bg.innerHTML = '';
    
    // Create floating particles
    for (let i = 0; i < 30; i++) {
        const particle = document.createElement('div');
        particle.className = 'bg-particle';
        const size = Math.random() * 6 + 2;
        particle.style.cssText = `
            position: absolute;
            width: ${size}px;
            height: ${size}px;
            background: radial-gradient(circle, rgba(108, 99, 255, ${Math.random() * 0.4 + 0.2}) 0%, transparent 70%);
            border-radius: 50%;
            left: ${Math.random() * 100}%;
            top: ${Math.random() * 100}%;
            animation-duration: ${Math.random() * 10 + 10}s;
            animation-delay: ${Math.random() * 5}s;
        `;
        bg.appendChild(particle);
    }
}

// UI Animations with Anime.js
function initUIAnimations() {
    // Animate cards on page load with staggered effect
    const cards = document.querySelectorAll('.card, .pricing-card, .pain-card, .testimonial-card, .step');
    if (cards.length > 0) {
        anime({
            targets: cards,
            opacity: [0, 1],
            translateY: [40, 0],
            scale: [0.95, 1],
            delay: anime.stagger(120, {start: 100}),
            duration: 800,
            easing: 'easeOutCubic'
        });
    }
    
    // Animate hero title with glow effect
    const heroTitle = document.querySelector('.hero-title');
    if (heroTitle) {
        anime({
            targets: '.hero-title .text-gradient',
            opacity: [0.7, 1, 0.7],
            duration: 3000,
            easing: 'easeInOutSine',
            loop: true
        });
    }
    
    // Animate buttons on hover with spring effect
    const buttons = document.querySelectorAll('.btn');
    buttons.forEach(btn => {
        btn.addEventListener('mouseenter', () => {
            anime({
                targets: btn,
                scale: 1.08,
                duration: 300,
                easing: 'easeOutQuad'
            });
        });
        
        btn.addEventListener('mouseleave', () => {
            anime({
                targets: btn,
                scale: 1,
                duration: 300,
                easing: 'easeOutQuad'
            });
        });
    });
    
    // Animate navigation links with underline effect
    const navLinks = document.querySelectorAll('.nav-link');
    navLinks.forEach(link => {
        link.addEventListener('mouseenter', () => {
            anime({
                targets: link,
                color: '#F0F0FF',
                duration: 200,
                easing: 'easeOutQuad'
            });
        });
        
        link.addEventListener('mouseleave', () => {
            anime({
                targets: link,
                color: '#8B8BA8',
                duration: 200,
                easing: 'easeOutQuad'
            });
        });
    });
    
    // Animate pricing cards popular badge pulse
    const popularBadge = document.querySelector('.popular-badge');
    if (popularBadge) {
        anime({
            targets: popularBadge,
            scale: [1, 1.05, 1],
            duration: 2000,
            easing: 'easeInOutSine',
            loop: true
        });
    }
    
    // Animate step numbers rotation
    const stepNumbers = document.querySelectorAll('.step-number');
    stepNumbers.forEach((num, index) => {
        anime({
            targets: num,
            rotate: [0, 360],
            duration: 20000,
            easing: 'linear',
            loop: true,
            delay: index * 2000
        });
    });
}

// Scroll Reveal Animation with Intersection Observer
function initScrollReveal() {
    const observerOptions = {
        threshold: 0.1,
        rootMargin: '0px 0px -80px 0px'
    };
    
    const revealObserver = new IntersectionObserver((entries) => {
        entries.forEach(entry => {
            if (entry.isIntersecting) {
                const element = entry.target;
                element.classList.add('revealed');
                
                // Trigger anime.js animation
                anime({
                    targets: element,
                    opacity: [0, 1],
                    translateY: [50, 0],
                    duration: 800,
                    easing: 'easeOutCubic'
                });
                
                revealObserver.unobserve(element);
            }
        });
    }, observerOptions);
    
    // Observe elements
    document.querySelectorAll('.section-title, .pain-card, .step, .pricing-card, .testimonial-card, .faq-item').forEach(el => {
        el.style.opacity = '0';
        el.style.transform = 'translateY(50px)';
        revealObserver.observe(el);
    });
}

// HTMX event handlers
document.body.addEventListener('htmx:beforeRequest', function() {
    // Show loading state
    const submitBtn = document.querySelector('button[type="submit"]');
    if (submitBtn) {
        submitBtn.disabled = true;
        submitBtn.innerHTML = '<span class="loading">Загрузка...</span>';
    }
});

document.body.addEventListener('htmx:afterRequest', function() {
    // Restore button state
    const submitBtn = document.querySelector('button[type="submit"]');
    if (submitBtn) {
        submitBtn.disabled = false;
        submitBtn.innerHTML = submitBtn.dataset.original || submitBtn.innerHTML;
    }
});

// Enhanced counter animation for stats
function animateCounter(element, target, duration = 2000) {
    const start = 0;
    const increment = target / (duration / 16);
    let current = start;
    
    const timer = setInterval(() => {
        current += increment;
        if (current >= target) {
            current = target;
            clearInterval(timer);
        }
        element.textContent = Math.floor(current);
    }, 16);
}

// Parallax effect for hero section
window.addEventListener('scroll', function() {
    const scrolled = window.pageYOffset;
    const parallaxElements = document.querySelectorAll('.parallax');
    
    parallaxElements.forEach(el => {
        const speed = el.dataset.speed || 0.5;
        el.style.transform = `translateY(${scrolled * speed}px)`;
    });
});
