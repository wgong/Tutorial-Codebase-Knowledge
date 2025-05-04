# Chapter 4: Prompt Engineering (Guiding the LLM)

Welcome back! In [Chapter 3: LLM Connector (Reasoning Engine)](03_llm_connector__reasoning_engine__.md), we saw how Vanna uses a specialized "communicator" (the LLM Connector) to talk to the powerful AI brain (the Large Language Model or LLM) that actually generates the SQL. We learned that Vanna can swap out different LLM brains by using different connectors.

But just knowing *how* to talk to the LLM isn't enough. We need to know *what* to say. How do we make sure the LLM understands our specific database and gives us the *right* SQL query for our question?

**Problem:** Imagine asking a very smart, general-purpose assistant (the LLM) to write code for a very specific task (querying *your* unique database). If you just ask, "How many babies were named Emma in 2022?", the LLM has no idea:
*   What tables your database has (Is there a `birth_records` table? Or `ssa_data`?)
*   What the columns in those tables are called (Is it `baby_name` or `first_name`? Is the year column `year` or `birth_year`?)
*   How you've asked similar questions before.
*   Any specific rules or definitions for your data.

Without this information, the LLM is just guessing, and its SQL query will likely be wrong!

**Solution:** Don't just send the raw question. Instead, send a carefully crafted message – a **prompt** – that gives the LLM all the context and instructions it needs. This process of designing these instructions is called **Prompt Engineering**.

Think of it like giving detailed instructions to a contractor. You don't just say "Build a house." You provide blueprints (database structure), examples of features you like (example SQL), specific requirements (documentation), and clear instructions on the final output.

## What is Prompt Engineering in Vanna?

Prompt Engineering isn't a single class you import. It's a *concept* and a *process* built into the core Vanna logic, especially within the [VannaBase (Core Interface)](02_vannabase__core_interface__.md) methods like `generate_sql` and helper functions like `get_sql_prompt`.

It involves strategically combining several pieces of information into the text prompt sent to the LLM:

1.  **The User's Question:** The original question asked by the user (e.g., "Top 5 states by births in 2020?").
2.  **Instructions (System Prompt):** Clear directives telling the LLM its role (e.g., "You are a SQL expert"), the expected output format (e.g., "Only respond with SQL code inside ```sql ... ```"), and the specific SQL dialect to use (e.g., "Use SQLite syntax").
3.  **Context - Database Schema (DDL):** Information about the relevant database tables, like their names and column definitions (`CREATE TABLE` statements). Vanna finds relevant DDL using the [Vector Store (Knowledge Storage)](05_vector_store__knowledge_storage__.md).
4.  **Context - Example Questions/SQL:** Pairs of similar questions asked in the past and the correct SQL queries that answered them. These examples help the LLM learn patterns. Vanna also retrieves these using the [Vector Store (Knowledge Storage)](05_vector_store__knowledge_storage__.md).
5.  **Context - Documentation:** Any extra helpful text descriptions or definitions about the data or business logic. Again, retrieved via the [Vector Store (Knowledge Storage)](05_vector_store__knowledge_storage__.md).

By putting all this together, Vanna gives the LLM a much better chance of understanding the request in the context of *your specific database* and generating accurate SQL.

## How Vanna Builds the Prompt (The Process)

When you call `vn.generate_sql("Your Question")`, the following happens behind the scenes (simplified):

1.  **Retrieve Context:** Vanna uses the `get_related_ddl`, `get_similar_question_sql`, and `get_related_documentation` methods (powered by the [Vector Store (Knowledge Storage)](05_vector_store__knowledge_storage__.md)) to find information relevant to your question.
2.  **Assemble Prompt:** Vanna calls an internal method, often `get_sql_prompt`. This method takes the user question and the retrieved context.
3.  **Format Prompt:** Inside `get_sql_prompt`, Vanna carefully arranges the information. It uses helper functions (like `add_ddl_to_prompt`, `add_sql_to_prompt`) to format the context clearly. It also uses the `system_message`, `user_message`, and `assistant_message` methods (provided by the specific [LLM Connector (Reasoning Engine)](03_llm_connector__reasoning_engine__.md)) to structure the prompt in a way the LLM understands (often as a conversation history).
4.  **Send to LLM:** The final, assembled prompt is passed to the `submit_prompt` method of the [LLM Connector (Reasoning Engine)](03_llm_connector__reasoning_engine__.md), which sends it to the AI.

