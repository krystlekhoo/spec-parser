import streamlit as st
import fitz  # PyMuPDF
import re
import pandas as pd
import spacy
import openai

st.set_page_config(layout="wide")
st.title("Hybrid NLP + GPT Mechanical Insulation Spec Parser")

# Ensure spaCy model is available
try:
    nlp = spacy.load("en_core_web_sm")
except OSError:
    with st.spinner("Downloading spaCy model..."):
        from spacy.cli import download
        download("en_core_web_sm")
        nlp = spacy.load("en_core_web_sm")

use_gpt = st.toggle("Use GPT for fallback extraction", value=False)
openai_api_key = st.text_input("Enter OpenAI API Key (only if GPT is toggled on)", type="password") if use_gpt else None

uploaded_file = st.file_uploader("Upload PDF Spec", type="pdf")
if not uploaded_file:
    st.stop()

text = "\n".join(page.get_text() for page in fitz.open(stream=uploaded_file.read(), filetype="pdf"))
doc = nlp(text)

rows = []
suspects = []

for sent in doc.sents:
    line = sent.text.strip()
    lowered = line.lower()

    if "insul" not in lowered:
        continue

    service = re.search(r"(chilled water|heating water|cooling system|condensate|refrigerant|hot water|cold water|supply air|return air|exhaust air)", lowered)
    size = re.search(r"\d+(\.\d+)?\s?(inches|inch|\")", lowered)
