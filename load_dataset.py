import os
import requests

# Target URL of the raw CSV file
csv_url = "https://huggingface.co/datasets/ItshMoh/kubernetes_qa_pairs/resolve/main/kubernetes_qa.csv"

# Directory to save the dataset
save_dir = os.path.join(os.getcwd(), "dataset")
os.makedirs(save_dir, exist_ok=True)

# File path where CSV will be saved
csv_path = os.path.join(save_dir, "kubernetes_qa_pairs.csv")

# Download and save the file
response = requests.get(csv_url)
if response.status_code == 200:
    with open(csv_path, "wb") as f:
        f.write(response.content)
    print(f"Downloaded and saved to {csv_path}")
else:
    print(f"Failed to download. Status code: {response.status_code}")