Here's a diagram illustrating the prompt assembly:

```mermaid
graph LR
    A[User Question: "Top 5 states?"] --> B(Vanna: generate_sql);
    C[Vector Store] -->|Relevant DDL| B;
    C -->|Similar Q/SQL Pairs| B;
    C -->|Relevant Docs| B;
    B --> D{Vanna: get_sql_prompt};
    D --> E[Formatted Prompt];
    subgraph "Prompt Components"
        F[Instructions: "Be a SQL expert..."]
        G[Context: DDL, Q/SQL, Docs]
        H[User Question]
    end
    F --> E;
    G --> E;
    H --> E;
    E --> I(LLM Connector: submit_prompt);
    I --> J[LLM];
    J --> I;
    I --> B;
    B --> K[Generated SQL];

    style C fill:#f9f,stroke:#333,stroke-width:2px;
    style J fill:#ccf,stroke:#333,stroke-width:2px;
    style E fill:#ff9,stroke:#333,stroke-width:2px;
```

## Example: What a Prompt Might Look Like

Let's imagine you ask: "What were the top 5 states with the most births in 2020?"

The prompt Vanna sends to the LLM might look something like this (simplified):

```text
[SYSTEM MESSAGE]
You are a SQLite SQL Database expert. Please help to generate a SQL query to answer the question.
Your response should ONLY be based on the given context and follow the response guidelines and format instructions.

===Tables
CREATE TABLE ssa_data (
  year INTEGER,
  state TEXT,
  name TEXT,
  gender TEXT,
  births INTEGER
)

===Additional Context
The 'ssa_data' table contains US social security administration baby name data, including counts by year and state.

===Question-SQL Pairs
Question: Total births per year?
SQL: SELECT year, SUM(births) FROM ssa_data GROUP BY year

Question: Count of names starting with 'A' in CA in 2021?
SQL: SELECT COUNT(DISTINCT name) FROM ssa_data WHERE state = 'CA' AND year = 2021 AND name LIKE 'A%'

===Response Guidelines
1. Generate valid SQLite SQL.
2. Place the generated SQL inside a Markdown sql code block (```sql ... ```).
3. Only respond with the SQL code block.

[USER MESSAGE]
What were the top 5 states with the most births in 2020?
```

**Explanation:**

*   The **SYSTEM MESSAGE** sets the stage, telling the LLM its role and giving general instructions.
*   **===Tables** provides the relevant `CREATE TABLE` statement (DDL).
*   **===Additional Context** gives documentation Vanna found.
*   **===Question-SQL Pairs** shows examples of previous interactions.
*   **===Response Guidelines** gives specific rules for the output.
*   The **USER MESSAGE** contains the actual question.

This detailed prompt gives the LLM much more information to work with than just the raw question alone, leading to more accurate SQL like:

```sql
SELECT state, SUM(births) as total_births
FROM ssa_data
WHERE year = 2020
GROUP BY state
ORDER BY total_births DESC
LIMIT 5
```

## Under the Hood: The `get_sql_prompt` Method

The magic of assembling this prompt often happens in the `get_sql_prompt` method defined in `src/vanna/base/base.py` and potentially overridden or used by specific connectors.

