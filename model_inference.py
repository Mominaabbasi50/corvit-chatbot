import logging
import sys
from langchain.vectorstores import FAISS
from langchain.embeddings import HuggingFaceEmbeddings
from sentence_transformers import SentenceTransformer, util
import torch
import re
from transformers import AutoTokenizer, AutoModelForSeq2SeqLM

# Set up logging
logging.basicConfig(level=logging.DEBUG, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# === Initialize models ===
try:
    logger.debug("Loading tokenizer and model...")
    tokenizer = AutoTokenizer.from_pretrained("google/flan-t5-small")
    model = AutoModelForSeq2SeqLM.from_pretrained("google/flan-t5-small")
    model.to("cpu")  # Ensure CPU usage
    logger.debug("Tokenizer and model loaded successfully.")
except Exception as e:
    logger.error(f"Error loading tokenizer/model: {e}")
    sys.exit(1)

# === Embedding and reranker models ===
try:
    logger.debug("Loading embedding and reranker models...")
    embedding_model = HuggingFaceEmbeddings(model_name="sentence-transformers/all-mpnet-base-v2")
    reranker_model = SentenceTransformer("sentence-transformers/all-mpnet-base-v2")
    logger.debug("Embedding and reranker models loaded successfully.")
except Exception as e:
    logger.error(f"Error loading embedding/reranker models: {e}")
    sys.exit(1)

# === Load FAISS retriever ===
try:
    faiss_path = "retriever/corvit_faiss_index"
    logger.debug(f"Loading FAISS index from {faiss_path}...")
    retriever = FAISS.load_local(
        folder_path=faiss_path,
        embeddings=embedding_model,
        allow_dangerous_deserialization=True
    ).as_retriever(search_type="similarity", k=4)  # Increased k to 4 for better coverage
    logger.debug("FAISS retriever loaded successfully.")
except Exception as e:
    logger.error(f"Error loading FAISS index: {e}")
    sys.exit(1)

# === Utility functions ===
def clean_output(text):
    logger.debug(f"Cleaning output: {text}")
    # Remove question prefixes, artifacts, and extra whitespace
    text = re.sub(r"Q:.*?\n|A:\s*", "", text, flags=re.DOTALL)
    text = re.sub(r'(##end_quote##|\bTherefore\b.*|[\(\[][^)]*[:\]]|[^\w\s.,!?])', '', text, flags=re.IGNORECASE)
    text = re.sub(r'\s+', ' ', text).strip()
    logger.debug(f"Cleaned output: {text}")
    return text if text else "I'm sorry, I couldn't find a specific answer to your question at the moment. However, Corvit Systems Islamabad offers a wide range of IT training programs, including CCNA, Cybersecurity, AWS, and many more. If you're looking to enhance your skills or start a career in IT, we’d be happy to help you explore the right course. Would you like to know more about our available training options?"

def is_out_of_domain(query):
    blacklist = [
        "google", "amazon", "facebook", "pakistan politics", "elon musk", "cooking","supprots","games"
        "yoga", "swimming", "fitness", "music", "photography", "driving", "language learning", "dresses","makup","dress","jewellery"
        "interior design", "bakery", "pizza", "philosophy", "movies", "travel","art","animals","cats","mountines","river"
    ]
    result = any(re.search(rf'\b{word}\b', query.lower()) for word in blacklist)
    logger.debug(f"Out-of-domain check for query '{query}': {result}")
    return result

def is_general_knowledge(query):
    general_knowledge_terms = [
        "capital city", "capital of", "president of", "population of", "history of",
        "who invented", "what is the meaning", "weather in", "stock price"
    ]
    result = any(term in query.lower() for term in general_knowledge_terms)
    logger.debug(f"General knowledge check for query '{query}': {result}")
    return result

def is_outside_islamabad(query):
    cities = ["lahore", "karachi", "multan", "peshawar", "faisalabad"]
    result = any(city in query.lower() for city in cities)
    logger.debug(f"Outside Islamabad check for query '{query}': {result}")
    return result

# === Main QA function ===
def generate_response(query):
    logger.debug(f"Processing query: {query}")
    
    if is_general_knowledge(query):
        return "🤖 Sorry, I’m only trained to answer questions about Corvit Islamabad’s IT training and services."
    if is_out_of_domain(query):
        return "🤖 Sorry, I’m only trained to answer questions about Corvit Islamabad."
    if is_outside_islamabad(query):
        return "🤖 I’m focused only on Corvit Islamabad. I don’t have data for other branches."

    # Step 1: Retrieve documents
    try:
        results = retriever.get_relevant_documents(query)
        logger.debug(f"Retrieved documents: {[doc.page_content for doc in results]}")
        logger.debug(f"Document metadata: {[doc.metadata for doc in results]}")
        if not results:
            logger.warning("No documents retrieved.")
            return "I'm sorry, I couldn't find a specific answer to your question at the moment. However, Corvit Systems Islamabad offers a wide range of IT training programs, including CCNA, Cybersecurity, AWS, and many more. If you're looking to enhance your skills or start a career in IT, we’d be happy to help you explore the right course. Would you like to know more about our available training options?"
    except Exception as e:
        logger.error(f"Retriever error: {e}")
        return "Error retrieving documents."

    # Step 2: Rerank using semantic similarity
    try:
        query_emb = reranker_model.encode(query, convert_to_tensor=True)
        doc_texts = [doc.page_content for doc in results]
        doc_embs = reranker_model.encode(doc_texts, convert_to_tensor=True)
        sims = util.cos_sim(query_emb, doc_embs)[0]
        logger.debug(f"Similarity scores: {sims.tolist()}")
        ranked = sorted(zip(sims, results), key=lambda x: x[0], reverse=True)
        top_sim, top_doc = ranked[0]
        top_answer = top_doc.metadata.get("answer", "").strip()
        logger.debug(f"Top similarity: {top_sim.item()}, Top answer: {top_answer}, Query: {query}")
    except Exception as e:
        logger.error(f"Reranking error: {e}")
        return "Error during reranking."

    # Step 3: Hard filter
    if not top_answer or top_sim.item() < 0.5:
        logger.warning(f"Top answer empty or similarity too low: {top_sim.item()}")
        return "I'm sorry, I couldn't find a specific answer to your question at the moment. However, Corvit Systems Islamabad offers a wide range of IT training programs, including CCNA, Cybersecurity, AWS, and many more. If you're looking to enhance your skills or start a career in IT, we’d be happy to help you explore the right course. Would you like to know more about our available training options?"

    # Step 4: Use direct answer if high confidence
    logger.debug(f"Checking direct answer condition: top_sim={top_sim.item()}")
    if top_sim.item() >= 0.64:
        logger.debug("Returning direct answer due to high confidence.")
        return clean_output(top_answer)

    # Step 5: Generate answer with context
    context = ""
    for sim, doc in ranked[:2]:
        context += f"Q: {doc.page_content}\nA: {doc.metadata.get('answer', '')}\n\n"
    logger.debug(f"Context for generation: {context}")

    prompt = f"""You are a customer support assistant for Corvit Islamabad, specializing in IT training and certifications (e.g., CCNA, CCNP, cybersecurity, AWS, Azure). 
Use only the provided context to answer questions about Corvit’s services, registration, or courses in Islamabad. For process-related queries (e.g., how to register), provide full steps. For irrelevant or unrelated questions (e.g., cooking, yoga, general knowledge), respond only with: "Sorry, I couldn’t find a relevant answer to your question. Corvit offers IT training like CCNA, cybersecurity, and AWS in Islamabad. Interested?" Do not guess or repeat question or generate answers outside Corvit’s scope. If no relevant answer is found in the context, use the same apology.

Context:
{context}

User Question: {query}
Answer:"""
    logger.debug(f"Prompt: {prompt}")

    try:
        inputs = tokenizer(prompt, return_tensors="pt", truncation=True, padding=True).to(model.device)
        outputs = model.generate(
            **inputs,
            max_new_tokens=300,
            min_length=20,
            num_beams=4,
            no_repeat_ngram_size=2
        )
        response = tokenizer.decode(outputs[0], skip_special_tokens=True)
        final = clean_output(response)
        logger.debug(f"Generated response: {final}")
        # Fallback to top answer if generated response is too short or empty
        if not final or len(final.split()) < 5 and top_answer:
            logger.debug("Generated response too short or empty, using top answer instead.")
            return clean_output(top_answer)
        return final
    except Exception as e:
        logger.error(f"Generation error: {e}")
        return "🤖 Error generating response."