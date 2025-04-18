import requests

MCP_SERVER_URL = "http://localhost:8000/chat"

class ChatbotSDK:
    
    def __init__(self, session_id="user_123"):
        self.session_id = session_id

    def send_message(self, user_input):
        payload = {"query": user_input,"session_id": self.session_id} 
        
        try:
            response = requests.post(MCP_SERVER_URL, json=payload)
            if response.status_code == 200:
                return response.json().get("response", "No response received.")
            else:
                return f"Error: {response.status_code}, {response.text}"
        except requests.exceptions.RequestException as e:
            return f"Request Error: {e}"

if __name__ == "__main__":
    chatbot = ChatbotSDK()
    print("Chatbot is ready! Type 'exit' to quit.")

    while True:
        user_input = input("You: ")
        if user_input.lower() == "exit":
            print("Goodbye!")
            break

        ai_response = chatbot.send_message(user_input)
        print(f"AI: {ai_response}")
