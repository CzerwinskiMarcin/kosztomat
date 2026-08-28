from pathlib import Path

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_prefix='KOSZTOMATOR_')

    data_dir: Path = Path(__file__).resolve().parent.parent / 'data'
    max_upload_bytes: int = 10 * 1024 * 1024

    @property
    def db_path(self) -> Path:
        return self.data_dir / 'kosztomator.db'

    @property
    def uploads_dir(self) -> Path:
        return self.data_dir / 'uploads'

    @property
    def database_url(self) -> str:
        return f'sqlite:///{self.db_path}'


settings = Settings()
