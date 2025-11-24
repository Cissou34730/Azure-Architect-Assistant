"""
Test LLM directly without RAG to measure baseline performance
"""
import os
import time
from dotenv import load_dotenv
from llama_index.llms.openai import OpenAI

load_dotenv()

def test_llm_speed():
    """Test LLM response time with a simple query"""
    
    llm = OpenAI(
        model="gpt-4o-mini",
        temperature=0.1,
        max_tokens=500,
        timeout=90.0
    )
    
    question = "What are the five pillars of the Azure Well-Architected Framework?"
    
    print("Testing LLM directly (no retrieval)...")
    print(f"Model: gpt-4o-mini")
    print(f"Question: {question}\n")
    
    start_time = time.time()
    response = llm.complete(question)
    elapsed = time.time() - start_time
    
    print(f"Response received in {elapsed:.2f}s")
    print(f"Answer length: {len(response.text)} chars")
    print(f"\nAnswer:\n{response.text}\n")
    
    return elapsed

def test_llm_with_context():
    """Test LLM with a typical RAG context size"""
    
    llm = OpenAI(
        model="gpt-4o-mini",
        temperature=0.1,
        max_tokens=500,
        timeout=90.0
    )
    
    # Simulate typical RAG context (3 chunks)
    mock_context = "[Source 1]\n" + ("This is sample content from the documentation. " * 100) + "\n\n"
    mock_context += "[Source 2]\n" + ("More documentation content here. " * 100) + "\n\n"
    mock_context += "[Source 3]\n" + ("Additional information from docs. " * 100) + "\n"
    
    prompt = f"""You are an Azure Well-Architected Framework expert. Answer the question using ONLY the provided sources.

Sources:
{mock_context}

Question: What are the five pillars of the Well-Architected Framework?

Provide a clear, concise answer with specific details from the sources. If the sources lack information, state this clearly.

Answer:"""
    
    print("\n" + "="*80)
    print("Testing LLM with RAG-style context...")
    print(f"Context size: {len(mock_context)} chars (~{len(mock_context)//4} tokens)")
    print(f"Total prompt: {len(prompt)} chars (~{len(prompt)//4} tokens)\n")
    
    start_time = time.time()
    response = llm.complete(prompt)
    elapsed = time.time() - start_time
    
    print(f"Response received in {elapsed:.2f}s")
    print(f"Answer length: {len(response.text)} chars")
    
    return elapsed

if __name__ == "__main__":
    time1 = test_llm_speed()
    time2 = test_llm_with_context()
    
    print("\n" + "="*80)
    print("SUMMARY:")
    print(f"  Simple query: {time1:.2f}s")
    print(f"  With context: {time2:.2f}s")
    print(f"  Difference: {time2-time1:.2f}s")
