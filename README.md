# Gen Z Workplace Coach - Web Chatbot

This is a simple, web-based AI coach that helps people handle workplace situations. It uses a small frontend (HTML/CSS/JS) and a Python Flask backend. The backend retrieves relevant examples from a vector database (Qdrant) and asks OpenAI to produce helpful coaching replies using two short frameworks (STEP and 4Rs). The app supports a two-step quick-reply flow: first the user chooses a tone (Professional or Casual), then the bot offers topic quick-replies (e.g. Work relationships).

This README explains how the whole system works in plain language and gives step-by-step instructions for someone who already has a frontend and wants to plug our backend in while keeping all features (tone selection, quick replies, session behavior).

## How it works (plain language)

- You open the web page. The chat shows a short greeting.
- You type something (e.g. "hi"). The frontend sends that text to the backend endpoint `/api/chat`.
- The backend uses a tiny set of rules and AI to decide what to do next:
	- If this is the first user message, the bot replies and returns two quick-reply buttons for tone selection: "Professional" and "Casual".
	- If the user clicks a tone, the frontend sends that tone as a message (e.g. "Professional"). The backend stores that choice in the session and replies confirming the tone.
	- After a tone is chosen the backend returns topic quick-replies (Work relationships, Stress & deadlines, Career growth, Team conflicts).
	- When you pick a topic or type a full question, the backend: 1) fetches short context examples from Qdrant, 2) builds a prompt using the chosen tone and coaching frameworks, 3) asks OpenAI for a reply and sends it back to the frontend.

All chat history is stored in the browser session (Flask session cookie). By design the app clears history when the page is refreshed to keep the demo stateless and private.

## What you need (prerequisites)

- Python 3.10+ (or a recent 3.x)
- A virtual environment (recommended)
- API keys and services:
	- OpenAI API key (set as `OPENAI_API_KEY`)
	- Qdrant URL and API key (set as `QDRANT_URL` and `QDRANT_API_KEY`)
	- Google Generative AI key if you use Google embeddings (`GOOGLE_API_KEY`) — optional depending on your setup
- The repository code (backend files: `app.py`, template `templates/index.html`, and static assets)

## Environment variables (put in a `.env` file or set in your environment)

- OPENAI_API_KEY=sk-...
- QDRANT_URL=https://... (your Qdrant HTTP(s) URL)
- QDRANT_API_KEY=...(if your Qdrant requires an API key)
- GOOGLE_API_KEY=... (only if using Google embeddings)
- FLASK_SECRET_KEY=some-secret
- PORT=5001 (optional)

## Install and run (Windows example)

Open a command prompt in the project folder and run:

```powershell
# 1. Create virtual environment
python -m venv venv

# 2. Activate virtual environment
.\venv\Scripts\activate

# 3. Install dependencies
pip install -r requirements.txt

# 4. Create .env file from example
copy .env.example .env

# 5. Edit .env file and add your API keys
notepad .env

# 6. Run the app
python app.py
```

Visit `http://localhost:5001` in your browser.

**For Linux/Mac:**
```bash
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
cp .env.example .env
nano .env  # or use any text editor
python app.py
```

## Backend endpoints you will use from your frontend

- POST /api/chat  
	- Request JSON: { "message": "user text" }
	- Response JSON: { "response": "AI text", "quick_replies": [ ... ], "success": true }
	- Behavior: returns a reply plus an array of quick replies (which can be tone buttons or topic buttons depending on conversation step).

- GET /api/history  
	- Returns the session's saved chat history: { "history": [...] }

- POST /api/clear  
	- Clears the session chat history. Response: { "success": true }

- GET /health  
	- Returns service health info. Useful for monitoring.

## Quick frontend integration (human-friendly)

If someone already has a frontend (HTML + JS) and wants to use our backend while keeping the exact flow (tone selection → topics → full coaching), follow these steps.

