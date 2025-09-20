from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from rest_framework.permissions import IsAuthenticated


from core.weather_agent import WeatherAgent
import logging
logger = logging.getLogger(__name__)

class WeatherAgentQueryView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request, session_id, *args, **kwargs):
        question = request.data.get("question")

        if not question:
            return Response({"error": "Question is required"}, status=400)

        try:
            agent = WeatherAgent(
                user_id=str(request.user.id),
                session_id=session_id,
            )
            result = agent.run(question)
            return Response(result, status=status.HTTP_200_OK)
        except Exception as e:
            logger.error("Error in WeatherAgentQueryView: %s", str(e))
            return Response({"error": str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)