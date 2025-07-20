import requests
import numpy as np
from sentence_transformers import SentenceTransformer
from sklearn.metrics.pairwise import cosine_similarity
import re
import os
import json

def test_extraction_accuracy(file_path, keywords, expected_results, backend_url="http://127.0.0.1:5000"):
    """
    Test the accuracy of document extraction system
    
    Args:
        file_path (str): Path to test document
        keywords (str): Comma-separated keywords
        expected_results (dict): Expected extraction results
        backend_url (str): Backend API URL
    
    Returns:
        dict: Accuracy metrics and scores
    """
    # Initialize sentence transformer for semantic similarity
    sentence_model = SentenceTransformer('all-MiniLM-L6-v2')
    
    # Call extraction API
    try:
        with open(file_path, 'rb') as f:
            files = [("files", (os.path.basename(file_path), f.read()))]
            data = {"keywords": keywords}
            
            response = requests.post(f"{backend_url}/upload", files=files, data=data, timeout=60)
            
            if response.status_code != 200:
                return {"error": f"API call failed: {response.text}"}
                
            extracted_results = response.json().get("data", {})
            
    except Exception as e:
        return {"error": f"API call error: {str(e)}"}
    
    # Extract text from results
    extracted_text = ""
    if 'results' in extracted_results:
        for result in extracted_results['results']:
            for field in ['definition', 'key_details', 'programs_courses', 'requirements', 'additional_context']:
                if field in result and result[field]:
                    extracted_text += str(result[field]) + " "
    
    # Extract expected text
    expected_text = ""
    for key, value in expected_results.items():
        if isinstance(value, str):
            expected_text += value + " "
        elif isinstance(value, list):
            expected_text += " ".join([str(v) for v in value]) + " "
    
    # Calculate metrics
    metrics = {}
    
    # 1. Semantic Similarity
    if extracted_text and expected_text:
        embeddings1 = sentence_model.encode([extracted_text])
        embeddings2 = sentence_model.encode([expected_text])
        semantic_similarity = cosine_similarity(embeddings1, embeddings2)[0][0]
        metrics['semantic_similarity'] = float(semantic_similarity)
    else:
        metrics['semantic_similarity'] = 0.0
    
    # 2. Keyword Coverage
    keyword_list = [k.strip().lower() for k in keywords.split(',')]
    extracted_lower = extracted_text.lower()
    covered_keywords = sum(1 for keyword in keyword_list if keyword in extracted_lower)
    metrics['keyword_coverage'] = covered_keywords / len(keyword_list) if keyword_list else 0.0
    
    # 3. Information Completeness
    expected_fields = set(expected_results.keys())
    actual_fields = set()
    if 'results' in extracted_results:
        for result in extracted_results['results']:
            actual_fields.update(result.keys())
    
    covered_fields = expected_fields.intersection(actual_fields)
    metrics['information_completeness'] = len(covered_fields) / len(expected_fields) if expected_fields else 0.0
    
    # 4. Relevance Score
    relevance_scores = []
    if 'results' in extracted_results:
        for result in extracted_results['results']:
            result_text = " ".join([str(result.get(field, '')) for field in result.keys()])
            for keyword in keyword_list:
                if keyword in result_text.lower():
                    relevance_scores.append(1.0)
    
    metrics['relevance_score'] = np.mean(relevance_scores) if relevance_scores else 0.0
    
    # 5. Confidence Score (based on content quality)
    confidence_indicators = []
    if 'results' in extracted_results:
        for result in extracted_results['results']:
            field_presence = sum(1 for field in ['definition', 'key_details', 'programs_courses', 'requirements'] 
                               if field in result and result[field])
            total_length = sum(len(str(result.get(field, ''))) for field in result.keys())
            
            field_score = field_presence / 4.0
            length_score = min(total_length / 500, 1.0)
            confidence_indicators.append(np.mean([field_score, length_score]))
    
    metrics['confidence_score'] = np.mean(confidence_indicators) if confidence_indicators else 0.0
    
    # 6. Overall Accuracy (weighted average)
    metrics['overall_accuracy'] = (
        metrics['semantic_similarity'] * 0.3 +
        metrics['keyword_coverage'] * 0.2 +
        metrics['information_completeness'] * 0.2 +
        metrics['relevance_score'] * 0.2 +
        metrics['confidence_score'] * 0.1
    )
    
    return ({
        'metrics': metrics,
        'extracted_results': extracted_results,
        'test_summary': {
            'file_tested': os.path.basename(file_path),
            'keywords_used': keywords,
            'overall_score': f"{metrics['overall_accuracy']:.3f}",
            'performance_level': 'Excellent' if metrics['overall_accuracy'] >= 0.8 
                               else 'Good' if metrics['overall_accuracy'] >= 0.6 
                               else 'Needs Improvement'
        }
    })
if __name__ == "__main__":
    test_doc = "/Users/aditya/Desktop/Study-Assistant/1050-text-s.pdf"
    test_keywords = "sequences, geometric"
    expected_results = {
        "sequences": "Expected definition text...",
        "geometric": ["Expected detail 1", "Expected detail 2"]
    }
    
    results = test_extraction_accuracy(test_doc, test_keywords, expected_results)
    print(json.dumps(results, indent=2))