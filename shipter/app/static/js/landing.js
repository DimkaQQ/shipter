// Landing Page - Apple Style with Anime.js

document.addEventListener('DOMContentLoaded', function() {
    // Add animated background orbs
    addAnimatedBackground();
    
    // Initialize hero canvas animation
    initHeroCanvas();
    
    // Initialize typewriter effect
    initTypewriter();
    
    // Initialize tab switching
    initTabs();
    
    // Initialize scroll animations
    initScrollAnimations();
    
    // Animate hero elements with Anime.js
    animateHeroElements();
    
    // Simulate AI demo loading - FIXED: no infinite loop
    simulateAILoading();
});

// Add animated background orbs to body
function addAnimatedBackground() {
    const orbsContainer = document.createElement('div');
    orbsContainer.className = 'animated-bg-orbs';
    orbsContainer.innerHTML = `
        <div class="orb orb-1"></div>
        <div class="orb orb-2"></div>
        <div class="orb orb-3"></div>
    `;
    document.body.insertBefore(orbsContainer, document.body.firstChild);
}

// Simulate AI Demo Loading - Fixed version (runs once, no infinite loop)
function simulateAILoading() {
    const demoCard = document.getElementById('ai-demo-card');
    const statusEl = document.getElementById('demo-status');
    const demoContent = document.querySelector('.demo-content');
    
    if (!demoCard || !statusEl) return;
    
    // Remove any existing result to avoid duplicates
    const existingResult = demoCard.querySelector('.demo-result');
    if (existingResult) {
        existingResult.remove();
    }
    
    // Reset loaded state
    demoCard.classList.remove('loaded');
    statusEl.textContent = 'Загрузка...';
    statusEl.classList.add('loading');
    
    // Show skeleton, hide result
    if (demoContent) {
        demoContent.style.display = 'block';
    }
    
    // After 1.5 seconds, show result ONCE
    setTimeout(() => {
        // Update status
        statusEl.textContent = 'Готово ✓';
        statusEl.classList.remove('loading');
        
        // Add loaded class to card
        demoCard.classList.add('loaded');
        
        // Hide skeleton lines
        if (demoContent) {
            demoContent.style.display = 'none';
        }
        
        // Create result content only if it doesn't exist
        if (!demoCard.querySelector('.demo-result')) {
            const resultContent = document.createElement('div');
            resultContent.className = 'demo-result';
            resultContent.innerHTML = `
                <p style="color: var(--apple-accent); font-weight: 600; margin-bottom: 12px;">
                    🎯 Анализ ниши completed
                </p>
                <p style="color: var(--apple-text-secondary); line-height: 1.7;">
                    Рынок цифровых продуктов растёт на 20% ежегодно.<br>
                    Основные барьеры — маркетинг и доверие аудитории.
                </p>
            `;
            demoCard.appendChild(resultContent);
            
            // Animate result with anime.js
            anime({
                targets: '.demo-result',
                opacity: [0, 1],
                translateY: [20, 0],
                duration: 500,
                easing: 'easeOutCubic'
            });
        }
    }, 1500);
}

// Animate Hero Elements with Anime.js
function animateHeroElements() {
    const timeline = anime.timeline({
        easing: 'easeOutCubic',
        duration: 800
    });
    
    timeline
    .add({
        targets: '.hero-title',
        opacity: [0, 1],
        translateY: [40, 0],
        delay: 100
    })
    .add({
        targets: '.hero-subtitle',
        opacity: [0, 1],
        translateY: [40, 0]
    }, '-=600')
    .add({
        targets: '.hero-cta',
        opacity: [0, 1],
        translateY: [40, 0]
    }, '-=600')
    .add({
        targets: '.hero-demo',
        opacity: [0, 1],
        scale: [0.95, 1]
    }, '-=600');
}

// Hero Canvas Animation - Smooth Particles
function initHeroCanvas() {
    const canvas = document.getElementById('hero-canvas');
    if (!canvas) return;
    
    const ctx = canvas.getContext('2d');
    let width, height;
    let particles = [];
    
    function resize() {
        width = canvas.width = window.innerWidth;
        height = canvas.height = window.innerHeight;
    }
    
    class Particle {
        constructor() {
            this.x = Math.random() * width;
            this.y = Math.random() * height;
            this.vx = (Math.random() - 0.5) * 0.3;
            this.vy = (Math.random() - 0.5) * 0.3;
            this.size = Math.random() * 2 + 1;
            this.opacity = Math.random() * 0.5 + 0.2;
        }
        
        update() {
            this.x += this.vx;
            this.y += this.vy;
            
            if (this.x < 0 || this.x > width) this.vx *= -1;
            if (this.y < 0 || this.y > height) this.vy *= -1;
        }
        
        draw() {
            ctx.beginPath();
            ctx.arc(this.x, this.y, this.size, 0, Math.PI * 2);
            ctx.fillStyle = `rgba(41, 151, 255, ${this.opacity})`;
            ctx.fill();
        }
    }
    
    function init() {
        resize();
        particles = [];
        for (let i = 0; i < 60; i++) {
            particles.push(new Particle());
        }
    }
    
    function animate() {
        ctx.clearRect(0, 0, width, height);
        
        particles.forEach(p => {
            p.update();
            p.draw();
        });
        
        // Draw connections
        for (let i = 0; i < particles.length; i++) {
            for (let j = i + 1; j < particles.length; j++) {
                const dx = particles[i].x - particles[j].x;
                const dy = particles[i].y - particles[j].y;
                const dist = Math.sqrt(dx * dx + dy * dy);
                
                if (dist < 150) {
                    const opacity = (1 - dist / 150) * 0.15;
                    ctx.strokeStyle = `rgba(41, 151, 255, ${opacity})`;
                    ctx.lineWidth = 1;
                    ctx.beginPath();
                    ctx.moveTo(particles[i].x, particles[i].y);
                    ctx.lineTo(particles[j].x, particles[j].y);
                    ctx.stroke();
                }
            }
        }
        
        requestAnimationFrame(animate);
    }
    
    window.addEventListener('resize', () => {
        resize();
        init();
    });
    
    init();
    animate();
}

