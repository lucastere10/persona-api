import sqlite3
import openai
import speech_recognition as sr
from decouple import config

# === SETUP ===
openai.api_key = config('OPENAI_API_KEY')
DATABASE_PATH = "test_database.db"

# === Function: Convert Natural Language to SQL ===
def nlp_to_sql(prompt, table_schema):
    full_prompt = f"""You are an assistant that converts natural language to SQL queries.
Use this table schema:
{table_schema}

Convert this request to a SQL query: "{prompt}"
Only return the SQL query."""
    
    response = openai.ChatCompletion.create(
        model="gpt-3.5-turbo",
        messages=[{"role": "user", "content": full_prompt}]
    )
    return response['choices'][0]['message']['content'].strip()

# === Function: Get Spoken Input ===
def get_spoken_input():
    r = sr.Recognizer()
    with sr.Microphone() as source:
        print("Ask your question:")
        audio = r.listen(source)

    try:
        text = r.recognize_google(audio)
        print(f"You said: {text}")
        return text
    except Exception as e:
        print("Speech Recognition error:", e)
        return None

# === Function: Get DB Schema ===
def get_db_schema(cursor):
    schema = ""
    cursor.execute("SELECT name FROM sqlite_master WHERE type='table';")
    tables = cursor.fetchall()
    for table_name in tables:
        table = table_name[0]
        cursor.execute(f"PRAGMA table_info({table});")
        columns = cursor.fetchall()
        schema += f"\nTable: {table}\nColumns: {', '.join([col[1] for col in columns])}\n"
    return schema

# === MAIN ===
def main():
    conn = sqlite3.connect(DATABASE_PATH)
    cursor = conn.cursor()

    question = get_spoken_input()
    if not question:
        return

    schema = get_db_schema(cursor)
    sql_query = nlp_to_sql(question, schema)

    print("\nGenerated SQL:")
    print(sql_query)

    try:
        cursor.execute(sql_query)
        results = cursor.fetchall()
        print("\nQuery Results:")
        for row in results:
            print(row)
    except Exception as e:
        print("SQL Execution error:", e)

if __name__ == "__main__":
    main()
