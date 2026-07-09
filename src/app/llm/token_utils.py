def extract_tokens(response) -> int:
    """Best-effort token extraction from a LangChain AIMessage."""
    usage = getattr(response, "usage_metadata", None)
    if usage and "total_tokens" in usage:
        return usage["total_tokens"]

    meta = getattr(response, "response_metadata", None) or {}
    token_usage = meta.get("token_usage") or {}
    if "total_tokens" in token_usage:
        return token_usage["total_tokens"]

    return 0