```python
# Simplified snippet from src/vanna/base/base.py VannaBase.get_sql_prompt

    def get_sql_prompt(
        self,
        initial_prompt : str, # Base instructions, might come from config
        question: str,
        question_sql_list: list, # Retrieved similar Q/SQL pairs
        ddl_list: list,         # Retrieved relevant DDL
        doc_list: list,          # Retrieved relevant documentation
        **kwargs,
    ):
        if initial_prompt is None:
            # Default system instructions if none provided
            initial_prompt = f"""
                You are a {self.dialect} SQL Database expert.
                Please help to generate a SQL query to answer the question.
                Your response should ONLY be based on the given context...
            """

        # Add the retrieved DDL context using a helper function
        initial_prompt = self.add_ddl_to_prompt(
            initial_prompt, ddl_list, max_tokens=self.max_tokens
        )

        # Add any static documentation and retrieved docs
        if self.static_documentation != "":
            doc_list.append(self.static_documentation)
        initial_prompt = self.add_documentation_to_prompt(
            initial_prompt, doc_list, max_tokens=self.max_tokens
        )

        # Add specific response guidelines
        initial_prompt += (
            "===Response Guidelines \n"
            # ... (Guidelines like format, dialect, etc.) ...
            "7. Place the generated SQL inside a Markdown sql code block. \n"
        )

        # Start building the message list for the LLM
        # Uses methods like self.system_message which are implemented by the LLM Connector
        message_log = [self.system_message(initial_prompt)]

        # Add the example Q/SQL pairs as a conversation history
        for example in question_sql_list:
            if example is not None and "question" in example and "sql" in example:
                message_log.append(self.user_message(example["question"]))
                # We wrap the example SQL in ```sql ... ``` before sending
                message_log.append(self.assistant_message(f"```sql\n{example['sql']}\n```"))

        # Finally, add the user's actual question
        message_log.append(self.user_message(question))

        # Return the complete message list, ready for the LLM Connector
        return message_log

# Simplified snippet for a helper function like add_ddl_to_prompt
    def add_ddl_to_prompt(
        self, initial_prompt: str, ddl_list: list[str], max_tokens: int = 14000
    ) -> str:
        # Only add DDL if the list isn't empty
        if len(ddl_list) > 0:
            # Add a clear heading
            initial_prompt += "\n===Tables \n"

            # Add each DDL statement, checking we don't exceed token limits
            for ddl in ddl_list:
                # Estimate token count (very rough approximation)
                if (self.str_to_approx_token_count(initial_prompt) +
                    self.str_to_approx_token_count(ddl) < max_tokens):
                    initial_prompt += f"{ddl}\n\n" # Add the DDL and spacing
                else:
                    break # Stop adding if we exceed the limit

        return initial_prompt # Return the modified prompt string
```

**Explanation:**

*   The `get_sql_prompt` function takes the question and all the context retrieved earlier.
*   It constructs a base `initial_prompt` containing system-level instructions and guidelines.
*   It calls helper functions like `add_ddl_to_prompt` and `add_documentation_to_prompt` to format and append the relevant context pieces, carefully managing the total length (token count).
*   It uses the `system_message`, `user_message`, and `assistant_message` methods (implemented by the [LLM Connector (Reasoning Engine)](03_llm_connector__reasoning_engine__.md)) to structure the prompt as a list of messages, often simulating a conversation. This format helps many LLMs understand context and roles.
*   The final `message_log` is a structured list ready to be sent to the LLM.

## Why Good Prompt Engineering Matters

*   **Accuracy:** Provides the LLM with necessary context about *your* specific database, reducing guesswork and errors.
*   **Specificity:** Guides the LLM to use the correct SQL dialect (SQLite, PostgreSQL, Snowflake, etc.).
*   **Consistency:** Helps ensure the LLM provides answers in the desired format (e.g., just SQL code).
*   **Learning:** Including examples allows the LLM to learn from past successful queries.
*   **Efficiency:** Prevents the LLM from generating queries for non-existent tables or columns.

## Conclusion

Prompt Engineering is the art and science of crafting the perfect "job description" for the LLM. It's not just about asking a question; it's about providing clear instructions, relevant context (like database schema and examples), and formatting guidelines. Vanna automates much of this process by retrieving context from its knowledge base and assembling a detailed prompt using methods like `get_sql_prompt`. This careful guidance is crucial for getting accurate and useful SQL queries from the LLM.

But where does Vanna get all this context (DDL, examples, documentation) to put *into* the prompt? How does it store and efficiently retrieve this knowledge?

Let's explore the knowledge base! [Chapter 5: Vector Store (Knowledge Storage)](05_vector_store__knowledge_storage__.md)

---

Generated by [AI Codebase Knowledge Builder](https://github.com/The-Pocket/Tutorial-Codebase-Knowledge)