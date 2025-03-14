import os
import asyncio
from fastapi import FastAPI, Depends, HTTPException, Request, BackgroundTasks
from fastapi.security import APIKeyHeader
from fastapi.middleware.cors import CORSMiddleware
from typing import Dict, Any, List, Optional
from datetime import datetime
from ib_insync import IB, Contract, util
import logging
import json

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Initialize FastAPI app
app = FastAPI(
    title="IBEam API",
    description="API for Interactive Brokers using ib_insync",
    version="1.0.0"
)

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Restrict in production
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# API Key security
API_KEY = os.environ.get("API_KEY", "")
api_key_header = APIKeyHeader(name="X-API-Key")

# IB credentials from environment
IB_USERNAME = os.environ.get("IB_USERNAME", "")
IB_PASSWORD = os.environ.get("IB_PASSWORD", "")
USER_ID = os.environ.get("USER_ID", "")
ENVIRONMENT = os.environ.get("ENVIRONMENT", "development")

# Global IB instance
ib = IB()
connected = False

# Server state
server_state = {
    "status": "initializing",
    "user_id": USER_ID,
    "account_id": f"ib_{IB_USERNAME}",
    "connected": False,
    "last_connected": None,
    "startup_time": datetime.utcnow().isoformat(),
    "ib_gateway_version": None,
    "error_message": None
}

# Security dependency
async def verify_api_key(api_key: str = Depends(api_key_header)):
    if api_key != API_KEY:
        raise HTTPException(
            status_code=401,
            detail="Invalid API Key"
        )
    return api_key

# Helper functions
def contract_to_dict(contract):
    """Convert IB contract to dictionary"""
    if not contract:
        return None
    
    return {
        "symbol": contract.symbol,
        "secType": contract.secType,
        "exchange": contract.exchange,
        "currency": contract.currency,
        "localSymbol": contract.localSymbol,
        "conId": contract.conId
    }

def position_to_dict(position):
    """Convert IB position to dictionary"""
    if not position:
        return None
    
    return {
        "symbol": position.contract.symbol,
        "secType": position.contract.secType,
        "exchange": position.contract.exchange,
        "currency": position.contract.currency,
        "position": position.position,
        "avgCost": position.avgCost,
        "marketPrice": position.marketPrice,
        "marketValue": position.marketValue,
        "unrealizedPNL": position.unrealizedPNL,
        "realizedPNL": position.realizedPNL
    }

def order_to_dict(trade):
    """Convert IB trade/order to dictionary"""
    if not trade:
        return None
    
    return {
        "orderId": trade.order.orderId,
        "clientId": trade.order.clientId,
        "action": trade.order.action,
        "totalQuantity": trade.order.totalQuantity,
        "orderType": trade.order.orderType,
        "lmtPrice": trade.order.lmtPrice,
        "auxPrice": trade.order.auxPrice,
        "status": trade.orderStatus.status,
        "filled": trade.orderStatus.filled,
        "remaining": trade.orderStatus.remaining,
        "avgFillPrice": trade.orderStatus.avgFillPrice,
        "lastFillPrice": trade.orderStatus.lastFillPrice,
        "symbol": trade.contract.symbol,
        "secType": trade.contract.secType,
        "exchange": trade.contract.exchange
    }

# IB connection management
async def connect_to_ib():
    """Connect to Interactive Brokers"""
    global connected, server_state
    
    if connected:
        return True
    
    try:
        # Try to connect to IB Gateway/TWS
        # In production you would use the actual IB Gateway/TWS host and port
        # For testing, we'll just set the connected flag to True
        server_state["status"] = "connecting"
        
        # In a real implementation, you would uncomment this:
        # await ib.connectAsync("127.0.0.1", 7496, clientId=1)
        # connected = ib.isConnected()
        
        # For demo purposes
        connected = True
        server_state["connected"] = connected
        server_state["last_connected"] = datetime.utcnow().isoformat()
        server_state["status"] = "connected"
        server_state["ib_gateway_version"] = "Demo Version"
        
        return connected
    except Exception as e:
        logger.error(f"Error connecting to IB: {str(e)}")
        server_state["status"] = "error"
        server_state["error_message"] = str(e)
        connected = False
        server_state["connected"] = connected
        return False

