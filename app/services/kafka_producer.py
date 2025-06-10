import json
import asyncio
from typing import Dict, Optional
from datetime import datetime
from aiokafka import AIOKafkaProducer
from aiokafka.errors import KafkaError
import logging
from app.core.kafka_config import kafka_settings

logger = logging.getLogger(__name__)


class KafkaProducerService:
    """
    Kafka producer for publishing transactions and alerts
    """
    
    def __init__(self):
        self.producer: Optional[AIOKafkaProducer] = None
        self._lock = asyncio.Lock()
        
    async def start(self):
        """Start the Kafka producer"""
        async with self._lock:
            if self.producer is None:
                try:
                    self.producer = AIOKafkaProducer(
                        bootstrap_servers=kafka_settings.KAFKA_BOOTSTRAP_SERVERS,
                        compression_type=kafka_settings.PRODUCER_COMPRESSION_TYPE,
                        value_serializer=lambda v: json.dumps(v).encode('utf-8'),
                        key_serializer=lambda k: k.encode('utf-8') if k else None,
                        max_batch_size=kafka_settings.PRODUCER_BATCH_SIZE,
                        linger_ms=kafka_settings.PRODUCER_LINGER_MS
                    )
                    await self.producer.start()
                    logger.info("Kafka producer started successfully")
                except Exception as e:
                    logger.error(f"Failed to start Kafka producer: {e}")
                    self.producer = None
                    raise
    
    async def stop(self):
        """Stop the Kafka producer"""
        async with self._lock:
            if self.producer:
                await self.producer.stop()
                self.producer = None
                logger.info("Kafka producer stopped")
    
    async def publish_transaction(self, transaction_data: Dict, transaction_id: str):
        """
        Publish transaction to Kafka for processing
        """
        if not self.producer:
            await self.start()
        
        try:
            # Add metadata
            message = {
                "transaction_id": transaction_id,
                "timestamp": datetime.utcnow().isoformat(),
                "data": transaction_data,
                "status": "pending_analysis"
            }
            
            # Send to Kafka
            await self.producer.send(
                topic=kafka_settings.TRANSACTION_TOPIC,
                key=transaction_id,
                value=message
            )
            
            logger.info(f"Published transaction {transaction_id} to Kafka")
            return True
            
        except KafkaError as e:
            logger.error(f"Failed to publish transaction {transaction_id}: {e}")
            return False
    
    async def publish_alert(self, alert_data: Dict):
        """
        Publish fraud alert to alert topic
        """
        if not self.producer:
            await self.start()
        
        try:
            alert_id = alert_data.get("transaction_id", "unknown")
            
            # Send to alert topic
            await self.producer.send(
                topic=kafka_settings.ALERT_TOPIC,
                key=alert_id,
                value=alert_data
            )
            
            logger.info(f"Published fraud alert for transaction {alert_id}")
            return True
            
        except KafkaError as e:
            logger.error(f"Failed to publish alert: {e}")
            return False
    
    async def publish_processed_result(self, result_data: Dict):
        """
        Publish processed transaction result
        """
        if not self.producer:
            await self.start()
        
        try:
            transaction_id = result_data.get("transaction_id", "unknown")
            
            # Send to processed topic
            await self.producer.send(
                topic=kafka_settings.PROCESSED_TOPIC,
                key=transaction_id,
                value=result_data
            )
            
            logger.info(f"Published processed result for transaction {transaction_id}")
            return True
            
        except KafkaError as e:
            logger.error(f"Failed to publish processed result: {e}")
            return False


# Create singleton instance
kafka_producer = KafkaProducerService()