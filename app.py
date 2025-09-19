import streamlit as st
from docx.document import Document
from transformers import pipeline
import fitz  # PyMuPDF
from dotenv import load_dotenv
import os
import tempfile
from google.cloud import texttospeech
import base64

# --- Fix 1: Properly load and handle credentials ---
# For local development with a .env file
load_dotenv()

# For Streamlit Cloud deployment
if "GOOGLE_APPLICATION_CREDENTIALS" in os.environ and os.getenv("GOOGLE_APPLICATION_CREDENTIALS") is not None:
    # Use the path to the credentials file from .env
    os.environ["GOOGLE_APPLICATION_CREDENTIALS"] = os.getenv("GOOGLE_APPLICATION_CREDENTIALS")
elif st.secrets and "google_creds" in st.secrets:
    # Use the embedded JSON content from Streamlit Secrets
    creds_json = st.secrets["google_creds"]
    
    # Check if the secret is a single-line base64 string
    if isinstance(creds_json, str) and len(creds_json) > 100 and not creds_json.startswith('{'):
        creds_json_decoded = base64.b64decode(creds_json).decode('utf-8')
    else:
        # Assume it's a direct JSON object or string
        creds_json_decoded = creds_json

    # Write the JSON to a temporary file
    with tempfile.NamedTemporaryFile(mode='w', delete=False, suffix=".json") as temp_file:
        temp_file.write(creds_json_decoded)
        os.environ["GOOGLE_APPLICATION_CREDENTIALS"] = temp_file.name
else:
    st.error("Google Cloud credentials not found. Please set `GOOGLE_APPLICATION_CREDENTIALS` as an environment variable or a Streamlit secret.")
    st.stop()
# --- End Fix 1 ---

# Initialize summarization pipeline
try:
    summarizer = pipeline("summarization", model="facebook/bart-large-cnn")
except Exception as e:
    st.error(f"Failed to load summarization model: {e}")
    st.stop()

# Streamlit page config
st.set_page_config(page_title="Document to Podcast", layout="centered")
st.title("📄 ➡️ 🎧 Text to Podcast")

# The rest of your code remains the same...
def extract_text(file):
    # ... (code for text extraction)
    if file.name.endswith(".txt"):
        return file.read().decode("utf-8")
    elif file.name.endswith(".pdf"):
        doc = fitz.open(stream=file.read(), filetype="pdf")
        return "\n".join([page.get_text() for page in doc])
    elif file.name.endswith(".docx") or file.name.endswith(".doc"):
        temp_path = tempfile.NamedTemporaryFile(delete=False, suffix=".docx").name
        with open(temp_path, "wb") as temp_file:
            temp_file.write(file.read())
        doc = Document(temp_path)
        return "\n".join([para.text for para in doc.paragraphs])
    else:
        return None

def summarize_large_text(text, chunk_size=1000):
    # ... (code for summarization)
    chunks = [text[i:i + chunk_size] for i in range(0, len(text), chunk_size)]
    summarized = []
    for chunk in chunks:
        result = summarizer(chunk, max_length=200, min_length=50, do_sample=False)
        summarized.append(result[0]['summary_text'])
    return " ".join(summarized)

def synthesize_speech(text, output_path):
    # ... (code for text-to-speech)
    client = texttospeech.TextToSpeechClient()
    synthesis_input = texttospeech.SynthesisInput(text=text)
    voice = texttospeech.VoiceSelectionParams(
        language_code="en-US",
        ssml_gender=texttospeech.SsmlVoiceGender.FEMALE
    )
    audio_config = texttospeech.AudioConfig(
        audio_encoding=texttospeech.AudioEncoding.MP3
    )
    response = client.synthesize_speech(
        input=synthesis_input, voice=voice, audio_config=audio_config
    )
    with open(output_path, "wb") as out:
        out.write(response.audio_content)

# File upload UI
uploaded_file = st.file_uploader("Upload a .txt, .pdf, .docx, or .doc file", type=["txt", "pdf", "docx", "doc"])


if uploaded_file:
    raw_text = extract_text(uploaded_file)

    if raw_text:
        st.subheader("📃 Document Preview")
        st.write(raw_text[:1000] + "..." if len(raw_text) > 1000 else raw_text)

        if st.button("🔍 Summarize and 🎤 Generate Podcast"):
            with st.spinner("Summarizing..."):
                summary = summarize_large_text(raw_text)
                st.success("Summary Ready!")
                st.subheader("✍️ Summary")
                st.write(summary)

            with st.spinner("Generating audio..."):
                with tempfile.NamedTemporaryFile(delete=False, suffix=".mp3") as tmp_file:
                    synthesize_speech(summary, tmp_file.name)
                    audio_path = tmp_file.name

                with open(audio_path, "rb") as f:
                    audio_bytes = f.read()

                st.success("🎧 Audio Ready!")
                st.download_button("⬇️ Download Podcast", data=audio_bytes, file_name="summary_podcast.mp3", mime="audio/mp3")

    else:
        st.error("Unsupported file or failed to extract text.")
