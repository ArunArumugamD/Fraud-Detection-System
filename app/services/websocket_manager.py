import json
import logging
from typing import Dict, List, Set
from fastapi import WebSocket, WebSocketDisconnect
from datetime import datetime

logger = logging.getLogger(__name__)


class WebSocketManager:
    """
    Manages WebSocket connections for real-time fraud alerts
    """
    
    def __init__(self):
        self.active_connections: List[WebSocket] = []
        self.connection_metadata: Dict[WebSocket, Dict] = {}
        
    async def connect(self, websocket: WebSocket, client_id: str = None):
        """Accept a new WebSocket connection"""
        await websocket.accept()
        self.active_connections.append(websocket)
        
        # Store metadata
        self.connection_metadata[websocket] = {
            "client_id": client_id,
            "connected_at": datetime.utcnow().isoformat(),
            "alerts_received": 0
        }
        
        logger.info(f"WebSocket client {client_id} connected. Total connections: {len(self.active_connections)}")
        
        # Send welcome message
        await websocket.send_json({
            "type": "connection",
            "message": "Connected to fraud detection alert system",
            "timestamp": datetime.utcnow().isoformat()
        })
    
    def disconnect(self, websocket: WebSocket):
        """Remove a WebSocket connection"""
        if websocket in self.active_connections:
            self.active_connections.remove(websocket)
            
        metadata = self.connection_metadata.pop(websocket, {})
        client_id = metadata.get("client_id", "unknown")
        
        logger.info(f"WebSocket client {client_id} disconnected. Remaining connections: {len(self.active_connections)}")
    
    async def send_alert(self, alert_data: Dict):
        """Send fraud alert to all connected clients"""
        if not self.active_connections:
            return
        
        # Prepare alert message
        message = {
            "type": "fraud_alert",
            "data": alert_data,
            "timestamp": datetime.utcnow().isoformat()
        }
        
        # Send to all active connections
        disconnected = []
        for connection in self.active_connections:
            try:
                await connection.send_json(message)
                
                # Update metadata
                if connection in self.connection_metadata:
                    self.connection_metadata[connection]["alerts_received"] += 1
                    
            except Exception as e:
                logger.error(f"Error sending alert to WebSocket: {e}")
                disconnected.append(connection)
        
        # Clean up disconnected clients
        for connection in disconnected:
            self.disconnect(connection)
    
    async def send_personal_alert(self, client_id: str, alert_data: Dict):
        """Send alert to specific client"""
        for connection, metadata in self.connection_metadata.items():
            if metadata.get("client_id") == client_id:
                try:
                    await connection.send_json({
                        "type": "personal_alert",
                        "data": alert_data,
                        "timestamp": datetime.utcnow().isoformat()
                    })
                except Exception as e:
                    logger.error(f"Error sending personal alert to {client_id}: {e}")
    
    async def broadcast_stats(self, stats: Dict):
        """Broadcast system statistics to all clients"""
        message = {
            "type": "system_stats",
            "data": stats,
            "timestamp": datetime.utcnow().isoformat()
        }
        
        for connection in self.active_connections:
            try:
                await connection.send_json(message)
            except:
                pass
    
    def get_connection_stats(self) -> Dict:
        """Get WebSocket connection statistics"""
        return {
            "active_connections": len(self.active_connections),
            "connection_details": [
                {
                    "client_id": meta.get("client_id"),
                    "connected_at": meta.get("connected_at"),
                    "alerts_received": meta.get("alerts_received", 0)
                }
                for meta in self.connection_metadata.values()
            ]
        }


# Create singleton instance
websocket_manager = WebSocketManager()