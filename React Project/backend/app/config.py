from functools import lru_cache
from pathlib import Path

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    aide_checkpoint_path: Path = Field(
        default=Path("results/progan_train.pth"),
        description="Path to the AIDE fine-tuned checkpoint (.pth).",
    )
    aide_resnet_path: Path = Field(default=Path("pretrained_ckpts/resnet50.pth"))
    aide_convnext_path: Path = Field(
        default=Path("pretrained_ckpts/open_clip_pytorch_model.bin")
    )
    aide_device: str | None = Field(
        default=None,
        description="Override device: 'cpu' | 'cuda' | 'mps'. None = auto-detect.",
    )
    aide_mock_mode: bool = Field(
        default=False,
        validation_alias="AIDE_MOCK_MODE",
        description="If True, returns random scores without loading the model.",
    )

    gcp_project_id: str = Field(default="", validation_alias="GCP_PROJECT_ID")
    gcp_location: str = Field(default="us-central1", validation_alias="GCP_LOCATION")

    router_model: str = "gemini-2.5-flash"
    eval_model: str = "gemini-2.5-pro"
    greeting_model: str = "gemini-2.5-flash"

    upload_dir: Path = Field(default=Path("temp_uploads"))


@lru_cache
def get_settings() -> Settings:
    return Settings()
