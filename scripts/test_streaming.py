import asyncio
import aiohttp
import json
import random
from datetime import datetime

# Test transactions
TEST_TRANSACTIONS = [
    # Normal transactions
    {
        "amount": 45.99,
        "transaction_type": "purchase",
        "merchant_name": "Coffee Shop",
        "merchant_category": "Food & Beverage",
        "merchant_country": "US",
        "customer_id": "CUST001",
        "payment_method": "credit_card",
        "transaction_country": "US",
        "ip_address": "192.168.1.100",
        "device_id": "device-001"
    },
    # Medium risk
    {
        "amount": 3500,
        "transaction_type": "purchase",
        "merchant_name": "Electronics Store",
        "merchant_category": "Electronics",
        "merchant_country": "MX",
        "customer_id": "CUST002",
        "payment_method": "credit_card",
        "transaction_country": "US",
        "transaction_city": "San Diego"
    },
    # High risk
    {
        "amount": 9500,
        "transaction_type": "transfer",
        "merchant_name": "Wire Transfer Service",
        "merchant_category": "Money Transfer",
        "merchant_country": "XX",
        "customer_id": "CUST003",
        "payment_method": "prepaid_card",
        "transaction_country": "US"
    },
    # Fraudulent
    {
        "amount": 15000,
        "transaction_type": "withdrawal",
        "merchant_name": "Suspicious ATM Network",
        "merchant_category": "ATM",
        "merchant_country": "YY",
        "customer_id": "CUST004",
        "payment_method": "prepaid_card",
        "transaction_country": "XX"
    }
]

async def test_streaming_mode():
    """Test transactions via Kafka streaming"""
    print("🚀 Testing Kafka Streaming Mode")
    print("=" * 50)
    
    async with aiohttp.ClientSession() as session:
        # Submit transactions in streaming mode
        for i, transaction in enumerate(TEST_TRANSACTIONS):
            try:
                async with session.post(
                    'http://localhost:8000/api/v1/transactions?stream_mode=true',
                    json=transaction
                ) as response:
                    result = await response.json()
                    print(f"\n✅ Transaction {i+1} submitted to stream")
                    print(f"   Amount: ${transaction['amount']}")
                    print(f"   Merchant: {transaction['merchant_name']}")
                    print(f"   Status: {result.get('status', 'pending')}")
                    
            except Exception as e:
                print(f"❌ Error submitting transaction {i+1}: {e}")
            
            # Small delay between submissions
            await asyncio.sleep(0.5)

async def test_batch_processing():
    """Test batch transaction processing"""
    print("\n\n📦 Testing Batch Processing")
    print("=" * 50)
    
    # Generate batch of transactions
    batch_transactions = []
    for i in range(10):
        transaction = TEST_TRANSACTIONS[i % len(TEST_TRANSACTIONS)].copy()
        transaction["amount"] = round(random.uniform(50, 5000), 2)
        transaction["customer_id"] = f"BATCH-{i:03d}"
        batch_transactions.append(transaction)
    
    async with aiohttp.ClientSession() as session:
        try:
            async with session.post(
                'http://localhost:8000/api/v1/transactions/batch',
                json=batch_transactions
            ) as response:
                result = await response.json()
                print(f"✅ Batch submitted successfully")
                print(f"   Submitted: {result['submitted_count']}")
                print(f"   Failed: {result['failed_count']}")
                
        except Exception as e:
            print(f"❌ Error submitting batch: {e}")

async def check_streaming_status():
    """Check streaming system status"""
    print("\n\n📊 Streaming System Status")
    print("=" * 50)
    
    async with aiohttp.ClientSession() as session:
        try:
            async with session.get(
                'http://localhost:8000/api/v1/streaming/status'
            ) as response:
                status = await response.json()
                print(json.dumps(status, indent=2))
                
        except Exception as e:
            print(f"❌ Error checking status: {e}")

async def main():
    """Run all tests"""
    print("🧪 Fraud Detection Streaming Test Suite")
    print("=" * 50)
    print("Make sure:")
    print("1. Kafka is running (docker-compose up)")
    print("2. FastAPI server is running")
    print("3. WebSocket client is connected (open test_websocket_client.html)")
    print()
    
    input("Press Enter to start tests...")
    
    # Run tests
    await test_streaming_mode()
    await asyncio.sleep(2)  # Let consumer process
    
    await test_batch_processing()
    await asyncio.sleep(2)  # Let consumer process
    
    await check_streaming_status()
    
    print("\n\n✅ Tests completed! Check the WebSocket client for real-time alerts.")

if __name__ == "__main__":
    asyncio.run(main())