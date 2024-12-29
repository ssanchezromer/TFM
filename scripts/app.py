# Description: Flask API to run endpoints in port 5000
# Author: Sergio Sánchez Romero
# Date: 2024-12-01
import os

from bs4 import BeautifulSoup
from flask import Flask, request, jsonify
from selenium.webdriver import Keys
from selenium.webdriver.common.by import By

from crawler.QdrantVectorial import QdrantVectorial
from langchain_openai import ChatOpenAI
from langchain_core.prompts import PromptTemplate
from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.chrome.options import Options
import requests
from dotenv import load_dotenv

load_dotenv()
app = Flask(__name__)


def get_prompt_template(question):
    return """
    ### Goal:
    This agent is designed to identify if a clear question is present in the user's input or conversation history. If no explicit question is found but the input implies a request, the agent should reformulate it into a well-defined question, **always related to calls, grants, proposals, and funding opportunities**.

    ### Steps:

    1. Analyze the user input and/or the conversation context.
    2. Determine if the input contains a well-defined question related to calls, funding opportunities, eligibility, or grants.
    3. If a question is present, return it as-is.
    4. If no explicit question is found but the input implies a request, reformulate it into a clear and concise question focused on grants, calls, funding, eligibility criteria, etc.

    ### Output format:

    If you can identify a question, provide the following JSON format:
    {
"question": "<question>"
    }

    If no specific question can be identified, respond with:
    {
"question": ""
    }

    ### Important Notes:

    - Reformulate ambiguous or implicit requests into precise questions whenever possible.
    - Always ensure the question is directly related to calls, funding, grants, eligibility criteria, deadlines, or proposals.
    - Avoid fabricating questions if the input lacks meaningful context.
    - Only respond with a valid JSON response.

    ### Example Inputs and Outputs:

    1. Input: "What is the deadline for this call?"
    Output:
    {
"question": "What is the deadline for this call?"
    }

    2. Input: "I need information about the opening date and the budget."
    Output:
    {
"question": "What are the opening date and the budget for this call?"
    }
    3. Input: "Tell me something interesting about this call."
    Output:
    {
"question": "Could you give me some information about the call we are speaking?"
    }
    4. Input: "Tell me a joke!"
    Output:
    {
"question": ""
    }

    Your turn!

    Input: "{""" + question + """}"
    Output:
    """


@app.route('/run-script', methods=['POST'])
def run_script():
    """
    Execute a script
    :param script: script name
    :return: status and message
    """
    # Execute a script
    # Get data from the request (script name of the python file)
    # Returns a json with the result of the script
    data = request.json
    script_name = data.get('script', '')

    try:
        # Execute the script
        exec(open(f"/usr/src/app/{script_name}.py").read())
        return jsonify({"status": "success", "message": f"{script_name} executed successfully"})
    except Exception as e:
        return jsonify({"status": "error", "message": str(e)}), 500

@app.route('/run-script-get', methods=['GET'])
def run_script_get():
    """
    Execute a script in get method is not permitted
    :return: status and message
    """
    # Execute script in get method is not permitted
    return jsonify({"status": "success", "message": "Not permitted"}), 200

@app.route('/get-points', methods=['POST'])
def get_points():
    """
    Get points from Qdrant
    :param question: question
    :param file_ids: file_ids
    :param limit: limit
    :return: response to question
    """
    # Retrieve points from Qdrant
    # Get data from the request (question, field_id, limit)
    # Returns a json with a summary of the content of the points
    # Add the links with the pages
    try:
        data = request.json
        question = data.get('question', '')
        file_ids = data.get('file_ids', '')
        limit = data.get('limit', 4)
        points = []

        # file_ids to list
        file_ids = file_ids.split(",")

        q = QdrantVectorial(host="host.docker.internal", port=6333)
        points = q.get_points(question, file_ids, limit)
        content = ""
        links = ""
        for point in points:
            json_data = point.payload
            score = point.score

            content += f"\n{json_data['content']}"
            page = json_data['metadata']['page']
            file_url = json_data['metadata']['file_url']
            # construct html of links with pages
            links += f"\n<a href='{file_url}'>{file_url}</a> - Page: {page} - Score: {score}"

        if links:
            links = f"<h3>Links with pages</h3>{links}"

        data = {"content": content, "links": links}

        llm = ChatOpenAI(
            temperature=0.1,
            model_name=os.getenv("OLLAMA_MODEL_SUMMARIZE", "llama3.2:1b-instruct-q3_K_L"),
            api_key="ollama",
            base_url=os.getenv("OLLAMA_URL", "http://host.docker.internal:11434/v1"),
        )
        prompt_template = f"Write a summary of the document in base of the following question: {question}."
        prompt_template += """Only include information that is part of the document. 
                                    Do not include your own opinion or analysis.

                                    Document:
                                    "{document}"
                                    Summary:"""

        prompt = PromptTemplate.from_template(prompt_template)

        stuff_chain = prompt | llm
        input_data = {"document": data["content"]}
        summary = stuff_chain.invoke(input_data)
        # get content from summary
        summary = summary.content + "\n" + links

        return jsonify({"status": "success", "output": summary}), 200

    except Exception as e:
        return jsonify({"status": "error", "message": str(e)}), 500


