from typing import Dict, List, Any
from dotenv import load_dotenv
import os
import aiohttp
import asyncio
import base64

# Load environment variables
load_dotenv()

async def call_external_api(file_content: bytes, filename: str) -> Dict:
    """Call external API with basic auth for a single file"""
    try:
        # Get API configuration from environment
        base_url = os.getenv("TARGET_API_BASE_URL", "https://api.example.com")
        username = os.getenv("API_USERNAME", "default_user")
        password = os.getenv("API_PASSWORD", "default_password")
        endpoint = os.getenv("API_ENDPOINT", "/process-file")
        
        # Create auth header
        credentials = f"{username}:{password}"
        encoded_credentials = base64.b64encode(credentials.encode()).decode()
        auth_header = f"Basic {encoded_credentials}"
        
        async with aiohttp.ClientSession() as session:
            # Prepare the request data
            data = aiohttp.FormData()
            data.add_field('file', file_content, filename=filename)
            
            # Make the API call with basic auth
            headers = {
                'Authorization': auth_header,
                'Content-Type': 'multipart/form-data'
            }
            
            url = f"{base_url}{endpoint}"
            
            async with session.post(url, data=data, headers=headers) as response:
                if response.status == 200:
                    result = await response.json()
                    return {
                        "filename": filename,
                        "status": "success",
                        "api_response": result
                    }
                else:
                    error_text = await response.text()
                    return {
                        "filename": filename,
                        "status": "error",
                        "error": f"API returned status {response.status}: {error_text}"
                    }
                    
    except Exception as e:
        return {
            "filename": filename,
            "status": "error",
            "error": f"Exception occurred: {str(e)}"
        }

async def doc_classification_agent(uploaded_files: List[Dict]) -> Dict[str, Any]:
    """Document Classification Agent: Calls external API service to classify and process uploaded documents"""
    
    # Call external API for each file
    tasks = []
    for file_info in uploaded_files:
        task = call_external_api(file_info["content"], file_info["filename"])
        tasks.append(task)
    
    # Wait for all API calls to complete
    api_results = await asyncio.gather(*tasks, return_exceptions=True)
    
    # Process results
    processed_results = []
    for i, result in enumerate(api_results):
        if isinstance(result, Exception):
            processed_results.append({
                "filename": uploaded_files[i]["filename"],
                "status": "error",
                "error": f"Task failed with exception: {str(result)}"
            })
        else:
            processed_results.append(result)
    
    # Consolidate results
    successful_files = [r for r in processed_results if r["status"] == "success"]
    failed_files = [r for r in processed_results if r["status"] == "error"]
    
    doc_classification_result = {
        "message": f"Classified {len(uploaded_files)} documents",
        "summary": {
            "total_files": len(uploaded_files),
            "successful": len(successful_files),
            "failed": len(failed_files)
        },
        "results": processed_results,
        "successful_files": successful_files,
        "failed_files": failed_files
    }
    
    return doc_classification_result 