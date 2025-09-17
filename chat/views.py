from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from rest_framework.permissions import IsAuthenticated
from django.shortcuts import get_object_or_404
from .models import Conversation, Message
from .serializers import ConversationSerializer, MessageSerializer
import uuid

from core.service import OllamaChatServiceSingleton

class ConversationCreateView(APIView):
    permission_classes = [IsAuthenticated]
    def post(self, request):
        session_id = str(uuid.uuid4())
        conversation = Conversation.objects.create(user = request.user, session_id=session_id)
        chat_service = OllamaChatServiceSingleton.get_service(request.user.id)
        chat_service.get_memory(session_id)
        serializer = ConversationSerializer(conversation)
        return Response(serializer.data, status=status.HTTP_201_CREATED)

class ConversationDetailView(APIView):
    permission_classes = [IsAuthenticated]
    def get(self, request, session_id):
        conversation = get_object_or_404(Conversation, session_id=session_id)
        chat_service = OllamaChatServiceSingleton.get_service(request.user.id)
        stats = chat_service.get_conversation_stats(session_id)
        
        serializer = ConversationSerializer(conversation)
        response_data = {
            "conversation": serializer.data,
            "stats": stats
        }
        
        return Response(response_data)

class SendMessageView(APIView):    
    permission_classes = [IsAuthenticated]
    def post(self, request, session_id):
        conversation, created = Conversation.objects.get_or_create(
            session_id=session_id
        )
        
        if created:
            chat_service = OllamaChatServiceSingleton.get_service(request.user.id)
            chat_service.get_memory(session_id)
        user_message = request.data.get('message', '').strip()
        
        if not user_message:
            return Response(
                {'error': 'Message is required and cannot be empty'},
                status=status.HTTP_400_BAD_REQUEST
            )
        user_msg = Message.objects.create(
            conversation=conversation,
            content=user_message,
            is_user=True,
            user=request.user
        )
        chat_service = OllamaChatServiceSingleton.get_service(request.user.id)
        ai_response_data = chat_service.generate_response(session_id, user_message)
        ai_msg = Message.objects.create(
            conversation=conversation,
            content=ai_response_data,
            is_user=False,
            user=request.user
        )
        
        response_data = {
            "user_message": MessageSerializer(user_msg).data,
            "ai_message": MessageSerializer(ai_msg).data,
            "conversation_id": conversation.id,
            "session_id": session_id,
            "service_info": {
                "method": ai_response_data.get('method', 'unknown'),
                "success": ai_response_data.get('success', False),
                "model_used": ai_response_data.get('model_used', 'llama2')
            }
        }
        
        if status.HTTP_200_OK:
            response_data["debug"] = {
                "history_preview": ai_response_data.get('history', '')[:200] + "..." if ai_response_data.get('history') else 'No history',
                "context_used": ai_response_data.get('context_used', '')[:200] + "..." if ai_response_data.get('context_used') else 'No context'
            }
        
        status_code = status.HTTP_200_OK if ai_response_data.get('success', False) else status.HTTP_207_MULTI_STATUS
        
        return Response(response_data, status=status_code)

class ClearConversationView(APIView):
    permission_classes = [IsAuthenticated]
    def post(self, request, session_id):
        conversation = get_object_or_404(Conversation, session_id=session_id)        
        deleted_count, _ = Message.objects.filter(conversation=conversation, user=request.user).delete() 
        chat_service = OllamaChatServiceSingleton.get_service(request.user.id)      
        memory_cleared = chat_service.clear_memory(session_id)        
        chat_service.get_memory(session_id)
        
        return Response({
            "status": "success",
            "database_messages_deleted": deleted_count,
            "memory_cleared": memory_cleared,
            "session_id": session_id,
            "message": "Conversation history cleared successfully"
        })

class ConversationStatsView(APIView):
    permission_classes = [IsAuthenticated]
    def get(self, request, session_id):
        conversation = get_object_or_404(Conversation, session_id=session_id)    
        chat_service = OllamaChatServiceSingleton.get_service(request.user.id)    
        stats = chat_service.get_conversation_stats(session_id)        
        message_count = Message.objects.filter(conversation=conversation, user=request.user).count()
        
        response_data = {
            "session_id": session_id,
            "database_messages": message_count,
            "service_stats": stats,
            "conversation_created": conversation.created_at,
            "conversation_updated": conversation.updated_at
        }
        
        return Response(response_data)

class SystemStatusView(APIView):  
    permission_classes = [IsAuthenticated]  
    def get(self, request):
        chat_service = OllamaChatServiceSingleton.get_service(request.user.id)
        try:
            import ollama
            models = ollama.list()
            model_list = [model['name'] for model in models.get('models', [])]
            status_data = {
                "status": "operational",
                "active_sessions": len(chat_service.memory),
                "available_models": model_list,
                "default_model": "llama2",
                "service": "Ollama + LangChain Chat API"
            }
            
        except Exception as e:
            status_data = {
                "status": "degraded",
                "error": str(e),
                "active_sessions": len(chat_service.memory),
                "service": "Ollama + LangChain Chat API"
            }
        
        return Response(status_data)