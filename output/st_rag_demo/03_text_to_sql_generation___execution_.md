# Chapter 3: Text-to-SQL Generation & Execution

In [Chapter 2: Chatbot Model Hierarchy](02_chatbot_model_hierarchy_.md), we learned how `st_rag_demo` uses specialized chatbots for different data types. We saw that the `SQLiteChatbot` is the specialist for talking to databases. But how does it understand questions about data stored in tables, like "Show me the top 5 customers by sales"? You don't need to write complicated code (SQL) yourself! This chapter explains the magic behind **Text-to-SQL Generation & Execution**.

## The Problem: Talking "Database" is Hard!

Databases store information in a very organized way, usually in tables with rows and columns. To get specific information out, you typically need to write queries in a special language called SQL (Structured Query Language).

For example, if you have a `customers` table and an `orders` table, asking "Show me the names of customers who ordered product 'X'" might require a SQL query like this:

```sql
SELECT c.customer_name
FROM customers c
JOIN orders o ON c.customer_id = o.customer_id
WHERE o.product_name = 'X';
```

That looks complicated, right? Especially if you're not a database expert. Wouldn't it be great if you could just ask the question in plain English?

## The Solution: A Translator for Your Database

This is exactly what the Text-to-SQL feature does! Think of the `SQLiteChatbot` as having a super-smart translator assistant.

1.  **You speak English:** You ask your question naturally, like "Which customers bought product X?".
2.  **The Translator Listens:** The `SQLiteChatbot` recognizes that this question is about the database content.
3.  **It Consults the Dictionary (Schema):** The chatbot looks at the *structure* of your database – the names of the tables (`customers`, `orders`), the columns within them (`customer_id`, `customer_name`, `product_name`), and how they relate. This structure is called the **schema**.
4.  **It Asks the Expert (LLM):** The chatbot sends your English question AND the database schema to the powerful Language Model (LLM) we discussed earlier. It essentially asks the LLM, "Given this database structure, how would you write a SQL query to answer the question: 'Which customers bought product X?'"
5.  **The Expert Writes SQL:** The LLM, using its knowledge of language and the provided schema, generates the SQL query (like the example above).
6.  **The Translator Runs the Query:** The `SQLiteChatbot` takes the generated SQL query and runs it directly on your uploaded SQLite database file.
7.  **It Delivers the Answer:** The database sends back the results (e.g., a list of customer names). The chatbot then presents this answer back to you in a user-friendly way, maybe as a list, a table, or even triggering a chart if appropriate ([Chapter 7: Data Visualization Generation](07_data_visualization_generation_.md)).

This process allows you to query your database without writing a single line of SQL yourself!

## How it Works: Key Steps Inside the Chatbot

Let's peek inside the `SQLiteChatbot` (from `src/models/sqlite_chatbot.py`) to see how this happens. When you ask a question, the `ask` method is called. It has some special logic for database questions:

```python
# Simplified from src/models/sqlite_chatbot.py

class SQLiteChatbot(DocumentChatbot): # Inherits from the base chatbot

    # ... (initialization, database loading methods) ...

    def ask(self, question, return_context=False):
        """Ask a question, potentially generating and running SQL."""
        # 1. Check if a database is loaded
        if not self.sql_database:
            return "Please upload a database first."

        # 2. Decide if this question likely needs SQL
        #    (Looks for keywords like 'table', 'count', 'show me', 'top 5' etc.)
        is_sql_query = self._should_use_sql(question)

        if is_sql_query:
            try:
                # 3. Generate the SQL query using the LLM
                generated_query = self.generate_sql_query(question)
                # ... (handle potential errors in generation) ...

                # 4. Execute the generated SQL query against the database
                query_result = self.execute_sql_query(generated_query)

                # 5. Format the result nicely for the user
                answer = self._format_sql_response(generated_query, query_result)

                # Return answer (maybe with data for visualization)
                return {"answer": answer, "query": generated_query, "data": query_result}

            except Exception as e:
                # Handle errors during SQL generation or execution
                return f"Sorry, I couldn't answer that using SQL: {e}"
        else:
            # If it doesn't seem like a SQL question, use the standard
            # RAG approach (explained in Chapter 4)
            return super().ask(question, return_context=return_context)

    def _should_use_sql(self, question):
        """A simple helper to guess if SQL is needed."""
        keywords = ["table", "database", "count", "list", "show", "top", "query"]
        return any(keyword in question.lower() for keyword in keywords)

    # ... other methods like generate_sql_query, execute_sql_query ...
```

**Explanation:**

1.  It first checks if a database (`self.sql_database`) has been loaded.
2.  It uses a simple helper (`_should_use_sql`) to guess if the question requires database querying.
3.  If yes, it calls `generate_sql_query`.
4.  Then, it calls `execute_sql_query` with the SQL it got back.
5.  Finally, it formats the results into a friendly answer.
6.  If the question doesn't seem like it needs SQL, it falls back to the standard approach inherited from `DocumentChatbot` (covered in [Chapter 4: RAG Core Logic](04_rag_core_logic_.md)).

### Generating the SQL (`generate_sql_query`)

This method is responsible for talking to the LLM to get the SQL code.

```python
# Simplified from src/models/sqlite_chatbot.py

    def generate_sql_query(self, question):
        """Generate SQL query using LLM and database schema."""
        # 1. Get the database schema information (table names, columns)
        schema_info = self.sql_database.get_table_info()

        # 2. Create a detailed prompt for the LLM
        prompt = f"""Given the SQLite database schema:
{schema_info}

Generate a SQL query to answer the question: "{question}"

Return ONLY the SQL query.
SQL Query:"""

        # 3. Send the prompt to the LLM
        #    (self.llm is the Language Model initialized in the parent class)
        response = self.llm.invoke([{"role": "user", "content": prompt}])
        generated_query = response.content.strip()

        # 4. Clean up the response (remove potential explanations, backticks)
        cleaned_query = self._clean_llm_sql_output(generated_query)

        return cleaned_query
```

