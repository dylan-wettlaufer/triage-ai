# services/document_analyzer.py
import os
from pathlib import Path
from typing import List, Dict, Any
import fitz # PyMuPDF for PDF handling
from PIL import Image
import io # To handle image bytes
from transformers import AutoProcessor, AutoModelForDocumentQuestionAnswering
from supabase import create_client
from transformers import AutoModelForImageClassification
import torch
from config.settings import settings
from services.file_manager import file_manager # This handles downloading from Supabase
import pytesseract

pytesseract.pytesseract.tesseract_cmd = r'C:\Program Files\Tesseract-OCR\tesseract.exe'


# Moved Supabase client initialization to a more appropriate place if needed, or ensure it's handled externally.
# For demonstration, I'll keep it outside the class but remind to consider dependency injection.
supabase = create_client(settings.SUPABASE_URL, settings.SUPABASE_KEY) # Uncommented for direct use as per original code

class DocumentAnalyzer:
    def __init__(self):
        self.layoutlmv3_processor = None
        self.layoutlmv3_model = None
        self.device = "cuda" if torch.cuda.is_available() else "cpu"
        if settings.LAYOUTLMV3_MODEL_ID:
            print(f"Loading LayoutLMv3 model from Hugging Face: {settings.LAYOUTLMV3_MODEL_ID}")
            try:
                self.layoutlmv3_processor = AutoProcessor.from_pretrained(
                    settings.LAYOUTLMV3_MODEL_ID,
                    apply_ocr=True # <--- ADD THIS LINE
                )
                self.layoutlmv3_model = AutoModelForDocumentQuestionAnswering.from_pretrained(settings.LAYOUTLMV3_MODEL_ID)
                print(f"Loaded processor type: {type(self.layoutlmv3_processor)}")
                if torch.cuda.is_available():
                    self.layoutlmv3_model.to("cuda")
                print("LayoutLMv3 model loaded successfully.")

            except Exception as e:
                print(f"Error loading LayoutLMv3 model: {e}")
        else:
            print("LAYOUTLMV3_MODEL_ID not set in settings. Document analysis will be skipped.")


    async def analyze_document(self, file_path_in_supabase: str, file_type: str, patient_identifier: str) -> Dict[str, Any]:
        """
        Analyze a document (PDF) to extract patient information using LayoutLMv3.
        :param file_path_in_supabase: The path of the file in Supabase Storage.
        :param file_type: The type of the file (e.g., "pdf").
        :param patient_identifier: The patient identifier to associate with the analysis.
        :return: A dictionary containing the extracted patient information.
        """

        print(f"Starting analysis for file: {file_path_in_supabase}, type: {file_type}, patient: {patient_identifier}")
        analysis_results = {
            "file_path": file_path_in_supabase,
            "patient_identifier": patient_identifier,
            "extracted_data": {}, # This will hold our key-value pairs from forms
            "image_classification_results": {}, # Results from ViT if applicable (not used in this version, but kept for structure)
            "status": "pending",
            "error": None
        }

        local_file_path = None # Initialize local_file_path outside try block

        try:
            # Download the file from Supabase Storage
            local_file_path = await file_manager.download_file_from_supabase(
                supabase_path=file_path_in_supabase,
            )

            if not local_file_path:
                raise FileNotFoundError(f"File {file_path_in_supabase} not found in Supabase Storage.")
        
        except Exception as e:
            analysis_results["status"] = "failed_download"
            analysis_results["error"] = f"Failed to download file: {e}"
            print(f"Error downloading file {file_path_in_supabase}: {e}")
            return analysis_results # Return early if download fails
        
        document_images: List[Image.Image] = []
        try:
            if file_type == "document" and local_file_path.lower().endswith(".pdf"):
                try:
                    # Open the PDF file using PyMuPDF
                    doc = fitz.open(local_file_path)
                    for page_num in range(doc.page_count):
                        page = doc.load_page(page_num)
                        pix = page.get_pixmap(matrix=fitz.Matrix(2, 2))
                        img_bytes = pix.tobytes("png")
                        document_images.append(Image.open(io.BytesIO(img_bytes)).convert("RGB"))
                    
                    doc.close()
                    print(f"Converted {len(document_images)} PDF page(s) to images.")

                except Exception as e:
                    analysis_results["status"] = "failed_pdf_conversion"
                    analysis_results["error"] = f"Failed to convert PDF to images: {e}"
                    print(f"Error converting PDF {local_file_path} to images: {e}")
                    return analysis_results # Return early if PDF conversion fails

            elif file_type == "image" and local_file_path.lower().endswith(('.jpg', '.jpeg', '.png')):
                document_images.append(Image.open(local_file_path).convert("RGB"))
                print(f"Loaded image file: {local_file_path}")

            else:
                analysis_results["status"] = "unsupported_file_type"
                analysis_results["error"] = "Unsupported file type. Only PDF and image files are supported for document analysis."
                print(f"Unsupported file type for {local_file_path}. Only PDF and image files are supported.")
                return analysis_results # Return early if file type is unsupported
            
            if not document_images:
                analysis_results["status"] = "no_images_generated"
                analysis_results["error"] = "No images were generated from the document/image for analysis."
                print("Error: No images were generated from the document/image for analysis.")
                return analysis_results # Exit if no images to process

            if self.layoutlmv3_processor and self.layoutlmv3_model and document_images:
                print("Starting LayoutLMv3 analysis...")
                questions_for_form = [
                        "What is the patient's full name?",
                        "What is the patient's date of birth?",
                        "What is the patient's phone number?",
                        "What is their primary complaint?",
                        "List all known allergies.",
                        "What medications are they currently taking?",
                        "What is the patient's address?"
                        # Add more questions specific to your forms
                    ]
                
                extracted_kv_pairs = {} # stores the extracted key-value pairs from the document

                for i, image_page in enumerate(document_images):
                    if not isinstance(image_page, Image.Image):
                        print(f"Skipping page {i+1}: Not a valid PIL Image object found in document_images. Type: {type(image_page)}")
                        continue # Skip to next image if this one is somehow corrupted or not an image

                    print(f"Processing page {i+1} with LayoutLMv3...")

                    # Process each question individually on the current image page
                    for q_idx, q in enumerate(questions_for_form):
                        if q in extracted_kv_pairs and extracted_kv_pairs[q] not in ["Not Found", "Error: No answer found"]: # Skip if already found and valid
                            continue

                        try:
                            # --- Key Change Here ---
                            # Prepare inputs for each question on the current image
                            single_question_inputs = self.layoutlmv3_processor(
                                images=image_page,
                                text=[q], # Pass just the current question
                                return_tensors="pt"
                            ).to(self.device) # Move to device here

                            with torch.no_grad(): # Use no_grad for inference to save memory and speed up
                                outputs = self.layoutlmv3_model(**single_question_inputs)

                            start_logits = outputs.start_logits
                            end_logits = outputs.end_logits
                            answer_start = torch.argmax(start_logits)
                            answer_end = torch.argmax(end_logits) + 1 

                            # Decode the answer
                            answer = self.layoutlmv3_processor.tokenizer.decode(
                                single_question_inputs["input_ids"][0][answer_start:answer_end],
                                skip_special_tokens=True
                            ).strip()

                            if answer and answer not in ["[CLS]", "[SEP]", ""]:
                                extracted_kv_pairs[q] = answer
                                print(f"    Q: {q} -> A: {answer}")
                            elif q not in extracted_kv_pairs: # If not found yet for this question across all pages
                                extracted_kv_pairs[q] = "Not Found"
                            
                        except Exception as e:
                            print(f"    Error processing question '{q}' on page {i+1}: {e}")
                            if q not in extracted_kv_pairs or "Error" in extracted_kv_pairs[q]:
                                extracted_kv_pairs[q] = f"Error: {e}" # Store the error message
                
                analysis_results["extracted_data"] = extracted_kv_pairs
                analysis_results["status"] = "completed"

            elif not self.layoutlmv3_processor or not self.layoutlmv3_model:
                analysis_results["status"] = "model_not_loaded"
                analysis_results["error"] = "LayoutLMv3 model or processor could not be loaded."
            else:
                analysis_results["status"] = "no_document_images_for_qa"
                analysis_results["error"] = "No document images were generated for LayoutLMv3 QA."
        
        except Exception as e:
            analysis_results["status"] = "failed_analysis"
            analysis_results["error"] = f"An unexpected error occurred during document processing: {e}"
            print(f"Error analyzing document {local_file_path if local_file_path else 'unknown'}: {e}")

        finally:
            # Clean up the local file if it was downloaded
            if local_file_path and os.path.exists(local_file_path):
                os.remove(local_file_path)
                print(f"Cleaned up local file: {local_file_path}")
            print(f"Finished analysis for file: {file_path_in_supabase}, status: {analysis_results['status']}")

        return analysis_results
    

document_analyzer = DocumentAnalyzer()