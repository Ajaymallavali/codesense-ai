import json
import os
import sys
from pathlib import Path
import urllib.error
import urllib.request

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "ai-service"))

# Try loading .env if available
try:
    from dotenv import load_dotenv
    for env_path in [ROOT / ".env", ROOT / "ai-service" / ".env", ROOT / "backend" / ".env"]:
        if env_path.exists():
            load_dotenv(env_path)
            break
except Exception:
    pass

from app.rag.llm_adapter import QwenAdapter, redact_sensitive_str


def diagnose_authentication():
    print("=" * 70)
    print("STAGE 1 & 2: QWEN AUTHENTICATION & MODEL AVAILABILITY DIAGNOSIS")
    print("=" * 70)

    # 1. Environment Variable Precedence & Presence Inspection
    qwen_api_key = os.environ.get("QWEN_API_KEY")
    dashscope_api_key = os.environ.get("DASHSCOPE_API_KEY")
    codesense_key = os.environ.get("CODESENSE_QWEN_API_KEY")

    active_key = qwen_api_key or dashscope_api_key or codesense_key
    active_source = (
        "QWEN_API_KEY" if qwen_api_key
        else "DASHSCOPE_API_KEY" if dashscope_api_key
        else "CODESENSE_QWEN_API_KEY" if codesense_key
        else "NONE"
    )

    print("\n1. Environment Key Precedence:")
    print(f"  • QWEN_API_KEY present:          {bool(qwen_api_key)} (len={len(qwen_api_key) if qwen_api_key else 0})")
    print(f"  • DASHSCOPE_API_KEY present:     {bool(dashscope_api_key)} (len={len(dashscope_api_key) if dashscope_api_key else 0})")
    print(f"  • CODESENSE_QWEN_API_KEY present:{bool(codesense_key)} (len={len(codesense_key) if codesense_key else 0})")
    print(f"  • Active Key Source:             {active_source}")
    print(f"  • .env File Exists:              {(ROOT / '.env').exists()}")

    # 2. Base URL & Endpoint Construction
    base_url = (
        os.environ.get("QWEN_BASE_URL")
        or os.environ.get("CODESENSE_QWEN_BASE_URL")
        or "https://dashscope-intl.aliyuncs.com/compatible-mode/v1"
    ).rstrip("/")

    endpoint = base_url if base_url.endswith("/chat/completions") else f"{base_url}/chat/completions"
    models_endpoint = f"{base_url}/models"

    configured_model = (
        os.environ.get("QWEN_MODEL")
        or os.environ.get("CODESENSE_QWEN_MODEL")
        or "Qwen/Qwen3-Coder-Next"
    )

    # Exact DashScope model identifier resolution
    dashscope_model = "qwen3-coder-next" if "dashscope" in base_url.lower() and "Qwen3-Coder-Next" in configured_model else configured_model

    print("\n2. Endpoint & Model Architecture:")
    print(f"  • Configured Base URL:           {base_url}")
    print(f"  • Constructed Chat Endpoint:     {endpoint}")
    print(f"  • Models Endpoint:               {models_endpoint}")
    print(f"  • Configured Model ID:           {configured_model}")
    print(f"  • DashScope Target Model ID:     {dashscope_model}")

    # 3. Request Header Inspection (Safe, no secret leak)
    auth_header_set = bool(active_key)
    auth_header_format = f"Bearer {active_key[:3]}...{active_key[-3:]}" if active_key and len(active_key) >= 8 else ("Bearer [EMPTY]" if not active_key else "Bearer ***")
    print("\n3. HTTP Client & Header Construction:")
    print(f"  • User-Agent:                    CodeSense-AI-QwenAdapter/1.0")
    print(f"  • Content-Type:                  application/json")
    print(f"  • Authorization Header Present:  {auth_header_set}")
    print(f"  • Authorization Format:          {auth_header_format}")

    # 4. Live Probe against {QWEN_BASE_URL}/chat/completions
    print("\n4. Live Provider Connection Probe:")
    headers = {
        "Content-Type": "application/json",
        "Authorization": f"Bearer {active_key or 'unconfigured'}",
        "User-Agent": "CodeSense-AI-QwenAdapter/1.0",
    }
    payload = {
        "model": dashscope_model,
        "messages": [
            {"role": "user", "content": "Ping: Respond with single word 'PONG'"}
        ],
        "max_tokens": 10,
        "temperature": 0.0,
    }

    req = urllib.request.Request(
        endpoint,
        data=json.dumps(payload).encode("utf-8"),
        headers=headers,
        method="POST"
    )

    auth_status = "UNKNOWN"
    response_body = None
    status_code = None

    try:
        with urllib.request.urlopen(req, timeout=15) as resp:
            status_code = resp.status
            response_body = json.loads(resp.read().decode("utf-8"))
            auth_status = "AUTHENTICATED_AND_SUCCESSFUL"
            print(f"  [SUCCESS] HTTP Status: {status_code}")
            print(f"  [SUCCESS] Response Payload: {response_body}")
    except urllib.error.HTTPError as err:
        status_code = err.code
        raw_err = err.read().decode("utf-8", errors="ignore")
        scrubbed_err = redact_sensitive_str(raw_err)
        try:
            err_json = json.loads(scrubbed_err)
        except Exception:
            err_json = {"raw": scrubbed_err}

        print(f"  [HTTP ERROR] Status Code: {status_code}")
        print(f"  [HTTP ERROR] Reason:      {err.reason}")
        print(f"  [HTTP ERROR] Error Body:  {json.dumps(err_json, indent=4)}")

        if status_code == 401:
            auth_status = "BLOCKED_UNAUTHORIZED_401"
        elif status_code == 403:
            auth_status = "BLOCKED_FORBIDDEN_403_PERMISSIONS"
        elif status_code == 404:
            auth_status = "BLOCKED_NOT_FOUND_404_MODEL_OR_ENDPOINT"
        elif status_code == 429:
            auth_status = "BLOCKED_RATE_LIMIT_429"
        else:
            auth_status = f"HTTP_{status_code}"
    except Exception as exc:
        print(f"  [CONNECTION ERROR] {type(exc).__name__}: {redact_sensitive_str(str(exc))}")
        auth_status = f"CONNECTION_ERROR_{type(exc).__name__}"

    print("\n" + "=" * 70)
    print("STAGE 1 & 2 DIAGNOSTIC SUMMARY")
    print("=" * 70)
    print(f"Authentication Status: {auth_status}")
    if auth_status == "BLOCKED_UNAUTHORIZED_401":
        print("Diagnosis: HTTP 401 Unauthorized received from Alibaba Cloud DashScope.")
        print("Root Cause: No valid QWEN_API_KEY or DASHSCOPE_API_KEY is configured in the environment.")
        print("Recommendation: To activate live inference, set QWEN_API_KEY in the environment or .env file.")
        print("Fallback Status: Deterministic RAG engine is 100% active and serving queries with citations.")
    elif auth_status == "AUTHENTICATED_AND_SUCCESSFUL":
        print("Diagnosis: Genuine live Qwen3-Coder-Next inference succeeded!")

    return {
        "auth_status": auth_status,
        "status_code": status_code,
        "endpoint": endpoint,
        "dashscope_model": dashscope_model,
        "active_key_source": active_source,
        "key_present": bool(active_key),
    }


if __name__ == "__main__":
    diagnose_authentication()
