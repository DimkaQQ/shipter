from flask import Blueprint, render_template, redirect, url_for, g, Response
from app.config import Config

public_bp = Blueprint('public', __name__)

@public_bp.route('/')
def landing():
    if g.current_user:
        return redirect(url_for('dashboard.index'))
    return render_template('public/landing.html')

@public_bp.route('/pricing')
def pricing():
    return render_template('public/pricing.html')

@public_bp.route('/about')
def about():
    return render_template('public/about.html')

@public_bp.route('/features')
def features():
    return render_template('public/features.html')

@public_bp.route('/privacy')
def privacy():
    return render_template('legal/privacy.html')

@public_bp.route('/terms')
def terms():
    return render_template('legal/terms.html')

@public_bp.route('/robots.txt')
def robots_txt():
    lines = [
        'User-agent: *',
        'Allow: /$',
        'Allow: /pricing$',
        'Allow: /features$',
        'Allow: /about$',
        'Allow: /privacy$',
        'Allow: /terms$',
        'Disallow: /dashboard',
        'Disallow: /projects',
        'Disallow: /ai',
        'Disallow: /billing',
        'Disallow: /integrations',
        'Disallow: /subscribers',
        'Disallow: /meta-ads',
        'Disallow: /settings',
        'Disallow: /auth',
        f'Sitemap: {Config.APP_URL}/sitemap.xml',
    ]
    return Response('\n'.join(lines) + '\n', mimetype='text/plain')

@public_bp.route('/sitemap.xml')
def sitemap_xml():
    pages = ['landing', 'pricing', 'features', 'about', 'privacy', 'terms']
    urls = ''.join(
        f'<url><loc>{Config.APP_URL}{url_for(f"public.{name}")}</loc></url>'
        for name in pages
    )
    xml = f'<?xml version="1.0" encoding="UTF-8"?>' \
          f'<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">{urls}</urlset>'
    return Response(xml, mimetype='application/xml')
