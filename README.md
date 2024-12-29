# TFM Máster Universitario en Ciencia de Datos

Development of a GPT capable of synthesizing information from a call for proposals and determining its applicability to a specific company or entity.

## Author

- Sergi Sánchez Romero [@ssanchezromer](https://www.github.com/ssanchezromer)


## Repository content

- **README.md:** This file you are reading right now 
- **LICENSE:** MIT License
- **docker-compose.yml:** Docker compose file
- **docker-compose.override.yml:** Docker compose file for development (delete if GPU is used)
- **DockerFile:** Docker file for the n8n instance
- **n8n_pipe.py:** Python script for the n8n instance
- **.env.example:** Example .env file
- **n8n:** Folder with the n8n workflows
- **scripts:** Folder with the scripts for the project

## Installation (Docker)

### For Nvidia GPU users

```
git clone https://github.com/ssanchezromer/TFM.git
docker compose --profile gpu-nvidia up
```

> [!NOTE]
> If you have not used your Nvidia GPU with Docker before, please follow the
> [Ollama Docker instructions](https://github.com/ollama/ollama/blob/main/docs/docker.md).

### For Mac / Apple Silicon users

If you’re using a Mac with an M1 or newer processor, you can't expose your GPU
to the Docker instance, unfortunately. There are two options in this case:

1. Run the starter kit fully on CPU, like in the section "For everyone else"
   below
2. Run Ollama on your Mac for faster inference, and connect to that from the
   n8n instance

If you want to run Ollama on your mac, check the
[Ollama homepage](https://ollama.com/)
for installation instructions, and run the starter kit as follows:

```
git clone https://github.com/ssanchezromer/TFM.git
docker compose up
```

After you followed the quick start set-up below, change the Ollama credentials
by using `http://host.docker.internal:11434/` as the host.

### For everyone else

```
git clone https://github.com/ssanchezromer/TFM.git
docker compose --profile cpu up
```

## ⚡️ Quick start and usage

![n8n.io - Screenshot](https://raw.githubusercontent.com/n8n-io/self-hosted-ai-starter-kit/main/assets/n8n-demo.gif)

[Original Local AI Starter Kit](https://github.com/n8n-io/self-hosted-ai-starter-kit)

The main component of the self-hosted AI starter kit is a docker compose file
pre-configured with network and disk so there isn’t much else you need to
install. After completing the installation steps above, follow the steps below
to get started.

1. Open <http://localhost:5678/> in your browser to set up n8n. You’ll only
   have to do this once. You are NOT creating an account with n8n in the setup here,
   it is only a local account for your instance!
2. Open the included workflow (SuperAgent):
   <http://localhost:5678/workflow/2P3gbYuGSR0j8GEx>
3. Create credentials for every service:
   
   Ollama URL: http://ollama:11434

   Postgres: use DB, username, and password from .env. Host is postgres

   Qdrant URL: http://qdrant:6333 (API key can be whatever since this is running locally)

4. Select **Test workflow** to start running the workflow.
5. If this is the first time you’re running the workflow, you may need to wait
   until Ollama finishes downloading Llama3.1. You can inspect the docker
   console logs to check on the progress.
6. Make sure to toggle the workflow as active and copy the "Production" webhook URL!
7. Open <http://localhost:3000/> in your browser to set up Open WebUI.
You’ll only have to do this once. You are NOT creating an account with Open WebUI in the 
setup here, it is only a local account for your instance!
8. Go to Workspace -> Functions -> Add Function -> Give name + description then paste in
the code from `n8n_pipe.py`

   The function is also [published here on Open WebUI's site](https://openwebui.com/f/coleam/n8n_pipe/).

9. Click on the gear icon and set the n8n_url to the production URL for the webhook
you copied in a previous step.
10. Toggle the function on and now it will be available in your model dropdown in the top left! 

To open n8n at any time, visit <http://localhost:5678/> in your browser.
To open Open WebUI at any time, visit <http://localhost:3000/>.

With your n8n instance, you’ll have access to over 400 integrations and a
suite of basic and advanced AI nodes such as
[AI Agent](https://docs.n8n.io/integrations/builtin/cluster-nodes/root-nodes/n8n-nodes-langchain.agent/),
[Text classifier](https://docs.n8n.io/integrations/builtin/cluster-nodes/root-nodes/n8n-nodes-langchain.text-classifier/),
and [Information Extractor](https://docs.n8n.io/integrations/builtin/cluster-nodes/root-nodes/n8n-nodes-langchain.information-extractor/)
nodes. To keep everything local, just remember to use the Ollama node for your
language model and Qdrant as your vector store.

> [!NOTE]
> This starter kit is designed to help you get started with self-hosted AI
> workflows. While it’s not fully optimized for production environments, it
> combines robust components that work well together for proof-of-concept
> projects. You can customize it to meet your specific needs

## Upgrading

### For Nvidia GPU users

```
docker compose --profile gpu-nvidia pull
docker compose create && docker compose --profile gpu-nvidia up
```

### For Mac / Apple Silicon users

```
docker compose pull
docker compose create && docker compose up
```

### For everyone else

```
docker compose --profile cpu pull
docker compose create && docker compose --profile cpu up
```


## Installation (Local environment for scraping)

After downloading the code from the **source** folder, go to crawler folder and follow these steps to run the application:  

**1. Create the environment (venv) into crawler folder:**  
```
python -m venv venv  
```
**2. Activate the environment:**  

  Windows:  
```
venv\Scripts\activate  
```
  macOS & Linux:  
```
venv/bin/activate  
```
**3. Install the libraries:**  
```
pip install -r requirements.txt  
```
**4. Start the crawl program:**  
```
python main.py  
```

## Don't start from scratch

If you want to start with previous data into the mysql database, you can use the following commands:
```
docker cp scripts/crawler/data/calls.sql db-1:/tmp/
docker exec db-1 sh -c "mysql -h localhost -u root -ppassword -v < /tmp/calls.sql"
```
Where **'db-1'** is the name of the database container and **'password'** is the password set in the .env file.

We provide also a snapshot of the database with all pdf files (data/pdf_collection-initial.snapshot). 
1. Uncompress the snapshot rar file (pdf_collection-initial.part1.rar & pdf_collection-initial.part2.rar) to get the snapshot file.
2. Upload this snapshot into qdrant database using the collection name: **'pdf_collection'**.

## Licenses

This environment project (originally created by the n8n team, link at the top of the README) is licensed under the Apache License 2.0 - see the
[LICENSE](LICENSE) file for details.

This implementation project is licensed under the Creative Commons Attribution-NonCommercial-ShareAlike 4.0 International License (CC BY-NC-SA) - see the [LICENSE](LICENSE2) file for details.
