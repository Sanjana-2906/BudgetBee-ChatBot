import os, requests

def _have_env():
    return all([
        os.getenv("WATSONX_KEY"),
        os.getenv("WATSONX_URL"),
        os.getenv("WATSONX_MODEL_ID"),
        os.getenv("WATSONX_PROJECT_ID")
    ])

def nlu_analyze(text: str):
    """Optional: IBM Watson NLU sentiment/keywords (silent fail)."""
    key = os.getenv("NLU_KEY"); url = os.getenv("NLU_URL")
    if not key or not url:
        return None
    try:
        headers = {"Authorization": f"Bearer {key}", "Content-Type": "application/json"}
        payload = {"text": text, "features": {"keywords": {}, "sentiment": {}}}
        r = requests.post(url.rstrip('/') + '/v1/analyze?version=2022-04-07',
                          json=payload, headers=headers, timeout=12)
        if r.ok:
            return r.json()
    except Exception:
        pass
    return None

def watsonx_generate(prompt: str):
    """Optional: call watsonx text-generation (silent fail). Returns None on error."""
    if not _have_env():
        return None
    try:
        # NOTE: API surface can vary by account/region; keep this minimal and fail-safe.
        headers = {
            "Authorization": f"Bearer {os.getenv('WATSONX_KEY')}",
            "Content-Type": "application/json"
        }
        body = {
            "model_id": os.getenv("WATSONX_MODEL_ID"),
            "input": prompt,
            "parameters": {"decoding_method": "greedy", "max_new_tokens": 400},
            "project_id": os.getenv("WATSONX_PROJECT_ID")
        }
        url = os.getenv("WATSONX_URL").rstrip('/') + "/ml/v1/text/generation?version=2023-10-31"
        resp = requests.post(url, json=body, headers=headers, timeout=20)
        if resp.ok:
            data = resp.json()
            # attempt to pull text field commonly present
            for k in ("results", "generations", "output"):
                if k in data:
                    try:
                        if isinstance(data[k], list) and data[k]:
                            cand = data[k][0]
                            return cand.get("generated_text") or cand.get("text") or str(cand)
                    except Exception:
                        pass
            return str(data)[:1200]
    except Exception:
        return None
    return None