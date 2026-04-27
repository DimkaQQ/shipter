#!/usr/bin/env python3
"""Shipter Application Entry Point."""

from app import create_app
from app.extensions import db, scheduler
from app.models import User, Project, DistributionPlan, GeneratedContent, Subscription, ActionTask
from app.services.trial_service import init_scheduler
import click
import os
import click

app = create_app()

@app.cli.command('init-db')
def init_db():
    """Initialize the database."""
    db.create_all()
    print('Database initialized.')

@app.cli.command('create-admin')
@click.argument('email')
@click.argument('password')
def create_admin(email, password):
    """Create an admin user."""
    user = User.create_with_trial(email=email, password=password, name='Admin')
    user.email_verified = True
    db.session.add(user)
    db.session.commit()
    print(f'Admin user {email} created.')

if __name__ == '__main__':
    # Initialize scheduler for background tasks
    init_scheduler()
    
    # Run the application
    port = int(os.environ.get('PORT', 5000))
    debug = os.environ.get('FLASK_ENV', 'production') == 'development'
    app.run(host='0.0.0.0', port=port, debug=debug)
