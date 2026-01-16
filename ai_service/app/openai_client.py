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
You are writing a quiet, human observation for a personal weekly digest.

This is not a feed, caption, or content description.
It should feel like a line in a journal, not a report.

Post content (if any): {post_content or "(no text)"}
Author’s name: {author_name}

Write:
- ONE short sentence (15-20 words)
- Third person
- Using the person’s first name to be friendly
- Calm and observational
- Be poetic and descriptive
- No meta language (do not say “posted”, “shared”, “photo”, “caption”, or describe clothing)
- Do not infer intent or emotion unless explicitly stated

Examples of tone:
- “Deepak enjoyed some matcha during a quiet afternoon.”
- “Deepak spent some time skiing in snow-capped mountains of Gulmarg.”
- “Deepak attended a wedding with friends.”

Then assign an internal importance score (0–10) using these rough guidelines:
- 8–10: Explicit major life events (weddings, births, graduations, family gatherings)
- 6–7: Meaningful social moments, trips, photos of beautiful landscapes/architecture.
- 4–5: Regular activities or casual moments
- 2–3: Routine daily moments
- 0–1: Minimal or repetitive content
- 0: Memes, jokes, etc.

Important:
- If unsure, choose the lower importance.
- Do not explain the score.
- Do not mention importance in the summary.

Respond ONLY as JSON:

{{
  "summary": "...",
  "importance": 0
}}
"""

        # Prepare messages
        messages = [
            {
                "role": "system",
                "content": "You are a calm, factual observer. Generate brief, third-person summaries for a weekly digest feature. Always respond with valid JSON."
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
            "temperature": 1,  # Lower temperature for more consistent, factual output
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

