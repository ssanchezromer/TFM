from qdrant_client import QdrantClient, models
from qdrant_client.models import PointStruct
from langchain.text_splitter import RecursiveCharacterTextSplitter
import uuid
import requests


class EmbeddingGenerator:
    def __init__(self, url="http://localhost:11434"):
        self.url = url

    def get_embedding(self, text):
        try:
            # With request method
            payload = {"model": "nomic-embed-text:latest", "prompt": text}
            response = requests.post(f"{self.url}/api/embeddings", json=payload)

            if response.status_code == 200:
                data = response.json()

                if 'embedding' in data:
                    return data['embedding']
                else:
                    print(f"Respuesta incorrecta del servidor: {data}")

            else:
                print(f"Error HTTP al obtener el embedding: {response.status_code}")
        except requests.RequestException as e:
            print(f"Error al conectar con el servidor Ollama: {str(e)}")

            # With Ollama to generate embeddings
        #     response = ollama.embeddings(model="nomic-embed-text:latest", prompt=text)
        #     embedding = response.get("embedding", [])
        #
        #     return embedding
        #
        #
        #
        # except Exception as e:
        #     print(f"Error obteniendo embedding: {e}")
        #     return []

    def encode(self, text):
        return self.get_embedding(text)


class QdrantVectorial:
    def __init__(self, host="localhost", port=6333, collection_name="pdf_collection"):
        self.error = False
        self.error_message = ""
        try:
            self.client = QdrantClient(host=host, port=port)
            print(f"Connected to Qdrant at http://{host}:{port}")
            # define encoder model (ollama local server)
            self.encoder = EmbeddingGenerator(url="http://"+host+":11434")
            print(f"Connected to Ollama at http://{host}:11434")
            self.collection_name = collection_name
            # create collection if it doesn't exist
            if collection_name not in self.list_collections():
                if not self.create_collection(collection_name):
                    self.error = True
                    self.error_message = f"Error creating collection '{collection_name}'."
            print(f"Collection '{collection_name}' initialized successfully.")
        except Exception as e:
            self.error = True
            self.error_message = f"Error initializing Qdrant client: {e}"

    def list_collections(self):
        """List all existing collections in Qdrant."""
        try:
            # Get the list of collections
            response = self.client.get_collections()

            # Extract the names of the collections
            return [collection.name for collection in response.collections]
        except AttributeError:
            raise ValueError("Unexpected response format from Qdrant API.")
        except Exception as e:
            # Error fetching collections
            raise RuntimeError(f"Failed to list collections: {e}")

    def create_collection(self, collection_name: str):
        """Create a new collection in Qdrant."""
        try:
            self.client.create_collection(
                collection_name=collection_name,
                vectors_config=models.VectorParams(size=768, distance=models.Distance.COSINE)
            )
            print(f"Collection '{collection_name}' created successfully.")
            return True
        except Exception as e:
            print(f"Error creating collection '{collection_name}': {e}")
            return False

    def list_collection_data(self, collection_name: str, limit: int = 10):
        """
        List data from a specific Qdrant collection.

        Args:
            collection_name (str): Name of the collection to query.
            limit (int): Maximum number of items to retrieve (default: 10).

        Returns:
            list: A list of dictionaries containing the IDs, vectors, and metadata of the points in the collection.
        """
        try:
            response = self.client.scroll(
                collection_name=collection_name,
                limit=limit
            )
            points = [
                {
                    "id": point.id,
                    "vector": point.vector,
                    "metadata": point.payload,
                }
                for point in response[0]  # Accessing the list of points
            ]
            return points
        except Exception as e:
            print(f"Error fetching data from collection '{collection_name}': {e}")
            return []

    @staticmethod
    def split_text_into_chunks(text, chunk_size=500, chunk_overlap=50):
        """
        Divide un texto en fragmentos de tamaño definido para almacenar en Qdrant.
        """
        splitter = RecursiveCharacterTextSplitter(chunk_size=chunk_size, chunk_overlap=chunk_overlap)
        chunks = splitter.split_text(text)
        return chunks

    @staticmethod
    def generate_unique_id():
        return str(uuid.uuid4())

    def insert_full_text(self, file_id: str, file_url: str, docs: list):
        """
        Inserts the full text of a document (e.g., a PDF) into a Qdrant collection.

        Args:
            file_id (str): Unique identifier for the file (used as the point ID).
            file_url (str): URL of the file for metadata.
            docs (list): List of document objects (e.g., PDF pages) for metadata.

        Returns:
            bool: True if the insertion was successful, False otherwise.
        """
        try:

            # Generate embeddings for each chunk
            embeddings = [self.encoder.get_embedding(text=doc.page_content) for doc in docs]

            # Prepare points for insertion into Qdrant
            points = [
                PointStruct(
                    id=int(f"{file_id:04}{i + 1:04}"),  # file_id (4 digits) + page (3 digits),
                    vector=embedding,
                    payload={
                        "content": doc.page_content,
                        "metadata": {
                            "file_id": file_id,
                            "file_url": file_url,
                            "page": i + 1,  # Número de fragmento o página
                       }
                    }
                )
                for i, (doc, embedding) in enumerate(zip(docs, embeddings))
            ]

            # Insert points into the collection
            self.client.upsert(collection_name=self.collection_name, points=points)
            print(f"Inserted {len(points)} chunks for file_id '{file_id}' into collection '{self.collection_name}'.")
            return True
        except Exception as e:
            print(f"Error inserting text into collection '{self.collection_name}': {e}")
            return False

    def delete_data(self, point_ids: list[str] = None, filter_conditions: dict = None):
        """
        Deletes data from a Qdrant collection, either by point IDs or filter conditions.

        Args:
            point_ids (list[str], optional): List of point IDs to delete. Defaults to None.
            filter_conditions (dict, optional): Filter conditions to delete specific data. Defaults to None.

        Returns:
            bool: True if the deletion was successful, False otherwise.
        """
        try:
            if point_ids:
                # Delete by point IDs
                response = self.client.delete(
                    collection_name=self.collection_name,
                    points_selector={"points": point_ids}
                )
                print(f"Deleted {len(point_ids)} points from collection '{self.collection_name}'.")
            elif filter_conditions:
                # Delete by filter conditions
                response = self.client.delete(
                    collection_name=self.collection_name,
                    points_selector={"filter": filter_conditions}
                )
                print(
                    f"Deleted points from collection '{self.collection_name}'"
                    f" based on filter conditions: {filter_conditions}."
                )
            else:
                raise ValueError("Either point_ids or filter_conditions must be provided.")

            return True
        except Exception as e:
            print(f"Error deleting data from collection '{self.collection_name}': {e}")
            return False

    def point_exists(self, point_id: int) -> bool:
        """
        Check if a point with the given ID already exists in the collection.

        Args:
            point_id (int): ID of the point to check.

        Returns:
            bool: True if the point exists, False otherwise.
        """
        try:
            response = self.client.retrieve(
                collection_name=self.collection_name,
                ids=[point_id]
            )
            return len(response) > 0
        except Exception as e:
            print(f"Error checking point existence: {e}")
            return False

    def get_points(self, question: str, file_ids: list, limit: int = 10):
        """
        Get points from a Qdrant collection based on filter conditions.

        Args:
            question (str): Question to search for
            file_ids (list): List of field IDs to filter
            limit (int): Maximum number of items to retrieve (default: 10).

        Returns:
            list: A list of dictionaries containing the IDs, vectors, and metadata of the points in the collection.
        """
        try:
            query_vector = self.encoder.get_embedding(question)
            query_filter = models.Filter(
                must=[
		        {
                  "key": "metadata.file_id",
                  "match": {
                    "any": file_ids
                    }
                }
    	        ])

            # Perform the search
            points = self.client.search(
                collection_name=self.collection_name,
                query_vector=query_vector,
                query_filter=query_filter,
                limit=limit
            )

            return points
        except Exception as e:
            print(f"Error fetching data from collection '{self.collection_name}': {e}")
            return []

# Ejecución de prueba
# generator = EmbeddingGenerator()
# embedding = generator.get_embedding('Prueba de texto')