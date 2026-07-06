import os
from pydantic_settings import BaseSettings
from dotenv import load_dotenv

# Load from .env if present
load_dotenv()

class Settings(BaseSettings):
    product_hunt_token: str = os.getenv("PRODUCT_HUNT_TOKEN", "")
    default_sync_mode: str = os.getenv("DEFAULT_SYNC_MODE", "today")

    class Config:
        env_file = ".env"
        extra = "ignore"

settings = Settings()

def get_setting_value(db, key: str, default: str = "") -> str:
    """Helper to get a setting from SQLite first, falling back to environment settings."""
    from .models import Setting
    db_setting = db.query(Setting).filter(Setting.key == key).first()
    if db_setting and db_setting.value is not None:
        return db_setting.value
    
    # Fallback to .env / environment settings
    if key == "product_hunt_token":
        return settings.product_hunt_token
    elif key == "default_sync_mode":
        return settings.default_sync_mode
    return default

def set_setting_value(db, key: str, value: str):
    """Helper to save/update a setting in SQLite."""
    from .models import Setting
    db_setting = db.query(Setting).filter(Setting.key == key).first()
    if db_setting:
        db_setting.value = value
    else:
        db_setting = Setting(key=key, value=value)
        db.add(db_setting)
    db.commit()
