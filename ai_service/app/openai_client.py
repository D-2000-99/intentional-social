"""
OpenAI client for generating digest summaries.

Handles image processing and API calls to OpenAI.
"""
import base64
import logging
import requests
from typing import Optional, Tuple
from openai import OpenAI
from openai import APIError, APIConnectionError, APITimeoutError
from app.config import settings

logger = logging.getLogger(__name__)

# Initialize OpenAI client
client = OpenAI(api_key=settings.OPENAI_API_KEY)


def download_and_encode_image(image_url: str, max_size_mb: int = None) -> Optional[str]:
    """
    Download an image from URL and encode it to base64.
    
    Args:
        image_url: URL of the image to download
        max_size_mb: Maximum size in MB (defaults to config value)
    
    Returns:
        Base64-encoded image string in data URI format, or None if failed
    """
    if max_size_mb is None:
        max_size_mb = settings.MAX_IMAGE_SIZE_MB
    
    try:
        # Download the image
        response = requests.get(image_url, timeout=30)
        if response.status_code != 200:
            logger.warning(f"Failed to download image from {image_url}: HTTP {response.status_code}")
            return None
        
        # Check image size
        image_size_mb = len(response.content) / (1024 * 1024)
        if image_size_mb > max_size_mb:
            logger.warning(
                f"Image too large: {image_size_mb:.2f}MB > {max_size_mb}MB. Skipping image."
            )
            return None
        
        # Encode to base64
        base64_image = base64.b64encode(response.content).decode('utf-8')
        
        # Determine content type from URL or default to jpeg
        content_type = "image/jpeg"
        if image_url.lower().endswith('.png'):
            content_type = "image/png"
        elif image_url.lower().endswith('.webp'):
            content_type = "image/webp"
        elif image_url.lower().endswith('.gif'):
            content_type = "image/gif"
        
        return f"data:{content_type};base64,{base64_image}"
    
    except requests.exceptions.RequestException as e:
        logger.error(f"Error downloading image from {image_url}: {str(e)}")
        return None
    except Exception as e:
        logger.error(f"Unexpected error processing image from {image_url}: {str(e)}")
        return None


