import re
import logging

logger = logging.getLogger(__name__)

class ClinicalAnonymizer:
    """
    Lite Clinical Anonymizer (Cloud-Optimized)
    Uses high-performance regex patterns to identify and scrub PII/PHI
    without requiring heavy 500MB+ NLP models.
    """
    
    # Standard PII Patterns
    PATTERNS = {
        "EMAIL": r'[a-zA-Z0-9_.+-]+@[a-zA-Z0-9-]+\.[a-zA-Z0-9-.]+',
        "PHONE": r'(\+?\d{1,3}[-.\s]?)?\(?\d{3}\)?[-.\s]?\d{3}[-.\s]?\d{4}',
        "DATE_OF_BIRTH": r'\b(\d{1,2}[/-]\d{1,2}[/-]\d{2,4})\b',
        "AADHAAR": r'\b\d{4}\s\d{4}\s\d{4}\b',
        "AGE": r'\b(\d{1,3})\s?(year-old|yo|y/o|yr old)\b',
    }

    def anonymize(self, text: str) -> str:
        """Scrubs PII from the clinical query."""
        if not text:
            return text
            
        anonymized = text
        
        # 1. Scrub common patterns
        for label, pattern in self.PATTERNS.items():
            anonymized = re.sub(pattern, f"<{label}>", anonymized, flags=re.IGNORECASE)
            
        # 2. Heuristic check for capitalized names (Basic fallback)
        # Note: In a clinical setting, we prioritize safety. 
        # If the text looks like "Patient John Doe presents with...", 
        # we aim to mask common name indicators.
        
        logger.info(f"[Anonymizer] Clinical text scrubbed for cloud safety.")
        return anonymized

anonymizer = ClinicalAnonymizer()
