import streamlit as st
from docx import Document
from transformers import pipeline
import fitz  # PyMuPDF
import os
import tempfile
from google.cloud import texttospeech
import google.generativeai as genai # Import the new library

# --- INITIALIZATION ---

# Load Google Cloud credentials for Text-to-Speech
with tempfile.NamedTemporaryFile(delete=False, suffix=".json") as f:
    f.write(st.secrets["gcp"]["credentials"].encode())
    os.environ["GOOGLE_APPLICATION_CREDENTIALS"] = f.name
    
# Configure the Gemini API with the secret key
try:
    genai.configure(api_key=st.secrets["gemini"]["api_key"])
except Exception as e:
    st.error("Failed to configure Gemini API. Please check your API key in the secrets file.")


# Initialize the summarization pipeline (still needed for the document part)
summarizer = pipeline("summarization", model="facebook/bart-large-cnn")


# --- HELPER FUNCTIONS ---

def extract_text(file):
    """Extracts text from uploaded .txt, .pdf, or .docx files."""
    file_extension = os.path.splitext(file.name)[1]
    
    if file_extension == ".txt":
        return file.read().decode("utf-8")

    elif file_extension == ".pdf":
        doc = fitz.open(stream=file.read(), filetype="pdf")
        return "\n".join([page.get_text() for page in doc])

    elif file_extension in [".docx", ".doc"]:
        with tempfile.NamedTemporaryFile(delete=False, suffix=".docx") as temp_file:
            temp_file.write(file.read())
            temp_path = temp_file.name
        doc = Document(temp_path)
        os.remove(temp_path)
        return "\n".join([para.text for para in doc.paragraphs])
    
    return None

def summarize_large_text(text, chunk_size=1024, max_length=150, min_length=40):
    """Summarizes text by breaking it into chunks first."""
    text = text.replace('.', '.<eos>').replace('?', '?<eos>').replace('!', '!<eos>')
    sentences = text.split('<eos>')
    current_chunk = ""
    chunks = []
    
    for sentence in sentences:
        if len(current_chunk) + len(sentence) <= chunk_size:
            current_chunk += sentence
        else:
            chunks.append(current_chunk)
            current_chunk = sentence
    if current_chunk:
        chunks.append(current_chunk)

    summaries = summarizer(chunks, max_length=max_length, min_length=min_length, do_sample=False)
    return " ".join([summary['summary_text'] for summary in summaries])

# MODIFIED FUNCTION: Uses Gemini API instead of a local model
def generate_text_from_topic(topic):
    """Generates a short article on a given topic using the Gemini API."""
    model = genai.GenerativeModel('gemini-pro')
    # A more descriptive prompt for better podcast-style content
    prompt = f"""
    Generate a short, engaging article about the topic: '{topic}'.
    The article should be suitable to be read aloud as a mini-podcast segment.
    Keep the tone informative yet conversational.
    Aim for a length of about 300-400 words.
    """
    try:
        response = model.generate_content(prompt)
        return response.text
    except Exception as e:
        # Handle potential API errors, e.g., content filtering
        st.error(f"An error occurred while generating text: {e}")
        return None

def synthesize_speech(text, output_path):
    """Synthesizes text into an MP3 audio file using Google Cloud TTS."""
    client = texttospeech.TextToSpeechClient()
    synthesis_input = texttospeech.SynthesisInput(text=text)
    voice = texttospeech.VoiceSelectionParams(
        language_code="en-US",
        name="en-US-Wavenet-F",
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

# --- STREAMLIT UI ---

st.set_page_config(page_title="Content to Podcast", layout="wide")
st.title("📄 ➡️ 🎧 Content to Podcast Generator")
st.markdown("Turn any document or topic into a short, listenable audio podcast!")

tab1, tab2 = st.tabs(["▶️ From a Document", "▶️ From a Topic"])

# --- TAB 1: Process from a Document ---
with tab1:
    st.header("Upload a Document")
    uploaded_file = st.file_uploader(
        "Upload a .txt, .pdf, or .docx file to summarize and convert to audio.",
        type=["txt", "pdf", "docx", "doc"]
    )
    if uploaded_file:
        raw_text = extract_text(uploaded_file)
        if raw_text:
            st.subheader("📃 Document Preview")
            st.text_area("Preview of your document:", raw_text[:1500] + "...", height=200)
            if st.button("🔍 Summarize and 🎤 Generate Podcast", key="summarize_btn"):
                with st.spinner("Summarizing the document... ⏳"):
                    summary = summarize_large_text(raw_text)
                st.success("Summary Ready!")
                st.subheader("✍️ Generated Summary")
                st.write(summary)
                with st.spinner("Generating audio podcast... 🎙️"):
                    with tempfile.NamedTemporaryFile(delete=False, suffix=".mp3") as tmp_audio_file:
                        synthesize_speech(summary, tmp_audio_file.name)
                        audio_path = tmp_audio_file.name
                st.success("🎧 Audio Ready!")
                with open(audio_path, "rb") as f:
                    st.audio(f.read(), format="audio/mp3")
                os.remove(audio_path)
        else:
            st.error("Unsupported file type or failed to extract text.")

# --- TAB 2: Process from a Topic (Now using Gemini) ---
with tab2:
    st.header("Generate from a Topic")
    topic_input = st.text_input("Enter a topic you want to hear a podcast about (e.g., 'The science of sleep'):")
    if st.button("✍️ Generate Text & 🎤 Podcast", key="generate_btn"):
        if topic_input:
            with st.spinner(f"Generating an article about '{topic_input}' with Gemini... 🧠"):
                generated_text = generate_text_from_topic(topic_input)
            if generated_text:
                st.success("Article Ready!")
                st.subheader("✍️ Generated Text")
                st.write(generated_text)
                with st.spinner("Generating audio podcast... 🎙️"):
                    with tempfile.NamedTemporaryFile(delete=False, suffix=".mp3") as tmp_audio_file:
                        synthesize_speech(generated_text, tmp_audio_file.name)
                        audio_path = tmp_audio_file.name
                st.success("🎧 Audio Ready!")
                with open(audio_path, "rb") as f:
                    audio_bytes = f.read()
                st.audio(audio_bytes, format="audio/mp3")
                st.download_button(
                    "⬇️ Download Podcast",
                    data=audio_bytes,
                    file_name=f"{topic_input.replace(' ', '_')}.mp3",
                    mime="audio/mp3"
                )
                os.remove(audio_path)
        else:
            st.warning("Please enter a topic first!")
