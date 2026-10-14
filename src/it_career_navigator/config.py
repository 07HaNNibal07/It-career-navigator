from pydantic import SecretStr
from pydantic_settings import BaseSettings, SettingsConfigDict

class Settings(BaseSettings):
    db_url: str 
    secret_key: str
    algorithm: str = "HS256"
    access_token_expire_minutes: int = 30
    internal_api_key: SecretStr | None = None
    
    
    
    model_config = SettingsConfigDict(env_file=".env",extra="ignore")
    
    
settings = Settings()