def generate_digest_summary(
    post_content: str,
    author_name: str,
    image_urls: list[str] = None,
    timestamp: Optional[str] = None
) -> Tuple[str, float]:
    """
    Generate a digest summary and importance score for a post using OpenAI.
    
    Args:
        post_content: The text content of the post
        author_name: The name of the post author
        image_urls: List of image URLs from the post (first one will be used)
        timestamp: ISO timestamp of the post (optional)
    
    Returns:
        tuple: (summary: str, importance_score: float)
            - summary: Third-person, factual observation
            - importance_score: Internal score 0-10 (never exposed to users)
    
    Rules:
        - Summary must be third-person
        - Use the person's name
        - No emotional inference unless explicitly stated
        - No exaggeration or editorial judgment
        - Default to neutral, factual phrasing for sensitive content
    """
    try:
        # Build the prompt
        prompt = f"""
You are an objective observer creating a factual summary for a weekly digest.

Your role is to provide a clear, neutral, and factual summary of the post content.

Post content (if any): {post_content or "(no text)"}
Author’s name: {author_name}

Core requirements:
1. Be objective and factual - report what is stated, not inferred
2. Do not add emotional interpretation unless explicitly stated in the content
3. Do not editorialize or add commentary
4. Focus on the key information and facts presented
5. If the content is unclear or ambiguous, state that objectively

Write:

1. ONE concise sentence (15–25 words) summarizing the key content

2. Third person perspective

3. Use the author’s first name only if their involvement is explicit

4. Calm, observant, and lightly editorial

5. Clear and direct language

6. No meta language (do not say “posted”, “shared”, “photo”, “caption”)

7. No emojis, slang, or editorial commentary

Summary guidelines:

1. Major life events → State the event factually (e.g., "John announced a new job at Company X")

2. Activities or experiences → Describe what happened (e.g., "Sarah visited Paris and shared photos of landmarks")

3. Casual content → Summarize the main point (e.g., "Mike shared thoughts on the weather")

4. Ambiguous or minimal content → State what is visible or stated (e.g., "Alex shared an image with minimal context")

5. Memes, jokes, or low-signal content → Note the type of content objectively

Then assign an internal importance score (0–10) based on objective significance:

8–10: Major life events (job changes, moves, major milestones, significant announcements)

6–7: Notable experiences (trips, events, achievements, meaningful social gatherings)

4–5: Regular activities (routine updates, casual sharing, everyday moments)

2–3: Low-signal content (minimal updates, routine posts, unclear content)

0–1: Trivial or unserious content (memes, jokes, repetitive content, noise)

If unsure, choose the lower score.

Respond only with valid JSON:

{{
  "summary": "...",
  "importance": 0
}}
"""

        # Prepare messages
        messages = [
            {
                "role": "system",
                "content": "You are an objective, factual observer. Generate neutral, third-person summaries for a weekly digest feature. Always respond with valid JSON."
            },
            {
                "role": "user",
                "content": []
            }
        ]
        
        # Add text prompt
        messages[1]["content"].append({
            "type": "text",
            "text": prompt
        })
        
        # Add image if available (use first image)
        if image_urls and len(image_urls) > 0:
            image_data_uri = download_and_encode_image(image_urls[0])
            if image_data_uri:
                messages[1]["content"].append({
                    "type": "image_url",
                    "image_url": {
                        "url": image_data_uri,
                        "detail": settings.IMAGE_DETAIL_LEVEL
                    }
                })
                logger.info(f"Added image to prompt for post by {author_name}")
        
        # Make API call
        # Note: For gpt-5-nano, we don't set max_completion_tokens as it may cause issues
        # For older models, we use max_tokens
        api_params = {
            "model": settings.OPENAI_MODEL_NAME,
            "messages": messages,
            "temperature": 1,
        }
        
        # Only set max_tokens for older models (not gpt-5 or o3 models)
        model_name_lower = settings.OPENAI_MODEL_NAME.lower()
        if "gpt-5" not in model_name_lower and "o3" not in model_name_lower:
            api_params["max_tokens"] = 200
        
        try:
            response = client.chat.completions.create(**api_params)
        except (APIError, APIConnectionError, APITimeoutError) as api_error:
            # Log the full error details for OpenAI-specific errors
            error_msg = str(api_error)
            if hasattr(api_error, 'response') and api_error.response is not None:
                try:
                    if hasattr(api_error.response, 'json'):
                        error_body = api_error.response.json()
                    elif hasattr(api_error.response, 'text'):
                        error_body = api_error.response.text
                    else:
                        error_body = str(api_error.response)
                    status_code = getattr(api_error.response, 'status_code', None)
                    if status_code:
                        error_msg = f"Error code: {status_code} - {error_body}"
                    else:
                        error_msg = f"API Error: {error_body}"
                except Exception:
                    error_msg = f"API Error: {str(api_error)}"
            logger.error(f"OpenAI API call failed: {error_msg}")
            # Re-raise as a generic exception to ensure it's caught by post_processor
            raise Exception(f"OpenAI API error: {error_msg}")
        except Exception as api_error:
            # Catch any other unexpected errors
            error_msg = str(api_error)
            logger.error(f"Unexpected error in OpenAI API call: {error_msg}")
            raise Exception(f"OpenAI API error: {error_msg}")
        
        # Validate response structure before accessing it
        if not response or not hasattr(response, 'choices') or not response.choices:
            logger.error(f"Invalid response structure: response={response}")
            raise Exception("OpenAI API returned invalid response: no choices")
        if not response.choices[0] or not hasattr(response.choices[0], 'message'):
            logger.error(f"Invalid response structure: choices[0]={response.choices[0] if response.choices else None}")
            raise Exception("OpenAI API returned invalid response: no message")
        if not response.choices[0].message or not hasattr(response.choices[0].message, 'content'):
            logger.error(f"Invalid response structure: message={response.choices[0].message if response.choices[0] else None}")
            raise Exception("OpenAI API returned invalid response: no content")
        
        # Parse response
        response_text = response.choices[0].message.content
        
        # Log the raw response for debugging
        logger.debug(f"Raw OpenAI response content: {repr(response_text)}")
        logger.debug(f"Response type: {type(response_text)}")
        logger.debug(f"Response length: {len(response_text) if response_text else 0}")
        
        # Validate that we got actual content
        if response_text is None:
            logger.error("OpenAI API returned None for content")
            raise Exception("OpenAI API returned None for response content")
        if not isinstance(response_text, str):
            logger.error(f"OpenAI API returned non-string content: {type(response_text)}")
            raise Exception(f"OpenAI API returned invalid content type: {type(response_text)}")
        if len(response_text.strip()) == 0:
            logger.error("OpenAI API returned empty string for content")
            raise Exception("OpenAI API returned empty response content")
        
        logger.debug(f"OpenAI response: {response_text}")
        
        # Parse JSON response
        import json
        import re
        
        try:
            # Try to parse as JSON directly
            result = json.loads(response_text)
        except json.JSONDecodeError:
            # If that fails, try to extract JSON from markdown code blocks or text
            logger.warning("Response is not valid JSON, attempting to extract...")
            json_match = re.search(r'\{[^{}]*"summary"[^{}]*"importance"[^{}]*\}', response_text, re.DOTALL)
            if json_match:
                try:
                    result = json.loads(json_match.group(0))
                except json.JSONDecodeError:
                    logger.error("Could not parse JSON from response")
                    raise Exception("Failed to parse JSON response from OpenAI")
            else:
                logger.error("No JSON found in response")
                raise Exception("No valid JSON found in OpenAI response")
        
        # Validate required fields exist
        if "summary" not in result:
            raise Exception("Missing 'summary' field in OpenAI response")
        if "importance" not in result:
            raise Exception("Missing 'importance' field in OpenAI response")
        
        summary = result["summary"]
        importance = float(result["importance"])
        
        # Clamp importance to 0-10 range
        importance = max(0.0, min(10.0, importance))
        
        logger.info(
            f"Generated digest for {author_name}: "
            f"summary_length={len(summary)}, importance={importance:.1f}"
        )
        
        return summary, importance
    
    except Exception as e:
        logger.error(f"Error generating digest summary: {str(e)}")
        # Don't return fallback values - raise exception so post is not updated
        raise Exception(f"Failed to generate digest summary: {str(e)}")


