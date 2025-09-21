# Single API with Pessimistic Locking

This directory contains an implementation of the order processing system using a single API endpoint and pessimistic locking (`SELECT ... FOR UPDATE`) to ensure data consistency.

## Architecture

*   **API**: A single FastAPI endpoint (`/orders`).
*   **Database**: A single MySQL database.
*   **Locking**: Pessimistic locking is used on the `inventory` table during order processing to prevent race conditions.

## How to Run

1.  **Start the services:**
    ```bash
    docker-compose up -d --build
    ```

2.  **Check the logs:**
    ```bash
    docker-compose logs -f app
    ```

3.  **Send a request:**
    ```bash
    curl -X POST http://localhost:8006/orders -H "Content-Type: application/json" -d '{"customer_id": "customer-001", "items": [{"book_id": "book-123", "quantity": 1}]}'
    ```
