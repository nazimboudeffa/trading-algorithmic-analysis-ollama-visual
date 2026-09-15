import requests
import json
import re

OLLAMA_URL = "http://localhost:11434/api/generate"
MODEL = "gemma4"


def analyze_with_ai(signal_data):
    prompt = f"""Analyze this forex price action data and provide a trading signal.

Data:
{json.dumps(signal_data, indent=2)}

Rules:
- HOLD → set entry, stop_loss, take_profit to null
- BUY  → take_profit > entry > stop_loss (ex: 1.15300 > 1.15100 > 1.14900)
- SELL → stop_loss > entry > take_profit (ex: 1.14900 > 1.15100 > 1.15300)

Use 5 decimals for prices.
Respond with JSON only (no explanation):
{{"signal": "BUY or SELL or HOLD", "confidence": 0-100, "reason": "brief reason", "entry": null, "stop_loss": null, "take_profit": null}}"""

    try:
        response = requests.post(
            OLLAMA_URL,
            json={
                "model": MODEL,
                "prompt": prompt,
                "stream": False,
                "format": "json",
                "options": {
                    "temperature": 0.1,
                    "num_predict": 500
                }
            },
            timeout=30
        )

        response.raise_for_status()
        response_data = response.json()

        raw_response = response_data.get("response", "").strip()
        if not raw_response:
            raw_response = response_data.get("thinking", "").strip()

        if not raw_response:
            raise ValueError(f"Empty response from LLM")

        try:
            return json.loads(raw_response)
        except json.JSONDecodeError:
            json_match = re.search(r'\{[^{}]+\}', raw_response, re.DOTALL)
            if json_match:
                return json.loads(json_match.group())
            else:
                raise ValueError(f"No valid JSON found")

    except requests.exceptions.ConnectionError:
        raise ConnectionError(f"Cannot connect to Ollama at {OLLAMA_URL}")
    except Exception as e:
        print(f"AI analysis failed: {e}")
        return None
