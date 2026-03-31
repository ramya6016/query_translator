📊 Smart Inventory Manager AI

A Streamlit web app that allows you to interact with your inventory database using natural language.
Powered by LangChain, Google's Gemini LLM, and Supabase PostgreSQL, it automatically generates SQL queries
from user questions and provides friendly answers.

Features:
- Natural Language to SQL: Ask questions in plain English and get database answers.
- Schema Browser: Explore tables and columns in your database.
- Quick Insert: Click a table or column to insert it into your question.
- Chat Interface: Maintain a conversation history with the AI.
- Live Search: Filter tables/columns quickly.
- LangChain + Google Generative AI: Uses gemini-2.5-flash-lite for SQL reasoning and natural language answers.
- Supabase Integration: Connects directly to a PostgreSQL database for real-time data querying.

Tech Stack:
- Streamlit — Web interface
- Supabase — PostgreSQL database hosting
- LangChain — LLM orchestration
- Google Gemini API — LLM for SQL and natural language responses
- Python 3.12+

Installation:
1. Clone the repository:
   git clone https://github.com/yourusername/smart-inventory-ai.git
   cd smart-inventory-ai

2. Create a virtual environment:
   python -m venv venv
   source venv/bin/activate  # Linux/macOS
   venv\Scripts\activate     # Windows

3. Install dependencies:
   pip install -r requirements.txt

4. Configure Streamlit secrets (.streamlit/secrets.toml):
   SUPABASE_URL = "postgresql://<user>:<password>@<host>:5432/<database>"
   SUPABASE_KEY = "<your_supabase_api_key>"
   GOOGLE_API_KEY = "<your_google_api_key>"

> Make sure to use the PostgreSQL connection URL, not the REST API URL.

Running the App:
   streamlit run app.py

Usage:
1. Browse your database schema on the left sidebar.
2. Use the search box to filter tables and columns.
3. Use Quick Insert to add table/column names to your question.
4. Type your question in natural language (e.g., "Show products with stock < 10").
5. Click Ask to get a SQL-generated answer from the AI.

Project Structure:
smart-inventory-ai/
├── app.py                 # Main Streamlit app
├── requirements.txt       # Python dependencies
├── .streamlit/
│   └── secrets.toml       # Streamlit secrets for API keys and DB URL
└── README.txt

Notes:
- Ensure your Supabase database allows connections from Streamlit Cloud.
- Ensure the PostgreSQL URL is correct; do not use HTTPS REST URLs with SQLAlchemy.
- Currently, the AI assumes simple SQL generation; you can extend it with advanced LangChain chains for full NL → SQL conversion.

Future Improvements:
- Automatic natural language → SQL query generation using LangChain.
- Support multiple databases dynamically.
- Enhanced chat history with export functionality.
- Customizable AI response styles (friendly, concise, detailed).

License:
MIT License © 2026 Your Name