**Explanation:**

1.  It fetches the database schema using `self.sql_database.get_table_info()`. LangChain provides helpful utilities for this.
2.  It constructs a specific prompt telling the LLM its task, providing the schema as context, and asking it to translate the user's `question` into SQL.
3.  It calls the LLM (`self.llm.invoke`) with this prompt.
4.  It cleans up the LLM's response to ensure it only returns the SQL code.

### Executing the SQL (`execute_sql_query`)

Once the SQL is generated, this method runs it against the actual database file.

```python
# Simplified from src/models/sqlite_chatbot.py
import sqlite3
import pandas as pd # Pandas is great for handling table data

    def execute_sql_query(self, query):
        """Execute the generated SQL query on the database."""
        if not self.db_path: # Path to the actual .db file
            return "Error: Database path not set."

        try:
            # Connect to the SQLite database file
            conn = sqlite3.connect(self.db_path)

            # Use pandas to execute the query and get results as a DataFrame
            # This is good for SELECT queries that return tables of data
            if query.strip().upper().startswith("SELECT"):
                result_df = pd.read_sql_query(query, conn)
                return result_df # Return the data as a table (DataFrame)
            else:
                # For non-SELECT queries (INSERT, UPDATE, DELETE)
                cursor = conn.cursor()
                cursor.execute(query)
                conn.commit() # Save changes
                return f"Query executed successfully. Rows affected: {cursor.rowcount}"

        except Exception as e:
            return f"Error executing query: {str(e)}"
        finally:
            # Always close the connection
            if 'conn' in locals() and conn:
                conn.close()
```

**Explanation:**

1.  It checks if the path to the database file (`self.db_path`) exists.
2.  It establishes a connection to the SQLite database file.
3.  If the query is a `SELECT` statement (asking for data), it uses the `pandas` library's `read_sql_query` function, which conveniently runs the query and puts the results into a table-like structure called a DataFrame.
4.  If it's another type of query (like `UPDATE`), it executes it differently and reports the number of affected rows.
5.  It includes error handling (`try...except`) in case the generated SQL is invalid or something goes wrong.
6.  Crucially, it closes the database connection afterwards (`finally`).

## The Journey of a Question: From English to Answer

Let's trace the flow with a simple example: You ask "How many customers do we have?".

```mermaid
sequenceDiagram
    participant U as User
    participant SP as Streamlit Page (3_SQLite_RAG.py)
    participant SQLChatbot as SQLiteChatbot
    participant LLM as Language Model
    participant SQLiteDB as SQLite Database File

    U->>SP: Enters "How many customers do we have?"
    SP->>SQLChatbot: Calls ask("How many customers...")
    SQLChatbot->>SQLChatbot: Decides SQL is needed
    SQLChatbot->>SQLChatbot: Calls generate_sql_query()
    SQLChatbot->>SQLiteDB: Gets schema (e.g., 'customers' table info)
    SQLChatbot->>LLM: Sends prompt (schema + question)
    LLM-->>SQLChatbot: Returns generated SQL (e.g., "SELECT COUNT(*) FROM customers;")
    SQLChatbot->>SQLChatbot: Calls execute_sql_query("SELECT COUNT(*)...")
    SQLChatbot->>SQLiteDB: Executes the SQL query
    SQLiteDB-->>SQLChatbot: Returns result (e.g., 150)
    SQLChatbot->>SQLChatbot: Formats result into answer text
    SQLChatbot-->>SP: Returns answer (e.g., "The query returned 1 row: 150")
    SP->>U: Displays the answer
```

This diagram shows the collaboration: the chatbot orchestrates the process, using the LLM as the SQL writer and directly interacting with the database file to get the final data.

## Interacting via the Streamlit Page

The Streamlit page (`src/pages/3_SQLite_RAG.py`) handles the user interface. When you type your question and hit Enter:

1.  It takes your input text.
2.  It calls `st.session_state.sqlite_chatbot.ask(your_question)`.
3.  It receives the response from the chatbot.
4.  If the response contains just text, it displays it.
5.  If the response indicates a successful SQL query and includes data (like a pandas DataFrame), the Streamlit page might:
    *   Display the confirmation text ("I executed this query...").
    *   Display the data itself in a table using `st.dataframe(response['data'])`.
    *   Potentially trigger a visualization based on the data (see [Chapter 7: Data Visualization Generation](07_data_visualization_generation_.md)).

This separation keeps the core logic inside the `SQLiteChatbot` and the UI presentation logic in the Streamlit page file.

## Conclusion

Text-to-SQL is a powerful feature of the `SQLiteChatbot` that bridges the gap between natural human language and the structured language of databases. By leveraging the database schema and a Language Model, it can:

1.  Understand your English questions about the database.
2.  Generate the corresponding SQL query automatically.
3.  Execute that query against your data.
4.  Present the results back to you.

This allows you to explore and get insights from your SQLite databases without needing to be an SQL expert.

While Text-to-SQL is fantastic for structured database queries, what about asking questions about the *content* of text documents like PDFs or CSVs, or even asking more general questions about the database structure itself? For that, `st_rag_demo` uses a more general technique called Retrieval-Augmented Generation (RAG), which we'll explore next.

**Next:** [Chapter 4: RAG Core Logic](04_rag_core_logic_.md)

---

Generated by [AI Codebase Knowledge Builder](https://github.com/The-Pocket/Tutorial-Codebase-Knowledge)