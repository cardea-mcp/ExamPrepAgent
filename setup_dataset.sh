#!/bin/bash

echo "🚀 Starting dataset setup process..."

# Step 1: Download dataset from Hugging Face
echo "📥 Step 1: Downloading dataset from Hugging Face..."
python3 load_dataset.py

if [ $? -ne 0 ]; then
    echo "❌ Failed to download dataset. Exiting..."
    exit 1
fi

echo "✅ Dataset downloaded successfully!"

# Step 2: Navigate to dataset folder and load data to TiDB
echo "📊 Step 2: Loading data into TiDB..."
cd dataset

python3 csv_loader.py

if [ $? -ne 0 ]; then
    echo "❌ Failed to load data into TiDB. Exiting..."
    exit 1
fi

echo "✅ Data successfully loaded into TiDB database!"
echo "🎉 Dataset setup completed!"

# Return to original directory
cd ..

echo "✨ All done! Your TiDB database is ready to use."