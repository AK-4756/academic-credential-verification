import pytest
from unittest.mock import AsyncMock, patch, MagicMock
from datetime import datetime, timedelta, timezone
from uuid import uuid4

from core.constants import MAX_FAILED_LOGIN_ATTEMPTS, UserRole
from core.exceptions import (
    DuplicateEmailError,
    InvalidCredentialsError,
    AccountLockedError,
    UniversityNotFoundError,
    UnverifiedUniversityError,
    UserNotFoundError,
)
from services.auth_service import (
    register_user,
    authenticate_user,
    refresh_access_token,
    logout,
)

# Mock models
class MockUser:
    def __init__(self, **kwargs):
        self.id = kwargs.get('id', uuid4())
        self.email = kwargs.get('email', 'test@example.com')
        self.password_hash = kwargs.get('password_hash', 'hashed_pass')
        self.role = kwargs.get('role', UserRole.STUDENT)
        self.first_name = kwargs.get('first_name', 'First')
        self.last_name = kwargs.get('last_name', 'Last')
        self.university_id = kwargs.get('university_id', None)
        self.is_active = kwargs.get('is_active', True)
        self.locked_until = kwargs.get('locked_until', None)
        self.failed_login_attempts = kwargs.get('failed_login_attempts', 0)

class MockRefreshToken:
    def __init__(self, **kwargs):
        self.id = kwargs.get('id', uuid4())
        self.user_id = kwargs.get('user_id', uuid4())
        self.token_hash = kwargs.get('token_hash', 'hashed_token')
        self.expires_at = kwargs.get('expires_at', datetime.now(timezone.utc) + timedelta(days=1))
        self.is_revoked = kwargs.get('is_revoked', False)
        self.replaced_by_id = kwargs.get('replaced_by_id', None)

class MockUniversity:
    def __init__(self, **kwargs):
        self.id = kwargs.get('id', uuid4())
        self.is_verified = kwargs.get('is_verified', True)

@pytest.fixture
def db():
    from sqlalchemy.ext.asyncio import AsyncSession
    db_mock = AsyncMock(spec=AsyncSession)
    
    ctx_mock = MagicMock()
    ctx_mock.__aenter__ = AsyncMock()
    ctx_mock.__aexit__ = AsyncMock(return_value=False)
    
    db_mock.begin = MagicMock(return_value=ctx_mock)
    return db_mock

@pytest.mark.asyncio
@pytest.mark.unit
@patch('services.auth_service.UserRepository')
@patch('services.auth_service.StudentRepository')
@patch('services.auth_service.hash_password')
async def test_register_user_success(mock_hash_password, mock_student_repo, mock_user_repo, db):
    mock_user_repo.get_by_email = AsyncMock(return_value=None)
    mock_hash_password.return_value = 'hashed_password'
    
    user = MockUser(email='test@example.com', role=UserRole.STUDENT)
    mock_user_repo.create = AsyncMock(return_value=user)
    mock_student_repo.create = AsyncMock()
    
    registration_data = {
        'email': 'test@example.com',
        'password': 'password123',
        'first_name': 'First',
        'last_name': 'Last',
        'role': UserRole.STUDENT
    }
    
    result = await register_user(registration_data, db)
    
    assert result['email'] == 'test@example.com'
    assert result['role'] == UserRole.STUDENT
    assert result['message'] == 'Registration successful'
    mock_user_repo.get_by_email.assert_called_once_with(db, 'test@example.com')
    mock_hash_password.assert_called_once_with('password123')
    mock_user_repo.create.assert_called_once()
    mock_student_repo.create.assert_called_once_with(db, {"user_id": user.id})

@pytest.mark.asyncio
@pytest.mark.unit
@patch('services.auth_service.UserRepository')
async def test_register_user_duplicate_email(mock_user_repo, db):
    mock_user_repo.get_by_email = AsyncMock(return_value=MockUser())
    
    registration_data = {
        'email': 'test@example.com',
        'password': 'password123',
        'first_name': 'First',
        'last_name': 'Last',
        'role': UserRole.STUDENT
    }
    
    with pytest.raises(DuplicateEmailError):
        await register_user(registration_data, db)

@pytest.mark.asyncio
@pytest.mark.unit
@patch('services.auth_service.UserRepository')
@patch('services.auth_service.RefreshTokenRepository')
@patch('services.auth_service.verify_password')
@patch('services.auth_service.create_access_token')
@patch('services.auth_service.generate_refresh_token')
@patch('services.auth_service.hash_token')
async def test_authenticate_user_success(mock_hash_token, mock_gen_refresh, mock_create_access, mock_verify_pw, mock_rt_repo, mock_user_repo, db):
    user = MockUser(email='test@example.com')
    mock_user_repo.get_by_email = AsyncMock(return_value=user)
    mock_user_repo.reset_failed_attempts = AsyncMock()
    mock_user_repo.update_last_login = AsyncMock()
    mock_rt_repo.create = AsyncMock()
    mock_verify_pw.return_value = True
    
    mock_create_access.return_value = 'access_token_123'
    mock_gen_refresh.return_value = 'refresh_token_123'
    mock_hash_token.return_value = 'hashed_refresh_token'
    
    result = await authenticate_user('test@example.com', 'password123', '127.0.0.1', db)
    
    assert result['access_token'] == 'access_token_123'
    assert result['refresh_token'] == 'refresh_token_123'
    mock_user_repo.reset_failed_attempts.assert_called_once_with(db, user.id)
    mock_user_repo.update_last_login.assert_called_once_with(db, user.id, '127.0.0.1')
    mock_rt_repo.create.assert_called_once()

