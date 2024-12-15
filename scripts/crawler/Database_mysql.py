import time
from mysql.connector import connection
from langchain_community.utilities import SQLDatabase
import os
from dotenv import load_dotenv
from rich import print
import requests
from langchain_community.document_loaders.pdf import PyPDFLoader
from langchain_core.prompts import PromptTemplate
from langchain_openai import ChatOpenAI
from langchain_groq import ChatGroq
from langchain.chains.llm import LLMChain
from langchain.schema import Document

load_dotenv(override=True)


class Llm:
    def __init__(self):
        self.llm = self.create_llm(chat="openai",
                                   model_name=os.getenv('OLLAMA_MODEL_SUMMARIZE'),
                                   base_url=os.getenv('OLLAMA_BASE_URL'))

    @staticmethod
    def get_prompt(type_prompt="summary"):
        """
        Get prompt for summary
        :param type_prompt: type_prompt
        :return: prompt
        """
        type_prompt = type_prompt.lower()

        if type_prompt == "summary":
            prompt_template = """Write a long summary of the following document. 
            Only include information that is part of the document. 
            Do not include your own opinion or analysis.

            Document:
            "{document}"
            Summary:"""
        elif type_prompt == "type_company":
            prompt_template = """You are an expert assistant in identifying the types of entities a text is directed to.
             Classify the text into one or more of the following categories. 
             If multiple categories apply, separate them with commas. 
             Do not combine options into new categories.

+ Company:
  - Large Company
  - Midcap
  - SME
  - Microenterprise
  - Self-Employed

+ Organization:
  - NGO
  - Technology Centers
  - Universities
  - Research Centers
  - Others

+ Particulars:

If it is not possible to determine or if the text does not fit any category, leave the response empty (do not write anything).
Provide only the classification as shown in the examples below. 

Examples of Responses:

- Company: SME
- Organization: Technology Centers
- Individual
- Company: SME, Organization: Universities

Text to classify:
{text}

Classification:"""
        else:
            prompt_template = """Escribe un resumen largo del siguiente documento. 
            El idioma del resumen debe ser el mismo del documento.
                        Incluya únicamente información que forme parte del documento. 
                        No incluyas tu propia opinión o análisis.

                        Documento:
                        "{document}"
                        Resumen:"""

        return prompt_template

    @staticmethod
    def create_llm(chat="openai", temperature=0.1, model_name="mistral-nemo:latest", api_key="ollama",
                   base_url="http://host.docker.internal:11434/v1"):
        """
        Create LLM
        :return: LLM
        """
        if chat == "openai":
            llm = ChatOpenAI(
                temperature=temperature,
                model_name=model_name,
                api_key=api_key,
                base_url=base_url,
            )
        else:
            llm = ChatGroq(
                temperature=temperature,
                model_name=model_name,
            )
        return llm

    @staticmethod
    def create_llm_chain(llm, prompt):
        """
        Create LLM chain
        :param llm: llm
        :param prompt: prompt
        :return: llm_chain
        """
        llm_chain = LLMChain(llm=llm, prompt=prompt)
        return llm_chain


