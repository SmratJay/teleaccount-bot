import pytest
from unittest.mock import AsyncMock, MagicMock
from handlers.user_panel import handle_language_selection
from services.translation_service import translation_service
from database.operations import UserService

@pytest.mark.asyncio
async def test_handle_language_selection_persists_language(mocker):
    """Test that handle_language_selection persists the selected language to the database."""
    # Mock the update and context
    update = MagicMock()
    context = MagicMock()
    
    # Mock callback query data
    update.callback_query.data = 'lang_es'
    update.callback_query.edit_message_text = AsyncMock()
    update.effective_user.id = 12345

    # Mock the database session and user service
    mock_db_session = mocker.patch('handlers.user_panel.get_db_session', return_value=MagicMock())
    mock_close_db_session = mocker.patch('handlers.user_panel.close_db_session')
    mock_user_service = mocker.patch('handlers.user_panel.UserService.get_user_by_telegram_id')

    # Mock user object
    mock_user = MagicMock()
    mock_user_service.return_value = mock_user

    # Call the handler
    await handle_language_selection(update, context)

    # Assertions
    mock_db_session.assert_called_once()
    mock_user_service.assert_called_once_with(mock_db_session.return_value, 12345)
    assert mock_user.language_code == 'es'
    mock_db_session.return_value.commit.assert_called_once()
    mock_close_db_session.assert_called_once_with(mock_db_session.return_value)

    # Check if the success message was sent
    update.callback_query.edit_message_text.assert_called_once()
    assert 'Idioma Actualizado' in update.callback_query.edit_message_text.call_args[0][0]