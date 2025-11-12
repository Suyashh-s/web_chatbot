"""
Simple Web Chatbot - Uses Qdrant for context retrieval with OpenAI embeddings
"""

import os
from flask import Flask, render_template, request, jsonify, session
from flask_cors import CORS
from dotenv import load_dotenv
from qdrant_client import QdrantClient
from openai import OpenAI
import logging
from datetime import datetime

# Load environment variables
load_dotenv()

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Initialize Flask app
app = Flask(__name__)
app.secret_key = os.getenv("FLASK_SECRET_KEY", "your-secret-key")
CORS(app)

# Configuration
QDRANT_URL = os.getenv("QDRANT_URL")
QDRANT_API_KEY = os.getenv("QDRANT_API_KEY")
COLLECTION_NAME = "bridgetext_scenarios"
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")

# Global variables
qdrant_client = None
openai_client = None

def initialize_services():
    """Initialize Qdrant and OpenAI services"""
    global qdrant_client, openai_client
    
    try:
        logger.info("🔌 Connecting to services...")
        
        # Initialize Qdrant client
        qdrant_client = QdrantClient(
            url=QDRANT_URL,
            api_key=QDRANT_API_KEY
        )
        
        # Initialize OpenAI client (for embeddings AND chat)
        openai_client = OpenAI(api_key=OPENAI_API_KEY)
        
        logger.info("✅ All services initialized successfully")
        return True
        
    except Exception as e:
        logger.error(f"❌ Failed to initialize services: {str(e)}")
        return False

def get_relevant_context(user_message: str, top_k: int = 3) -> str:
    """Retrieve relevant context from Qdrant using OpenAI embeddings"""
    try:
        # Generate embedding using OpenAI (text-embedding-3-small model)
        embedding_response = openai_client.embeddings.create(
            model="text-embedding-3-small",
            input=user_message
        )
        query_vector = embedding_response.data[0].embedding
        
        # Search in Qdrant
        search_results = qdrant_client.search(
            collection_name=COLLECTION_NAME,
            query_vector=query_vector,
            limit=top_k
        )
        
        # Extract context from results
        context_parts = []
        for result in search_results:
            if hasattr(result, 'payload') and result.payload:
                text = result.payload.get('text', '') or result.payload.get('page_content', '')
                if text:
                    context_parts.append(text)
        
        return "\n\n".join(context_parts) if context_parts else "No relevant context found."
        
    except Exception as e:
        logger.error(f"Error retrieving context: {str(e)}")
        return "No context available."

