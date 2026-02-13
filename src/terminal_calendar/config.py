"""Configuration management for terminal calendar."""

import json
from pathlib import Path
from typing import Literal

from pydantic import BaseModel, Field


class ThemeConfig(BaseModel):
    """Theme configuration for the TUI.

    Attributes:
        current_task_color: Color for current task highlighting
        completed_task_color: Color for completed tasks
        pending_task_color: Color for pending tasks
        high_priority_color: Color for high priority tasks
        medium_priority_color: Color for medium priority tasks
        low_priority_color: Color for low priority tasks
        progress_bar_colors: Whether to use colored progress bars
    """

    current_task_color: str = Field(default="yellow", description="Color for current task")
    completed_task_color: str = Field(default="green", description="Color for completed tasks")
    pending_task_color: str = Field(default="white", description="Color for pending tasks")
    high_priority_color: str = Field(default="red", description="Color for high priority")
    medium_priority_color: str = Field(default="yellow", description="Color for medium priority")
    low_priority_color: str = Field(default="green", description="Color for low priority")
    progress_bar_colors: bool = Field(default=True, description="Use colored progress bars")


class UIConfig(BaseModel):
    """UI behavior configuration.

    Attributes:
        auto_refresh_interval: Seconds between auto-refreshes (60 = 1 minute)
        vim_mode_only: Only use vim keys (disable arrow keys)
        show_descriptions: Show task descriptions in list
        show_durations: Show task durations in list
        compact_mode: Use compact display (less spacing)
    """

    auto_refresh_interval: int = Field(
        default=60,
        ge=10,
        le=600,
        description="Auto-refresh interval in seconds"
    )
    vim_mode_only: bool = Field(default=False, description="Only use vim keys")
    show_descriptions: bool = Field(default=True, description="Show task descriptions")
    show_durations: bool = Field(default=True, description="Show task durations")
    compact_mode: bool = Field(default=False, description="Use compact display")


class ReportConfig(BaseModel):
    """Report generation configuration.

    Attributes:
        default_format: Default report format
        include_insights: Include AI-like insights
        auto_save: Automatically save reports
        open_after_generate: Open report in editor after generation
    """

    default_format: Literal["text", "markdown", "json"] = Field(
        default="text",
        description="Default report format"
    )
    include_insights: bool = Field(default=True, description="Include insights")
    auto_save: bool = Field(default=True, description="Automatically save reports")
    open_after_generate: bool = Field(default=False, description="Open after generation")


class ValidationConfig(BaseModel):
    """Schedule validation configuration.

    Attributes:
        warn_overlapping: Warn about overlapping tasks
        warn_gaps: Warn about large gaps between tasks
        min_gap_minutes: Minimum gap to warn about (default: 60 minutes)
        max_gap_minutes: Maximum gap before warning (default: 120 minutes)
        validate_on_load: Validate schedule when loading
    """

    warn_overlapping: bool = Field(default=True, description="Warn about overlaps")
    warn_gaps: bool = Field(default=False, description="Warn about gaps")
    min_gap_minutes: int = Field(default=5, ge=0, description="Min gap for buffer")
    max_gap_minutes: int = Field(default=120, ge=0, description="Max gap before warning")
    validate_on_load: bool = Field(default=True, description="Validate on load")


class Config(BaseModel):
    """Main application configuration.

    Attributes:
        theme: Theme configuration
        ui: UI behavior configuration
        report: Report generation configuration
        validation: Schedule validation configuration
        default_schedule_dir: Default directory for schedules
    """

    theme: ThemeConfig = Field(default_factory=ThemeConfig)
    ui: UIConfig = Field(default_factory=UIConfig)
    report: ReportConfig = Field(default_factory=ReportConfig)
    validation: ValidationConfig = Field(default_factory=ValidationConfig)
    default_schedule_dir: str | None = Field(
        default=None,
        description="Default directory for schedule files"
    )


class ConfigManager:
    """Manages application configuration.

    Handles loading and saving configuration to a JSON file,
    with sensible defaults for all settings.

    Attributes:
        config_file: Path to the configuration file
        config_dir: Path to the configuration directory
    """

    DEFAULT_CONFIG_DIR = Path.home() / ".terminal-calendar"
    DEFAULT_CONFIG_FILE = "config.json"

    def __init__(self, config_dir: Path | None = None) -> None:
        """Initialize the config manager.

        Args:
            config_dir: Optional custom configuration directory.
                       Defaults to ~/.terminal-calendar
        """
        self.config_dir = config_dir or self.DEFAULT_CONFIG_DIR
        self.config_file = self.config_dir / self.DEFAULT_CONFIG_FILE
        self._ensure_config_dir()

    def _ensure_config_dir(self) -> None:
        """Ensure the configuration directory exists."""
        self.config_dir.mkdir(parents=True, exist_ok=True)

    def load_config(self) -> Config:
        """Load configuration from disk.

        Returns:
            Config object with loaded or default settings
        """
        # If config file doesn't exist, return defaults
        if not self.config_file.exists():
            return Config()

        try:
            with self.config_file.open("r", encoding="utf-8") as f:
                data = json.load(f)

            # Validate and convert to Config
            config = Config.model_validate(data)
            return config

        except (json.JSONDecodeError, Exception):
            # If config is corrupted, return defaults
            return Config()

    def save_config(self, config: Config) -> None:
        """Save configuration to disk.

        Args:
            config: The Config object to save
        """
        # Convert to JSON-serializable dict
        config_dict = config.model_dump(mode="json")

        # Write to file with nice formatting
        with self.config_file.open("w", encoding="utf-8") as f:
            json.dump(config_dict, f, indent=2, ensure_ascii=False)

    def reset_config(self) -> Config:
        """Reset configuration to defaults.

        Returns:
            Default Config object
        """
        config = Config()
        self.save_config(config)
        return config

    def get_config_path(self) -> Path:
        """Get the path to the config file.

        Returns:
            Path to the config file
        """
        return self.config_file

    def config_exists(self) -> bool:
        """Check if a config file exists.

        Returns:
            True if config file exists, False otherwise
        """
        return self.config_file.exists()
