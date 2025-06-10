from pydantic_settings import BaseSettings
import os
from typing import List

class KafkaSettings(BaseSettings):
    """Kafka configuration settings"""
    
    # Kafka broker settings
    KAFKA_BOOTSTRAP_SERVERS: str = os.getenv("KAFKA_BOOTSTRAP_SERVERS", "localhost:9092")
    
    # Topics
    TRANSACTION_TOPIC: str = "fraud-detection-transactions"
    ALERT_TOPIC: str = "fraud-detection-alerts"
    PROCESSED_TOPIC: str = "fraud-detection-processed"
    
    # Consumer settings
    CONSUMER_GROUP_ID: str = "fraud-detection-consumer-group"
    AUTO_OFFSET_RESET: str = "earliest"
    ENABLE_AUTO_COMMIT: bool = True
    AUTO_COMMIT_INTERVAL_MS: int = 1000
    
    # Producer settings
    PRODUCER_COMPRESSION_TYPE: str = "gzip"
    PRODUCER_BATCH_SIZE: int = 16384
    PRODUCER_LINGER_MS: int = 10
    
    # Processing settings
    MAX_BATCH_SIZE: int = 100
    PROCESSING_TIMEOUT: int = 30
    
    class Config:
        env_file = ".env"
        case_sensitive = True
        extra = "ignore"  # Allow extra fields from .env

# Create settings instance
kafka_settings = KafkaSettings()