// Typewriter Effect
function initTypewriter() {
    const textElement = document.getElementById('typewriter-text');
    if (!textElement) return;
    
    const texts = {
        niche: '🎯 Анализ ниши:\n\nРынок цифровых продуктов растёт на 20% ежегодно. Ваша ниша перспективна но конкурентна. Основные барьеры входа — маркетинг и доверие аудитории.',
        competitors: '🏆 Конкуренты:\n\n• Competitor A: Сильный бренд, но дорого\n• Competitor B: Дёшево, но мало функций\n• Competitor C: Хороший баланс цены и качества',
        strategy: '📅 Стратегия дистрибуции:\n\nНеделя 1: Подготовка контента и соцсетей\nНеделя 2: Запуск в Product Hunt\nНеделя 3: Outreach в LinkedIn\nНеделя 4: Анализ и оптимизация',
        content: '✍️ Пример контента:\n\n🚀 Запускаем новый продукт!\n\nМы создали решение которое поможет вам сэкономить время и увеличить продажи.\n\n✅ Автоматизация процессов\n✅ Простая интеграция\n\nПопробуйте бесплатно →'
    };
    
    let currentTab = 'niche';
    let isTyping = false;
    
    function typeText(text, callback) {
        isTyping = true;
        textElement.textContent = '';
        let i = 0;
        
        function type() {
            if (i < text.length) {
                textElement.textContent += text.charAt(i);
                i++;
                setTimeout(type, 20);
            } else {
                isTyping = false;
                if (callback) callback();
            }
        }
        
        type();
    }
    
    // Initial type
    typeText(texts.niche);
    
    // Store for tab switching
    window.typewriterTexts = texts;
    window.typeTypewriterText = typeText;
}

// Tab Switching with smooth transition
function initTabs() {
    const tabBtns = document.querySelectorAll('.tab-btn');
    
    tabBtns.forEach(btn => {
        btn.addEventListener('click', function() {
            const tab = this.dataset.tab;
            
            // Update active state
            tabBtns.forEach(b => b.classList.remove('active'));
            this.classList.add('active');
            
            // Fade out, type new text, fade in
            const outputEl = document.getElementById('typewriter-text');
            anime({
                targets: outputEl,
                opacity: [1, 0],
                duration: 200,
                easing: 'linear',
                complete: function() {
                    if (window.typeTypewriterText && window.typewriterTexts[tab]) {
                        window.typeTypewriterText(window.typewriterTexts[tab]);
                        anime({
                            targets: outputEl,
                            opacity: [0, 1],
                            duration: 300,
                            easing: 'easeOutCubic'
                        });
                    }
                }
            });
        });
    });
}

// Scroll Animations with Intersection Observer
function initScrollAnimations() {
    const observerOptions = {
        threshold: 0.1,
        rootMargin: '0px 0px -50px 0px'
    };
    
    const observer = new IntersectionObserver((entries) => {
        entries.forEach(entry => {
            if (entry.isIntersecting) {
                entry.target.classList.add('visible');
                
                // Trigger anime.js animation
                if (entry.target.classList.contains('pain-card') || 
                    entry.target.classList.contains('pricing-card') ||
                    entry.target.classList.contains('testimonial-card')) {
                    anime({
                        targets: entry.target,
                        opacity: [0, 1],
                        translateY: [40, 0],
                        scale: [0.97, 1],
                        duration: 600,
                        easing: 'easeOutCubic'
                    });
                } else if (entry.target.classList.contains('step')) {
                    anime({
                        targets: entry.target,
                        opacity: [0, 1],
                        translateX: [-60, 0],
                        duration: 700,
                        easing: 'easeOutCubic'
                    });
                } else if (entry.target.classList.contains('faq-item')) {
                    anime({
                        targets: entry.target,
                        opacity: [0, 1],
                        translateY: [30, 0],
                        duration: 500,
                        easing: 'easeOutCubic'
                    });
                }
                
                observer.unobserve(entry.target);
            }
        });
    }, observerOptions);
    
    // Observe elements
    document.querySelectorAll('.pain-card, .step, .pricing-card, .testimonial-card, .faq-item').forEach(el => {
        el.style.opacity = '0';
        el.style.transform = 'translateY(40px)';
        el.style.transition = 'none';
        observer.observe(el);
    });
}

// Smooth scroll to section
document.querySelectorAll('a[href^="#"]').forEach(anchor => {
    anchor.addEventListener('click', function(e) {
        e.preventDefault();
        const target = document.querySelector(this.getAttribute('href'));
        if (target) {
            target.scrollIntoView({ behavior: 'smooth', block: 'start' });
        }
    });
});
