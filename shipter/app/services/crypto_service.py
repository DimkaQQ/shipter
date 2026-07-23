import json
import logging
from cryptography.fernet import Fernet, InvalidToken
from app.config import Config

logger = logging.getLogger(__name__)


def _get_fernet() -> Fernet:
    if not Config.ENCRYPTION_KEY:
        raise RuntimeError(
            'ENCRYPTION_KEY не настроен. Сгенерируйте: '
            'python -c "from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())"'
        )
    return Fernet(Config.ENCRYPTION_KEY.encode())


def encrypt_dict(data: dict) -> str:
    """Шифрует словарь с секретами (токены, пароли) для хранения в БД."""
    fernet = _get_fernet()
    raw = json.dumps(data, ensure_ascii=False).encode()
    return fernet.encrypt(raw).decode()


def decrypt_dict(encrypted: str) -> dict:
    """Расшифровывает словарь с секретами."""
    fernet = _get_fernet()
    try:
        raw = fernet.decrypt(encrypted.encode())
        return json.loads(raw.decode())
    except InvalidToken:
        logger.error("Failed to decrypt integration config: invalid token")
        raise
