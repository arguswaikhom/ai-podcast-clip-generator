def format_time(seconds: float) -> str:
    """
    Format seconds to a readable time format (HH:MM:SS)
    
    Args:
        seconds: Time in seconds
        
    Returns:
        str: Formatted time string
    """
    hours, remainder = divmod(int(seconds), 3600)
    minutes, seconds = divmod(remainder, 60)
    
    if hours > 0:
        return f"{hours}h {minutes}m {seconds}s"
    elif minutes > 0:
        return f"{minutes}m {seconds}s"
    else:
        return f"{seconds}s"