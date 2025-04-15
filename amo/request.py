import requests

url = "https://amo.style-ai.ru/amo/webhook"
data = {
    "test": "hello from test script"
}
if __name__ == "__main__":
    response = requests.post(url, data=data)  # вместо json=data
    print("Status code:", response.status_code)
    print("Response:", response.text)