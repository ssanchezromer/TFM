import math
from random import randrange
from Crawler import Crawler
from selenium.webdriver.common.by import By
import requests
import time
from dotenv import load_dotenv
import os

load_dotenv()


class Fandit(Crawler):
    def __init__(self):
        super().__init__("fandit")
        # options by default
        self.page = 1
        self.page_all = 0
        self.is_open = 'true'
        self.num_results_per_page = 20
        self.search_tab = 1
        # get first page
        self.url = self.getUrl()
        # login utl
        self.url_login = 'https://api.fandit.es/api/v1/dj-rest-auth/login/'
        # user fandit
        self.username = os.getenv("FANDIT_USERNAME")
        self.password = os.getenv("FANDIT_PASSWORD")
        # auth token
        self.auth_token = None
        # number max of attempts to login
        self.try_login_number = 5
        self.data = []

    def getUrl(self):
        # URL to access the Fandit API (get json data)
        self.url = 'https://api.fandit.es/api/v1/fund-list?page=' + str(
            self.page) + '&requestData=%7B%22format%22:%22json%22,%22page%22:' + str(
            self.page) + ',%22applicants%22:%5B%5D,%22provinces%22:%5B%5D,%22communities%22:%5B%5D,%22action_items%22:%5B%5D,%22origins%22:%5B%5D,%22activities%22:%5B%5D,%22region_types%22:%5B%5D,%22types%22:%5B%5D,%22max_budget%22:null,%22max_total_amount%22:null,%22min_total_amount%22:null,%22search_by_text%22:%22%22,%22office%22:%22%22,%22bdns%22:null,%22is_open%22:' + self.is_open + ',%22date_range%22:%22%22,%22start_date%22:null,%22end_date%22:null,%22reviewed%22:null,%22final_period_end_date%22:null,%22final_period_start_date%22:null,%22search_tab%22:' + str(
            self.search_tab) + '%7D'
        return self.url

    def login(self):
        # Data to authenticate
        data = {
            'email': self.username,
            'password': self.password
        }
        # Request headers
        headers = {
            'accept': 'application/json, text/plain, */*',
            'accept-encoding': 'gzip, deflate, br, zstd',
            'accept-language': 'ca-ES,ca;q=0.9,es;q=0.8,en;q=0.7',
            'content-type': 'application/json',
            'origin': 'https://app.fandit.es',
            'referer': 'https://app.fandit.es/',
            'sec-ch-ua': '"Google Chrome";v="129", "Not=A?Brand";v="8", "Chromium";v="129"',
            'sec-ch-ua-mobile': '?0',
            'sec-ch-ua-platform': '"Windows"',
            'user-agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/129.0.0.0 Safari/537.36'
        }
        # Make the POST request
        response = requests.post(self.url_login, json=data, headers=headers)

        if response.status_code == 200:
            self.auth_token = response.json().get('key')
            print(f'Authentication token: {self.auth_token}')
        else:
            print(f'Error logging in: {response.status_code}')
            print(response.text)
            self.try_login_number -= 1
            if self.try_login_number > 0:
                print(f"Trying to login again. {self.try_login_number} attempts left.")
                time.sleep(5)
                self.login()
            else:
                print("Login failed.")
                return False

        return True

    def getData(self, page=1, is_open='true', search_tab=1):
        # get Data for one page
        if self.auth_token:
            self.page = page
            self.is_open = is_open
            self.search_tab = search_tab
            self.url = self.getUrl()
            path = self.url.replace('https://api.fandit.es/', '')
            results = []
            try:
                headers_options = {
                    'authority': 'api.fandit.es',
                    'method': 'OPTIONS',
                    'path': path,
                    'scheme': 'https',
                    'Accept': '*/*',
                    'Accept-Encoding': 'gzip, deflate, br, zstd',
                    'Accept-Language': 'ca-ES,ca;q=0.9,es;q=0.8,en;q=0.7',
                    'Access-Control-Request-Headers': 'authorization,content-type',
                    'Access-Control-Request-Method': 'GET',
                    'Origin': 'https://fandit.es',
                    'Priority': 'u=1, i',
                    'Referer': 'https://fandit.es',
                    'Sec-Fetch-Dest': 'empty',
                    'Sec-Fetch-Mode': 'cors',
                    'Sec-Fetch-Site': 'same-site',
                    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/129.0.0.0 Safari/537.36',
                }
                headers_get = {
                    'authority': 'api.fandit.es',
                    'method': 'GET',
                    'path': path,
                    'scheme': 'https',
                    'Accept': 'application/json, text/plain, */*',
                    'Accept-Encoding': 'gzip, deflate, br, zstd',
                    'Accept-Language': 'ca-ES,ca;q=0.9,es;q=0.8,en;q=0.7',
                    'Authorization': 'Token ' + self.auth_token,
                    'Content-type': 'application/json',
                    'Origin': 'https://fandit.es',
                    'Priority': 'u=1, i',
                    'Referer': 'https://fandit.es/',
                    'Sec-Ch-Ua': '"Google Chrome";v="129", "Not=A?Brand";v="8", "Chromium";v="129"',
                    'Sec-Ch-Ua-Mobile': '?0',
                    'Sec-Ch-Ua-Platform': '"Windows"',
                    'Sec-Fetch-Dest': 'empty',
                    'Sec-Fetch-Mode': 'cors',
                    'Sec-Fetch-Site': 'same-site',
                    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/129.0.0.0 Safari/537.36'
                }
                response = requests.options(self.url, headers=headers_options)

                # Verificar si la respuesta fue exitosa
                if response.status_code == 200:
                    response = requests.get(self.url, headers=headers_get)
                    # Verificar si la respuesta fue exitosa
                    if response.status_code == 200:
                        # Obtener el contenido de la respuesta
                        content = response.json()
                        if content:
                            count = content.get('count')
                            results = content.get('results')
                            if self.page_all == 0:
                                # only for first page
                                self.page_all = math.ceil(count / self.num_results_per_page)
                            print(f'Número de convocatorias: {count}')
                            print(f'Número de páginas: {self.page_all}')
                            print(f'Página actual: {self.page}')
                            print(f"Resultados: {results}")

                            print(f"Data obtained from page {self.page} of {self.page_all}")

                        # esperar un tiempo aleatorio entre 1 y 3 segundos
                        time.sleep(randrange(2, 3))
                    else:
                        print(f"Error {response.status_code} while obtained data from page {self.page}")
                        print(response.text)

            except Exception as e:
                print(f"Error getting data: {e}")

            return results
        else:
            print("You need to login first.")
            self.login()

    def getDetails(self, id):
        print(f"Getting details for id: {id}")
        urlDetails = 'https://api.fandit.es/api/v1/summaries/' + str(id) + '/'
        print(f"URL Details: {urlDetails}")
        path = urlDetails.replace('https://api.fandit.es', '')
        print(f"Path: {path}")
        details = {}
        try:
            headers_options = {
                'authority': 'api.fandit.es',
                'method': 'OPTIONS',
                'path': path,
                'scheme': 'https',
                'Accept': '*/*',
                'Accept-Encoding': 'gzip, deflate, br, zstd',
                'Accept-Language': 'ca-ES,ca;q=0.9,es;q=0.8,en;q=0.7',
                'Access-Control-Request-Headers': 'authorization,content-type',
                'Access-Control-Request-Method': 'GET',
                'Origin': 'https://fandit.es',
                'Priority': 'u=1, i',
                'Referer': 'https://fandit.es',
                'Sec-Fetch-Dest': 'empty',
                'Sec-Fetch-Mode': 'cors',
                'Sec-Fetch-Site': 'same-site',
                'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/129.0.0.0 Safari/537.36'
            }
            headers_get = {
                'authority': 'api.fandit.es',
                'method': 'GET',
                'path': path,
                'scheme': 'https',
                'Accept': 'application/json, text/plain, */*',
                'Accept-Encoding': 'gzip, deflate, br, zstd',
                'Accept-Language': 'ca-ES,ca;q=0.9,es;q=0.8,en;q=0.7',
                'Authorization': 'Token ' + self.auth_token,
                'Content-type': 'application/json',
                'Origin': 'https://fandit.es',
                'Priority': 'u=1, i',
                'Referer': 'https://fandit.es/',
                'Sec-Ch-Ua': '"Google Chrome";v="129", "Not=A?Brand";v="8", "Chromium";v="129"',
                'Sec-Ch-Ua-Mobile': '?0',
                'Sec-Ch-Ua-Platform': '"Windows"',
                'Sec-Fetch-Dest': 'empty',
                'Sec-Fetch-Mode': 'cors',
                'Sec-Fetch-Site': 'same-site',
                'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/129.0.0.0 Safari/537.36'
            }
            response = requests.options(urlDetails, headers=headers_options)
            if response.status_code == 200:
                response = requests.get(urlDetails, headers=headers_get)
                if response.status_code == 200:
                    content = response.json()
                    if content:
                        details = content
                else:
                    print(f"Error {response.status_code} while obtained details from id {id}")
                    print(response.text)


        except Exception as e:
            print(f"Error getting details: {e}")

        time.sleep(randrange(5, 10))

        return details

    def resultsToData(self, results):
        # transform results to data (add details)
        data = []
        print(f"Getting {len(results)} results")
        for result in results:
            id = result.get('id')
            details = {}
            detailsSearch = 0
            # while details == {} and detailsSearch < 6:
            #     details = self.getDetails(id)
            #     detailsSearch += 1
            data_single = {
                'id': id,
                'total_amount': result.get('total_amount'),  # fondos: 0.0 = Sin datos
                'status': result.get('status'),  # 1 abierta
                'status_text': result.get('status_text'),  # Para saber si esta abierta (fechas)
                'slug': result.get('slug'),  # para saber detalles de la convocatoria
                'request_amount': result.get('request_amount'),  # ayuda máxima a recibir
                'title': result.get('title'),
                'cleaned_title': result.get('cleaned_title'),  # título limpio
                'goal_extra': result.get('goal_extra'),  # descripción de la ayuda, para que es la ayuda
                'entity': result.get('entity'),  # entidad que ofrece la ayuda
                'department': result.get('department'),  # departamento que ofrece la ayuda
                'start_date': result.get('start_date'),  # fecha que empieza ayuda yyyy-mm-dd
                'end_date': result.get('end_date'),  # fecha que acaba ayuda yyyy-mm-dd
                'url': result.get('url'),
                'fund_scope': None,  # ámbito de la ayuda
                'register_date': None,  # fecha de registro
                'pdf_file': None,  # archivo pdf
                'custom_pdf_file': None,  # archivo pdf personalizado
                'applicants': None,  # Quien puede pedir la ayuda
                'terms': None,  # Plazos que existen para la solicitud
                'line': None,  # Líneas de ayuda
                'help_type': None,  # En que consiste la ayuda
                'expenses': None,  # qué gastos o acciones me cubre
                'extra_limit': None,  # límites adicionales
                'info_extra': None,  # información extra (algo más que debes saber...)
                'min_budget': None,  # presupuesto mínimo a financiar
                'keywords': None,  # palabras clave
            }
            if details != {}:
                # add fields from details into data
                data_single.update({
                    'fund_scope': details.get('fund_scope'),  # ámbito de la ayuda
                    'register_date': details.get('register_date'),  # fecha de registro
                    'pdf_file': details.get('pdf_file'),  # archivo pdf
                    'custom_pdf_file': details.get('custom_pdf_file'),  # archivo pdf personalizado
                    'applicants': details.get('applicants'),  # Quien puede pedir la ayuda
                    'terms': details.get('terms'),  # Plazos que existen para la solicitud
                    'line': details.get('line'),  # Líneas de ayuda
                    'help_type': details.get('help_type'),  # En que consiste la ayuda
                    'expenses': details.get('expenses'),  # qué gastos o acciones me cubre
                    'extra_limit': details.get('extra_limit'),  # límites adicionales
                    'info_extra': details.get('info_extra'),  # información extra (algo más que debes saber...)
                    'min_budget': details.get('min_budget'),  # presupuesto mínimo a financiar
                    'keywords': details.get('keywords'),  # palabras clave
                })

            self.data.append(data_single)

