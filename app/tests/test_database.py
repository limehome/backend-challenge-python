from unittest.mock import MagicMock, patch

from sqlalchemy import text

from app import database


def test_session_local_can_connect() -> None:
    """Check that SessionLocal creates a working connection."""
    with database.SessionLocal() as session:
        result = session.execute(text("SELECT 1")).scalar()
        assert result == 1
        session.close()


def test_get_db_auto_close2() -> None:
    mock_session = MagicMock()
    with patch("app.database.SessionLocal", return_value=mock_session) as mock_factory:
        for _ in database.get_db():
            mock_factory.assert_called_once()
        mock_session.close.assert_called_once()