async def disconnect_from_ib():
    """Disconnect from Interactive Brokers"""
    global connected, server_state
    
    if not connected:
        return True
    
    try:
        # In a real implementation:
        # ib.disconnect()
        
        connected = False
        server_state["connected"] = connected
        server_state["status"] = "disconnected"
        return True
    except Exception as e:
        logger.error(f"Error disconnecting from IB: {str(e)}")
        server_state["error_message"] = str(e)
        return False

# Startup event
@app.on_event("startup")
async def startup_event():
    """Startup event handler"""
    logger.info("Starting IBEam API Server")
    
    if not API_KEY:
        logger.warning("No API_KEY environment variable set")
    
    if not IB_USERNAME or not IB_PASSWORD:
        logger.warning("IB credentials not properly set in environment variables")
    
    # Attempt initial connection to IB
    background_tasks = BackgroundTasks()
    background_tasks.add_task(connect_to_ib)

# Shutdown event
@app.on_event("shutdown")
async def shutdown_event():
    """Shutdown event handler"""
    logger.info("Shutting down IBEam API Server")
    await disconnect_from_ib()

# API endpoints
@app.get("/health")
async def health_check():
    """Health check endpoint"""
    return {
        "status": "healthy",
        "timestamp": datetime.utcnow().isoformat(),
        "service": "ibearmy",
        "user_id": USER_ID,
        "ib_connection": connected
    }

@app.get("/status", dependencies=[Depends(verify_api_key)])
async def get_status():
    """Get server status"""
    return server_state

@app.post("/connect", dependencies=[Depends(verify_api_key)])
async def connect():
    """Connect to Interactive Brokers"""
    success = await connect_to_ib()
    return {
        "success": success,
        "status": server_state["status"],
        "timestamp": datetime.utcnow().isoformat()
    }

@app.post("/disconnect", dependencies=[Depends(verify_api_key)])
async def disconnect():
    """Disconnect from Interactive Brokers"""
    success = await disconnect_from_ib()
    return {
        "success": success,
        "status": server_state["status"],
        "timestamp": datetime.utcnow().isoformat()
    }

@app.get("/accounts", dependencies=[Depends(verify_api_key)])
async def get_accounts():
    """Get IB accounts"""
    if not connected:
        connected = await connect_to_ib()
    
    if not connected:
        raise HTTPException(status_code=503, detail="Not connected to IB")
    
    # In a real implementation, you would get accounts from IB
    # For demo, return a mock account
    account = {
        "account_id": f"ib_{IB_USERNAME}",
        "type": "securities",
        "name": "Securities Account",
        "currency": "USD",
        "balance": 10000.0,
        "equity": 10500.0,
        "margin": 2000.0,
        "available_funds": 8000.0
    }
    
    return [account]

@app.get("/positions", dependencies=[Depends(verify_api_key)])
async def get_positions():
    """Get positions for the account"""
    if not connected:
        connected = await connect_to_ib()
    
    if not connected:
        raise HTTPException(status_code=503, detail="Not connected to IB")
    
    # In a real implementation, you would get positions from IB
    # For demo, return mock positions
    positions = [
        {
            "symbol": "AAPL",
            "secType": "STK",
            "exchange": "SMART",
            "currency": "USD",
            "position": 100,
            "avgCost": 150.0,
            "marketPrice": 155.0,
            "marketValue": 15500.0,
            "unrealizedPNL": 500.0,
            "realizedPNL": 0.0
        },
        {
            "symbol": "MSFT",
            "secType": "STK",
            "exchange": "SMART",
            "currency": "USD",
            "position": 50,
            "avgCost": 250.0,
            "marketPrice": 260.0,
            "marketValue": 13000.0,
            "unrealizedPNL": 500.0,
            "realizedPNL": 200.0
        }
    ]
    
    return positions

