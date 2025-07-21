import requests

snowflake_url = "http://snowflake:8080/generate"
ticket_url = "http://ticket-server:8080/generate"

for _ in range(5):
    sf = requests.get(snowflake_url).json()
    tk = requests.get(ticket_url).json()
    print(f"Snowflake ID: {sf['id']}, Ticket ID: {tk['id']}")
