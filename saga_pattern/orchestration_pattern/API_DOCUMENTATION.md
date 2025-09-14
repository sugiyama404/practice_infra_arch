# Saga Pattern Orchestration Services API Documentation

## Overview
This document describes all the services in the Saga Pattern Orchestration system, including their URLs, service names, endpoints, request bodies, and response bodies.

## Service URLs and Ports

Based on the docker-compose configuration:

- **Saga Orchestrator**: http://localhost:8005
- **Order Service**: http://localhost:8011
- **Inventory Service**: http://localhost:8012
- **Payment Service**: http://localhost:8013
- **Shipping Service**: http://localhost:8014

## 1. Order Service (order-service)

**Base URL**: http://localhost:8011

### POST /orders
**Description**: Create a new order and publish OrderCreated event

**Request Body**:
```json
{
  "customer_id": "string",
  "items": [
    {
      "book_id": "string",
      "quantity": 1
    }
  ],
  "notes": "string (optional)"
}
```

**Response Body**:
```json
{
  "order_id": "string",
  "status": "created",
  "total_amount": 3500.0,
  "message": "Order created successfully"
}
```

### GET /orders/{order_id}
**Description**: Get order details

**Response Body**:
```json
{
  "order_id": "string",
  "customer_id": "string",
  "status": "PENDING|COMPLETED|CANCELLED",
  "total_amount": 3500.0,
  "created_at": "2023-01-01T00:00:00",
  "updated_at": "2023-01-01T00:00:00"
}
```

### PUT /orders/{order_id}/cancel
**Description**: Cancel order and publish OrderCancelled event

**Response Body**:
```json
{
  "message": "Order cancelled successfully"
}
```

### GET /health
**Description**: Health check endpoint

**Response Body**:
```json
{
  "status": "healthy",
  "service": "order-service"
}
```

## 2. Inventory Service (inventory-service)

**Base URL**: http://localhost:8012

### POST /inventory/reserve
**Description**: Reserve stock for an item

**Request Body** (Direct):
```json
{
  "book_id": "string",
  "quantity": 1
}
```

**Request Body** (Command structure):
```json
{
  "payload": {
    "book_id": "string",
    "quantity": 1
  }
}
```

**Response Body**:
```json
{
  "message": "Stock reserved successfully"
}
```

### POST /inventory/release
**Description**: Release reserved stock (compensation)

**Request Body** (Direct):
```json
{
  "book_id": "string",
  "quantity": 1
}
```

**Request Body** (Command structure):
```json
{
  "payload": {
    "book_id": "string",
    "quantity": 1
  }
}
```

**Response Body**:
```json
{
  "message": "Stock released successfully"
}
```

### GET /inventory/{book_id}
**Description**: Get inventory details

**Response Body**:
```json
{
  "book_id": "string",
  "available_stock": 100,
  "reserved_stock": 5,
  "total_stock": 105
}
```

### GET /health
**Description**: Health check endpoint

**Response Body**:
```json
{
  "status": "healthy",
  "service": "inventory-service"
}
```

## 3. Payment Service (payment-service)

**Base URL**: http://localhost:8013

### POST /payments/process
**Description**: Process payment for an order

**Request Body** (Direct):
```json
{
  "order_id": "string",
  "amount": 3500.0
}
```

**Request Body** (Command structure):
```json
{
  "payload": {
    "order_id": "string",
    "amount": 3500.0
  }
}
```

**Response Body** (Success):
```json
{
  "message": "Payment processed successfully",
  "payment_id": "string"
}
```

### GET /payments/{order_id}
**Description**: Get payment details

**Response Body**:
```json
{
  "payment_id": "string",
  "order_id": "string",
  "amount": 3500.0,
  "status": "COMPLETED|FAILED|CANCELLED|REFUNDED",
  "transaction_id": "txn_123456",
  "processed_at": "2023-01-01T00:00:00"
}
```

### POST /payments/cancel
**Description**: Cancel payment (compensation)

**Request Body** (Direct):
```json
{
  "order_id": "string"
}
```

**Request Body** (Command structure):
```json
{
  "payload": {
    "order_id": "string"
  }
}
```

**Response Body**:
```json
{
  "message": "Payment cancelled successfully"
}
```

