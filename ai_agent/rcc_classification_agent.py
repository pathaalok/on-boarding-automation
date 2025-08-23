from typing import Dict, Any, List
import random
import string

def generate_rcc_code() -> str:
    """Generate a unique RCC code"""
    # Generate a random 6-character alphanumeric code
    return ''.join(random.choices(string.ascii_uppercase + string.digits, k=6))

def check_existing_rcc_codes() -> List[str]:
    """Check for existing RCC codes (simulated - in real implementation, this would query a database)"""
    # Simulated existing RCC codes - in real implementation, this would query a database
    return ["RCC001", "RCC002", "RCC003", "RCC004", "RCC005"]

def rcc_classification_agent(doc_classification_result: Dict[str, Any]) -> Dict[str, Any]:
    """RCC Classification Agent: Takes doc classification output, adds RCC codes, and returns enhanced structure"""
    
    # Extract successful files from doc classification results
    successful_files = doc_classification_result.get("successful_files", [])
    failed_files = doc_classification_result.get("failed_files", [])
    
    # Process each successful file and add RCC codes
    enhanced_successful_files = []
    existing_rcc_codes = check_existing_rcc_codes()
    
    for file_result in successful_files:
        # Generate RCC code for this file
        rcc_code = generate_rcc_code()
        
        # Check if RCC code already exists (simulate conflict detection)
        existing_rcc_code = None
        conflict_flag = False
        
        # Simulate checking for conflicts (in real implementation, this would be more sophisticated)
        if rcc_code in existing_rcc_codes:
            existing_rcc_code = rcc_code
            conflict_flag = True
            # Generate a new unique code
            while rcc_code in existing_rcc_codes:
                rcc_code = generate_rcc_code()
        
        # Create enhanced file result with RCC codes
        enhanced_file_result = {
            **file_result,  # Keep all original fields
            "rccCode": rcc_code,
            "existingRccCode": existing_rcc_code,
            "conflictFlag": conflict_flag
        }
        
        enhanced_successful_files.append(enhanced_file_result)
    
    # Process failed files (add RCC codes but with error status)
    enhanced_failed_files = []
    for file_result in failed_files:
        # Generate RCC code for this file
        rcc_code = generate_rcc_code()
        
        enhanced_failed_file = {
            **file_result,  # Keep all original fields
            "rccCode": rcc_code,
            "existingRccCode": None,
            "conflictFlag": False
        }
        
        enhanced_failed_files.append(enhanced_failed_file)
    
    # Combine enhanced successful and failed files
    enhanced_results = enhanced_successful_files + enhanced_failed_files
    
    # Return the same structure as doc classification but with RCC codes added
    enhanced_doc_classification_result = {
        **doc_classification_result,  # Keep all original fields
        "results": enhanced_results,
        "successful_files": enhanced_successful_files,
        "failed_files": enhanced_failed_files
    }
    
    return enhanced_doc_classification_result 