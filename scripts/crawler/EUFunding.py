import csv
from concurrent.futures.thread import ThreadPoolExecutor
from concurrent.futures import ProcessPoolExecutor
from concurrent.futures import as_completed
from Crawler import Crawler
import time
from selenium.webdriver.common.by import By
import html2text
from random import randrange
from rich import print
from rich.console import Console
from rich.progress import (
    BarColumn,
    MofNCompleteColumn,
    Progress,
    TextColumn,
    TimeElapsedColumn,
    TimeRemainingColumn,
)

# Increase limit of csv field size
csv.field_size_limit(10 ** 9)

console = Console()
# Define custom progress bar
progress_bar = Progress(
    TextColumn("[progress.percentage]{task.percentage:>3.0f}%"),
    BarColumn(),
    MofNCompleteColumn(),
    TextColumn("•"),
    TimeElapsedColumn(),
    TextColumn("•"),
    TimeRemainingColumn(),
)


class EUFunding(Crawler):
    def __init__(self):
        super().__init__("eu")
        self.page = 1
        self.page_all = 0
        self.is_open = True
        self.is_closed = False
        self.is_forthcoming = True
        self.num_results_per_page = 50  # 10, 50 or 100
        self.global_url = "https://ec.europa.eu"
        # get first page url
        self.url = self.get_url()
        self.soup = None
        self.location = "Europe"
        self.currency = "EUR"

    def start_crawling(self, force_update=False):
        """
        Start crawling
        """
        console.log("Starting crawling...", style="bold green")
        with console.status("[bold green]Starting crawling...[/bold green]") as status:
            self.get_page_source(self.url)  # initialize page source with first page (default)
            # accept cookies, only once?
            status.update("[bold yellow]Accepting cookies...[/bold yellow]")
            self.accept_cookies()
            # get all existing call_code, call_title in database
            call_codes = self.db.get_call_codes(self.location)
            # get soup
            soup = self.get_soup()
            # get number of items found (total)
            status.update("[bold yellow]Getting items...[/bold yellow]")
            items_found = self.get_items(soup)
            print(f"\nEu funding has {items_found} calls")
            current_page = self.get_current_page(soup)
            status.update(f"[bold yellow]Getting calls from page {current_page}[/bold yellow]")
            # Get all calls from the page
            calls = self.get_calls(soup)

            # Get number of calls in the page
            len_calls = len(calls)
            i = 0
            call_fields = []
            if len_calls > 0:
                while True:
                    # execute in parallel
                    with ThreadPoolExecutor(max_workers=5) as executor:
                        # Utilizamos map para aplicar `get_call_fields` a cada elemento de `calls`
                        call_fields_page = list(executor.map(self.get_call_fields, calls))

                    i += len(call_fields_page)
                    call_fields.extend(call_fields_page)
                    # if more items found than i, go to next page
                    if int(items_found) > i:
                        # go to next page
                        self.go_next_page()
                        # Get new page source
                        soup = self.get_soup()
                        # get current page
                        current_page = self.get_current_page(soup)
                        status.update(f"[bold yellow]Getting calls from page {current_page}[/bold yellow]")
                        # get calls from the page
                        calls = self.get_calls(soup)
                        # get number of calls in the page
                        items_found = self.get_items(soup)
                    else:
                        # out of while loop
                        break
                time.sleep(1)
                print(f"\nProcessed {i} calls")

        # At the end get extended fields from each call
        console.log("Getting extended information...", style="bold green")
        status_name_list = ()
        # get all status name list
        for i, call in enumerate(call_fields):
            call_code = call['call_code']
            status_name = f"Getting extended fields for call code ({i + 1}/{len(call_fields)}): {call_code}"
            status_name_list += (status_name,)

        with progress_bar as p:
            for call_num in p.track(range(len(call_fields))):
                call = call_fields[call_num]
                call_code = call['call_code']
                call_title = call['call_title']

                if not (call_code, call_title) in call_codes or force_update:
                    fields_extended, links = self.get_call_fields_extended(call)
                    # added fields to call
                    call.update(fields_extended)
                    # save call to database
                    self.db.save_call_database(call, links, self.calls_delete)

        print(f"\nProcessed {i} calls in {current_page} pages")
        # Cierra el navegador al finalizar
        status.update("[bold yellow]Closing browser...[/bold yellow]")
        self.driver.quit()
        print("\nDriver closed!")
        console.log("Closing not existing calls", style="bold green")
        number_calls_removed = self.db.remove_call_delete(self.calls_delete)
        print(f"\nClosed {number_calls_removed} calls")
        console.log("Start NLP links summary", style="bold green")
        self.get_text_and_summary_from_links(force_update)

        console.log("Start NLP type_company", style="bold green")
        self.get_type_company_from_descriptions(force_update)

        console.log("Start vectorial database (PDF)", style="bold green")
        self.insert_full_text_from_links()

        console.log("Crawling finished!", style="bold green")
        # print call_fields
        print(f"Call fields length: {len(call_fields)}")

    def get_text_and_summary_from_links(self, force_update=False):
        """
        Get text and summary from calls files table
        """
        # get all links from database
        if force_update:
            sql = "SELECT DISTINCT(file_url) FROM calls_files_information"
        else:
            sql = "SELECT DISTINCT(file_url) FROM calls_files_information WHERE file_text = '' OR file_summary = '' AND file_error_code = '' AND file_error_description = ''"
        cursor = self.db.get_cursor()
        cursor.execute(sql)
        links = cursor.fetchall()
        # get number of links
        num_links = len(links)
        print(f"\nExtracting text and summary from {num_links} links...")
        # parallel processing
        # Iniciar la barra de progreso de rich
        with Progress(
                TextColumn("[bold blue]{task.fields[link_id]}[/bold blue]", justify="right"),
                BarColumn(),
                TextColumn("[progress.percentage]{task.percentage:>3.1f}%"),
                TimeElapsedColumn(),
                TextColumn("•"),
                TimeRemainingColumn(),
        ) as progress:
            task_id = progress.add_task("Processing Links", link_id="", total=num_links)
            with ThreadPoolExecutor(max_workers=4) as pool:
                # Utilizamos map para aplicar `get_call_fields` a cada elemento de `calls`
                futures = {pool.submit(self.db.get_text_summary_from_link, link): link for link in links}
                for future in as_completed(futures):
                    link = futures[future]
                    # Tiempo de inicio
                    link_id = f"{link[0]}"
                    # progress.update(task_id=call_url_id, advance=1)
                    progress.update(task_id, advance=1, link_id=link_id)
                    # try:
                    #     result = future.result()  # Esto lanza cualquier excepción de los hilos
                    # except Exception as e:
                    #     print(f"Error al procesar el enlace {futures[future]}: {e}")
                    #     # Manejo de errores adecuado
                    # progress.update(task_id, advance=1, link_id=f"{futures[future][0]}")

        print("\nFinished extracting text and summary from links")

    def get_type_company_from_descriptions(self, force_update=False):
        """
        Get type of company from description information
        """
        # get all links from database
        if force_update:
            sql = "SELECT call_code, call_title, topic_description, topic_destination, topic_conditions_and_documents, extra_information FROM calls_description_information"
        else:
            sql = "SELECT a.call_code, a.call_title, a.topic_description, a.topic_destination, a.topic_conditions_and_documents, a.extra_information FROM calls_description_information as a, calls_basic_information as b WHERE b.type_company IS NULL AND a.call_code = b.call_code AND a.call_title = b.call_title"
        cursor = self.db.get_cursor()
        cursor.execute(sql)
        descriptions = cursor.fetchall()
        # get number of links
        num_descriptions = len(descriptions)
        print(f"\nExtracting type of company from {num_descriptions} descriptions...")
        # parallel processing
        # Iniciar la barra de progreso de rich
        with Progress(
                TextColumn("[bold blue]{task.fields[link_id]}[/bold blue]", justify="right"),
                BarColumn(),
                TextColumn("[progress.percentage]{task.percentage:>3.1f}%"),
                TimeElapsedColumn(),
                TextColumn("•"),
                TimeRemainingColumn(),
        ) as progress:
            task_id = progress.add_task("Processing Descriptions", link_id="", total=num_descriptions)
            with ThreadPoolExecutor(max_workers=4) as pool:
                # Utilizamos map para aplicar `get_call_fields` a cada elemento de `calls`
                futures = {pool.submit(self.db.get_type_company_from_description, description): description for
                           description in descriptions}
                for future in as_completed(futures):
                    description = futures[future]
                    # Tiempo de inicio
                    description_id = f"{description[0]}_{description[1]}"
                    # progress.update(task_id=call_url_id, advance=1)
                    progress.update(task_id, advance=1, description_id=description_id)

        print("\nFinished extracting type of company from descriptions")

    def get_url(self):
        """
        Get URL for EU funding
        https://ec.europa.eu/info/funding-tenders/opportunities/portal/screen/opportunities/calls-for-proposals?isExactMatch=true&status=31094501,31094502&order=DESC&pageNumber=1&pageSize=50&sortBy=startDate
        :return: URL string
        """
        status_text = ""
        if self.is_forthcoming:
            status_text = "31094501" + ","
        if self.is_open:
            status_text += "31094502" + ","
        if self.is_closed:
            status_text += "31094503" + ","
        if status_text.endswith(","):
            status_text = status_text[:-1]

        init_url = self.global_url + '/info/funding-tenders/opportunities/portal/screen/opportunities/calls-for-proposals?isExactMatch=true&status='

        url = init_url + status_text + '&order=DESC&pageNumber=' + str(self.page) + '&pageSize=' + str(
            self.num_results_per_page) + '&sortBy=startDate'

        return url

    def accept_cookies(self):
        """
        Accept cookies if banner appears
        """
        try:
            accept_cookies_button = self.driver.find_element(By.XPATH,
                                                             "//a[@href='#accept' and contains(@class, 'wt-ecl-button')]")
            accept_cookies_button.click()  # Click on "Accept all cookies"
            #time.sleep(2)  # Wait a moment to make sure the banner closes
        except Exception as e:
            print(f"\nCookie banner not found or already accepted: {e}")

    def get_items(self, soup):
        """
        Get items found from the page
        :return: items
        """
        # Get number of calls
        # inside div with class="row eui-u-mb-s eui-u-flex-align-items-center ng-star-inserted"
        div_num_elements = self.get_div_from_class(soup,
                                                   "row eui-u-mb-s eui-u-flex-align-items-center ng-star-inserted")
        # inside this div there is another div with class="col-sm-6 col-lg-7 col-xl-8"
        div_num_elements = self.get_div_from_class(div_num_elements, "col-sm-6 col-lg-7 col-xl-8")
        # inside this div there is a strong with the number of calls
        return div_num_elements.find("strong").text

    def get_current_page(self, soup):
        """
        Get current page from the page
        :return: current_page
        """
        # search for div with class="eui-paginator__page-range ng-star-inserted"
        div_num_pages = soup.find("div", class_="eui-paginator__page-range ng-star-inserted")
        # inside this div there is a text that says "Showing 1-50 of 342" where 342 is the total number of calls
        # I want to know what page we are on, that is, if we show 1-50 we are on page 1
        text_num_pages = div_num_pages.text.strip().split(" ")[1]
        page = str(text_num_pages).split("–")[0]
        if int(page) > 1:
            page = int(page) // self.num_results_per_page + 1

        return page

    @staticmethod
    def get_num_elements(source, element):
        """
        Get number of elements "sedia-result-card-calls-for-proposals" in the page
        :param source: page source
        :param element: element (Ex. sedia-result-card-calls-for-proposals)
        :return: number of elements
        """
        return source.count(element)

    @staticmethod
    def get_elements(soup, element):
        """
        Get elements from the page
        :param soup: soup
        :param element: element (Ex. sedia-result-card-calls-for-proposals)
        :return: elements
        """
        return soup.find_all(element)

    def get_calls(self, soup):
        """
        Get calls from the page
        :param soup: soup
        :return: calls
        """
        # calls are inside elements called "sedia-result-card-calls-for-proposals"
        return self.get_elements(soup, "sedia-result-card-calls-for-proposals")

    @staticmethod
    def get_call_text(call):
        """
        Get call text from the page
        :param call: call
        :return: call_text
        """
        # Extract text from call
        call_pretty = call.prettify()  # Pretty print
        text_maker = html2text.HTML2Text()  # Create html2text object
        text_maker.ignore_links = False  # Ignore links
        text_maker.bypass_tables = False  # Can disable tables
        call_text = text_maker.handle(call_pretty)  # Convert html to text

        return call_text

    def get_call_fields(self, call):
        """
        Get fields from call
        :param call: call
        :return: fields
        """
        # Detect fields from call
        # Get element "eui-card-header"
        header = call.find("eui-card-header")
        header_title = header.find("eui-card-header-title")
        # get a inside header_title
        a_header_title = header_title.find("a")
        # get title
        title = a_header_title.text
        # get href
        href = a_header_title["href"]
        # there are 2 elements "sedia-result-card-type" inside header
        # get first element
        card_contents = header.find_all("sedia-result-card-type")
        # get first element
        first_card_content = card_contents[0]
        # get elements span inside (there are 3)
        spans = first_card_content.find_all("span")
        # get first span text = call_code
        call_code = spans[0].text
        # get third span text = call_type
        call_type = spans[2].text
        # get second card content
        second_card_content = card_contents[1]
        # there are 2 elements strong inside second_card_content
        # get first strong element text = opening_date
        elements_strong = second_card_content.find_all("strong")
        opening_date = elements_strong[0].text
        # get second strong element text = next_deadline
        next_deadline = ""
        if len(elements_strong) > 1:
            next_deadline = elements_strong[1].text
        # also there are 3 span elements inside second_card_content
        elements_span = second_card_content.find_all("span")
        # get third span element text = deadline_model
        deadline_model = ""
        if len(elements_span) > 2:
            deadline_model = elements_span[2].text
        # get status
        right_content = call.find("eui-card-header-right-content")
        # get spans inside right_content
        spans = right_content.find_all("span")
        # get status
        status = spans[1].text
        # get programme and type of action inside element eui-card-content
        card_content = call.find("eui-card-content")
        # get elements strong
        elements_strong = card_content.find_all("strong")
        # get programme, first strong element text
        programme = elements_strong[0].text
        # get type of action, second strong element text
        type_of_action = elements_strong[1].text

        fields = {
            "call_code": call_code,
            "call_title": title,
            "call_href": self.global_url + href,
            "call_type": call_type,
            "opening_date": opening_date,
            "next_deadline": next_deadline,
            "deadline_model": deadline_model,
            "status": status,
            "programme": programme,
            "type_of_action": type_of_action,
            "budget_total": 0,
            "currency": self.currency,
            "location": self.location,
        }

        return fields

    def get_call_fields_extended(self, call):
        """
        Get fields from call
        :param call: call
        :return: fields
        """
        call_code = call["call_code"]
        call_title = call["call_title"]
        call_href = call["call_href"]
        # first get page source
        self.get_page_source(call_href)
        # get soup
        soup = self.get_soup()
        # get div with class="col-md-9 col-xxl-10"
        div_extended_info = soup.find("div", class_="col-md-9 col-xxl-10")
        fields_extended = {
            "call_code": call_code,
            "call_title": call_title,
            "topic_description": "",
            "topic_destination": "",
            "topic_conditions_and_documents": "",
            "budget_overview": "",
            "partner_search_announcements": "",
            "start_submission": "",
            "get_support": "",
            "extra_information": "",
            "budget_total": 0,
            "currency": self.currency,
            "budget_topic": "",
            "budget_amount": "",
            "budget_stages": "",
            "budget_opening_date": "",
            "budget_deadline": "",
            "budget_contributions": "",
            "budget_indicative_number_of_grants": "",
        }
        #budget = [{"budget_topic": "", "budget_amount": "", "budget_total": ""}]
        divs_extended_info = []
        links = []
        if div_extended_info:
            # get all divs inside div_extended_info with class="eui-u-mb-l sedia-base" or class="eui-u-mb-l sedia-base ng-star-inserted"
            divs_extended_info = div_extended_info.find_all("div", class_="eui-u-mb-l sedia-base")
            divs_extended_info += div_extended_info.find_all("div", class_="eui-u-mb-l sedia-base ng-star-inserted")

        if len(divs_extended_info) == 0:  # no eui-u-mb-l sedia-base found
            if div_extended_info:
                # get text from div_extended_info
                text = div_extended_info.prettify()
            else:
                # No extended info found
                # get all soup text
                text = soup.get_text()
            text_maker = html2text.HTML2Text()
            text_maker.ignore_links = False  # Ignore links if you don't need them
            text_maker.bypass_tables = False  # You can disable if you need tables in plain text
            plain_text = text_maker.handle(text)
            fields_extended["extra_information"] = plain_text

        else:
            # there are divs with class="eui-u-mb-l sedia-base"
            for div in divs_extended_info:
                # get eui-card-header-title
                card_header_title = div.find("eui-card-header-title")
                # get title
                title = card_header_title.text
                # get eui-card-content
                card_content = div.find("eui-card-content")
                # get budget overview
                if title == "Budget overview":
                    budget_total, budget = self.get_budget_total(card_content)
                    fields_extended["budget_total"] = budget_total
                    # update fields_extended with budget
                    fields_extended.update(budget)

                # get links in card_content
                # get all a elements
                a_elements = card_content.find_all("a")
                for a in a_elements:
                    if not a.has_attr("href"):
                        continue
                    # get href
                    file_url = a["href"]
                    # get text
                    file_title = a.text
                    # save link, only if href ends with .pdf
                    if file_url.endswith(".pdf"):
                        # add to links list
                        links.append({"call_code": call_code, "call_title": call_title, "file_url": file_url,
                                      "file_title": file_title, "file_text": "", "file_summary": ""})

                # get text
                text = card_content.prettify()
                text_maker = html2text.HTML2Text()
                text_maker.ignore_links = False  # Ignorar enlaces si no los necesitas
                text_maker.bypass_tables = False  # Puedes desactivar si necesitas tablas en texto plano
                plain_text = text_maker.handle(text)
                # save plain_text into fields_extended
                title = title.replace("&", "_and_").lower().replace(" ", "_")  # Topic Q&As -> topic_q_and_as
                fields_extended[title] = plain_text

                # check if title not in fields_extended, then saved into extra information
                if title not in fields_extended:
                    fields_extended["extra_information"] += plain_text + "\n\n"

        return fields_extended, links

    @staticmethod
    def get_urls_from_text(text):
        """
        Get urls from text
        :param text: text
        :return: urls
        """
        urls = []
        # get all urls from text
        for url in text.split():
            if url.startswith("http"):
                urls.append(url)
        return urls

    @staticmethod
    def get_budget_total(card_content):
        """
        Get budget overview
        :param card_content:
        :return: list with topic & budget overview
        """

        # Encontrar todas las filas de la tabla
        # select table with class="eui-table eui-table--responsive"
        table = card_content.find("table", class_="eui-table eui-table--responsive")
        # select tbody
        tbody = table.find("tbody")
        # select all tr
        rows = tbody.find_all("tr")
        # rows = card_content.select('table tbody tr')

        # Inicializar el total del presupuesto
        budget_total = 0
        budget = {
            "budget_topic": "",
            "budget_amount": "",
            "budget_stages": "",
            "budget_opening_date": "",
            "budget_deadline": "",
            "budget_contributions": "",
            "budget_indicative_number_of_grants": "",
        }
        # Iterar sobre cada fila y extraer el valor de la segunda columna
        for row in rows:
            cols = row.find_all('td')
            if len(cols) < 7:
                continue

            # Encontrar la primera columna en la fila
            budget["budget_topic"] += cols[0].get_text(strip=True) + "###"
            budget_cell = cols[1].get_text(strip=True)
            budget["budget_amount"] += budget_cell + "###"
            budget["budget_stages"] += cols[2].get_text(strip=True) + "###"
            budget["budget_opening_date"] += cols[3].get_text(strip=True) + "###"
            # check multiple deadlines
            # if cols[4] has multiple divs, then split it
            if cols[4].find_all("div"):
                for div in cols[4].find_all("div"):
                    budget["budget_deadline"] += div.get_text(strip=True) + ", "
                budget["budget_deadline"] = budget["budget_deadline"][:-2] + "###"
            else:
                budget["budget_deadline"] += cols[4].get_text(strip=True) + "###"
            if cols[5] == ' <td><div class="eui-u-text-wrap"></div></td>':
                budget["budget_contributions"] += " ###"
            else:
                budget["budget_contributions"] += cols[5].get_text() + " ###"
            if cols[6] == ' <td><div class="eui-u-text-wrap"></div></td>':
                budget["budget_indicative_number_of_grants"] += " ###"
            else:
                budget["budget_indicative_number_of_grants"] += cols[6].get_text() + " ###"

            if budget_cell:
                # extract number from budget_cell
                budget_text = budget_cell.replace(' ', '')
                try:
                    # Sum the budget
                    budget_total += float(budget_text)
                except ValueError:
                    # Number is not valid
                    print(f"Not valid value: {budget_text}")

            # check multiple lines in first column
            # Get text lines
            text_lines = cols[0].find('div').get_text(separator='\n').split('\n')
            # case unique rows and multiple lines
            if len(rows) == 1 and len(text_lines) > 1:
                budget = {
                    "budget_topic": "",
                    "budget_amount": "",
                    "budget_stages": "",
                    "budget_opening_date": "",
                    "budget_deadline": "",
                    "budget_contributions": "",
                    "budget_indicative_number_of_grants": "",
                }
                for col in text_lines:
                    budget["budget_topic"] += col + "###"
                    budget["budget_amount"] += budget_cell + "###"
                    budget["budget_stages"] += cols[2].get_text(strip=True) + "###"
                    budget["budget_opening_date"] += cols[3].get_text(strip=True) + "###"
                    budget["budget_deadline"] += cols[4].get_text(strip=True) + "###"
                    if cols[5] == ' <td><div class="eui-u-text-wrap"></div></td>':
                        budget["budget_contributions"] += " ###"
                    else:
                        budget["budget_contributions"] += cols[5].get_text() + " ###"
                    if cols[6] == ' <td><div class="eui-u-text-wrap"></div></td>':
                        budget["budget_indicative_number_of_grants"] += " ###"
                    else:
                        budget["budget_indicative_number_of_grants"] += cols[6].get_text() + " ###"
        # strip last "###"
        for key in budget:
            budget[key] = budget[key].rstrip("###")

        return budget_total, budget

    def go_next_page(self):
        """
        Go to next page
        """
        try:
            # click on next page button
            next_page_button = self.driver.find_element(By.XPATH, "//eui-icon-svg[@icon='eui-caret-right']")
            next_page_button.click()
            # Wait time rand to load page
            time.sleep(randrange(2, 5))
        except Exception as e:
            print(f"Error clicking on next page: {e}")

    def go_previous_page(self):
        """
        Go to previous page
        """
        # click on previous page button
        previous_page_button = self.driver.find_element(By.XPATH, "//eui-icon-svg[@icon='eui-caret-left']")
        previous_page_button.click()
        # Wait time rand to load page
        time.sleep(randrange(2, 5))