def generate_response(user_message: str, context: str, chat_history: str = "", tone: str = "Professional", chat_length: int = 0) -> str:
    """Generate response using GPT-4o-mini with STEP + 4Rs framework and Qdrant context"""
    try:
        # Safety check - Physical violence/abuse (CRITICAL) - Only if it's clearly physical violence
        # Improved: Check for context to avoid false positives (e.g., "beat me in workload")
        violence_keywords = ['hit', 'punch', 'slap', 'kick', 'physical violence', 'physically hurt', 'assault', 'attack', 'threatened with violence']
        workload_context = ['workload', 'work load', 'tasks', 'deadline', 'pressure', 'stress', 'overwhelm']
        
        # Only trigger violence warning if violence keywords found AND no workload context
        has_violence_keyword = any(keyword in user_message.lower() for keyword in violence_keywords)
        has_workload_context = any(keyword in user_message.lower() for keyword in workload_context)
        
        # Special check for "beat" - only warn if it's clearly physical, not metaphorical
        if 'beat' in user_message.lower() and not has_workload_context:
            # Check if it's physical violence context
            physical_indicators = ['physically', 'hit me', 'hurt me', 'threatened', 'violence']
            if any(indicator in user_message.lower() for indicator in physical_indicators):
                return """⚠️ **This is serious.** Physical violence at work is illegal and unacceptable.

Please take action immediately:
• Document everything (dates, witnesses, injuries)
• Report to HR or higher management NOW
• Contact workplace violence hotline: 1-800-799-7233
• If you're in immediate danger, call 911

This isn't a communication issue — it's workplace abuse. I can't coach you through this, but I strongly urge you to protect yourself and report this."""
        
        # Regular violence keywords (excluding 'beat' which is handled above)
        if has_violence_keyword and not has_workload_context:
            return """⚠️ **This is serious.** Physical violence at work is illegal and unacceptable.

Please take action immediately:
• Document everything (dates, witnesses, injuries)
• Report to HR or higher management NOW
• Contact workplace violence hotline: 1-800-799-7233
• If you're in immediate danger, call 911

This isn't a communication issue — it's workplace abuse. I can't coach you through this, but I strongly urge you to protect yourself and report this."""
        
        # Safety check - Harmful content
        harmful_keywords = ['kill', 'murder', 'suicide', 'weapon', 'gun', 'knife', 'blood', 'stab', 'threat', 'harass']
        if any(keyword in user_message.lower() for keyword in harmful_keywords):
            return """⚠️ I'm concerned about what you've shared. If you're in immediate danger or witnessing illegal activity, please contact:

• Emergency Services: 911
• National Suicide Prevention Lifeline: 988
• Workplace Violence Hotline: 1-800-799-7233

I'm designed to help with workplace communication challenges, not crisis or safety situations. Please reach out to professionals who can provide proper support."""
        
        # Safety check - Health issues
        health_keywords = ['headache', 'sick', 'pain', 'fever', 'medication', 'doctor', 'hospital']
        if any(keyword in user_message.lower() for keyword in health_keywords):
            return "I'm specifically designed for workplace communication challenges. For health concerns, please consult a medical professional. Can we focus on a work-related communication or teamwork challenge instead?"
        
        # Special handling for message 3 - Ask about tone preference (ONLY if previous messages were normal)
        if chat_length == 3:
            return "Before we dive in — how would you like me to respond? Pick the style that feels right for you."
        
        # Special handling for tone selection - Use chat history to continue the conversation
        if user_message.strip() in ["Professional", "Casual"]:
            selected_tone = user_message.strip()
            
            # Get the user's last substantive message (not just tone selection)
            if chat_history:
                # Extract the last user message from chat history
                history_lines = chat_history.strip().split('\n')
                last_user_msg = None
                for line in reversed(history_lines):
                    if line.startswith('User:'):
                        last_user_msg = line.replace('User:', '').strip()
                        break
                
                # If we found their problem, respond to it directly in the selected tone
                if last_user_msg and last_user_msg not in ["Professional", "Casual"]:
                    # Don't just acknowledge tone - jump straight into helping with their problem
                    # The system prompt will handle the tone, just return empty to let GPT respond
                    pass  # Let it fall through to normal GPT response
            
            # If no context, just acknowledge
            return f"Perfect! I'll keep it {selected_tone.lower()}. What's going on?"
        
        # Define tone-specific instructions
        if tone == "Casual":
            tone_instruction = """• Use a CASUAL, Gen Z tone: relaxed, conversational, like texting a smart friend
• Use phrases like: "That sucks", "Ugh that's annoying", "Yeah I get it", "Super frustrating"
• Use contractions: "you're", "that's", "don't", "can't"
• Keep it SHORT and NATURAL - sound like you're texting, not writing an essay
• Be supportive but chill: "Okay let's figure this out" instead of "I understand your concern"
• Example casual response: "Ugh that's super frustrating. So the main issue is they're ghosting you? What part bothers you most - them ignoring you or how it makes you look?"
"""
        else:  # Professional
            tone_instruction = """• Use a PROFESSIONAL tone: measured, empathetic, but formal like a workplace mentor or HR coach
• Use complete sentences with proper grammar
• Use phrases like: "I understand this is challenging", "That's a difficult situation", "Let's explore this together"
• Be empathetic but maintain professional distance
• Avoid slang or Gen Z casual language
• Example professional response: "That's a challenging situation. It sounds like communication barriers are impacting your work. Have you had an opportunity to address this directly with your colleague?"
"""
        
        system_prompt = f"""You are a Gen Z workplace coach helping young professionals with work challenges.

Use these frameworks:
• STEP (Adaptability): Spot → Think → Engage → Perform
• 4Rs (Emotional Intelligence): Recognize → Regulate → Respect → Reflect

⸻

🎯 CRITICAL FORMATTING RULE - BULLETS MUST BE ON SEPARATE LINES:

**NEVER use numbered lists (1. 2. 3. 4.)**
**ALWAYS use bullet points (•) with LINE BREAKS between each point**

Each bullet point MUST start on a NEW LINE. This is MANDATORY.

✅ CORRECT FORMAT (Each bullet on separate line):
"Ugh that sounds rough. Here's how to handle it with STEP:

• **Spot** - Figure out which tasks are urgent vs just feeling urgent

• **Think** - Your boss might not know they're overloading you

• **Engage** - Ask for a quick 15-min priority check

• **Perform** - Track progress and escalate if needed

Sound good?"

❌ WRONG (Bullets inline, no line breaks):
"Here's STEP: • **Spot** - ... • **Think** - ... • **Engage** - ..."

❌ WRONG (Using numbers):
"1. **Spot** - ... 2. **Think** - ..."

EACH BULLET (•) MUST BE ON ITS OWN LINE WITH A BLANK LINE AFTER IT.

⸻

🎯 TONE:
{tone_instruction}

⸻

🎯 CONVERSATION RULES:

1. **When user selects tone (Professional/Casual)**: 
   - Look at chat history to see their problem
   - IMMEDIATELY address it in their selected tone
   - Don't make them repeat themselves

2. **Give actionable advice quickly**
   - After 1 question, jump to STEP or 4Rs
   - Use bullet points (•) with line breaks, never numbers

3. **Keep it conversational**
   - 3-5 bullet points max
   - Each bullet = 1-2 sentences
   - Add blank line after each bullet
   - End with "Sound good?" or "Worth trying?"

⸻

**CONTEXT FROM YOUR DATASET:**
{context}

**PREVIOUS CONVERSATION:**
{chat_history}

**USER JUST SAID:**
{user_message}

**YOUR RESPONSE (USE BULLETS • WITH LINE BREAKS, NOT INLINE):**"""

        response = openai_client.chat.completions.create(
            model="gpt-4o-mini",  # Using GPT-4o-mini for smarter responses
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_message}
            ],
            temperature=0.7,  # Slightly higher for more creative, natural responses
            max_tokens=200  # Increased to allow more detailed framework explanations
        )
        
        return response.choices[0].message.content.strip()
        
    except Exception as e:
        logger.error(f"Error generating response: {str(e)}")
        return "Sorry, I'm having trouble generating a response right now. Please try again."

