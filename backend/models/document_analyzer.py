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
        self.device = "cuda" if torch.cuda.is_available() else "cpu" # Set device to GPU if available, else CPU
        if settings.LAYOUTLMV3_MODEL_ID:
           
            try:
                self.layoutlmv3_processor = AutoProcessor.from_pretrained( # Load the LayoutLMv3 processor
                    settings.LAYOUTLMV3_MODEL_ID,
                    apply_ocr=True # <-- Enable OCR processing
                )
                self.layoutlmv3_model = AutoModelForDocumentQuestionAnswering.from_pretrained(settings.LAYOUTLMV3_MODEL_ID) 
                
                if torch.cuda.is_available():
                    self.layoutlmv3_model.to("cuda")
                

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
        
        document_images: List[Image.Image] = [] # This will hold the images extracted from the document

        try: # Check if the file is a PDF or an image
            if file_type == "document" and local_file_path.lower().endswith(".pdf"):
                try:
                    # Open the PDF file using PyMuPDF
                    doc = fitz.open(local_file_path)
                    for page_num in range(doc.page_count): # Iterate through each page
                        page = doc.load_page(page_num) # Load the page
                        pix = page.get_pixmap(matrix=fitz.Matrix(2, 2)) # Get a high-resolution image of the page
                        img_bytes = pix.tobytes("png") # Convert to PNG bytes
                        document_images.append(Image.open(io.BytesIO(img_bytes)).convert("RGB")) # Convert to RGB to ensure compatibility with LayoutLMv3
                    
                    doc.close()
                    print(f"Converted {len(document_images)} PDF page(s) to images.")

                except Exception as e:
                    analysis_results["status"] = "failed_pdf_conversion"
                    analysis_results["error"] = f"Failed to convert PDF to images: {e}"
                    print(f"Error converting PDF {local_file_path} to images: {e}")
                    return analysis_results # Return early if PDF conversion fails

            
            elif file_type == "image" and local_file_path.lower().endswith(('.jpg', '.jpeg', '.png')):
                document_images.append(Image.open(local_file_path).convert("RGB")) # Convert to RGB to ensure compatibility with LayoutLMv3
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
                
                extracted_kv_pairs = {q: [] for q in questions_for_form} # stores the extracted key-value pairs from the document

                for i, image_page in enumerate(document_images):
                    if not isinstance(image_page, Image.Image): # Check if image_page is a valid PIL Image object
                        print(f"Skipping page {i+1}: Not a valid PIL Image object found in document_images. Type: {type(image_page)}")
                        continue # Skip to next image if this one is somehow corrupted or not an image

                    print(f"Processing page {i+1} with LayoutLMv3...")

                    # Process each question individually on the current image page
                    for q_idx, q in enumerate(questions_for_form):
                        try:
                            
                            # Prepare inputs for each question on the current image
                            single_question_inputs = self.layoutlmv3_processor(
                                images=image_page,
                                text=[q], # Pass just the current question
                                return_tensors="pt"
                            ).to(self.device) # Move to device here

                            with torch.no_grad(): # Use no_grad for inference to save memory and speed up
                                outputs = self.layoutlmv3_model(**single_question_inputs)

                            start_logits = outputs.start_logits # Get the start logits for the answer
                            end_logits = outputs.end_logits # Get the end logits for the answer
                            answer_start = torch.argmax(start_logits) # Get the index of the start position of the answer
                            answer_end = torch.argmax(end_logits) + 1  # Get the index of the end position of the answer (add 1 to include the end token)

                            current_start_logit = start_logits[0, answer_start].item() # Get the logit for the start position
                            current_end_logit = end_logits[0, answer_end - 1].item() # Get the logit for the end position

                            confidence_score = current_start_logit + current_end_logit # Confidence score for the answer

                            # Decode the answer
                            answer = self.layoutlmv3_processor.tokenizer.decode(
                                single_question_inputs["input_ids"][0][answer_start:answer_end],
                                skip_special_tokens=True
                            ).strip()

                            if answer and answer not in ["[CLS]", "[SEP]", ""]: # Valid answer found
                                extracted_kv_pairs[q].append({
                                    'answer': answer,
                                    'score': confidence_score,
                                    'page': i + 1
                                })

                                print(f"    Q: {q} -> A: {answer}, score: {confidence_score}, page: {i + 1}")

                            elif q not in extracted_kv_pairs: # If not found yet for this question across all pages
                                extracted_kv_pairs[q].append({
                                    'answer': "Not Found (Empty/Special)",
                                    'score': -100.0, # Very low score for invalid answers
                                    'page': i + 1
                                })
                            
                        except Exception as e:
                            print(f"    Error processing question '{q}' on page {i+1}: {e}")
                            if q not in extracted_kv_pairs or "Error" in extracted_kv_pairs[q]:
                                extracted_kv_pairs[q] = f"Error: {e}" # Store the error message


                final_extracted_kv_pairs = {} # Final structure to hold the cleaned up results
                CONFIDENCE_THRESHOLD = 1.0 # Set a threshold for confidence score to filter out low-confidence answers

                # Define a blacklist of common problematic answers to filter out
                ANSWER_BLACKLIST = [
                    "PATIENT CONSENT", "PATIENT DETAILS", "MEDICAL HISTORY",
                    "PHYSICIAN", "DOCTOR", "BIRTH", "ACTIVE TREATING PHYSICIANS",
                    "SECONDARY INSURANCE POLICY", "PREFFERED PHARMACY", "STREET ADDRESS",
                    "2 OF 6", "3", "4", "5", "6", # Page numbers
                    # Add more as you observe problematic common extractions
                ]

                for question, answers in extracted_kv_pairs.items():
                    best_answer = "Not Found" # Default if no valid answers found
                    highest_score_for_q = -float('inf') # Initialize to negative infinity
                    answers.sort(key=lambda x: x['score'], reverse=True) # Sort answers by score in descending order

                    for item in answers:
                        current_answer = item['answer'].strip() # Get the answer text
                        current_score = item['score']

                        if current_score < CONFIDENCE_THRESHOLD:
                            continue # Skip answers below threshold

                        # Apply blacklist filter
                        # Check for exact match to a blacklisted term (case-insensitive for safety)
                        if current_answer.upper() in ANSWER_BLACKLIST:
                            continue # Skip blacklisted answers

                        # Additional heuristic for numbers that might be page numbers for phone/dob/address
                        if q in ["What is the patient's phone number?", "What is the patient's date of birth?", "What is the patient's address?"] and current_answer.isdigit() and len(current_answer) < 5:
                             continue # Likely a page number or irrelevant digit

                        best_answer = current_answer
                        highest_score_for_q = current_score
                        break # Found a valid answer with sufficient confidence score
                       

                    if best_answer != "Not Found":
                        # Cleaning for "What is the patient's full name?"
                        if q == "What is the patient's full name?":
                            if best_answer.startswith("PATIENT DETAILS"):
                                # This handles "PATIENT DETAILS First Name: Dylan Last Name: Wettlaufer"
                                # We want just "Dylan Wettlaufer"
                                best_answer = best_answer.replace("PATIENT DETAILS", "").strip()
                                best_answer = best_answer.replace("First Name:", "").replace("Last Name:", "").strip()
                            elif best_answer.startswith("First Name:"):
                                best_answer = best_answer.replace("First Name:", "").replace("Last Name:", "").strip()

                    
                        final_extracted_kv_pairs[question] = best_answer

                    else:
                        # If no valid answer found, store a default message
                        final_extracted_kv_pairs[question] = "Not Found"


                analysis_results["extracted_data"] = final_extracted_kv_pairs
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