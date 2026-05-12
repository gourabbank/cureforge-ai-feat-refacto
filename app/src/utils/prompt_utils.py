def truncate_error_message(error_message: str, max_length: int = 1000) -> str:
    """Truncate error messages to a specified maximum length."""
    if len(error_message) <= max_length:
        return error_message
    half_length = max_length // 2
    return (
        (
            f"{error_message[:half_length]}...(truncated)...{error_message[-half_length:]}"
        )
        if len(error_message) > max_length
        else error_message
    )
