// Shipter Main JavaScript with Anime.js

document.addEventListener('DOMContentLoaded', function() {
    // Initialize anime.js background particles
    initBackgroundParticles();
    
    // Initialize UI animations
    initUIAnimations();
    
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
    
    // Create floating particles
    for (let i = 0; i < 20; i++) {
        const particle = document.createElement('div');
        particle.className = 'bg-particle';
        particle.style.cssText = `
            position: absolute;
            width: ${Math.random() * 4 + 2}px;
            height: ${Math.random() * 4 + 2}px;
            background: rgba(108, 99, 255, ${Math.random() * 0.3 + 0.1});
            border-radius: 50%;
            left: ${Math.random() * 100}%;
            top: ${Math.random() * 100}%;
        `;
        bg.appendChild(particle);
        
        // Animate each particle
        anime({
            targets: particle,
            translateX: () => anime.random(-100, 100),
            translateY: () => anime.random(-100, 100),
            scale: () => anime.random(0.5, 1.5),
            opacity: () => anime.random(0.2, 0.6),
            duration: () => anime.random(3000, 8000),
            easing: 'easeInOutQuad',
            loop: true,
            direction: 'alternate'
        });
    }
}

// UI Animations with Anime.js
function initUIAnimations() {
    // Animate cards on page load
    const cards = document.querySelectorAll('.card');
    if (cards.length > 0) {
        anime({
            targets: cards,
            opacity: [0, 1],
            translateY: [30, 0],
            delay: anime.stagger(100, {start: 200}),
            duration: 600,
            easing: 'easeOutCubic'
        });
    }
    
    // Animate buttons on hover
    const buttons = document.querySelectorAll('.btn');
    buttons.forEach(btn => {
        btn.addEventListener('mouseenter', () => {
            anime({
                targets: btn,
                scale: 1.05,
                duration: 200,
                easing: 'easeOutQuad'
            });
        });
        
        btn.addEventListener('mouseleave', () => {
            anime({
                targets: btn,
                scale: 1,
                duration: 200,
                easing: 'easeOutQuad'
            });
        });
    });
    
    // Animate navigation links
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
