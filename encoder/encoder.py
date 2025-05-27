from sentence_transformers import SentenceTransformer

# Load model once at the start of your application
model = SentenceTransformer('all-MiniLM-L6-v2')

def create_embedding(text):
    embedding = model.encode(text)
    return embedding.tolist() 