class Database:
    def __init__(self):
        """
        Initialize the database
        """
        self.connection = None
        self.database_type = "mysql"

        self.host = os.getenv('DB_HOST')
        self.port = os.getenv('DB_PORT')
        self.user = os.getenv('DB_USER')
        self.password = os.getenv('DB_PASSWORD')
        self.database = os.getenv('DB_DATABASE')
        self.table_names = ["calls_basic_information", "calls_description_information", "calls_budget_information",
                            "calls_files_information", "calls_urls"]
        self.Llm = Llm()

        self.types_companies = ["Company: Large", "Company: Midcap", "Company: SME", "Company: Microenterprise",
                                "Company: Self-Employed", "Organization: NGO", "Organization: Technology Centers",
                                "Organization: Universities", "Organization: Research Centers", "Organization: Others",
                                "Particulars", ""]

    def connect(self):
        """"
        Get a connection
        """
        self.connection = connection.MySQLConnection(
            host=self.host,
            port=self.port,
            user=self.user,
            password=self.password
        )

    def get_connection(self):
        """
        Get the connection
        """
        return connection.MySQLConnection(
            host=self.host,
            port=self.port,
            user=self.user,
            password=self.password,
            database=self.database
        )

    def connect_database(self):
        """
        Connect to the database
        """
        self.connection = connection.MySQLConnection(
            host=self.host,
            port=self.port,
            user=self.user,
            password=self.password,
            database=self.database
        )

    def get_cursor(self):
        """
        Get a cursor
        :return: cursor
        """
        return self.connection.cursor()

    @staticmethod
    def execute_query(cursor, query):
        """
        Execute a query
        :param cursor:
        :param query:
        :return: result
        """
        cursor.execute(query)

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
        self.connection.close()

    def check_database(self):
        """
        Check if database exists
        :return: boolean
        """
        try:
            cursor = self.connection.cursor()
            cursor.execute("SHOW DATABASES")
            dbnames = cursor.fetchall()
            for dbname in dbnames:
                if self.database in dbname:
                    # use database
                    cursor.execute(f"USE {self.database}")
                    return True

            return False
        except Exception as e:
            print("Error checking database:", f"{e}")
            return False

    def create_database(self):
        """
        Create database
        :return: none
        """
        try:
            cursor = self.connection.cursor()
            cursor.execute(f"CREATE DATABASE IF NOT EXISTS {self.database}")
            cursor.execute(f"USE {self.database}")
            return True
        except Exception as e:
            print("[bold red]Error creating database:[/bold red]", f"{e}")
            return False

    def check_tables(self):
        """
        Check if tables exist
        :return: boolean
        """
        try:
            cursor = self.connection.cursor()
            cursor.execute(f"SHOW TABLES FROM {self.database}")
            tables = cursor.fetchall()
            return len(tables) == 5
        except Exception as e:
            print("[bold red]Error checking tables:[/bold red]", f"{e}")
            return False

    def get_calls(self):
        """
        Get calls
        :return: call_code, call_title
        """
        cursor = self.get_cursor()
        cursor.execute("SELECT call_code, call_title FROM calls_basic_information")
        return self.fetch_all(cursor)

    def create_tables(self):
        """
        Create tables
        :return: none
        """
        try:
            cursor = self.connection.cursor()
            # drop tables
            for table in self.table_names:
                cursor.execute(f"DROP TABLE IF EXISTS {table}")
            self.connection.commit()
            time.sleep(1)

            # create tables for external sql file (tables.sql)
            cursor = self.connection.cursor()
            with open("tables.sql", "r") as file:
                sql = file.read()
                for _ in cursor.execute(sql, multi=True):
                    pass

            self.connection.commit()
            time.sleep(1)
            return True
        except Exception as e:
            print("[bold red]Error creating tables:[/bold red]", f"{e}")
            return False

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
            sql = "SELECT * FROM calls_basic_information WHERE call_code = %s AND call_title = %s"
            cursor.execute(sql, (call['call_code'], call['call_title']))
            if cursor:
                result = cursor.fetchall()
            else:
                result = []
            if len(result) == 0:
                sql = (
                    "INSERT INTO calls_basic_information "
                    "(call_code, call_title, call_href, call_type, "
                    "opening_date, next_deadline, deadline_model, status, programme, "
                    "type_of_action, budget_total, location) "
                    "VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)")
                val = (
                    call['call_code'], call['call_title'], call['call_href'], call['call_type'], call['opening_date'],
                    call['next_deadline'], call['deadline_model'], call['status'], call['programme'],
                    call['type_of_action'], call['budget_total'], call['location'])
            else:
                # update
                sql = (
                    "UPDATE calls_basic_information SET call_href = %s, call_type = %s, opening_date = %s, next_deadline = %s, deadline_model = %s, status = %s, programme = %s, type_of_action = %s, budget_total = %s, location = %s WHERE call_code = %s and call_title = %s")
                val = (call['call_href'], call['call_type'], call['opening_date'], call['next_deadline'],
                       call['deadline_model'], call['status'], call['programme'], call['type_of_action'],
                       call['budget_total'], call['location'], call['call_code'], call['call_title'])

            # Ejecuta la inserción o actualización
            cursor.execute(sql, val)
            self.connection.commit()  # Haz commit después de la inserción/actualización

            # check if exists in calls_description_information
            cursor.execute("SELECT * FROM calls_description_information WHERE call_code = %s AND call_title = %s",
                           (call['call_code'], call['call_title']))
            result = self.fetch_all(cursor)

            if len(result) == 0:
                sql = (
                    "INSERT INTO calls_description_information (call_code, call_title, topic_description, topic_destination, topic_conditions_and_documents, budget_overview, partner_search_announcements, start_submission, get_support, extra_information) "
                    "VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s)")
                val = (call['call_code'], call['call_title'], call['topic_description'], call['topic_destination'],
                       call['topic_conditions_and_documents'], call['budget_overview'],
                       call['partner_search_announcements'], call['start_submission'], call['get_support'],
                       call['extra_information'])
            else:
                # update
                sql = "UPDATE calls_description_information SET topic_description = %s, topic_destination = %s, topic_conditions_and_documents = %s, budget_overview = %s, partner_search_announcements = %s, start_submission = %s, get_support = %s, extra_information = %s WHERE call_code = %s and call_title = %s"
                val = (call['topic_description'], call['topic_destination'], call['topic_conditions_and_documents'],
                       call['budget_overview'], call['partner_search_announcements'], call['start_submission'],
                       call['get_support'], call['extra_information'], call['call_code'], call['call_title'])

            # Ejecuta la inserción o actualización
            cursor.execute(sql, val)
            self.connection.commit()  # Haz commit después de la inserción/actualización
            cursor.close()  # Cierra el cursor

            # check if exists in calls_budget_information
            cursor = self.get_cursor()
            cursor.execute("SELECT * FROM calls_budget_information WHERE call_code = %s AND call_title = %s",
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
                            "VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s)")
                        val = (call['call_code'], call['call_title'], budget_topic, budget_amount, budget_stages,
                               budget_opening_date, budget_deadline, budget_contributions,
                               budget_indicative_number_of_grants)
                    else:
                        # update
                        sql = "UPDATE calls_budget_information SET budget_amount = %s, budget_stages = %s, budget_opening_date = %s, budget_deadline = %s, budget_contributions = %s, budget_indicative_number_of_grants = %s WHERE call_code = %s and call_title = %s and budget_topic = %s"
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
                sql = "SELECT * FROM calls_files_information WHERE file_url = %s"
                cursor.execute(sql, (file_url,))
                result = self.fetch_all(cursor)
                if len(result) == 0:
                    sql = "INSERT INTO calls_files_information (file_url, file_text, file_summary) VALUES (%s, %s, %s)"
                    val = (link['file_url'], link['file_text'].strip(), link['file_summary'].strip())
                    # Execute the insertion or update
                    cursor.execute(sql, val)
                    self.connection.commit()
                # get file_id
                sql = "SELECT id FROM calls_files_information WHERE file_url = %s"
                cursor.execute(sql, (file_url,))
                file_id = self.fetch_one(cursor)[0]
                self.connection.commit()

                # check if exists in calls_urls
                sql = "SELECT * FROM calls_urls WHERE call_code = %s AND call_title = %s AND file_id = %s AND file_title = %s"
                cursor.execute(sql, (call_code, call_title, file_id, file_title))
                result = self.fetch_all(cursor)
                if len(result) == 0:
                    sql = "INSERT INTO calls_urls (call_code, call_title, file_id, file_title) VALUES (%s, %s, %s, %s)"
                    val = (call_code, call_title, file_id, file_title)
                    # Execute the insertion or update
                    cursor.execute(sql, val)

                self.connection.commit()

            cursor.close()  # Cierra el cursor

            return True

        except Exception as e:
            print("[bold red]Error saving call to database:[/bold red]", f"{e}")
            print(f"SQL: {sql}")
            print(f"Call url: {call['call_href']}")
            return False

    def remove_call_delete(self, calls_delete):
        """
        Remove call from calls_delete
        :return: number of calls removed
        """
        j = 0
        try:
            for i in range(len(calls_delete)):
                call = calls_delete[i]
                cursor = self.get_cursor()
                cursor.execute(
                    "UPDATE calls_basic_information SET status = %s WHERE call_code = %s AND call_title = %s",
                    ("Closed", call['call_code'], call['call_title']))
                self.connection.commit()
                j += 1

            return len(calls_delete)
        except Exception as e:
            print("[bold red]Error closing call from database:[/bold red]", f"{e}")
            return j

    def clear_all_tables(self):
        """
        Clear all tables: calls_basic_information, calls_budget_information, calls_description_information, calls_urls, calls_files_information
        :return: commit
        """
        # clear tables
        try:
            cursor = self.connection.cursor()
            for table in self.table_names:
                cursor.execute(f"DELETE FROM {table}")

            self.connection.commit()
            return True
        except Exception as e:
            print("[bold red]Error clearing tables:[/bold red]", f"{e}")
            return False

    def get_schema(self):
        """
        Get schema
        :return: schema
        """
        self.connect_database()
        cursor = self.get_cursor()
        cursor.execute("SHOW TABLES")
        tables = self.fetch_all(cursor)

        schema = {}
        for table in tables:
            table_name = table[0]
            cursor.execute(f"DESCRIBE {table_name}")
            schema[table_name] = self.fetch_all(cursor)

        return schema

    def get_schema_sqlconnector(self):
        """
        Get schema
        :return: schema
        """
        try:
            if self.password:
                mysql_uri = f'mysql+mysqlconnector://{self.user}:{self.password}@{self.host}:{self.port}/{self.database}'
            else:
                mysql_uri = f'mysql+mysqlconnector://{self.user}@{self.host}:{self.port}/{self.database}'

            print(f"[INFO] Conectando a la base de datos con la URI: {mysql_uri}")

            dbschema = SQLDatabase.from_uri(mysql_uri)
            # Verificar si dbschema tiene un valor
            if dbschema:
                print("[INFO] Conexión exitosa.")
                return dbschema.get_table_info()
            else:
                print("[ERROR] dbschema no contiene datos.")
                return None
        except Exception as e:
            print("Error getting schema:", f"{e}")
            return None

    def get_call_codes(self, location):
        """
        Get call codes from database
        :param location: location
        :return: call_codes
        """
        # get call_code from calls_basic_information table
        sql = "SELECT call_code, call_title FROM calls_basic_information WHERE location = %s"
        cursor = self.get_cursor()
        cursor.execute(sql, (location,))
        call_codes = cursor.fetchall() if cursor.rowcount > 0 else []

        return [(row[0], row[1]) for row in call_codes]

    def get_text_summary_from_link(self, link):
        """
        Get text and summary from link
        :param link: link
        """
        file_url = link[0]
        conn = None  # Inicializar conn aquí para evitar errores
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

            # Actualizar la base de datos
            sql = ("UPDATE calls_files_information SET file_text = %s, file_summary = %s, "
                   "file_error_description = %s, file_error_code = %s WHERE file_url = %s")

            # Conectar a la base de datos
            conn = self.get_connection()

            with conn.cursor() as cursor:
                cursor.execute(sql,
                               (file_text, file_summary, file_error_description, file_error_code, file_url))
                conn.commit()

            # with self.get_connection() as conn:
            #     cursor = conn.cursor()
            #     cursor.execute(sql, (file_text, file_summary, file_error_description, file_error_code, file_url))
            #     conn.commit()

        except Exception as e:
            print(f"Error getting text and summary from link {file_url}: {e}")

        finally:
            if conn:
                conn.close()

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
        if text == "" and extra_information != "":
            text += f"EXTRA_INFORMATION:\n{extra_information}"
        if text == "" and topic_conditions_and_documents != "":
            text = f"TOPIC CONDITIONS AND DOCUMENTS:\n{topic_conditions_and_documents}"

        conn = None  # Inicializar conn aquí para evitar errores
        try:
            # get type of company from text
            type_company = self.get_type_company_from_text(text)
            sql = ("UPDATE calls_basic_information SET type_company = %s WHERE call_code = %s "
                   "AND call_title = %s")
            # Conectar a la base de datos
            conn = self.get_connection()

            with conn.cursor() as cursor:
                # update database

                cursor.execute(sql, (type_company, call_code, call_title))
                conn.commit()

        except Exception as e:
            print(f"Error getting type of company from description {call_code}: {call_title}: {e}")

        finally:
            if conn:
                conn.close()

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

    def get_text_from_pdf(self, url):
        """
        Get text from pdf
        :param url: url
        :return: text
        """
        docs = self.get_docs_from_pdf(url)
        return self.get_text_from_docs(docs)

    def get_summary_from_pdf(self, url):
        """
        Get summary from pdf
        :param url: url
        :return: summary
        """
        docs = self.get_docs_from_pdf(url)
        summary = ""
        if docs:
            try:
                prompt_template = """Write a long and exhaustive summary of the document. 
                            Only include information that is part of the document. 
                            Do not include your own opinion or analysis.
        
                            Document:
                            "{document}"
                            Summary:"""
                prompt = PromptTemplate.from_template(prompt_template)
                llm = ChatOpenAI(
                    temperature=0.1,
                    model_name="llama3.2:1b-instruct-q3_K_L",
                    api_key="ollama",
                    base_url="http://host.docker.internal:11434/v1",
                )
                stuff_chain = prompt | llm
                input_data = {"document": docs}
                summary = stuff_chain.invoke(input_data)
                # get content from summary
                summary = summary.content
            except Exception as e:
                print(f"Error getting summary from pdf {url}: {e}")

        return summary

    def get_type_company_from_text(self, text, tries=3):
        """
        Get type of company from text
        :param text: text
        :param tries: number of tries
        :return: type_company
        """
        type_company = "Unknown"
        try:
            while tries > 0 and not any(company.strip() in self.types_companies for company in type_company.split(',')):
                prompt_template = self.Llm.get_prompt(type_prompt="type_company")
                prompt = PromptTemplate.from_template(prompt_template)
                llm = ChatOpenAI(
                    temperature=0.1,
                    model_name="llama3.2:1b-instruct-q3_K_L",
                    api_key="ollama",
                    base_url="http://host.docker.internal:11434/v1",
                )
                # stuff_chain = create_stuff_documents_chain(llm=llm, prompt=prompt, document_variable_name="text")
                stuff_chain = prompt | llm
                # Crear un objeto Document con el texto y metadatos opcionales
                document = Document(page_content=text)
                documents = [document]
                # Create dict with the document key
                input_data = {"text": documents}
                # invoke the chain
                type_company = stuff_chain.invoke(input_data)
                # get content from type_company
                type_company = type_company.content
                # clean type_company
                type_company = self.clean_type_company(type_company)
                tries -= 1

            if not any(company.strip() in self.types_companies for company in type_company.split(',')):
                type_company = "Unknown"

        except Exception as e:
            type_company = ""
            print(f"Error getting type of company from text: {e}")
        return type_company

    @staticmethod
    def clean_type_company(type_company):
        """
        Clean type of company
        :param type_company: type_company
        :return: type_company
        """
        type_company.replace('"', '')
        if "en blanco" in type_company.lower():
            type_company = ""
        if len(type_company) > 100:
            type_company = ""

        return type_company

    @staticmethod
    def get_docs_from_pdf(url):
        """
        Get text from pdf
        :param url: url
        :return: text
        """
        try:
            loader = PyPDFLoader(url)
            # response = requests.get(url, timeout=10)
            # response.raise_for_status()  # Verifica si la respuesta es correcta
            # pdf_file = BytesIO(response.content)
            # loader = PyPDFLoader(pdf_file)
            docs = loader.load()
        except Exception:
            docs = []
        return docs

    @staticmethod
    def get_text_from_docs(docs):
        """
        Get text from docs
        :param docs: docs
        :return: text
        """
        return "\n\n".join([doc.page_content for doc in docs])

    def get_links(self):
        """
        Get links
        :return: links
        """
        cursor = self.get_cursor()
        cursor.execute("SELECT "
                       "a.id, b.call_code, b.call_title, a.file_url "
                       "FROM calls_files_information AS a INNER JOIN calls_urls AS b "
                       "ON a.id = b.file_id "
                       "WHERE a.file_text != '' AND a.file_error_code = '' "
                       "GROUP BY b.file_id"
                       )
        return self.fetch_all(cursor)
