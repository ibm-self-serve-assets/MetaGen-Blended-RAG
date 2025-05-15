import pandas as pd
import json
from keybert import KeyBERT
import yake
import spacy
from joblib import Parallel, delayed
import multiprocessing
import copy
import sys

# Initialize KeyBERT (using default sentence-transformer model)
kw_model = KeyBERT()

# Initialize YAKE keyword extractor
language = "en"
max_ngram_size = 3
deduplication_threshold = 0.9
numOfKeywords = 1  # we extract a single keyphrase
yake_extractor = yake.KeywordExtractor(lan=language,
                                       n=max_ngram_size,
                                       dedupLim=deduplication_threshold,
                                       top=numOfKeywords,
                                       features=None)

# Initialize spaCy model for NER
nlp = spacy.load("en_core_web_sm")

def extract_keybert(text, top_n=1, ngram_range=(1, 2)):
    """
    Extract the most representative keyphrase using KeyBERT.
    """
    keywords = kw_model.extract_keywords(text, 
                                         keyphrase_ngram_range=ngram_range, 
                                         stop_words='english', 
                                         top_n=top_n)
    return keywords[0][0] if keywords else ""

def extract_yake(text):
    """
    Extract a concise key idea using YAKE.
    """
    keywords = yake_extractor.extract_keywords(text)
    return keywords[0][0] if keywords else ""

def extract_entities(text, top_n=3, allowed_entity_types=["PERSON", "ORG", "GPE", "DATE", "EVENT", "NORP"]):
    """
    Extract key entities from the text using spaCy.
    Returns a comma-separated string of the top_n entities sorted by frequency.
    """
    doc = nlp(text)
    entity_freq = {}
    for ent in doc.ents:
        if ent.label_ in allowed_entity_types:
            ent_text = ent.text.strip()
            entity_freq[ent_text] = entity_freq.get(ent_text, 0) + 1
    sorted_entities = sorted(entity_freq.items(), key=lambda x: x[1], reverse=True)
    top_entities = [ent for ent, count in sorted_entities[:top_n]]
    return ", ".join(top_entities)


# Load your JSONL dataset into a DataFrame
file_path = "/data/NQ/nq/corpus.jsonl"
data = [json.loads(line) for line in open(file_path, "r", encoding="utf-8")]
df = pd.DataFrame(data)


# Define chunk size
chunk_size = 10000

print("Processing started...", flush=True)  # Ensures immediate output
sys.stdout.flush()

# Number of CPU cores to use (set to max available)
num_cores = multiprocessing.cpu_count()
print("num_cores----",num_cores)

# Function to process each chunk in parallel
def process_chunk(chunk_id, df_chunk):
    df_chunk = copy.deepcopy(df_chunk)
    print("chunk id------",chunk_id,len(df_chunk))
    df_chunk["keybert_title"] = df_chunk["text"].apply(extract_keybert)
    df_chunk["yake_key_idea"] = df_chunk["text"].apply(extract_yake)
    df_chunk["extracted_entities"] = df_chunk["text"].apply(extract_entities)

    # Save chunk to Excel
    output_filename = f"/output/nq/meta-data-lost/processed_chunk_{chunk_id + 1}.xlsx"
    df_chunk.to_excel(output_filename, index=False)
    print(f"Saved {output_filename}")

# Create chunks
chunks = [df.iloc[i:i + chunk_size].copy() for i in range(0, len(df), chunk_size)]

print("Total chunks ------",len(chunks))

chunks_up = chunks[268:269]
print(chunks_up)

print("Remening chunks ------",len(chunks_up))

# Process chunks in parallel
#Parallel(n_jobs=5)(delayed(process_chunk)(i, chunk) for i, chunk in enumerate(chunks))

Parallel(n_jobs=8, prefer="threads")(
    delayed(process_chunk)(i, chunk.copy()) for i, chunk in enumerate(chunks_up)
)

print("All chunks processed successfully!")

