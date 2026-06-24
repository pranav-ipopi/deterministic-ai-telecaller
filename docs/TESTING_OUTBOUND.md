# Testing Outbound Calls (End-to-End Local Setup)

This guide walks you through testing the entire outbound calling flow locally on your PC using Docker.

---

## Prerequisites

1. **Docker Desktop** is running.
2. The AI Telecaller services are running. You can start them by opening a terminal in your project directory and running:
   ```bash
   docker compose up --build -d
   ```
3. You have the `SHARED_API_KEY` from your `api/.env` file. You will need this for authorization when triggering calls.

---

## Step 1: Create a Client (Dealership)

The system needs to know the client's instructions, voice, and language preferences before it can make a call.

1. Open your browser and go to: **[http://localhost:8080/admin](http://localhost:8080/admin)**
2. Log in using the admin password defined in your `api/.env` file (e.g., `Password@123`).
3. Click **+ Add dealership**.
4. Fill out the details:
   * **Customer name:** `MyTestClient` *(This is the unique ID you will pass in the API)*
   * **Dealership name:** `My Test Client Motors`
   * **Language:** `en-IN` (Indian English) or `hi-IN` (Hindi)
   * **Voice:** `rahul` (Male) or `meera` (Female)
   * **Callback URL:** *To see the final call result, go to [webhook.site](https://webhook.site/), copy the unique URL they give you, and paste it here.*
   * **Extra prompt:** You can add specific instructions here, e.g., *"Mention the 10% holiday discount if they ask about pricing."*
5. Click **Save & sync**.

---

## Step 2: Trigger the Outbound Call

Simulate your CRM sending a new lead to the AI Telecaller API. You can use Postman, or simply run a `curl` command.

### Using Postman
1. **Method:** `POST`
2. **URL:** `http://localhost:8080/dispatch`
3. **Headers:**
   * `Content-Type`: `application/json`
   * `X-API-Key`: `<Your SHARED_API_KEY from api/.env>`
4. **Body (raw JSON):**
   ```json
   {
     "customer_name": "MyTestClient",
     "lead_id": 1001,
     "name": "John Doe",
     "phone": "+919876543210",
     "model": "Tata Nexon",
     "location": "Delhi"
   }
   ```
   *(Be sure to replace the `phone` value with your actual mobile number!)*

### Using PowerShell
If you don't want to use Postman, you can run this in your terminal:
```powershell
curl.exe -X POST http://localhost:8080/dispatch `
  -H "Content-Type: application/json" `
  -H "X-API-Key: YOUR_SHARED_API_KEY" `
  -d '{
    "customer_name": "MyTestClient",
    "lead_id": 1001,
    "name": "John Doe",
    "phone": "+919876543210",
    "model": "Tata Nexon",
    "location": "Delhi"
  }'
```

---

## Step 3: Answer the Call

1. Once you send the request, you should receive a `202 Accepted` response from the API.
2. The API forwards the request to LiveKit, which assigns the task to your local `ai-telecaller-agent-outbound` container.
3. Within **3 to 5 seconds**, your phone will ring.
4. Pick up the phone. The AI will introduce itself based on the dealership name and lead data you provided. 
5. Answer its questions (it will ask about your location, timeline, etc.) and then end the call.

*(To view the agent's live logs during the call, run `docker logs -f ai-telecaller-agent-outbound` in your terminal).*

---

## Step 4: Verify the Results

As soon as the call ends, the local agent automatically computes the duration, cost, lead status, and generates a transcript. It then POSTs this data back to the `Callback URL` you provided in Step 1.

If you used [webhook.site](https://webhook.site/), go back to that browser tab. You will see a new incoming POST request containing the final JSON payload.

**Example Result Payload:**
```json
{
  "lead_id": 1001,
  "name": "John Doe",
  "model": "Tata Nexon",
  "location": "Delhi",
  "cost": 1.4500,
  "status_id": 2,
  "tries": 1,
  "remarks": "Hot lead | Timing: looking to buy next week",
  "conversation": [
    {"id": 1, "who": "agent", "message": "Hi, am I speaking with John Doe? This is John from My Test Client Motors."},
    {"id": 2, "who": "customer", "message": "Yes, speaking."},
    {"id": 3, "who": "agent", "message": "Great! Are you still looking for a Tata Nexon in Delhi?"}
  ]
}
```

**Testing Complete!** Your local outbound architecture is fully verified.
