from rest_framework.views import APIView
from rest_framework.response import Response

class ClassWiseImageView(APIView):
    permission_classes = []

    def get(self, request):
        data = {
            "status": "success",
            "message": "Class-wise counts API working from test app!",
            "counts": {"cat": 10, "dog": 15}
        }
        return Response(data)