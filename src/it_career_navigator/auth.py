import secrets

from typing_extensions import Annotated

from pwdlib import PasswordHash
from fastapi import Depends, HTTPException, status
from it_career_navigator.config import settings
from fastapi.security import APIKeyHeader, OAuth2PasswordBearer
import jwt
from datetime import datetime, timedelta,UTC

pwd_context = PasswordHash.recommended()

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/users/login")


def hash_password(password: str) -> str:
    return pwd_context.hash(password)

def verify_password(plain_password: str, hashed_password: str) -> bool:
    return pwd_context.verify(plain_password, hashed_password)


def decode_jwt(token: str, secret_key: str, algorithms: list) -> dict:
    try:
        payload = jwt.decode(token, secret_key, algorithms=algorithms)
        return payload
    except jwt.PyJWTError:
        raise HTTPException(status_code=401, detail="Invalid token")

def encode_jwt(payload: dict, secret_key: str, algorithm: str) -> str:
    return jwt.encode(payload, secret_key, algorithm=algorithm)

def create_access_token(data: dict) -> str:
    to_encode = data.copy()
    from it_career_navigator.config import settings
    expire = datetime.now(UTC) + timedelta(minutes=settings.access_token_expire_minutes)
    to_encode.update({"exp": expire})
    return encode_jwt(to_encode, settings.secret_key, settings.algorithm)

def get_current_user(
    token: Annotated[str, Depends(oauth2_scheme)],
) -> dict:
    payload = decode_jwt(
        token,
        settings.secret_key,
        [settings.algorithm],
    )

    user_id = payload.get("sub")
    if user_id is None:
        raise HTTPException(
            status_code=401,
            detail="Invalid token",
        )

    return {"id": int(user_id)}

CurrentUser = Annotated[dict, Depends(get_current_user)]



internal_api_key_header = APIKeyHeader(
    name="X-Internal-API-Key",
    auto_error=False,
)
async def verify_internal_api_key(
    provided_key: Annotated[str | None, Depends(internal_api_key_header)],
) -> None:
    expected_key = settings.internal_api_key

    if expected_key is None:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Internal API key is not configured",
        )

    if provided_key is None or not secrets.compare_digest(
        provided_key,
        expected_key.get_secret_value(),
    ):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid internal API key",
        )


InternalAPIKey = Annotated[None, Depends(verify_internal_api_key)]