@app.get("/orders", dependencies=[Depends(verify_api_key)])
async def get_orders():
    """Get orders for the account"""
    if not connected:
        connected = await connect_to_ib()
    
    if not connected:
        raise HTTPException(status_code=503, detail="Not connected to IB")
    
    # In a real implementation, you would get orders from IB
    # For demo, return mock orders
    orders = [
        {
            "orderId": 1,
            "clientId": 1,
            "action": "BUY",
            "totalQuantity": 100,
            "orderType": "LMT",
            "lmtPrice": 150.0,
            "auxPrice": 0.0,
            "status": "Filled",
            "filled": 100,
            "remaining": 0,
            "avgFillPrice": 149.5,
            "lastFillPrice": 149.5,
            "symbol": "AAPL",
            "secType": "STK",
            "exchange": "SMART"
        }
    ]
    
    return orders

@app.post("/orders", dependencies=[Depends(verify_api_key)])
async def place_order(order_data: Dict[str, Any]):
    """Place a new order"""
    if not connected:
        connected = await connect_to_ib()
    
    if not connected:
        raise HTTPException(status_code=503, detail="Not connected to IB")
    
    # Validate order data
    required_fields = ["symbol", "action", "quantity", "orderType"]
    for field in required_fields:
        if field not in order_data:
            raise HTTPException(status_code=400, detail=f"Missing required field: {field}")
    
    # In a real implementation, you would place an order with IB
    # For demo, return a mock order confirmation
    new_order = {
        "orderId": 2,
        "clientId": 1,
        "action": order_data["action"],
        "totalQuantity": order_data["quantity"],
        "orderType": order_data["orderType"],
        "lmtPrice": order_data.get("limitPrice", 0.0),
        "auxPrice": order_data.get("stopPrice", 0.0),
        "status": "PreSubmitted",
        "filled": 0,
        "remaining": order_data["quantity"],
        "avgFillPrice": 0.0,
        "lastFillPrice": 0.0,
        "symbol": order_data["symbol"],
        "secType": order_data.get("secType", "STK"),
        "exchange": order_data.get("exchange", "SMART")
    }
    
    return new_order

@app.delete("/orders/{order_id}", dependencies=[Depends(verify_api_key)])
async def cancel_order(order_id: int):
    """Cancel an existing order"""
    if not connected:
        connected = await connect_to_ib()
    
    if not connected:
        raise HTTPException(status_code=503, detail="Not connected to IB")
    
    # In a real implementation, you would cancel the order with IB
    # For demo, return a mock cancellation confirmation
    return {
        "orderId": order_id,
        "status": "Cancelled",
        "message": "Order cancelled successfully",
        "timestamp": datetime.utcnow().isoformat()
    }

@app.get("/marketdata/{symbol}", dependencies=[Depends(verify_api_key)])
async def get_market_data(symbol: str, sec_type: str = "STK", exchange: str = "SMART", currency: str = "USD"):
    """Get market data for a symbol"""
    if not connected:
        connected = await connect_to_ib()
    
    if not connected:
        raise HTTPException(status_code=503, detail="Not connected to IB")
    
    # In a real implementation, you would fetch market data from IB
    # For demo, return mock market data
    return {
        "symbol": symbol,
        "secType": sec_type,
        "exchange": exchange,
        "currency": currency,
        "last": 155.0,
        "bid": 154.9,
        "ask": 155.1,
        "high": 156.0,
        "low": 154.0,
        "volume": 5000000,
        "timestamp": datetime.utcnow().isoformat()
    }

# Main entry point
if __name__ == "__main__":
    import uvicorn
    port = int(os.environ.get("PORT", 8000))
    uvicorn.run("main:app", host="0.0.0.0", port=port, reload=False)