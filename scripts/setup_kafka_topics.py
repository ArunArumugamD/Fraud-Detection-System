import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from kafka.admin import KafkaAdminClient, NewTopic
from kafka.errors import TopicAlreadyExistsError
from app.core.kafka_config import kafka_settings
import time

def create_topics():
    """Create Kafka topics for fraud detection system"""
    
    print("Waiting for Kafka to be ready...")
    time.sleep(5)  # Give Kafka time to start
    
    try:
        # Create admin client
        admin_client = KafkaAdminClient(
            bootstrap_servers=kafka_settings.KAFKA_BOOTSTRAP_SERVERS,
            client_id='fraud-detection-admin'
        )
        
        # Define topics
        topics = [
            NewTopic(
                name=kafka_settings.TRANSACTION_TOPIC,
                num_partitions=3,
                replication_factor=1
            ),
            NewTopic(
                name=kafka_settings.ALERT_TOPIC,
                num_partitions=1,
                replication_factor=1
            ),
            NewTopic(
                name=kafka_settings.PROCESSED_TOPIC,
                num_partitions=3,
                replication_factor=1
            )
        ]
        
        # Create topics
        for topic in topics:
            try:
                admin_client.create_topics([topic])
                print(f"Created topic: {topic.name}")
            except TopicAlreadyExistsError:
                print(f"Topic already exists: {topic.name}")
        
        # List all topics
        metadata = admin_client.list_topics()
        print("\nAll topics:")
        for topic in metadata:
            print(f"  - {topic}")
        
        print("\nKafka topics setup completed!")
        
    except Exception as e:
        print(f"Error setting up Kafka topics: {e}")
        print("Make sure Kafka is running (docker-compose up)")

if __name__ == "__main__":
    create_topics()