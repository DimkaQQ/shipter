from flask import Blueprint, render_template

public_bp = Blueprint('public', __name__)

@public_bp.route('/')
def landing():
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