### GET /health
**Description**: Health check endpoint

**Response Body**:
```json
{
  "status": "healthy",
  "service": "payment-service"
}
```

## 4. Shipping Service (shipping-service)

**Base URL**: http://localhost:8014

### POST /shipping/arrange
**Description**: Arrange shipping for an order

**Request Body** (Direct):
```json
{
  "order_id": "string"
}
```

**Request Body** (Command structure):
```json
{
  "payload": {
    "order_id": "string"
  }
}
```

**Response Body** (Success):
```json
{
  "message": "Shipping arranged successfully",
  "shipment_id": "string"
}
```

### GET /shipping/{order_id}
**Description**: Get shipment details

**Response Body**:
```json
{
  "shipment_id": "string",
  "order_id": "string",
  "carrier": "Demo Carrier",
  "tracking_number": "TRK12345678",
  "status": "ARRANGED|CANCELLED|SHIPPED",
  "estimated_delivery": "2023-01-04T00:00:00",
  "shipping_cost": 500.0
}
```

### POST /shipping/cancel
**Description**: Cancel shipping arrangement (compensation)

**Request Body** (Direct):
```json
{
  "order_id": "string"
}
```

**Request Body** (Command structure):
```json
{
  "payload": {
    "order_id": "string"
  }
}
```

**Response Body**:
```json
{
  "message": "Shipping cancelled successfully"
}
```

### GET /health
**Description**: Health check endpoint

**Response Body**:
```json
{
  "status": "healthy",
  "service": "shipping-service"
}
```

## 5. Saga Orchestrator (saga-orchestrator)

**Base URL**: http://localhost:8005

### POST /saga/start
**Description**: Start a new saga workflow

**Request Body**:
```json
{
  "customer_id": "string",
  "items": [
    {
      "book_id": "string",
      "quantity": 1
    }
  ],
  "notes": "string (optional)"
}
```

**Response Body**:
```json
{
  "saga_id": "string",
  "order_id": "string",
  "status": "STARTED",
  "message": "Saga started successfully"
}
```

### GET /saga/{saga_id}/status
**Description**: Get saga status and step details

**Response Body**:
```json
{
  "saga_id": "string",
  "saga_type": "ORDER_PROCESSING",
  "order_id": "string",
  "status": "STARTED|COMPLETED|FAILED",
  "created_at": "2023-01-01T00:00:00",
  "completed_at": "2023-01-01T00:00:00",
  "steps": [
    {
      "step_number": 1,
      "step_name": "inventory.reserve_stock",
      "service_name": "inventory",
      "status": "COMPLETED|FAILED",
      "started_at": "2023-01-01T00:00:00",
      "completed_at": "2023-01-01T00:00:00",
      "duration_ms": 150
    }
  ]
}
```

### POST /saga/{saga_id}/cancel
**Description**: Cancel a running saga

**Response Body**:
```json
{
  "message": "Saga cancelled successfully"
}
```

### GET /health
**Description**: Health check endpoint

**Response Body**:
```json
{
  "status": "healthy",
  "service": "saga-orchestrator"
}
```

## Event Flow

The services communicate through Redis pub/sub events:

1. **OrderCreated**: Published by Order Service when an order is created
2. **StockReserved**: Published by Inventory Service when stock is reserved
3. **StockUnavailable**: Published by Inventory Service when stock is insufficient
4. **PaymentCompleted**: Published by Payment Service when payment succeeds
5. **PaymentFailed**: Published by Payment Service when payment fails
6. **ShippingArranged**: Published by Shipping Service when shipping is arranged
7. **ShippingFailed**: Published by Shipping Service when shipping fails
8. **OrderCancelled**: Published by Order Service when order is cancelled
9. **StockReleased**: Published by Inventory Service when stock is released
10. **PaymentRefunded**: Published by Payment Service when payment is refunded
11. **ShippingCancelled**: Published by Shipping Service when shipping is cancelled

## Notes

- All services support both direct payload format and command structure format for requests
- The Saga Orchestrator coordinates the entire workflow and handles compensations on failure
- Services listen to relevant events via Redis pub/sub for event-driven communication
- All monetary values are in float format
- Timestamps are in ISO 8601 format