@pytest.mark.asyncio
@pytest.mark.unit
@patch('services.auth_service.UserRepository')
@patch('services.auth_service.verify_password')
async def test_authenticate_user_wrong_password(mock_verify_pw, mock_user_repo, db):
    user = MockUser(email='test@example.com')
    mock_user_repo.get_by_email = AsyncMock(return_value=user)
    mock_user_repo.increment_failed_attempts = AsyncMock(return_value=1)
    mock_user_repo.set_account_lock = AsyncMock()
    mock_verify_pw.return_value = False
    
    with pytest.raises(InvalidCredentialsError):
        await authenticate_user('test@example.com', 'wrongpassword', '127.0.0.1', db)
        
    mock_user_repo.increment_failed_attempts.assert_called_once_with(db, user.id)
    mock_user_repo.set_account_lock.assert_not_called()

@pytest.mark.asyncio
@pytest.mark.unit
@patch('services.auth_service.UserRepository')
async def test_authenticate_user_not_found(mock_user_repo, db):
    mock_user_repo.get_by_email = AsyncMock(return_value=None)
    
    with pytest.raises(InvalidCredentialsError):
        await authenticate_user('nonexistent@example.com', 'password123', '127.0.0.1', db)

@pytest.mark.asyncio
@pytest.mark.unit
@patch('services.auth_service.UserRepository')
async def test_authenticate_user_account_locked(mock_user_repo, db):
    user = MockUser(email='test@example.com', locked_until=datetime.now(timezone.utc) + timedelta(minutes=10))
    mock_user_repo.get_by_email = AsyncMock(return_value=user)
    
    with pytest.raises(AccountLockedError):
        await authenticate_user('test@example.com', 'password123', '127.0.0.1', db)

@pytest.mark.asyncio
@pytest.mark.unit
@patch('services.auth_service.RefreshTokenRepository')
@patch('services.auth_service.UserRepository')
@patch('services.auth_service.hash_token')
@patch('services.auth_service.create_access_token')
@patch('services.auth_service.generate_refresh_token')
async def test_refresh_token_success(mock_gen_refresh, mock_create_access, mock_hash_token, mock_user_repo, mock_rt_repo, db):
    mock_hash_token.side_effect = ['hashed_old', 'hashed_new']
    stored_token = MockRefreshToken(token_hash='hashed_old')
    mock_rt_repo.get_by_token_hash = AsyncMock(return_value=stored_token)
    mock_rt_repo.revoke = AsyncMock()
    
    user = MockUser()
    mock_user_repo.get_by_id = AsyncMock(return_value=user)
    
    mock_create_access.return_value = 'new_access'
    mock_gen_refresh.return_value = 'new_refresh'
    
    new_token_mock = MockRefreshToken(id=uuid4())
    mock_rt_repo.create = AsyncMock(return_value=new_token_mock)
    
    result = await refresh_access_token('old_refresh', '127.0.0.1', db)
    
    assert result['access_token'] == 'new_access'
    assert result['refresh_token'] == 'new_refresh'
    mock_rt_repo.revoke.assert_called_once_with(db, stored_token.id, replaced_by_id=new_token_mock.id)

@pytest.mark.asyncio
@pytest.mark.unit
@patch('services.auth_service.RefreshTokenRepository')
@patch('services.auth_service.hash_token')
async def test_refresh_token_revoked(mock_hash_token, mock_rt_repo, db):
    mock_hash_token.return_value = 'hashed_old'
    stored_token = MockRefreshToken(is_revoked=True)
    mock_rt_repo.get_by_token_hash = AsyncMock(return_value=stored_token)
    
    with pytest.raises(InvalidCredentialsError) as exc:
        await refresh_access_token('old_refresh', '127.0.0.1', db)
    assert 'revoked' in str(exc.value)

@pytest.mark.asyncio
@pytest.mark.unit
@patch('services.auth_service.RefreshTokenRepository')
@patch('services.auth_service.hash_token')
async def test_refresh_token_expired(mock_hash_token, mock_rt_repo, db):
    mock_hash_token.return_value = 'hashed_old'
    stored_token = MockRefreshToken(expires_at=datetime.now(timezone.utc) - timedelta(days=1))
    mock_rt_repo.get_by_token_hash = AsyncMock(return_value=stored_token)
    
    with pytest.raises(InvalidCredentialsError) as exc:
        await refresh_access_token('old_refresh', '127.0.0.1', db)
    assert 'expired' in str(exc.value)

@pytest.mark.asyncio
@pytest.mark.unit
@patch('services.auth_service.RefreshTokenRepository')
@patch('services.auth_service.hash_token')
async def test_logout_success(mock_hash_token, mock_rt_repo, db):
    mock_hash_token.return_value = 'hashed_token'
    stored_token = MockRefreshToken(is_revoked=False)
    mock_rt_repo.get_by_token_hash = AsyncMock(return_value=stored_token)
    mock_rt_repo.revoke = AsyncMock()
    
    await logout('refresh_token', db)
    
    mock_rt_repo.revoke.assert_called_once_with(db, stored_token.id)
