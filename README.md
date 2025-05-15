# texttalk
Text to speech converter, summarized the text and gives an audio feedback about it.

# 📄 ➡️ 🎧 Document to Podcast

This Streamlit app lets you convert `.doc`,`.docx`,`.txt` or `.pdf` documents into summarized audio podcasts using Google Cloud Text-to-Speech and Hugging Face transformers.

---

## 🚀 Features

- Upload `.txt` or `.pdf` files
- Automatic summarization using BART (`facebook/bart-large-cnn`)
- Text Summarization
- Audio generation via Google Cloud TTS
- Download podcast

---

## 🛠️ Installation

1. **Clone the repository**
```
[git clone https://github.com/aswynn/texttalk.git](https://github.com/aswynnn/text-to-podcast.git)
```

```
cd text-to-podcast
```

---

**2. Create and activate a virtual environment (optional but recommended)**
For Windows:
```
python -m venv venv
venv\Scripts\activate
```

For macOS/Linux:
```
python3 -m venv venv
source venv/bin/activate
```
---

**3. Install dependencies**
```
pip install -r requirements.txt
```
---

**4. Set up environment variables**
Create a .env file in the project root directory and add the following, after creating your Google Cloud API json key:
```
GOOGLE_APPLICATION_CREDENTIALS=/absolute/path/to/your-service-account-key.json
```
_⚠️ Replace /absolute/path/to/your-service-account-key.json with the actual full path to your Google Cloud service account key file._

make the json key to one single line using:
```
base64 /absolute/path/to/your-service-account-key.json
```
if you are using MacOS, then:
```
base64 -i /absolute/path/to/your-service-account-key.json
```
---
**For streamlit:**
Copy the one line json key you generated and paste it in the Streamit>Your App>Three dots > Secrets
Name the varibale and paste the base64 json key.