def prepare_batch_request(
    post_content: str,
    author_name: str,
    image_urls: list[str] = None,
    timestamp: Optional[str] = None,
    custom_id: Optional[str] = None
) -> dict:
    """
    Prepare a single request for batch processing.
    
    Args:
        post_content: The text content of the post
        author_name: The name of the post author
        image_urls: List of image URLs from the post (first one will be used)
        timestamp: ISO timestamp of the post (optional)
        custom_id: Custom ID to track this request (typically post_id)
    
    Returns:
        Dictionary representing a batch request
    """
    # Build the prompt (same as generate_digest_summary)
    prompt = f"""
You are an objective observer creating a factual summary for a weekly digest.

Your role is to provide a clear, neutral, and factual summary of the post content.

Post content (if any): {post_content or "(no text)"}
Author's name: {author_name}

Core requirements:
1. Be objective and factual - report what is stated, not inferred
2. Do not add emotional interpretation unless explicitly stated in the content
3. Do not editorialize or add commentary
4. Focus on the key information and facts presented
5. If the content is unclear or ambiguous, state that objectively

Write:

1. ONE concise sentence (15–25 words) summarizing the key content

2. Third person perspective

3. Use the author's name when relevant to the content

4. Neutral, factual tone - like a news summary

5. Clear and direct language

6. No meta language (do not say "posted", "shared", "photo", "caption")

7. No emojis, slang, or editorial commentary

Summary guidelines:

1. Major life events → State the event factually (e.g., "John announced a new job at Company X")

2. Activities or experiences → Describe what happened (e.g., "Sarah visited Paris and shared photos of landmarks")

3. Casual content → Summarize the main point (e.g., "Mike shared thoughts on the weather")

4. Ambiguous or minimal content → State what is visible or stated (e.g., "Alex shared an image with minimal context")

5. Memes, jokes, or low-signal content → Note the type of content objectively

Then assign an internal importance score (0–10) based on objective significance:

8–10: Major life events (job changes, moves, major milestones, significant announcements)

6–7: Notable experiences (trips, events, achievements, meaningful social gatherings)

4–5: Regular activities (routine updates, casual sharing, everyday moments)

2–3: Low-signal content (minimal updates, routine posts, unclear content)

0–1: Trivial or unserious content (memes, jokes, repetitive content, noise)

If unsure, choose the lower score.

Respond only with valid JSON:

{{
  "summary": "...",
  "importance": 0
}}
"""

    # Prepare messages
    messages = [
        {
            "role": "system",
            "content": "You are an objective, factual observer. Generate neutral, third-person summaries for a weekly digest feature. Always respond with valid JSON."
        },
        {
            "role": "user",
            "content": []
        }
    ]
    
    # Add text prompt
    messages[1]["content"].append({
        "type": "text",
        "text": prompt
    })
    
    # Add image if available (use first image)
    if image_urls and len(image_urls) > 0:
        image_data_uri = download_and_encode_image(image_urls[0])
        if image_data_uri:
            messages[1]["content"].append({
                "type": "image_url",
                "image_url": {
                    "url": image_data_uri,
                    "detail": settings.IMAGE_DETAIL_LEVEL
                }
            })
    
    # Build the request
    api_params = {
        "model": settings.OPENAI_MODEL_NAME,
        "messages": messages,
        "temperature": 1,
    }
    
    # Only set max_tokens for older models (not gpt-5 or o3 models)
    model_name_lower = settings.OPENAI_MODEL_NAME.lower()
    if "gpt-5" not in model_name_lower and "o3" not in model_name_lower:
        api_params["max_tokens"] = 200
    
    # Create batch request format
    batch_request = {
        "custom_id": custom_id or f"post_{hash(post_content)}",
        "method": "POST",
        "url": "/v1/chat/completions",
        "body": api_params
    }
    
    return batch_request


