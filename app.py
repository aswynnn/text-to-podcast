import streamlit as st
from docx.document import Document
from transformers import pipeline
import fitz  # PyMuPDF
from dotenv import load_dotenv
import os
import tempfile
from google.cloud import texttospeech
import base64
import json

# Load environment variables
load_dotenv()

# --- FIX START ---
# Check if the environment variable is set
google_credentials_base64 = os.getenv("GOOGLE_APPLICATION_CREDENTIALS")

# Check for secrets on Streamlit Cloud, if not found, check for local .env
if not google_credentials_base64 and st.secrets.get("GOOGLE_APPLICATION_CREDENTIALS"):
    google_credentials_base64 = st.secrets.get("GOOGLE_APPLICATION_CREDENTIALS")

if google_credentials_base64:
    try:
        # Decode the base64 string and write it to a temporary file
        credentials_json_str = base64.b64decode(google_credentials_base64).decode('utf-8')
        credentials_json = json.loads(credentials_json_str)

        # Create a temporary file to store the credentials
        with tempfile.NamedTemporaryFile(delete=False, suffix=".json", mode='w') as temp_file:
            json.dump(credentials_json, temp_file)
            temp_file_path = temp_file.name
        
        # Set the environment variable to the path of the temporary file
        os.environ["GOOGLE_APPLICATION_CREDENTIALS"] = temp_file_path
        
    except Exception as e:
        st.error(f"Error decoding or creating credentials file: {e}")
        st.stop()
else:
    st.error("GOOGLE_APPLICATION_CREDENTIALS environment variable is not set. Please follow the installation instructions.")
    st.stop()

# --- FIX END ---

# Initialize summarization pipeline
summarizer = pipeline("summarization", model="facebook/bart-large-cnn")

# Streamlit page config
st.set_page_config(page_title="Document to Podcast", layout="centered")
st.title("📄 ➡️ 🎧 Text to Podcast")

# Extract text helper
def extract_text(file):
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

# Summarize text in chunks
def summarize_large_text(text, chunk_size=1000):
    chunks = [text[i:i + chunk_size] for i in range(0, len(text), chunk_size)]
    summarized = []
    for chunk in chunks:
        result = summarizer(chunk, max_length=200, min_length=50, do_sample=False)
        summarized.append(result[0]['summary_text'])
    return " ".join(summarized)

# Synthesize speech and save to file
def synthesize_speech(text, output_path):
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
                # Generate and save audio
                with tempfile.NamedTemporaryFile(delete=False, suffix=".mp3") as tmp_file:
                    synthesize_speech(summary, tmp_file.name)
                    audio_path = tmp_file.name

                # Read audio content
                with open(audio_path, "rb") as f:
                    audio_bytes = f.read()

                st.success("🎧 Audio Ready!")
                st.download_button("⬇️ Download Podcast", data=audio_bytes, file_name="summary_podcast.mp3", mime="audio/mp3")

    else:
        st.error("Unsupported file or failed to extract text.")