@app.route('/get-points-get', methods=['GET'])
def get_points_get():
    """
    Get points in get method is not permitted
    :return:
    """
    # Get points in get method is not permitted
    return jsonify({"status": "success", "message": "Not permitted"}), 200


@app.route('/check-company-and-location', methods=['POST'])
def check_company_and_location():
    """
    Check if the company type and location are valid
    :param type_company: company type
    :param location: company location
    :return: status and message
    """
    # Check if the company type and location are valid
    # Get data from the request (type_company, location)
    data = request.json
    type_company = data.get('type_company', '')
    location = data.get('location', '')

    try:

        types_companies = ["Large Company", "Midcap", "SME", "Microenterprise", "Self-Employed", "NGO", "Technology Centers", "Universities", "Research Centers", "Others", "Particulars"]
        locations = ["Other", "United States", "Europe", "Spain"]

        # list to lowercases
        types_companies = [x.lower() for x in types_companies]
        locations = [x.lower() for x in locations]

        if type_company.lower() not in types_companies:
            message = "Your company type is not valid. Could you please provide the following information? \n\n\ - **Company Type**: Large Company, Midcap, SME, Microenterprise, Self-Employed, NGO, Technology Centers, Universities, Research Centers, Particular, Other."
            return jsonify({"status": "error", "message": message}), 500
        if location.lower() not in locations:
            message = "Your location is not valid. Could you please provide the following information? \n\n\ - **Location**: United States, Europe, Spain, Other."
            return jsonify({"status": "error", "message": message}), 500

        return jsonify({"status": "success", "message": "Valid company type and scope"}), 200

    except Exception as e:
        return jsonify({"status": "error", "message": str(e)}), 500

@app.route('/get-details-cif', methods=['POST'])
def get_details_cif():
    """
    Get company name from CIF
    :param company_cif: company cif
    :return: company_name
    """
    # Get company_name from CIF
    data = request.json
    company_cif = data.get('company_cif', '')

    try:
        # options --disable-dev-shm-usage --no-sandbox
        options = Options()
        options.add_argument("--headless")
        options.add_argument("--disable-gpu")
        options.add_argument("--no-sandbox")
        options.add_argument("--disable-dev-shm-usage")
        # Change 'path/to/chromedriver' to the path where you downloaded ChromeDriver
        service = Service('/usr/local/bin/chromedriver')
        driver = webdriver.Chrome(service=service, options=options)

        driver.get("https://www.axesor.es/buscador-unificado")

        # Search for the company CIF in the input
        search_box = driver.find_element(By.ID, "nombreSociedad")
        search_box.send_keys(company_cif)  # CIF
        search_box.send_keys(Keys.RETURN)

        # Wait and redirect
        driver.implicitly_wait(10)  # Wait time to load redirects

        # Get the new URL and extract content
        new_url = driver.current_url

        # Extract data from the final page
        html = driver.page_source
        driver.quit()

        # Parse the html
        soup = BeautifulSoup(html, "html.parser")
        # get h3 with class "name"
        company_name = soup.find("h3", class_="name").text

        return jsonify({"status": "success", "company_name": company_name}), 200

    except Exception as e:
        print(f"Ocurrió un error: {e}")
        return jsonify({"status": "error", "message": str(e)}), 500


@app.route('/get-question', methods=['POST'])
def get_question():
    """
    Get a question from Ollama (test)
    :param chatInput: input from the user
    :param sessionId: session id
    :return: response
    """
    try:
        # Obtener los datos de la solicitud
        data = request.json
        chat_input = data.get('chatInput', '')
        session_id = data.get('sessionId', '')

        if not chat_input or not session_id:
            return jsonify({"error": "Faltan datos en la solicitud."}), 400

        # Crear el prompt para Ollama
        prompt = get_prompt_template(question=chat_input)

        # Llamada al modelo Ollama
        ollama_payload = {
            "model": "llama3.2:3b-instruct-q3_K_L",
            "prompt": prompt,
            "temperature": 0,
            "max_tokens": 2000,
            "top_p": 0.9,
            "top_k": 50
        }

        response = requests.post(os.getenv("OLLAMA_URL_GENERATE"), json=ollama_payload)

        if response.status_code != 200:
            return jsonify({"error": "Error al comunicarse con Ollama.", "details": response.text}), 500

        # Registrar la respuesta de Ollama para depuración
        print("Respuesta cruda de Ollama:", response.text)

        # Procesar la respuesta de Ollama
        ollama_response = response.json()
        answer = ollama_response.get('choices', [{}])[0].get('text', '').strip()

        # Construir la respuesta basada en el contenido de la respuesta
        if answer:
            return jsonify({"question": answer})
        else:
            return jsonify({"question": ""})

    except Exception as e:
        return jsonify({"error": "Ocurrió un error procesando la solicitud.", "details": response.text}), 500


if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000)