def create_batch_job(requests: list[dict]) -> str:
    """
    Create a batch job from a list of requests.
    
    Args:
        requests: List of batch request dictionaries
    
    Returns:
        Batch job ID
    """
    import json
    import tempfile
    import os
    
    try:
        # Create a temporary JSONL file
        with tempfile.NamedTemporaryFile(mode='w', suffix='.jsonl', delete=False) as f:
            for req in requests:
                f.write(json.dumps(req) + '\n')
            jsonl_path = f.name
        
        try:
            # Upload the file
            with open(jsonl_path, 'rb') as f:
                uploaded_file = client.files.create(
                    file=f,
                    purpose="batch"
                )
            
            logger.info(f"Uploaded batch file: {uploaded_file.id}")
            
            # Create the batch
            batch = client.batches.create(
                input_file_id=uploaded_file.id,
                endpoint="/v1/chat/completions",
                completion_window="24h"
            )
            
            logger.info(f"Created batch job: {batch.id}")
            return batch.id
        
        finally:
            # Clean up temporary file
            if os.path.exists(jsonl_path):
                os.unlink(jsonl_path)
    
    except Exception as e:
        logger.error(f"Error creating batch job: {str(e)}")
        raise Exception(f"Failed to create batch job: {str(e)}")


def get_batch_status(batch_id: str) -> dict:
    """
    Get the status of a batch job.
    
    Args:
        batch_id: The batch job ID
    
    Returns:
        Dictionary with batch status information
    """
    try:
        batch = client.batches.retrieve(batch_id)
        return {
            "id": batch.id,
            "status": batch.status,  # "validating", "in_progress", "finalizing", "completed", "failed", "expired", "cancelling", "cancelled"
            "request_counts": {
                "total": batch.request_counts.total if hasattr(batch, 'request_counts') else 0,
                "completed": batch.request_counts.completed if hasattr(batch, 'request_counts') else 0,
                "failed": batch.request_counts.failed if hasattr(batch, 'request_counts') else 0,
            } if hasattr(batch, 'request_counts') else {},
            "output_file_id": batch.output_file_id if hasattr(batch, 'output_file_id') else None,
            "error_file_id": batch.error_file_id if hasattr(batch, 'error_file_id') else None,
        }
    except Exception as e:
        logger.error(f"Error getting batch status: {str(e)}")
        raise Exception(f"Failed to get batch status: {str(e)}")


