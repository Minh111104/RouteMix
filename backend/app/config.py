from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    google_routes_api_key: str = ""
    amadeus_api_key: str = ""
    amadeus_api_secret: str = ""

    model_config = {"env_file": ".env", "env_file_encoding": "utf-8"}


settings = Settings()
