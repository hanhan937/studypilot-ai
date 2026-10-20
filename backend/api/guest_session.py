def get_guest_session_key(request) -> str:
    """Return or create the current Django guest session."""
    if not request.session.session_key:
        request.session.create()

    return request.session.session_key