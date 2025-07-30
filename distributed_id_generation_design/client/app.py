import requests
import time

snowflake_url = "http://snowflake:8080/generate"
ticket_url = "http://ticket-server:8080/generate"


if __name__ == "__main__":
    print("Starting ID generation client...")
    time.sleep(2)  # Wait for services to start
    print("Generating IDs from Snowflake and Ticket Server:")
    for _ in range(5):
        sf = requests.get(snowflake_url).json()
        tk = requests.get(ticket_url).json()
        print(f"Snowflake ID: {sf['id']}, Ticket ID: {tk['id']}")
        time.sleep(1)
    print("ID generation completed.")
