from presidio_analyzer import AnalyzerEngine
from presidio_anonymizer import AnonymizerEngine

# Initialize engines dynamically as a service
analyzer = AnalyzerEngine()
anonymizer = AnonymizerEngine()

def anonymize_text(text: str) -> str:
    """
    Strips PII (Names, Locations, Emails, Phone numbers, Dates) from the given text
    to ensure HIPAA compliance before sending data to LLMs or Vector DBs.
    """
    if not text:
        return text
        
    results = analyzer.analyze(
        text=text, 
        entities=["PERSON", "LOCATION", "EMAIL_ADDRESS", "PHONE_NUMBER", "DATE_TIME"], 
        language='en'
    )
    
    anonymized_result = anonymizer.anonymize(text=text, analyzer_results=results)
    return anonymized_result.text
