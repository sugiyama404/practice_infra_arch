import os


class Config:
    """Push Notification Server Configuration"""

    # Server Settings
    HOST: str = os.getenv("HOST", "0.0.0.0")
    PORT: int = int(os.getenv("PORT", "8000"))

    # Mock Settings
    LOG_LEVEL: str = os.getenv("LOG_LEVEL", "INFO")
    ENABLE_DETAILED_LOGS: bool = (
        os.getenv("ENABLE_DETAILED_LOGS", "true").lower() == "true"
    )

    # Notification Settings
    MAX_RECIPIENTS: int = int(os.getenv("MAX_RECIPIENTS", "1000"))
    CONTENT_MAX_LENGTH: int = int(os.getenv("CONTENT_MAX_LENGTH", "4000"))

    # Simulation Settings
    SIMULATE_DELAY: bool = os.getenv("SIMULATE_DELAY", "false").lower() == "true"
    MIN_DELAY_MS: int = int(os.getenv("MIN_DELAY_MS", "100"))
    MAX_DELAY_MS: int = int(os.getenv("MAX_DELAY_MS", "500"))

    # Statistics
    ENABLE_STATS: bool = os.getenv("ENABLE_STATS", "true").lower() == "true"


config = Config()
