# AI Photomosaik Generator (16K Resolution)

A high-performance photomosaic generator powered by **OpenAI CLIP** and **ResNet** architecture. 
This tool uses a hybrid analysis engine (Semantic Understanding + Color Matching) to create massive, highly detailed mosaics (up to 16K resolution) from a database of 300,000+ images.

![Example Mosaic](assets/preview.jpg) 
*(Tutaj warto wstawić ten screen ze zbliżeniem na kapelusz/skały, który mi wysłałeś, pokazuje detal)*

## 🚀 Features

* **Hybrid Matching Engine:** Balances Semantic Similarity (CLIP ViT-B/32) and Color Accuracy (RGB) for artistic yet accurate results.
* **Big Data Ready:** Efficiently handles datasets of 300,000+ tiles using batched processing and GPU acceleration.
* **Spatial Awareness:** Implements a "strict anti-repetition" algorithm that checks 2D neighbors to prevent tiling artifacts.
* **Performance:** Capable of processing 100M+ matrix comparisons in minutes using CUDA optimization.
* **Batch Processing:** Automatically processes all images in the `input` directory.
* **Auto-Downloader:** Includes an async downloader (`fast_downloader.py`) that fetches Public Domain art (Chicago Art Institute) and Creative Commons images to build the dataset.

## 🛠️ Installation

1.  Clone the repository:
    ```bash
    git clone [https://github.com/twoj-nick/ai-photomosaik.git](https://github.com/twoj-nick/ai-photomosaik.git)
    cd ai-photomosaik
    ```

2.  Install dependencies (GPU support recommended):
    ```bash
    pip install -r requirements.txt
    ```
    *Note: For CUDA support, ensure you install the PyTorch version matching your hardware.*

3.  Create `.env` file:
    ```ini
    NUM_TILES=300000
    TILE_SIZE=75
    TARGET_SHORT_SIDE=18000
    GHOSTING_OPACITY=0.25
    USE_CUDA=True
    ```

## 💻 Usage

1.  **Build the Dataset:**
    Run the downloader to fetch 300k images (mix of Museum Art & Stock Photos).
    ```bash
    python -m src.fast_downloader
    ```

2.  **Add Input Images:**
    Place your `.jpg` or `.png` images into the `input/` folder.

3.  **Generate:**
    ```bash
    python -m src.main
    ```
    *First run will take ~1.5h to index the database (create vector embeddings). Subsequent runs take minutes.*

## 🧠 How it works

The core engine calculates a **Similarity Score** for every tile candidate:
$$ Score = (w_{clip} \cdot D_{semantic}) + (w_{rgb} \cdot D_{color}) $$

It creates a 512-dimensional vector space where the input image sectors and tile database are compared. The `MosaicEngine` ensures that no identical tiles touch each other to maintain organic texture.

## 📜 License

This project is licensed under the MIT License.