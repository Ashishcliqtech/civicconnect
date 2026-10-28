"""Flask CLI commands:  flask init-db | create-admin | seed"""
import os
import re
import click
from .extensions import db
from .models import User
from .utils.validators import EMAIL_RE


def register_cli(app):
    @app.cli.command("init-db")
    def init_db():
        """Create tables if they do not exist (safe to run on every start)."""
        db.create_all()
        from .services.seed_service import ensure_reference_data
        ensure_reference_data()
        click.echo("Database ready.")

    @app.cli.command("create-admin")
    @click.option("--email", prompt=True)
    @click.option("--name", prompt="Full name")
    @click.option("--password", envvar="CIVICCONNECT_ADMIN_PASSWORD", prompt=True,
                  hide_input=True, confirmation_prompt=True)
    def create_admin(email, name, password):
        """Bootstrap the first administrator (password is prompted, never stored in Git)."""
        email = email.strip().lower()
        if not EMAIL_RE.match(email):
            raise click.ClickException("Invalid email.")
        if len(password) < 8 or not re.search(r"\d", password) or not re.search(r"[A-Za-z]", password):
            raise click.ClickException("Password needs 8+ characters with letters and numbers.")
        if User.query.filter_by(email=email).first():
            raise click.ClickException("A user with that email already exists.")
        user = User(full_name=name.strip(), email=email, role=User.ROLE_ADMIN)
        user.set_password(password)
        db.session.add(user)
        db.session.commit()
        click.echo(f"Administrator {email} created.")

    @app.cli.command("seed")
    def seed():
        """Add DEMO departments, officers, a demo citizen and sample complaints."""
        from .services.seed_service import seed_demo_data
        seed_demo_data()
        click.echo("Demo data added. All demo accounts use the password printed above.")
