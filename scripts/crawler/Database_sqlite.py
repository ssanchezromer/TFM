import sqlite3
import os
from dotenv import load_dotenv
from rich import print
import requests
from langchain_community.document_loaders.pdf import PyPDFLoader
from langchain_core.prompts import PromptTemplate
from langchain_openai import ChatOpenAI
from langchain_groq import ChatGroq
from langchain.chains.llm import LLMChain
from langchain.chains.combine_documents import create_stuff_documents_chain
from langchain.schema import Document

load_dotenv(override=True)

class Database:
    def __init__(self):
        """
        Initialize the database
        """
        self.connection = None
        self.database_type = "sqlite"
        self.database_path = os.getenv('DB_DATABASE_PATH')  # Ruta del archivo SQLite
        self.table_names = ["calls_basic_information", "calls_description_information", "calls_budget_information",
                            "calls_files_information", "calls_urls"]


    def connect(self):
        """
        Establish a connection to the SQLite database.
        """
        if not self.database_path:
            raise ValueError("Database path is not set.")

        # Crear el directorio si no existe
        if not os.path.exists(os.path.dirname(self.database_path)):
            os.makedirs(os.path.dirname(self.database_path))

        try:
            self.connection = sqlite3.connect(self.database_path)
        except sqlite3.OperationalError as e:
            print("Failed to connect to the database:", e)
            raise

    def connect_database(self):
        """
        Connect to the database
        :return: database connection
        """
        try:
            return self.connect()
        except Exception as e:
            print("[bold red]Error connecting to database:[/bold red]", f"{e}")
            return None

    def create_database(self):
        """
        Create the database schema (tables) if they do not exist.
        """
        # read query from file tables.sql
        create_table_queries = [
            """
            CREATE TABLE IF NOT EXISTS calls_basic_information (
                call_code TEXT NOT NULL,
                call_title TEXT NOT NULL,
                call_href TEXT NOT NULL,
                call_type TEXT DEFAULT NULL,
                opening_date TEXT DEFAULT NULL,
                next_deadline TEXT DEFAULT NULL,
                deadline_model TEXT DEFAULT NULL,
                status TEXT DEFAULT NULL,
                programme TEXT DEFAULT NULL,
                type_of_action TEXT DEFAULT NULL,
                budget_total REAL DEFAULT NULL,
                currency VARCHAR(30) DEFAULT NULL,
                scope TEXT NOT NULL,
                type_company VARCHAR(100) DEFAULT NULL,
                PRIMARY KEY (call_code, call_title)
            );
            """,
            """
            CREATE TABLE IF NOT EXISTS calls_description_information (
                call_code TEXT NOT NULL,
                call_title TEXT NOT NULL,
                topic_description TEXT NOT NULL,
                topic_destination TEXT NOT NULL,
                topic_conditions_and_documents TEXT NOT NULL,
                budget_overview TEXT NOT NULL,
                partner_search_announcements TEXT NOT NULL,
                start_submission TEXT NOT NULL,
                get_support TEXT NOT NULL,
                extra_information TEXT NOT NULL,
                PRIMARY KEY (call_code, call_title)
            );
            """,
            """
            CREATE TABLE IF NOT EXISTS calls_budget_information (
                call_code TEXT NOT NULL,
                call_title TEXT NOT NULL,
                budget_topic TEXT NOT NULL,
                budget_amount TEXT NOT NULL,
                budget_stages TEXT NOT NULL,
                budget_opening_date TEXT NOT NULL,
                budget_deadline TEXT NOT NULL,
                budget_contributions TEXT NOT NULL,
                budget_indicative_number_of_grants TEXT NOT NULL,
                PRIMARY KEY (call_code, call_title, budget_topic)
            );
            """,
            """
            CREATE TABLE IF NOT EXISTS calls_files_information (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                file_url TEXT NOT NULL,
                file_text TEXT NOT NULL,
                file_summary TEXT NOT NULL,
                file_error_description TEXT,
                file_error_code TEXT
            );
            """,
            """
            CREATE TABLE IF NOT EXISTS calls_urls (
                call_code TEXT NOT NULL,
                call_title TEXT NOT NULL,
                file_id INTEGER NOT NULL,
                file_title TEXT NOT NULL,
                PRIMARY KEY (call_code, call_title, file_id, file_title),
                FOREIGN KEY (file_id) REFERENCES calls_files_information(id)
            );
            """
        ]
        try:
            cursor = self.connection.cursor()
            for query in create_table_queries:
                cursor.execute(query)
            self.connection.commit()
            return True
        except Exception as e:
            print("Error creating tables:", f"{e}")
            return False


    def get_cursor(self):
        """
        Get a cursor
        :return: cursor
        """
        return self.connection.cursor()

    @staticmethod
    def execute_query(cursor, query, params=()):
        """
        Execute a query
        :param cursor:
        :param query:
        :param params: tuple of parameters for SQL query
        :return: result
        """
        cursor.execute(query, params)

    @staticmethod
    def fetch_one(cursor):
        """
        Fetch one result
        :param cursor:
        :return: result
        """
        return cursor.fetchone()

    @staticmethod
    def fetch_all(cursor):
        """
        Fetch all results
        :param cursor:
        :return: result
        """
        return cursor.fetchall()

    def close_connection(self):
        """
        Close the connection
        :return: None
        """
        if self.connection:
            self.connection.close()

    def check_database(self):
        """
        Check if the database file exists and the required tables are present.
        :return: boolean
        """
        try:
            # Conectarse a la base de datos de SQLite3 y obtener un cursor
            self.connect()
            cursor = self.get_cursor()

            # Comprobar si existen las tablas esperadas
            tables_exist = all(
                cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name=?", (table,)).fetchone()
                for table in self.table_names
            )

            return tables_exist
        except Exception as e:
            print("Error checking database:", f"{e}")
            return False

    def check_tables(self):
        """
        Check if all required tables exist
        :return: boolean
        """
        try:
            cursor = self.get_cursor()
            cursor.execute("SELECT name FROM sqlite_master WHERE type='table'")
            tables = cursor.fetchall()
            table_names = [t[0] for t in tables]
            return all(table in table_names for table in self.table_names)
        except Exception as e:
            print("[bold red]Error checking tables:[/bold red]", f"{e}")
            return False

    def create_tables(self):
        """
        Create tables from an external SQL file
        :return: boolean
        """
        try:
            cursor = self.get_cursor()
            with open("tables_sqlite3.sql", "r") as file:
                sql = file.read()
                cursor.executescript(sql)
            self.connection.commit()
            return True
        except Exception as e:
            print("[bold red]Error creating tables:[/bold red]", f"{e}")
            return False

    def get_calls(self):
        """
        Get calls
        :return: call_code, call_title
        """
        cursor = self.get_cursor()
        cursor.execute("SELECT call_code, call_title FROM calls_basic_information")
        return self.fetch_all(cursor)

    def save_call_database(self, call, links, calls_delete):
        """
        Save call to database
        :param call: call
        :param links: links
        :param calls_delete: calls_delete
        :return: commit
        """
        sql = ""
        try:
            # remove call from calls_delete
            for i in range(len(calls_delete)):
                if calls_delete[i]['call_code'] == call['call_code'] and calls_delete[i]['call_title'] == call[
                    'call_title']:
                    del calls_delete[i]
                    break
            self.connect_database()
            cursor = self.get_cursor()
            # check first if exists in calls_basic_information
            sql = "SELECT * FROM calls_basic_information WHERE call_code = ? AND call_title = ?"
            cursor.execute(sql, (call['call_code'], call['call_title']))
            if cursor:
                result = cursor.fetchall()
            else:
                result = []
            if len(result) == 0:
                sql = (
                    "INSERT INTO calls_basic_information (call_code, call_title, call_href, call_type, opening_date, next_deadline, deadline_model, status, programme, type_of_action, budget_total, scope) "
                    "VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)")
                val = (
                    call['call_code'], call['call_title'], call['call_href'], call['call_type'], call['opening_date'],
                    call['next_deadline'], call['deadline_model'], call['status'], call['programme'],
                    call['type_of_action'], call['budget_total'], call['scope'])
            else:
                # update
                sql = (
                    "UPDATE calls_basic_information SET call_href = ?, call_type = ?, opening_date = ?, next_deadline = ?, deadline_model = ?, status = ?, programme = ?, type_of_action = ?, budget_total = ?, scope = ? WHERE call_code = ? and call_title = ?")
                val = (call['call_href'], call['call_type'], call['opening_date'], call['next_deadline'],
                       call['deadline_model'], call['status'], call['programme'], call['type_of_action'],
                       call['budget_total'], call['scope'], call['call_code'], call['call_title'])

            # Ejecuta la inserción o actualización
            cursor.execute(sql, val)
            self.connection.commit()  # Haz commit después de la inserción/actualización

            # check if exists in calls_description_information
            cursor.execute("SELECT * FROM calls_description_information WHERE call_code = ? AND call_title = ?",
                           (call['call_code'], call['call_title']))
            result = self.fetch_all(cursor)

            if len(result) == 0:
                sql = (
                    "INSERT INTO calls_description_information (call_code, call_title, topic_description, topic_destination, topic_conditions_and_documents, budget_overview, partner_search_announcements, start_submission, get_support, extra_information) "
                    "VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)")
                val = (call['call_code'], call['call_title'], call['topic_description'], call['topic_destination'],
                       call['topic_conditions_and_documents'], call['budget_overview'],
                       call['partner_search_announcements'], call['start_submission'], call['get_support'],
                       call['extra_information'])
            else:
                # update
                sql = "UPDATE calls_description_information SET topic_description = ?, topic_destination = ?, topic_conditions_and_documents = ?, budget_overview = ?, partner_search_announcements = ?, start_submission = ?, get_support = ?, extra_information = ? WHERE call_code = ? and call_title = ?"
                val = (call['topic_description'], call['topic_destination'], call['topic_conditions_and_documents'],
                       call['budget_overview'], call['partner_search_announcements'], call['start_submission'],
                       call['get_support'], call['extra_information'], call['call_code'], call['call_title'])

            # Ejecuta la inserción o actualización
            cursor.execute(sql, val)
            self.connection.commit()  # Haz commit después de la inserción/actualización
            cursor.close()  # Cierra el cursor

            # check if exists in calls_budget_information
            cursor = self.get_cursor()
            cursor.execute("SELECT * FROM calls_budget_information WHERE call_code = ? AND call_title = ?",
                           (call['call_code'], call['call_title']))
            result = self.fetch_all(cursor)
            call_budget_topic_list = call['budget_topic'].split("###")
            call_budget_amount_list = call['budget_amount'].split("###")
            call_budget_stages_list = call['budget_stages'].split("###")
            call_budget_opening_date_list = call['budget_opening_date'].split("###")
            call_budget_deadline_list = call['budget_deadline'].split("###")
            call_budget_contributions_list = call['budget_contributions'].split("###")
            call_budget_indicative_number_of_grants_list = call['budget_indicative_number_of_grants'].split("###")
            if len(call_budget_topic_list) > 0:
                for i in range(len(call_budget_topic_list)):
                    budget_topic = call_budget_topic_list[i]
                    budget_amount = call_budget_amount_list[i]
                    budget_stages = call_budget_stages_list[i]
                    budget_opening_date = call_budget_opening_date_list[i]
                    budget_deadline = call_budget_deadline_list[i]
                    budget_contributions = call_budget_contributions_list[i]
                    budget_indicative_number_of_grants = call_budget_indicative_number_of_grants_list[i]
                    if len(result) == 0:
                        sql = (
                            "INSERT INTO calls_budget_information (call_code, call_title, budget_topic, budget_amount, budget_stages, budget_opening_date, budget_deadline, budget_contributions, budget_indicative_number_of_grants) "
                            "VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)")
                        val = (call['call_code'], call['call_title'], budget_topic, budget_amount, budget_stages,
                               budget_opening_date, budget_deadline, budget_contributions,
                               budget_indicative_number_of_grants)
                    else:
                        # update
                        sql = "UPDATE calls_budget_information SET budget_amount = ?, budget_stages = ?, budget_opening_date = ?, budget_deadline = ?, budget_contributions = ?, budget_indicative_number_of_grants = ? WHERE call_code = ? and call_title = ? and budget_topic = ?"
                        val = (budget_amount, budget_stages, budget_opening_date, budget_deadline, budget_contributions,
                               budget_indicative_number_of_grants, call['call_code'], call['call_title'], budget_topic)

                    # Ejecuta la inserción o actualización
                    cursor.execute(sql, val)
                    self.connection.commit()

            # check if exists in calls_files_information
            for link in links:
                call_code = call['call_code']
                call_title = call['call_title']
                file_url = link['file_url']
                file_title = link['file_title']
                # check if exists
                sql = "SELECT * FROM calls_files_information WHERE file_url = ?"
                cursor.execute(sql, (file_url,))
                result = self.fetch_all(cursor)
                if len(result) == 0:
                    sql = "INSERT INTO calls_files_information (file_url, file_text, file_summary) VALUES (?, ?, ?)"
                    val = (link['file_url'], link['file_text'], link['file_summary'])
                    # Execute the insertion or update
                    cursor.execute(sql, val)
                    self.connection.commit()
                # get file_id
                sql = "SELECT id FROM calls_files_information WHERE file_url = ?"
                cursor.execute(sql, (file_url,))
                file_id = self.fetch_one(cursor)[0]
                self.connection.commit()

                # check if exists in calls_urls
                sql = "SELECT * FROM calls_urls WHERE call_code = ? AND call_title = ? AND file_id = ? AND file_title = ?"
                cursor.execute(sql, (call_code, call_title, file_id, file_title))
                result = self.fetch_all(cursor)
                if len(result) == 0:
                    sql = "INSERT INTO calls_urls (call_code, call_title, file_id, file_title) VALUES (?, ?, ?, ?)"
                    val = (call_code, call_title, file_id, file_title)
                    # Execute the insertion or update
                    cursor.execute(sql, val)

                self.connection.commit()

            cursor.close()  # Cierra el cursor
            return True

        except Exception as e:
            print(f"Error saving call to database: {e}")
            print(f"SQL: {sql}")
            return False

    def remove_call_delete(self, calls_delete):
        """
        Remove call from calls_delete (Put status = 'Closed')
        :return: number of calls removed
        """
        j = 0
        try:
            for i in range(len(calls_delete)):
                call = calls_delete[i]
                cursor = self.get_cursor()
                # update status in table calls_basic_information
                cursor.execute("UPDATE calls_basic_information SET status = ? WHERE call_code = ? AND call_title = ?",
                               ("Closed", call['call_code'], call['call_title']))

                # for table in self.table_names:
                #     if table == "calls_files_information":
                #         continue
                #     cursor.execute(f"DELETE FROM {table} WHERE call_code = ? AND call_title = ?", (call['call_code'], call['call_title']))
                self.connection.commit()
                j += 1

            return len(calls_delete)
        except Exception as e:
            print("[bold red]Error closing call from database:[/bold red]", f"{e}")
            return j


    def clear_all_tables(self):
        """
        Clear all tables
        :return: commit
        """
        try:
            cursor = self.get_cursor()
            for table in self.table_names:
                cursor.execute(f"DELETE FROM {table}")
            self.connection.commit()
            return True
        except Exception as e:
            print("[bold red]Error clearing tables:[/bold red]", f"{e}")
            return False

    def get_schema(self):
        """
        Get schema information for SQLite
        :return: schema
        """
        cursor = self.get_cursor()
        schema = {}
        for table in self.table_names:
            cursor.execute(f"PRAGMA table_info({table})")
            schema[table] = self.fetch_all(cursor)
        return schema

    def get_call_codes(self, scope):
        """
        Get call codes from database
        :return: call_codes
        """
        # get call_code from calls_basic_information table
        sql = "SELECT call_code, call_title FROM calls_basic_information WHERE scope = ?"
        cursor = self.get_cursor()
        cursor.execute(sql, (scope,))
        call_codes = cursor.fetchall() if cursor.rowcount > 0 else []

        return [(row[0], row[1]) for row in call_codes]

    def get_text_summary_from_link(self, link):
        """
        Get text and summary from link
        :param link: link
        """
        file_url = link[0]
        try:
            # get text from url
            file_text = self.get_text_from_url(file_url)
            # get summary from url
            file_summary = self.get_summary_from_url(file_url)
            file_error_description = ""
            file_error_code = ""
            if file_text == "":
                file_summary = ""
                file_error_description, file_error_code = self.get_error_url(file_url)
                if file_error_description:
                    print(f"Error getting text from link {file_url}: {file_error_description}")
                    print(f"Error code: {file_error_code}")

            with sqlite3.connect(self.database_path) as conn:
                cursor = conn.cursor()
                cursor.execute("SELECT id FROM calls_files_information WHERE file_url = ?", (file_url,))
                result = cursor.fetchall()
                if len(result) == 0:
                    # insert into database
                    sql = "INSERT INTO calls_files_information (file_url, file_text, file_summary, file_error_description, file_error_code) VALUES (?, ?, ?, ?, ?)"
                    cursor.execute(sql, (file_url, file_text, file_summary, file_error_description, file_error_code))
                else:
                    # update database
                    sql = "UPDATE calls_files_information SET file_text = ?, file_summary = ?, file_error_description = ?, file_error_code = ? WHERE file_url = ?"
                    cursor.execute(sql, (file_text, file_summary, file_error_description, file_error_code, file_url))

                conn.commit()

        except Exception as e:
            print(f"Error getting text and summary from link {file_url}: {e}")

    def get_type_company_from_description(self, description):
        """
        Get type of company from description
        :param description: description
        """
        call_code = description[0]
        call_title = description[1]
        topic_description = description[2]
        topic_destination = description[3]
        topic_conditions_and_documents = description[4]
        extra_information = description[5]
        text = ""
        if topic_description != "":
            text += f"TOPIC DESCRIPTION:\n{topic_description}\n\n"
        if topic_destination != "":
            text += f"TOPIC DESTINATION:\n{topic_destination}\n\n"
        if text == "" and extra_information !="":
            text += f"EXTRA_INFORMATION:\n{extra_information}"
        if text == "" and topic_conditions_and_documents !="":
            text = f"TOPIC CONDITIONS AND DOCUMENTS:\n{topic_conditions_and_documents}"
        try:
            # get type of company from text
            type_company = self.get_type_company_from_text(text)

            with sqlite3.connect(self.database_path) as conn:
                cursor = conn.cursor()
                # update database
                sql = "UPDATE calls_basic_information SET type_company = ? WHERE call_code = ? AND call_title = ?"
                cursor.execute(sql, (type_company, call_code, call_title))

                conn.commit()

        except Exception as e:
            print(f"Error getting type of company from description {call_code}: {call_title}: {e}")

    @staticmethod
    def get_error_url(url):
        """
        Get error from url
        :param url: url
        :return: error_description, error_code
        """
        error_description = ""
        error_code = ""
        try:
            response = requests.get(url)
            response.raise_for_status()
        except requests.exceptions.HTTPError as http_err:
            error_description = f"HTTP error occurred: {http_err}"
            error_code = "HTTPError"
        except requests.exceptions.ConnectionError as conn_err:
            error_description = f"Error Connecting: {conn_err}"
            error_code = "ConnectionError"
        except requests.exceptions.Timeout as time_err:
            error_description = f"Timeout Error: {time_err}"
            error_code = "TimeoutError"
        except requests.exceptions.RequestException as req_err:
            error_description = f"Request Exception: {req_err}"
            error_code = "RequestException"
        except Exception as e:
            error_description = f"Error: {e}"
            error_code = "Error"
        return error_description, error_code

    def get_text_from_url(self, url):
        """
        Get text from url
        :param url: url
        :return: text
        """
        # return ""
        # if type of url is pdf
        if url.endswith(".pdf"):
            return self.get_text_from_pdf(url)
        else:
            return ""

    def get_summary_from_url(self, url):
        """
        Get summary from url
        :param url: url
        :return: summary
        """
        # return ""
        # if type of url is pdf
        if url.endswith(".pdf"):
            return self.get_summary_from_pdf(url)
        else:
            return ""