# Initialize services on startup
initialize_services()

# Routes
@app.route('/')
def index():
    """Main chat interface"""
    # Initialize session chat history
    if 'chat_history' not in session:
        session['chat_history'] = []
    return render_template('index.html')

@app.route('/api/chat', methods=['POST'])
def chat():
    """Handle chat messages"""
    try:
        data = request.get_json()
        user_message = data.get('message', '').strip()
        
        if not user_message:
            return jsonify({'error': 'Message cannot be empty'}), 400
        
        logger.info(f"📨 User: {user_message}")
        
        # Check if services are initialized
        if not qdrant_client or not openai_client:
            logger.error("Services not initialized, attempting to reinitialize...")
            if not initialize_services():
                return jsonify({'error': 'Services unavailable. Please try again later.', 'success': False}), 503
        
        # Check message limit (10 messages = 5 exchanges)
        current_count = len(session.get('chat_history', []))
        if current_count >= 10:
            return jsonify({
                'response': "You've reached the free message limit (10 messages). Upgrade to Premium for unlimited conversations! 🚀",
                'limit_reached': True,
                'quick_replies': [],
                'success': True
            })
        
        # Get relevant context from Qdrant using OpenAI embeddings
        context = get_relevant_context(user_message)
        
        # Get chat history for context - Include MORE history (last 4 exchanges instead of 2)
        history = session.get('chat_history', [])
        chat_history = "\n".join([f"User: {h['user']}\nAI: {h['ai']}" for h in history[-4:]])  # Last 4 exchanges for better context
        
        # Get selected tone (default to Professional)
        selected_tone = session.get('tone', 'Professional')
        
        # Calculate chat length BEFORE adding current message (for tone question detection)
        current_chat_length = len(history) + 1
        
        # Generate response using GPT-4o-mini with Qdrant context
        ai_response = generate_response(user_message, context, chat_history, selected_tone, current_chat_length)
        
        # Store in session history
        if 'chat_history' not in session:
            session['chat_history'] = []
        
        session['chat_history'].append({
            'user': user_message,
            'ai': ai_response,
            'timestamp': datetime.now().isoformat()
        })
        session.modified = True
        
        logger.info(f"✅ AI: {ai_response[:100]}...")
        
        # Simplified quick reply flow - ONLY tone buttons after problem is shared
        # DON'T show buttons if the response is a safety warning
        is_safety_warning = ai_response.startswith("⚠️") or "call 911" in ai_response.lower()
        
        # Check if user hasn't selected tone yet
        has_selected_tone = 'tone' in session and session['tone'] in ["Professional", "Casual"]
        
        quick_replies = []
        chat_length = len(session.get('chat_history', []))
        
        if is_safety_warning:
            # Never show buttons after safety warnings
            quick_replies = []
            logger.info("⚠️ Safety warning issued, no buttons shown")
        # If tone not selected yet and we have a real problem (not greeting), ask for tone
        elif not has_selected_tone and chat_length >= 2:
            # Check if current message is a real problem (not just greeting)
            greeting_words = ['hi', 'hello', 'hey', 'hii', 'hiii', 'sup', 'yo']
            if user_message.lower().strip() not in greeting_words:
                # Check if previous response wasn't already asking for tone
                if "Before we dive in" not in session['chat_history'][-1]['ai']:
                    quick_replies = ["Professional", "Casual"]
                    logger.info("🎯 No tone selected yet, showing tone buttons")
        # Step 1: First message (greeting) - NO buttons yet, just greet
        elif chat_length == 1:
            # Check if first message is just a greeting (hi, hello, hey, etc.)
            greeting_words = ['hi', 'hello', 'hey', 'hii', 'hiii', 'sup', 'yo']
            first_msg = user_message.lower().strip()
            if first_msg in greeting_words:
                # Just greet, no tone buttons yet
                quick_replies = []
                logger.info("👋 Step 1: Greeting detected, no buttons shown")
            else:
                # User asked a real question first - will ask about tone next
                quick_replies = []
                logger.info("🎯 Step 1: Problem detected on first message")
        
        # Step 2: User shared their problem - respond empathetically, NO buttons yet
        elif chat_length == 2:
            # Check if previous message was just greeting
            prev_msg = session['chat_history'][0]['user'].lower().strip()
            greeting_words = ['hi', 'hello', 'hey', 'hii', 'hiii', 'sup', 'yo']
            
            if prev_msg in greeting_words:
                # They shared problem after greeting - respond empathetically, NO buttons yet
                quick_replies = []
                logger.info("🎯 Step 2: User shared problem after greeting, no buttons yet")
            else:
                # They selected tone on previous step - no more buttons, just chat
                user_tone = session['chat_history'][1]['user'].strip()
                if user_tone in ["Professional", "Casual"]:
                    session['tone'] = user_tone
                    session.modified = True
                    quick_replies = []
                    logger.info(f"🎯 Step 2: Tone '{user_tone}' selected, continuing conversation")
        
        # Step 3: After empathetic response - NOW ask how they want responses & show tone buttons
        elif chat_length == 3:
            # Check if first was greeting and second was problem
            first_msg = session['chat_history'][0]['user'].lower().strip()
            greeting_words = ['hi', 'hello', 'hey', 'hii', 'hiii', 'sup', 'yo']
            
            if first_msg in greeting_words:
                # Now ask about tone preference with buttons
                quick_replies = ["Professional", "Casual"]
                logger.info("🎯 Step 3: Asking tone preference, showing tone buttons")
            else:
                # Check if they just selected a tone
                user_tone = session['chat_history'][2]['user'].strip()
                if user_tone in ["Professional", "Casual"]:
                    session['tone'] = user_tone
                    session.modified = True
                    quick_replies = []
                    logger.info(f"🎯 Step 3: Tone '{user_tone}' selected, continuing conversation")
        
        # Step 4+: After tone is selected - NO MORE BUTTONS, just natural conversation
        elif chat_length >= 4:
            # Check if user just selected a tone
            user_tone = session['chat_history'][-1]['user'].strip()
            if user_tone in ["Professional", "Casual"]:
                session['tone'] = user_tone
                session.modified = True
                logger.info(f"🎯 Step 4+: Tone '{user_tone}' selected")
            quick_replies = []  # No more buttons - let the bot provide actionable advice
        
        return jsonify({
            'response': ai_response,
            'quick_replies': quick_replies,
            'success': True
        })
        
    except Exception as e:
        logger.error(f"❌ Error in chat endpoint: {str(e)}")
        return jsonify({
            'error': 'An error occurred while processing your message.',
            'success': False
        }), 500

@app.route('/api/history', methods=['GET'])
def get_history():
    """Get chat history"""
    history = session.get('chat_history', [])
    return jsonify({'history': history})

@app.route('/api/clear', methods=['POST'])
def clear_history():
    """Clear chat history and reset tone preference"""
    session['chat_history'] = []
    # Also clear the tone preference so user gets asked again
    if 'tone' in session:
        del session['tone']
    session.modified = True
    return jsonify({'success': True, 'message': 'Chat history cleared'})

@app.route('/health')
def health():
    """Health check endpoint"""
    return jsonify({
        'status': 'healthy',
        'qdrant_connected': qdrant_client is not None,
        'openai_ready': openai_client is not None,
        'model': 'gpt-4o-mini',
        'embeddings': 'text-embedding-3-small',
        'timestamp': datetime.now().isoformat()
    })

if __name__ == '__main__':
    port = int(os.getenv('PORT', 5001))
    debug = os.getenv('FLASK_DEBUG', 'False').lower() == 'true'
    
    logger.info("=" * 60)
    logger.info("🚀 Starting Web Chatbot Application")
    logger.info("=" * 60)
    
    app.run(
        host='0.0.0.0',
        port=port,
        debug=debug
    )
