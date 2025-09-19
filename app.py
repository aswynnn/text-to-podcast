import streamlit as st
from transformers import pipeline
import fitz  # PyMuPDF
from docx import Document
import os
import tempfile
from google.cloud import texttospeech
import base64
import json

# --- Streamlit Page Config (MUST be the first Streamlit command) ---
st.set_page_config(page_title="Document to Podcast", layout="centered")

# --- Helper Functions ---

def setup_google_credentials():
    """
    Sets up Google Cloud credentials from Streamlit secrets.
    
    If the 'GOOGLE_APPLICATION_CREDENTIALS_BASE64' secret is available,
    it decodes it, saves it to a temporary file, and sets the
    GOOGLE_APPLICATION_CREDENTIALS environment variable to its path.
    """
    try:
        # Check if the secret is available in Streamlit secrets
        creds_base64 = st.secrets.get("GOOGLE_APPLICATION_CREDENTIALS_BASE64")
        if creds_base64:
            # Decode the base64 secret
            creds_json_str = base64.b64decode(creds_base64).decode("utf-8")
            
            # Write the decoded JSON to a temporary file
            with tempfile.NamedTemporaryFile(delete=False, suffix=".json") as temp_file:
                temp_file.write(creds_json_str.encode("utf-8"))
                # Set the environment variable to the path of the temporary file
                os.environ["GOOGLE_APPLICATION_CREDENTIALS"] = temp_file.name
    except (json.JSONDecodeError, FileNotFoundError) as e:
        st.error(f"Error setting up Google Cloud credentials from secrets: {e}")
        st.stop()
    except Exception as e:
        # Fallback for local development using a .env file or existing env var
        if "GOOGLE_APPLICATION_CREDENTIALS" not in os.environ:
             st.warning("Google Cloud credentials not found. Please set them up in your Streamlit secrets or locally.")
        

def extract_text(file):
    """Extracts text from uploaded .txt, .pdf, or .docx files."""
    if file.name.endswith(".txt"):
        return file.read().decode("utf-8")

    elif file.name.endswith(".pdf"):
        try:
            doc = fitz.open(stream=file.read(), filetype="pdf")
            return "\n".join([page.get_text() for page in doc])
        except Exception as e:
            st.error(f"Error reading PDF file: {e}")
            return None

    elif file.name.endswith(".docx"):
        try:
            doc = Document(file)
            return "\n".join([para.text for para in doc.paragraphs])
        except Exception as e:
            st.error(f"Error reading DOCX file: {e}")
            return None
    
    elif file.name.endswith(".doc"):
        st.error("'.doc' files are not supported. Please convert to '.docx', '.pdf', or '.txt'.")
        return None

    else:
        st.error("Unsupported file format.")
        return None


def summarize_large_text(text, chunk_size=1024):
    """Summarizes text in chunks to handle large documents."""
    # Split text into chunks, ensuring we don't split words
    text_words = text.split(' ')
    chunks = []
    current_chunk_words = []
    
    for word in text_words:
        current_chunk_words.append(word)
        if len(' '.join(current_chunk_words)) > chunk_size:
            # Join all but the last word to avoid overflow
            chunks.append(' '.join(current_chunk_words[:-1]))
            current_chunk_words = [word] # Start new chunk with the last word
            
    if current_chunk_words:
        chunks.append(' '.join(current_chunk_words))

    summarized_text = summarizer(chunks, max_length=150, min_length=40, do_sample=False)
    return " ".join([summary['summary_text'] for summary in summarized_text])


def synthesize_speech(text, output_path):
    """Synthesizes speech from text using Google Cloud TTS and saves it to a file."""
    try:
        client = texttospeech.TextToSpeechClient()
        synthesis_input = texttospeech.SynthesisInput(text=text)
        voice = texttospeech.VoiceSelectionParams(
            language_code="en-US",
            ssml_gender=texttospeech.SsmlVoiceGender.NEUTRAL
        )
        audio_config = texttospeech.AudioConfig(
            audio_encoding=texttospeech.AudioEncoding.MP3
        )
        response = client.synt
