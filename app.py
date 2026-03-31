import streamlit as st
from langchain_google_genai import ChatGoogleGenerativeAI
from langchain_community.utilities import SQLDatabase
from langchain_community.tools.sql_database.tool import QuerySQLDataBaseTool
from langchain_classic.chains import create_sql_query_chain
from langchain_core.prompts import PromptTemplate
from langchain_core.output_parsers import StrOutputParser
from langchain_core.runnables import RunnablePassthrough
from operator import itemgetter

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

# --- 3. Initialize Chain + Extract Schema ---
@st.cache_resource
def get_chain_and_schema():
    db = SQLDatabase.from_uri(db_uri)

    # Extract schema: {table_name: [col1, col2, ...]}
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

# --- 4. Sidebar: Schema Browser ---
with st.sidebar:
    st.header("🗂️ Database Schema")
    st.caption("Browse all tables and their columns.")

    if schema:
        for table, cols in schema.items():
            with st.expander(f"📋 {table}", expanded=False):
                if cols:
                    for col in cols:
                        st.code(col, language=None)
                else:
                    st.caption("No columns found.")
    else:
        st.info("No tables found in the database.")

# --- 5. Live Suggestion Filter ---
st.subheader("💡 Schema Suggestions")

all_names = list(schema.keys())
for cols in schema.values():
    all_names.extend(cols)
all_names = sorted(set(all_names))

search_term = st.text_input(
    "Filter tables/columns",
    placeholder="🔍 Start typing a table or column name...",
    label_visibility="collapsed"
)

if search_term:
    matches = [n for n in all_names if search_term.lower() in n.lower()]
    if matches:
        st.markdown("**Matching tables / columns:**")
        cols_per_row = 4
        rows = [matches[i:i+cols_per_row] for i in range(0, len(matches), cols_per_row)]
        for row in rows:
            grid = st.columns(cols_per_row)
            for idx, name in enumerate(row):
                tag = "🟦" if name in schema else "🔹"
                grid[idx].code(f"{tag} {name}", language=None)
        st.caption("🟦 = table &nbsp;&nbsp; 🔹 = column")
    else:
        st.info("No matches found.")
else:
    st.markdown("**All tables (quick reference):**")
    if schema:
        cols_ui = st.columns(min(len(schema), 5))
        for i, table in enumerate(schema.keys()):
            cols_ui[i % len(cols_ui)].code(table, language=None)

st.markdown("---")

# --- 6. Chat Interface ---
st.subheader("💬 Ask a Question")

if "messages" not in st.session_state:
    st.session_state.messages = []

for message in st.session_state.messages:
    with st.chat_message(message["role"]):
        st.markdown(message["content"])

if prompt := st.chat_input("e.g. How many products are low on stock?"):
    st.session_state.messages.append({"role": "user", "content": prompt})
    with st.chat_message("user"):
        st.markdown(prompt)

    with st.chat_message("assistant"):
        with st.spinner("Analyzing database..."):
            try:
                response = chain.invoke({"question": prompt})
                st.markdown(response)
                st.session_state.messages.append({"role": "assistant", "content": response})
            except Exception as e:
                st.error(f"Execution Error: {e}")