1. Hook your send button (or message submit) to call `/api/chat` with a JSON body: `{ message: "text" }`.
2. When you get the response JSON, always display the `response` text as the bot's message.
3. If `quick_replies` is a non-empty array, render them as buttons under the bot message. When a user clicks a quick-reply button, send its label as a new message to `/api/chat` (just like typing it). The backend treats tone labels ("Professional" or "Casual") specially and will save the selection.

Example minimal client-side fetch (copy to your JS):

```javascript
async function sendToBackend(text) {
	const res = await fetch('/api/chat', {
		method: 'POST',
		headers: { 'Content-Type': 'application/json' },
		body: JSON.stringify({ message: text })
	});
	const data = await res.json();
	// data.response -> add to chat UI
	// data.quick_replies -> render buttons if present
	return data;
}
```

4. Tone behavior: when `quick_replies` contains `Professional` and `Casual`, show them prominently. When the user clicks one, send the button text to the backend. The backend will store the tone in the session and apply it to subsequent replies.

5. Session behavior: the backend clears chat history when the page is loaded. If you want to preserve history across refreshes instead, you can remove the clearing logic in `app.py` (the `index()` route).

## Troubleshooting & tips (non-technical)

- If buttons don't appear: open your browser dev tools (F12) → Console and Network. Look at the `/api/chat` response — it should include `quick_replies`.
- If the UI seems out-of-date after code changes: do a hard refresh (Ctrl+Shift+R) to clear cached JS/CSS.
- If the app doesn't start: make sure you activated the virtual environment and installed packages in that environment.
- If embeddings or Qdrant responses are empty: double-check `QDRANT_URL` and `QDRANT_API_KEY` and that your collection name (`bridgetext_scenarios`) exists.

## Customization ideas (if you want to extend)

- Add more tone options (e.g., Empathetic, Direct).
- Persist user preferences to a database instead of session cookies.
- Add analytics to track which quick replies users choose.

## Deploy to Render (cloud hosting)

Your code is ready to deploy to Render! Follow these steps:

### Step 1: Push your code to GitHub
1. Create a new GitHub repository
2. Push this entire folder to GitHub (make sure `.env` is in `.gitignore` - never push API keys!)

### Step 2: Create a Web Service on Render
1. Go to [render.com](https://render.com) and sign in
2. Click "New +" → "Web Service"
3. Connect your GitHub repository
4. Render will auto-detect the settings from your `Procfile`

### Step 3: Configure Environment Variables
In the Render dashboard, add these environment variables:

| Key | Value | Where to get it |
|-----|-------|----------------|
| `OPENAI_API_KEY` | sk-... | OpenAI dashboard |
| `QDRANT_URL` | https://... | Qdrant Cloud dashboard (your cluster URL) |
| `QDRANT_API_KEY` | ... | Qdrant Cloud dashboard (API key) |
| `GOOGLE_API_KEY` | ... | Google AI Studio |
| `FLASK_SECRET_KEY` | any-random-string | Generate a random string (e.g., `openssl rand -hex 32`) |

### Step 4: Deploy
1. Click "Create Web Service"
2. Render will install packages from `requirements.txt` and start your app with gunicorn
3. Wait 2-3 minutes for the build to complete
4. Visit your app at the URL Render provides (e.g., `https://your-app.onrender.com`)

### Important Notes:
- ✅ Your app is already configured to use `PORT` from environment (Render sets this automatically)
- ✅ gunicorn is included in requirements for production serving
- ✅ Host `0.0.0.0` allows external connections
- ⚠️ Free tier on Render: app will sleep after 15 min of inactivity (first request after sleep takes ~30 sec)
- ⚠️ Make sure your Qdrant cluster allows connections from Render's IP addresses

## Push to GitHub

**First time setup:**
```bash
git init
git add .
git commit -m "Initial commit: Gen Z Workplace Coach chatbot"
git branch -M main
git remote add origin https://github.com/yourusername/your-repo-name.git
git push -u origin main
```

**Important:** The `.gitignore` file will automatically prevent your `.env` file (with API keys) from being uploaded. Only `.env.example` (without real keys) will be shared.

---

If you want, I can also generate a tiny integration snippet specific to your frontend framework (React / Vue / plain JS). Tell me which one and I will create it.

