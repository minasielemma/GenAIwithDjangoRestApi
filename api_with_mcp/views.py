from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from rest_framework.permissions import IsAuthenticated
import requests

class EmailAnalysisView(APIView):
    
    permission_classes = [IsAuthenticated]
    def post(self, request):
        email_content = request.data.get("email")  

        try:
            response = requests.get("http://localhost:8001/mcp/emails/since-yesterday")
            result = response.json()
        except Exception as e:
            return Response({"error": str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

        return Response(result, status=status.HTTP_200_OK)