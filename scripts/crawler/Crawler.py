import requests


from selenium import webdriver
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as ec
from selenium.webdriver.chrome.service import Service as ChromeService
from webdriver_manager.chrome import ChromeDriverManager
from selenium.webdriver.common.by import By
from bs4 import BeautifulSoup
from random import randrange

import time

from rich import print
from rich.console import Console

#from Database_sqlite import Database
from Database_mysql import Database
from QdrantVectorial import QdrantVectorial

console = Console()

class Crawler:
    # Description: Crawler class which is used to crawl a website with a given URL and extract all the content from it.
    pages = ["fandit", "eu"]

    def __init__(self, page):
        if page not in self.pages:
            raise ValueError(f"URL not valid. URL must be one of the following: {self.pages}")
        self.page = page
        self.url = None
        self.url_login = None
        self.html = None
        self.isLogged = False
        self.needsLogin = False
        console.log(f"Initializing crawler {page} started", style="bold green")
        with console.status(f"[bold green]Initializing crawler for {page}...[/bold green]", spinner="dots") as status:
            status.update("[bold yellow]Initializing database...[/bold yellow]")
            self.db = Database()
            self.db.connect()
            if self.db.connection is None:
                status.update("[bold red]Error connecting to database[/bold red]")
                exit("Error connecting to database")
            if not self.db.check_database():
                if not self.db.create_database():
                    status.update("[bold red]Error creating database[/bold red]")
                    exit("Error creating database")
            # database exists
            if not self.db.check_tables():
                if not self.db.create_tables():
                    status.update("[bold red]Error creating tables[/bold red]")
                    exit("Error creating tables")

            # get actual calls (call_code, call_title) from database
            calls = self.db.get_calls()
            self.calls = [{"call_code": call[0], "call_title": call[1]} for call in calls]
            self.calls_delete = self.calls.copy()
            # initialize qdrant database
            status.update("[bold yellow]Initializing Qdrant...[/bold yellow]")
            self.qdrant = QdrantVectorial(collection_name="pdf_collection")
            # check if qdrant error
            if self.qdrant.error:
                status.update("[bold red]Error initializing Qdrant[/bold red]")
                exit("Error initializing Qdrant")

            status.update("[bold yellow]Initializing webdriver...[/bold yellow]")
            # INITIALIZATION
            chrome_options = webdriver.ChromeOptions()
            # don't show browser

            chrome_options.add_argument("--headless")  # Runs Chrome in headless mode.
            chrome_options.add_argument('--no-sandbox')  # Bypass OS security model
            # chrome_options.add_argument("--window-position=-2400,-2400")  # start minimized
            chrome_options.add_argument('disable-infobars')
            chrome_options.add_argument("--disable-extensions")
            chrome_options.add_argument("--disable-usb")
            chrome_options.add_argument('--log-level=3')
            # disable notifications log level
            # options INFO = 0, WARNING = 1, LOG_ERROR = 2, LOG_FATAL = 3
            # chrome_options.add_argument("--log-level=3")
            # silent output true
            #chrome_options.add_argument("--silent")
            #chrome_options.add_experimental_option('excludeSwitches', ['enable-logging'])
            # chrome_options.add_argument("--disable-notifications")
            # init driver
            self.driver = webdriver.Chrome(service=ChromeService(ChromeDriverManager().install()), options=chrome_options)
            # self.driver = webdriver.Chrome(self.chrome_driver_path)
            # init colorama
            #print("init colorama")
            #init(autoreset=True)
            # check if MySQL database exists
            status.update("[bold green]Initialization complete[/bold green]")
        console.log(f"Initialization crawler {page} completed", style="bold green")


    def connect_database(self, database=""):
        """
        Connect to database
        :return: database connection
        """
        try:
            if database == "":
                return self.db.connect()
            else:
                return self.db.connect_database()

        except Exception as e:
            print("[bold red]Error connecting to database:[/bold red]", f"{e}")
            return None

    def get_html(self):
        """
        Get html from url
        :return: None
        """
        try:
            response = requests.get(self.url)
            response.encoding = 'utf-8'
            self.html = response.text
        except Exception as e:
            print(f"Error: {e}")

    def get_page_source(self, url, where="body", tries=3):
        """
        Get page source from url
        :param url: url string
        :param where: where to find (Ex. body)
        :param tries: number of tries
        :return: page source
        """
        # Obtiene el código fuente de la página
        try:
            self.driver.get(url)
            # wait to load page (presence of body element) 10 seconds
            WebDriverWait(self.driver, 10).until(ec.presence_of_element_located((By.TAG_NAME, where)))
            time.sleep(randrange(5, 10))
        except Exception as e:
            print(f"\nError: {e}")
            if tries > 0:
                print(f"\nRetrying {tries} more times")
                self.get_page_source(url, where, tries - 1)
            else:
                print("No more tries")

        return self.driver.page_source

    def __str__(self):
        return f"URL: {self.url}\nCalls: {self.calls}"

    def refresh_driver(self):
        """
        Refresh driver
        :return: none
        """
        self.driver.refresh()
        WebDriverWait(self.driver, 10).until(ec.presence_of_element_located((By.TAG_NAME, "body")))
        time.sleep(randrange(1, 3))

        return self.driver.page_source

    def get_soup(self):
        """
        Get soup from page source
        :return: soup
        """
        return BeautifulSoup(self.driver.page_source, 'html.parser')

    @staticmethod
    def get_div_from_class(soup, class_name):
        """
        Get div from soup
        :param soup: soup
        :param class_name: class_name
        :return: div
        """
        return soup.find("div", class_=class_name)


    def insert_full_text_from_links(self):
        """
        Insert full text from links
        :param force_update:
        :return:
        """
        # get all links from database
        links = self.db.get_links()
        # get all links from database
        for link in links:
            # get link
            file_id = link[0]
            # get call_code
            call_code = link[1]
            # get call_title
            call_title = link[2]
            # get file_url
            file_url = link[3]
            # check if point exists (first page)
            point_id = int(f"{file_id:04}{1:04}")
            if not self.qdrant.point_exists(point_id):
                docs = self.db.get_docs_from_pdf(file_url)
                # insert full text
                self.qdrant.insert_full_text(file_id, call_code, call_title, file_url, docs)