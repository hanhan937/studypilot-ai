from django.urls import include, path

from api.chat_view import chat

urlpatterns = [
    # Listed BEFORE include("api.urls") on purpose: this chat view (with the "mode" field)
    # takes over /api/chat/. All other /api/... routes still come from api/urls.py.
    path("api/chat/", chat, name="chat"),
    path("api/", include("api.urls")),
]