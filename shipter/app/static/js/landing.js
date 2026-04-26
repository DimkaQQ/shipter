// Landing Page JavaScript

document.addEventListener('DOMContentLoaded', function() {
    // Initialize hero canvas animation
    initHeroCanvas();
    
    // Initialize typewriter effect
    initTypewriter();
    
    // Initialize tab switching
    initTabs();
    
    // Initialize scroll animations
    initScrollAnimations();
});

// Hero Canvas Animation - Animated Grid
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
            this.vx = (Math.random() - 0.5) * 0.5;
            this.vy = (Math.random() - 0.5) * 0.5;
            this.size = Math.random() * 2 + 1;
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
            ctx.fillStyle = 'rgba(108, 99, 255, 0.3)';
            ctx.fill();
        }
    }
    
    function init() {
        resize();
        particles = [];
        for (let i = 0; i < 50; i++) {
            particles.push(new Particle());
        }
    }
    
    function animate() {
        ctx.clearRect(0, 0, width, height);
        
        // Update and draw particles
        particles.forEach(p => {
            p.update();
            p.draw();
        });
        
        // Draw connections
        ctx.strokeStyle = 'rgba(108, 99, 255, 0.1)';
        ctx.lineWidth = 1;
        for (let i = 0; i < particles.length; i++) {
            for (let j = i + 1; j < particles.length; j++) {
                const dx = particles[i].x - particles[j].x;
                const dy = particles[i].y - particles[j].y;
                const dist = Math.sqrt(dx * dx + dy * dy);
                
                if (dist < 150) {
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

// Tab Switching
function initTabs() {
    const tabBtns = document.querySelectorAll('.tab-btn');
    
    tabBtns.forEach(btn => {
        btn.addEventListener('click', function() {
            if (isTyping) return;
            
            const tab = this.dataset.tab;
            
            // Update active state
            tabBtns.forEach(b => b.classList.remove('active'));
            this.classList.add('active');
            
            // Type new text
            if (window.typeTypewriterText && window.typewriterTexts[tab]) {
                window.typeTypewriterText(window.typewriterTexts[tab]);
            }
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
                observer.unobserve(entry.target);
            }
        });
    }, observerOptions);
    
    // Observe sections
    document.querySelectorAll('.pain-card, .step, .pricing-card, .testimonial-card, .faq-item').forEach(el => {
        el.style.opacity = '0';
        el.style.transform = 'translateY(30px)';
        el.style.transition = 'opacity 0.6s ease, transform 0.6s ease';
        observer.observe(el);
    });
    
    // Add visible styles
    const style = document.createElement('style');
    style.textContent = `
        .pain-card.visible,
        .step.visible,
        .pricing-card.visible,
        .testimonial-card.visible,
        .faq-item.visible {
            opacity: 1 !important;
            transform: translateY(0) !important;
        }
    `;
    document.head.appendChild(style);
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
