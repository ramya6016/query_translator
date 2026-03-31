import streamlit as st
from langchain_google_genai import ChatGoogleGenerativeAI
from langchain_community.utilities import SQLDatabase
from langchain_community.tools.sql_database.tool import QuerySQLDataBaseTool
from langchain_classic.chains import create_sql_query_chain
from langchain_core.prompts import PromptTemplate
from langchain_core.output_parsers import StrOutputParser
from langchain_core.runnables import RunnablePassthrough
from operator import itemgetter
from sqlalchemy import create_engine

# --- 1. Page Config ---
st.set_page_config(page_title="Inventory AI Engineer", page_icon="📊", layout="wide")
st.title("📊 Smart Inventory Manager")
st.markdown("---")

# --- 2. Secrets Handling ---
try:
    db_uri = st.secrets["SUPABASE_URL"]
    api_key = st.secrets["GOOGLE_API_KEY"]
except KeyError:
    st.error("Missing Secrets! Add SUPABASE_URL and GOOGLE_API_KEY to your Streamlit secrets.")
    st.stop()

# --- Fix: Replace deprecated 'postgres://' with 'postgresql://' for SQLAlchemy 2.x ---
if db_uri.startswith("postgres://"):
    db_uri = db_uri.replace("postgres://", "postgresql://", 1)

# --- 3. Initialize Chain + Extract Schema ---
@st.cache_resource
def get_chain_and_schema():
    engine = create_engine(
        db_uri,
        connect_args={
            "sslmode": "require",
            "connect_timeout": 10,
        }
    )
    db = SQLDatabase(engine)

    schema = {}
    for table in db.get_usable_table_names():
        try:
            info = db.get_table_info([table])
            cols = []
            for line in info.splitlines():
                line = line.strip()
                if line.startswith("CREATE TABLE") or line in ("", ")"):
                    continue
                parts = line.split()
                if parts and parts[0].upper() not in (
                    "PRIMARY", "FOREIGN", "UNIQUE", "CHECK", "CONSTRAINT", "INDEX"
                ):
                    cols.append(parts[0].strip('",'))
            schema[table] = [c for c in cols if c]
        except Exception:
            schema[table] = []

    llm = ChatGoogleGenerativeAI(
        model="gemini-2.5-flash-lite",
        google_api_key=api_key,
        temperature=0
    )

    execute_query = QuerySQLDataBaseTool(db=db)
    write_query = create_sql_query_chain(llm, db)

    answer_prompt = PromptTemplate.from_template(
        "Given the following user question, corresponding SQL query, and SQL result, "
        "answer the user question in a friendly and natural way.\n\n"
        "Question: {question}\n"
        "SQL Query: {query}\n"
        "SQL Result: {result}\n\n"
        "Answer:"
    )

    full_chain = (
        RunnablePassthrough.assign(query=write_query).assign(
            result=itemgetter("query") | execute_query
        )
        | answer_prompt
        | llm
        | StrOutputParser()
    )

    return full_chain, schema

chain, schema = get_chain_and_schema()

# --- 4. Build flat list of all tables + columns for suggestions ---
all_suggestions = []
for table, cols in schema.items():
    all_suggestions.append(f"[TABLE] {table}")
    for col in cols:
        all_suggestions.append(f"[COL] {table}.{col}")

# --- 5. Layout: Left = Schema + Suggestions | Right = Chat ---
left_col, right_col = st.columns([1, 2], gap="large")

with left_col:
    st.subheader("🗂️ Schema Browser")

    search = st.text_input(
        "Search tables & columns",
        placeholder="🔍 Type to filter...",
        key="schema_search"
    )

    if search:
        filtered = [s for s in all_suggestions if search.lower() in s.lower()]
    else:
        filtered = all_suggestions

    if filtered:
        tables_found = [s for s in filtered if s.startswith("[TABLE]")]
        cols_found   = [s for s in filtered if s.startswith("[COL]")]

        if tables_found:
            st.markdown("**📋 Tables**")
            for t in tables_found:
                name = t.replace("[TABLE] ", "")
                st.code(name, language=None)

        if cols_found:
            st.markdown("**🔹 Columns**")
            for c in cols_found:
                label = c.replace("[COL] ", "")
                st.code(label, language=None)
    else:
        st.info("No matches found.")

    st.markdown("---")

    st.subheader("✨ Quick Insert")
    st.caption("Pick a table/column to insert into your question below.")

    options = ["(none)"] + [
        s.replace("[TABLE] ", "").replace("[COL] ", "") for s in all_suggestions
    ]
    selected = st.selectbox("Insert into question:", options, key="quick_insert")

    if selected != "(none)":
        st.session_state["inserted_term"] = selected

with right_col:
    st.subheader("💬 Ask a Question")

    prefill = st.session_state.get("inserted_term", "")

    user_question = st.text_area(
        "Your question",
        value=prefill,
        placeholder="e.g. Show me all products where stock is below 10",
        height=100,
        label_visibility="collapsed",
        key="question_input"
    )

    ask_btn = st.button("🚀 Ask", use_container_width=True, type="primary")

    st.markdown("---")

    if "messages" not in st.session_state:
        st.session_state.messages = []

    if ask_btn and user_question.strip():
        st.session_state["inserted_term"] = ""
        st.session_state.messages.append({"role": "user", "content": user_question})

        with st.spinner("🔍 Analyzing your database..."):
            try:
                response = chain.invoke({"question": user_question})
                st.session_state.messages.append({"role": "assistant", "content": response})
            except Exception as e:
                st.session_state.messages.append({
                    "role": "assistant",
                    "content": f"❌ Execution Error: {e}"
                })

    for message in reversed(st.session_state.messages):
        with st.chat_message(message["role"]):
            st.markdown(message["content"])
