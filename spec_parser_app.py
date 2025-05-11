import streamlit as st
import fitz  # PyMuPDF
import re
import pandas as pd
import spacy
import openai

st.set_page_config(layout="wide")
st.title("Hybrid NLP + GPT Mechanical Insulation Spec Parser")

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
    thickness = re.search(r"\d+(\.\d+)?\s?(inches|inch|\")\s?(thick|thickness)?", lowered)
    insul_type = re.search(r"(fiberglass|foam|phenolic|elastomeric|cellular|closed cell)", lowered)
    jacket = re.search(r"(vapor[-\s]?proof|canvas|aluminum|uv[-\s]?protected)", lowered)

    result = {
        "Service": service.group(1).title() if service else "",
        "Size": size.group(0) if size else "",
        "Thickness": thickness.group(0) if thickness else "",
        "Type": insul_type.group(1).title() if insul_type else "",
        "Jacket": jacket.group(1).title() if jacket else "",
        "Source": line
    }

    if any(val == "" for key, val in result.items() if key != "Source"):
        suspects.append(line)
    else:
        rows.append(result)

if use_gpt and openai_api_key and suspects:
    openai.api_key = openai_api_key
    for p in suspects:
        prompt = f"""
You are extracting insulation spec fields from this construction sentence:

"{p}"

Return the following fields as a JSON object:
Service, Size, Thickness, Type, Jacket
        """
        try:
            completion = openai.ChatCompletion.create(
                model="gpt-4-turbo",
                messages=[{"role": "user", "content": prompt}]
            )
            response_text = completion.choices[0].message["content"]
            gpt_result = eval(response_text)
            gpt_result["Source"] = p
            rows.append(gpt_result)
        except Exception as e:
            st.error(f"GPT error: {e}")

if not rows:
    st.warning("No structured rows found.")
    st.stop()

df = pd.DataFrame(rows)
df["Reviewed"] = False

st.data_editor(df, num_rows="dynamic", use_container_width=True, disabled=["Source"])
copy_block = st.selectbox("Copy source text for:", df["Source"].unique())
st.code(copy_block, language="text")

st.download_button("Download as CSV", data=df.to_csv(index=False).encode("utf-8"), file_name="parsed_insulation_specs.csv", mime="text/csv")