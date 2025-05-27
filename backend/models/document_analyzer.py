import fitz  # PyMuPDF
from transformers import pipeline
from typing import Dict
from supabase import create_client
import tempfile
import os
from config.settings import settings

supabase = create_client(settings.SUPABASE_URL, settings.SUPABASE_KEY)

# DocumentAnalyzer class for extracting patient information from PDF documents using Hugging Face's Transformers library.
class DocumentAnalyzer:
    # This class uses a pre-trained question-answering model to extract specific patient information from PDF documents.
    def __init__(self):
        self.qa_pipeline = pipeline("question-answering", model="deepset/roberta-base-squad2")

    # Method to extract text from a PDF file using PyMuPDF.
    def extract_text_from_pdf(self, pdf_path: str) -> str:
        with fitz.open(pdf_path) as doc:
            return "\n".join([page.get_text() for page in doc])

    # Method to extract specific patient information from the provided text.
    def analyze_document(self, text: str) -> dict:
        questions = [
            "What is the patient's name?",
            "What is the patient's age?",
            "What are the symptoms?",
            "What is the diagnosis?",
            "What medications are prescribed?"
        ]
        return {q: self.qa_pipeline(question=q, context=text)["answer"] for q in questions}
    
    def download_pdf(self, bucket_name: str, supabase_path: str) -> str:
        """
        Downloads a PDF file from Supabase storage to a temporary file.
        :param bucket_name: Name of the Supabase storage bucket.
        :param bucket_path: Path to the PDF file in the bucket.
        :return: Path to the downloaded temporary file.
        """

        response = supabase.storage.from_(bucket_name).download(supabase_path)
        if not response:
            raise FileNotFoundError(f"Failed to download file from Supabase: {supabase_path}")

        temp_file = tempfile.NamedTemporaryFile(delete=False, suffix=".pdf")
        temp_file.write(response)
        temp_file.flush()
        return temp_file.name  # Return local file path
    