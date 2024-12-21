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
from langchain_ollama import ChatOllama
from langchain.chains.llm import LLMChain
from langchain.schema import Document

from sentence_transformers import SentenceTransformer
from sklearn.metrics.pairwise import cosine_similarity

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
            prompt_template = """Write a detailed and exhaustive summary of the following document. 
Ensure that all key details, including numbers, dates, and specific terminology, are accurately included. 
Only include information that is part of the document. 
Do not include your own opinion, analysis, or interpretation.

Document:
"{document}"
Summary:"""
        elif type_prompt == "type_company":
            prompt_template = """You are an expert assistant in classifying the target audience of a text. Categorize the text into one or more of the following options. If multiple categories apply, list them separated by commas. Do not create new categories or modify the existing ones.

Categories:
- Company: Large Company, Midcap, SME, Microenterprise, Self-Employed
- Organization: NGO, Technology Centers, Universities, Research Centers, Others
- Particulars


If the text cannot be classified or does not match any category, leave the response blank.

Examples:
- Company: SME
- Organization: Technology Centers
- Particulars
- Company: SME, Organization: Universities
Text:
{text}

Classification:"""
        else:
            prompt_template = """"""

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
        elif chat == "ollama":
            llm = ChatOllama(
                temperature=temperature,
                model=model_name,
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

        self.connection = self.get_connection()

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
            return len(tables) == 6
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
            cursor.execute("SET FOREIGN_KEY_CHECKS = 0;")
            for table in self.table_names:
                cursor.execute(f"DROP TABLE IF EXISTS {table}")
            cursor.execute("SET FOREIGN_KEY_CHECKS = 1;")
            self.connection.commit()
            time.sleep(1)

            # create tables for external sql file (tables.sql)
            cursor = self.connection.cursor()
            with open("tables.sql", "r") as file:
                sql_commands = file.read().split(";")  # Split the file into commands

                for command in sql_commands:
                    if command.strip():  # Execute the command if it's not empty
                        cursor.execute(command + ";")

            self.connection.commit()
            time.sleep(5)
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
            if call['next_deadline_date'] == "":
                call['next_deadline_date'] = None
            if call['opening_date'] == "":
                call['opening_date'] = None

            # remove call from calls_delete
            for i in range(len(calls_delete)):
                if (calls_delete[i]['call_code'] == call['call_code'] and
                        calls_delete[i]['call_title'] == call['call_title']):
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
                    "(call_code, call_title, call_href, funding_mechanism, "
                    "opening_date, next_deadline_date, submission_type, call_state, programme, "
                    "type_of_action, budget_total, eligibility_region, extra_information) "
                    "VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)")
                val = (
                    call['call_code'], call['call_title'], call['call_href'], call['funding_mechanism'], call['opening_date'],
                    call['next_deadline_date'], call['submission_type'], call['call_state'], call['programme'],
                    call['type_of_action'], call['budget_total'], call['eligibility_region'], call['extra_information'])
            else:
                # print(f"Actualizamos con extra information: {call['extra_information']}")
                # update
                sql = (
                    "UPDATE calls_basic_information SET call_href = %s, funding_mechanism = %s, opening_date = %s,"
                    " next_deadline_date = %s, submission_type = %s, call_state = %s, programme = %s, type_of_action = %s,"
                    " budget_total = %s, eligibility_region = %s, extra_information = %s WHERE call_code = %s and call_title = %s")
                val = (call['call_href'], call['funding_mechanism'], call['opening_date'], call['next_deadline_date'],
                       call['submission_type'], call['call_state'], call['programme'], call['type_of_action'],
                       call['budget_total'], call['eligibility_region'], call['extra_information'],
                       call['call_code'], call['call_title'])

            # Execute the insertion or update
            cursor.execute(sql, val)
            self.connection.commit()  # Commit after the insertion/update

            # check if exists in calls_description_information
            cursor.execute("SELECT * FROM calls_description_information WHERE call_code = %s AND call_title = %s",
                           (call['call_code'], call['call_title']))
            result = self.fetch_all(cursor)

            if len(result) == 0:
                sql = (
                    "INSERT INTO calls_description_information (call_code, call_title, topic_description,"
                    " topic_destination, topic_conditions_and_documents, budget_overview,"
                    " partner_search_announcements, start_submission, get_support, extra_information) "
                    "VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s)")
                val = (call['call_code'], call['call_title'], call['topic_description'], call['topic_destination'],
                       call['topic_conditions_and_documents'], call['budget_overview'],
                       call['partner_search_announcements'], call['start_submission'], call['get_support'],
                       call['extra_information'])
            else:
                # update
                sql = ("UPDATE calls_description_information SET topic_description = %s, topic_destination = %s,"
                       " topic_conditions_and_documents = %s, budget_overview = %s, partner_search_announcements = %s,"
                       " start_submission = %s, get_support = %s, extra_information = %s "
                       "WHERE call_code = %s and call_title = %s")
                val = (call['topic_description'], call['topic_destination'], call['topic_conditions_and_documents'],
                       call['budget_overview'], call['partner_search_announcements'], call['start_submission'],
                       call['get_support'], call['extra_information'], call['call_code'], call['call_title'])

            # Execute the insertion or update
            cursor.execute(sql, val)
            self.connection.commit()  # Commit after the insertion/update
            cursor.close()

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
                            "INSERT INTO calls_budget_information ("
                            "call_code, call_title, budget_topic, budget_amount, budget_stages, "
                            "budget_opening_date, budget_deadline, budget_contributions, "
                            "budget_indicative_number_of_grants) "
                            "VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s)")
                        val = (call['call_code'], call['call_title'], budget_topic, budget_amount, budget_stages,
                               budget_opening_date, budget_deadline, budget_contributions,
                               budget_indicative_number_of_grants)
                    else:
                        # update
                        sql = ("UPDATE calls_budget_information SET budget_amount = %s, budget_stages = %s, "
                               "budget_opening_date = %s, budget_deadline = %s, budget_contributions = %s, "
                               "budget_indicative_number_of_grants = %s "
                               "WHERE call_code = %s and call_title = %s and budget_topic = %s")
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
                sql = ("SELECT * FROM calls_urls "
                       "WHERE call_code = %s AND call_title = %s AND file_id = %s AND file_title = %s")
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
            print(f"SQL: {sql}, Val: {val}")
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
                    "UPDATE calls_basic_information SET call_state = %s WHERE call_code = %s AND call_title = %s",
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

            print(f"[INFO] Connecting to the database with URI: {mysql_uri}")

            dbschema = SQLDatabase.from_uri(mysql_uri)
            # check if dbschema has data
            if dbschema:
                print("[INFO] Connected successfully to the database.")
                return dbschema.get_table_info()
            else:
                print("[ERROR] dbschema does not have data.")
                return None
        except Exception as e:
            print("Error getting schema:", f"{e}")
            return None

    def get_call_codes(self, eligibility_region):
        """
        Get call codes from database
        :param eligibility_region: eligibility_region
        :return: call_codes
        """
        cursor = None
        conn = None
        try:
            # Consulta para obtener los call_code y call_title
            sql = "SELECT call_code, call_title FROM calls_basic_information WHERE eligibility_region = %s"
            conn = self.get_connection()
            cursor = conn.cursor()

            cursor.execute(sql, (eligibility_region,))
            call_codes = cursor.fetchall()  # Get all the results
        except Exception as e:
            print(f"Error getting call codes from database: {e}")
            call_codes = []
        finally:
            if cursor:
                cursor.close()
            if conn:
                conn.close()

        return [(row[0], row[1]) for row in call_codes]

    @staticmethod
    def calculate_similarity(text, summary):
        """
        Calculate similarity
        :param text: text
        :param summary: summary
        :return: similarity
        """
        # Load embeddings model
        model = SentenceTransformer('paraphrase-MiniLM-L6-v2')
        # Get embeddings
        embedding_text = model.encode(text).reshape(1, -1)
        embedding_summary = model.encode(summary).reshape(1, -1)
        # Calculate cosine similarity
        similarity = cosine_similarity(embedding_text, embedding_summary)[0][0]
        similarity = float(similarity)  # Convert to Python float

        return similarity

    def get_text_summary_from_link(self, link):
        """
        Get text and summary from link
        :param link: link
        """
        file_url = link[0]
        conn = None
        cursor = None
        try:
            # get text from url
            file_text = self.get_text_from_url(file_url)
            # get summary from url
            file_summary = self.get_summary_from_url(file_url)
            file_similarity = self.calculate_similarity(file_text, file_summary)
            file_error_description = ""
            file_error_code = ""
            if file_text == "":
                file_summary = ""
                file_error_description, file_error_code = self.get_error_url(file_url)
                if file_error_description:
                    print(f"Error getting text from link {file_url}: {file_error_description}")
                    print(f"Error code: {file_error_code}")

            # Update database
            sql = ("UPDATE calls_files_information SET file_text = %s, file_summary = %s, "
                   "file_similarity = %s, file_error_description = %s, file_error_code = %s "
                   "WHERE file_url = %s")

            # Connect to the database
            conn = self.get_connection()
            cursor = conn.cursor()
            cursor.execute(sql,
                           (file_text.strip(), file_summary, file_similarity,
                            file_error_description, file_error_code, file_url))
            conn.commit()

        except Exception as e:
            print(f"Error getting text and summary from link {file_url}: {e}")
            if conn:
                conn.rollback()  # Rollback in case of error
        finally:
            if cursor:
                cursor.close()
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

        conn = None
        cursor = None
        try:
            # get type of company from text
            type_company = self.get_type_company_from_text(text)
            sql = ("UPDATE calls_basic_information SET type_company = %s WHERE call_code = %s "
                   "AND call_title = %s")
            # Connect to the database
            conn = self.get_connection()
            cursor = conn.cursor()
            cursor.execute(sql, (type_company, call_code, call_title))
            conn.commit()

        except Exception as e:
            print(f"Error getting type of company from description {call_code}: {call_title}: {e}")
            if conn:
                conn.rollback()  # Rollback in case of error
        finally:
            if cursor:
                cursor.close()
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
                prompt_template = """Write a detailed and exhaustive summary of the following document. 
Ensure that all key details, including numbers, dates, and specific terminology, are accurately included. 
Only include information that is part of the document. 
Do not include your own opinion, analysis, or interpretation.
        
                            Document:
                            "{document}"
                            Summary:"""
                prompt = PromptTemplate.from_template(prompt_template)
                # llm = ChatOpenAI(
                #     temperature=0.1,
                #     model_name=os.getenv('OLLAMA_MODEL_SUMMARIZE'),
                #     api_key="ollama",
                #     base_url="http://host.docker.internal:11434/v1",
                #     max_tokens=None,
                #
                # )
                llm = ChatOllama(
                    temperature=0.1,
                    model=os.getenv('OLLAMA_MODEL_SUMMARIZE'),
                    base_url=os.getenv('OLLAMA_BASE_URL')
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
                # llm = ChatOpenAI(
                #     temperature=0.1,
                #     model_name="llama3.2:1b-instruct-q3_K_L",
                #     api_key="ollama",
                #     base_url="http://host.docker.internal:11434/v1",
                # )
                llm = ChatOllama(
                    temperature=0.1,
                    model=os.getenv('OLLAMA_MODEL_TYPE_COMPANY'),
                    base_url=os.getenv('OLLAMA_BASE_URL'),
                    # num_ctx=2048
                )
                # stuff_chain = create_stuff_documents_chain(llm=llm, prompt=prompt, document_variable_name="text")
                stuff_chain = prompt | llm
                # Create document from text
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
            docs = loader.load()
            if not docs:
                print(f"Error getting docs from pdf {url}")
        except Exception as e:
            print(f"Error getting docs from pdf {url}")
            print(f"Error: {e}")
            docs = []

        return docs

    @staticmethod
    def get_text_from_docs(docs):
        """
        Get text from docs
        :param docs: docs
        :return: text
        """
        if not docs:
            return "No docs in pdf"
        content = "\n\n".join([doc.page_content for doc in docs])
        # trip content
        return content.strip()

    def get_links(self):
        """
        Get links
        :return: links
        """
        cursor = self.get_cursor()

        sql = """SELECT 
                    MIN(a.id) AS id, 
                    b.call_code, 
                    b.call_title, 
                    MIN(a.file_url) AS file_url
                FROM 
                    calls_files_information AS a 
                INNER JOIN 
                    calls_urls AS b 
                ON 
                    a.id = b.file_id 
                WHERE 
                    a.file_text != '' 
                    AND a.file_error_code = '' 
                GROUP BY 
                    b.call_code, b.call_title;"""

        sql = """SELECT 
                a.id, b.call_code, b.call_title, a.file_url 
                FROM calls_files_information AS a INNER JOIN calls_urls AS b 
                ON a.id = b.file_id 
                WHERE a.file_text != '' AND a.file_error_code = '' 
                GROUP BY b.file_id"""

        sql = """
        SELECT a.id, a.file_url FROM calls_files_information as a WHERE a.file_text!='' AND a.file_error_code=''
        """
        cursor.execute(sql)
        return self.fetch_all(cursor)

    def logging_crawling(self, crawler_name, status, root_id=0, message=""):
        """
        Logging crawling
        :param crawler_name: crawler_name
        :param status: status
        :param root_id: root_id
        :param message: message
        :return: log_id
        """
        log_id = None
        conn = None
        cursor = None
        try:
            status_list = os.getenv("STATUS_LIST").split(",")
            if status not in status_list:
                message = f"Status {status} not in {status_list}"
                status = 'ERROR'

            # Get the connection & cursor
            conn = self.get_connection()
            cursor = conn.cursor()

            # Insert the log
            sql_query = """
                    INSERT INTO calls_logs (root_id, crawler_name, created_at, status, message) 
                    VALUES (%s, %s, NOW(), %s, %s)
                """
            cursor.execute(sql_query, (root_id, crawler_name, status, message))

            # Realiza el commit de la transacción
            conn.commit()

            # Obtiene el ID del último registro insertado
            cursor.execute("SELECT LAST_INSERT_ID()")
            log_id = cursor.fetchone()[0]

        except Exception as e:
            print(f"Error logging crawling: {e}")
            if conn:
                conn.rollback()  # En caso de error, realiza un rollback
        finally:
            # Cierra el cursor y la conexión
            if cursor:
                cursor.close()
            if conn:
                conn.close()

        return log_id
