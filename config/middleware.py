from django.http import HttpResponse


class SimpleCorsMiddleware:
    """Allow browser requests from local frontend dev servers."""

    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        origin = request.headers.get("Origin", "")
        allowed_origins = {
            "http://localhost:3000",
            "http://127.0.0.1:3000",
        }

        if request.method == "OPTIONS":
            response = HttpResponse(status=204)
        else:
            response = self.get_response(request)

        if origin in allowed_origins:
            response["Access-Control-Allow-Origin"] = origin
            response["Vary"] = "Origin"
            response["Access-Control-Allow-Credentials"] = "true"
        response["Access-Control-Allow-Headers"] = "Content-Type"
        response["Access-Control-Allow-Methods"] = "GET, PUT, PATCH, POST, DELETE, OPTIONS"
        return response
