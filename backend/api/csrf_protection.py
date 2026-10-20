
from functools import wraps

from django.middleware.csrf import CsrfViewMiddleware


def require_csrf(view_func):
    """
    Enforce CSRF protection on DRF API views,
    including anonymous POST requests.
    """

    @wraps(view_func)
    def wrapped(request, *args, **kwargs):
        checker = CsrfViewMiddleware(lambda req: None)

        # This function is intentionally not csrf_exempt.
        def check_view(req, *args, **kwargs):
            return None

        rejection = checker.process_view(
            request,
            check_view,
            args,
            kwargs,
        )

        if rejection is not None:
            return rejection

        return view_func(request, *args, **kwargs)

    return wrapped
