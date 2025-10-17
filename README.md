🧠 Project Overview

This app takes a resume PDF as input, extracts all key information — such as personal details, education, work experience, skills, and certifications — and exports it in a machine-readable JSON format.

It’s ideal for:
Automating candidate parsing for HR systems
Preparing AI datasets for LLM fine-tuning
Building resume search/ranking engines
GenAI assistants that need structured user data
The app includes built-in OCR fallback for scanned PDFs and supports both Poppler and PyMuPDF extraction modes.

⚙️ Features
✅ Text-based extraction via pdfplumber
✅ OCR fallback using pytesseract and pdf2image or PyMuPDF
✅ Streamlit UI for upload, conversion, and download
✅ Downloadable JSON output
✅ Diagnostics panel for debugging missing dependencies
✅ Cross-platform (Mac, Windows, Linux)

🧩 Tech Stack
Component	Library/Tool	Description
Web App	Streamlit
	Interactive UI for upload and JSON generation
PDF Parsing	pdfplumber
	Extracts text from PDF
OCR Fallback	pytesseract
, PyMuPDF
	Extracts text from image-based PDFs
JSON Export	Python JSON library	Exports structured data
Deployment	Localhost / Streamlit Cloud	Runs anywhere Streamlit runs

🖥️ Installation
1️⃣ Clone the repository
git clone https://github.com/yourusername/resume-pdf-to-json.git
cd resume-pdf-to-json

2️⃣ Create and activate a virtual environment
python -m venv .venv
source .venv/bin/activate    # Windows: .venv\Scripts\activate

3️⃣ Install dependencies
pip install -r requirements.txt

4️⃣ Install system dependencies (optional for OCR)
macOS (Homebrew):
brew install tesseract poppler


Windows (manual installs):
Tesseract OCR
Poppler for Windows

🚀 Run the App
streamlit run app.py

Then open your browser at http://localhost:8501

🧠 Theory Behind the Project
Modern resume parsing requires semantic understanding of text structures like job roles, dates, and skills.
This app uses a rule-based + OCR hybrid approach:

Text Extraction Phase
Attempts to read text directly via pdfplumber.
If unsuccessful (e.g., scanned image PDFs), switches to OCR-based extraction.
Parsing Phase
Uses regex-based segmentation to identify sections (Experience, Education, Skills).
Extracts contact info with named pattern recognition.
Identifies bullet points, date ranges, and key fields to produce structured data.
JSON Conversion Phase
Aggregates parsed data into a normalized JSON schema suitable for database storage or ML ingestion.
This approach combines deterministic parsing with OCR flexibility—making it accurate and resilient across varied resume formats.

🧰 Possible Extensions
Integrate with OpenAI embeddings for semantic matching
Add NER models (spaCy) to improve company/role detection
Support multi-resume batch parsing
Build a FastAPI backend for large-scale deployment
Store parsed resumes in a Vector DB (e.g., Pinecone, FAISS) for similarity search

👤 Author
Bhavesh Kalluru
📧 kallurubhavesh341@gmail.com

🔗 LinkedIn
 | GitHub