def retrieve_batch_results(batch_id: str) -> list[dict]:
    """
    Retrieve results from a completed batch job.
    
    Args:
        batch_id: The batch job ID
    
    Returns:
        List of result dictionaries with custom_id and response
    """
    try:
        batch_status = get_batch_status(batch_id)
        
        if batch_status["status"] != "completed":
            raise Exception(f"Batch {batch_id} is not completed. Status: {batch_status['status']}")
        
        if not batch_status.get("output_file_id"):
            raise Exception(f"Batch {batch_id} has no output file")
        
        # Download the output file
        output_file = client.files.content(batch_status["output_file_id"])
        
        # Parse JSONL results
        import json
        results = []
        
        # Handle both text and bytes responses
        if hasattr(output_file, 'text'):
            content = output_file.text
        elif hasattr(output_file, 'read'):
            content = output_file.read().decode('utf-8')
        else:
            content = str(output_file)
        
        for line in content.split('\n'):
            if line.strip():
                try:
                    result = json.loads(line)
                    results.append(result)
                except json.JSONDecodeError:
                    logger.warning(f"Failed to parse result line: {line}")
        
        logger.info(f"Retrieved {len(results)} results from batch {batch_id}")
        return results
    
    except Exception as e:
        logger.error(f"Error retrieving batch results: {str(e)}")
        raise Exception(f"Failed to retrieve batch results: {str(e)}")


def parse_batch_result(result: dict) -> Tuple[str, float]:
    """
    Parse a batch result into summary and importance score.
    
    Args:
        result: Dictionary from batch result with 'response' and 'custom_id'
    
    Returns:
        tuple: (summary: str, importance_score: float)
    """
    import json
    import re
    
    try:
        # Extract the response body
        if "response" not in result:
            raise Exception("Missing 'response' field in batch result")
        
        response_body = result["response"]
        
        # Check status code first
        status_code = response_body.get("status_code", 0)
        if status_code != 200:
            error_msg = response_body.get("error", {}).get("message", f"Request failed with status {status_code}")
            raise Exception(f"Batch request failed: {error_msg}")
        
        # Handle both success and error responses
        if "body" not in response_body:
            if "error" in response_body:
                error_msg = response_body.get("error", {}).get("message", "Unknown error")
                raise Exception(f"Batch request failed: {error_msg}")
            raise Exception("Missing 'body' field in batch response")
        
        response_data = response_body["body"]
        
        # Extract content from response
        if "choices" not in response_data or not response_data["choices"]:
            raise Exception("No choices in batch response")
        
        response_text = response_data["choices"][0]["message"]["content"]
        
        if not response_text:
            raise Exception("Empty response content")
        
        # Parse JSON response
        try:
            result_json = json.loads(response_text)
        except json.JSONDecodeError:
            # Try to extract JSON from markdown or text
            json_match = re.search(r'\{[^{}]*"summary"[^{}]*"importance"[^{}]*\}', response_text, re.DOTALL)
            if json_match:
                result_json = json.loads(json_match.group(0))
            else:
                raise Exception("Failed to parse JSON from response")
        
        # Validate required fields
        if "summary" not in result_json:
            raise Exception("Missing 'summary' field in response")
        if "importance" not in result_json:
            raise Exception("Missing 'importance' field in response")
        
        summary = result_json["summary"]
        importance = float(result_json["importance"])
        
        # Clamp importance to 0-10 range
        importance = max(0.0, min(10.0, importance))
        
        return summary, importance
    
    except Exception as e:
        logger.error(f"Error parsing batch result: {str(e)}")
        raise Exception(f"Failed to parse batch result: {str(e)}")

