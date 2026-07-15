"""
tests/test_watchlist_routes.py - CineLog

Route tests for watchlist endpoints.
"""

import pytest
from app import create_app, db
from models import User, Film


@pytest.fixture
def app():
    """Create an isolated test app with an in-memory database."""
    app = create_app(config={
        "TESTING": True,
        "SQLALCHEMY_DATABASE_URI": "sqlite:///:memory:",
    })
    with app.app_context():
        db.create_all()
        yield app
        db.session.remove()
        db.drop_all()


@pytest.fixture
def client(app):
    """A Flask test client."""
    return app.test_client()


@pytest.fixture
def sample_user(app):
    """A user to use in route tests."""
    with app.app_context():
        user = User(username="routeuser", email="route@example.com")
        db.session.add(user)
        db.session.commit()
        return user.id


@pytest.fixture
def sample_film(app):
    """A film to use in route tests."""
    with app.app_context():
        film = Film(title="Moonlight", year=2016, genre="Drama")
        db.session.add(film)
        db.session.commit()
        return film.id


def test_add_watchlist_route_accepts_public_false(client, sample_user, sample_film):
    """
    POST /watchlist/<user_id>/add should let callers set public explicitly.
    """
    response = client.post(
        f"/watchlist/{sample_user}/add",
        json={"film_id": sample_film, "public": False},
    )

    assert response.status_code == 201
    data = response.get_json()
    assert data["film_id"] == sample_film
    assert data["public"] is False


def test_add_watchlist_route_duplicate_returns_conflict(
    client,
    sample_user,
    sample_film,
):
    """
    POSTing the same film twice should return 409 instead of duplicating it.
    """
    first = client.post(
        f"/watchlist/{sample_user}/add",
        json={"film_id": sample_film},
    )
    second = client.post(
        f"/watchlist/{sample_user}/add",
        json={"film_id": sample_film},
    )

    assert first.status_code == 201
    assert second.status_code == 409
