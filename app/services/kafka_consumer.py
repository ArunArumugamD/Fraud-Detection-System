import json
import asyncio
import logging
from typing import Dict, List, Optional
from datetime import datetime
from aiokafka import AIOKafkaConsumer
from aiokafka.errors import KafkaError
from sqlalchemy.orm import Session

from app.core.kafka_config import kafka_settings
from app.services.fraud_detector import fraud_detector
from app.services.kafka_producer import kafka_producer
from app.services.websocket_manager import websocket_manager
from app.models.transaction_model import Transaction
from app.models.schemas import TransactionCreate, TransactionStatus
from app.db.database import SessionLocal

logger = logging.getLogger(__name__)


class KafkaConsumerService:
    """
    Kafka consumer for processing transactions in real-time
    """
    
    def __init__(self):
        self.consumer: Optional[AIOKafkaConsumer] = None
        self.running = False
        self.processed_count = 0
        self.error_count = 0
        
    async def start(self):
        """Start the Kafka consumer"""
        try:
            # Ensure Kafka producer is started for publishing alerts
            if not kafka_producer.producer:
                await kafka_producer.start()
                logger.info("Started Kafka producer in consumer service")
            
            self.consumer = AIOKafkaConsumer(
                kafka_settings.TRANSACTION_TOPIC,
                bootstrap_servers=kafka_settings.KAFKA_BOOTSTRAP_SERVERS,
                group_id=kafka_settings.CONSUMER_GROUP_ID,
                auto_offset_reset=kafka_settings.AUTO_OFFSET_RESET,
                enable_auto_commit=kafka_settings.ENABLE_AUTO_COMMIT,
                auto_commit_interval_ms=kafka_settings.AUTO_COMMIT_INTERVAL_MS,
                value_deserializer=lambda v: json.loads(v.decode('utf-8')),
                key_deserializer=lambda k: k.decode('utf-8') if k else None
            )
            
            await self.consumer.start()
            self.running = True
            logger.info("Kafka consumer started successfully")
            
        except Exception as e:
            logger.error(f"Failed to start Kafka consumer: {e}")
            raise
    
    async def stop(self):
        """Stop the Kafka consumer"""
        self.running = False
        if self.consumer:
            await self.consumer.stop()
            logger.info(f"Kafka consumer stopped. Processed: {self.processed_count}, Errors: {self.error_count}")
    
    async def process_messages(self):
        """Main message processing loop"""
        logger.info("Starting message processing loop")
        
        try:
            async for message in self.consumer:
                if not self.running:
                    break
                
                logger.info(f"Received message: {message.key} from partition {message.partition}")
                
                try:
                    await self._process_single_message(message.value)
                    self.processed_count += 1
                    
                except Exception as e:
                    self.error_count += 1
                    logger.error(f"Error processing message: {e}", exc_info=True)
                    
        except Exception as e:
            logger.error(f"Consumer loop error: {e}", exc_info=True)
            self.running = False
    
    async def _process_single_message(self, message: Dict):
        """Process a single transaction message"""
        transaction_id = message.get("transaction_id")
        transaction_data = message.get("data")
        
        logger.info(f"Processing transaction {transaction_id}")
        
        # Create database session
        db = SessionLocal()
        
        try:
            # Convert to TransactionCreate schema
            transaction = TransactionCreate(**transaction_data)
            
            # Run fraud detection with ML
            risk_score, fraud_reasons, ml_info = fraud_detector.analyze_transaction(transaction)
            risk_level = fraud_detector.get_risk_level(risk_score)
            is_fraud = fraud_detector.is_fraud(risk_score)
            
            # Determine status
            if is_fraud:
                status = TransactionStatus.DECLINED
            elif risk_level == "medium":
                status = TransactionStatus.FLAGGED
            else:
                status = TransactionStatus.APPROVED
            
            # Save to database
            db_transaction = Transaction(
                **transaction.dict(),
                status=status,
                risk_score=risk_score,
                risk_level=risk_level,
                fraud_prediction=is_fraud,
                fraud_reasons=json.dumps(fraud_reasons) if fraud_reasons else None,
                verification_required=risk_level in ["medium", "high"]
            )
            
            db.add(db_transaction)
            db.commit()
            db.refresh(db_transaction)
            
            # Prepare result (convert numpy types to Python types)
            result = {
                "transaction_id": str(db_transaction.id),
                "status": status.value,  # Convert enum to string
                "risk_score": float(risk_score),  # Convert numpy float
                "risk_level": risk_level,
                "fraud_prediction": bool(is_fraud),  # Convert numpy bool
                "fraud_reasons": fraud_reasons,
                "ml_info": ml_info,
                "processed_at": datetime.utcnow().isoformat()
            }
            
            # Publish processed result
            await kafka_producer.publish_processed_result(result)
            
            # Send alert if high risk
            if is_fraud or risk_level == "high":
                alert_data = {
                    "transaction_id": str(db_transaction.id),
                    "alert_type": "FRAUD_DETECTED" if is_fraud else "HIGH_RISK",
                    "risk_score": float(risk_score),  # Convert numpy float
                    "amount": float(transaction.amount),  # Ensure float
                    "merchant": transaction.merchant_name,
                    "customer_id": transaction.customer_id,
                    "reasons": fraud_reasons,
                    "timestamp": datetime.utcnow().isoformat()
                }
                
                # Publish to alert topic
                await kafka_producer.publish_alert(alert_data)
                
                # Send WebSocket notification
                await websocket_manager.send_alert(alert_data)
            
            logger.info(f"Transaction {db_transaction.id} processed: {status} (risk: {risk_score:.2f})")
            
        except Exception as e:
            logger.error(f"Error processing transaction: {e}")
            db.rollback()
            raise
        finally:
            db.close()
    
    async def get_stats(self) -> Dict:
        """Get consumer statistics"""
        return {
            "running": self.running,
            "processed_count": self.processed_count,
            "error_count": self.error_count,
            "success_rate": (self.processed_count / (self.processed_count + self.error_count) * 100) if self.processed_count > 0 else 0
        }


# Create singleton instance
kafka_consumer = KafkaConsumerService()