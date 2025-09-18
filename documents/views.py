from rest_framework.views import APIView
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.parsers import MultiPartParser, FormParser
import os

from core.agent import DocumentAgent

from .models import UploadedDocument
from .serializers import UploadedDocumentSerializer
from core.rag_service import LocalPDFVectorizer

class DocumentUploadView(APIView):
    permission_classes = [IsAuthenticated]
    parser_classes = [MultiPartParser, FormParser]

    def post(self, request, *args, **kwargs):
        serializer = UploadedDocumentSerializer(data=request.data)
        if serializer.is_valid():
            doc = serializer.save(user=request.user)
            file_path = doc.file.path
            vectorizer = LocalPDFVectorizer(doc_id=doc.id)
            chunks = vectorizer.load_and_split_pdf(file_path)
            vectorizer.create_faiss_index(chunks)

            return Response({
                "message": "File uploaded and vectorized",
                "doc_id": doc.id
            })
        return Response(serializer.errors, status=400)


class DocumentAgentQueryView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request,session_id, *args, **kwargs):
        question = request.data.get("question")
        doc_id = request.data.get("doc_id")

        if not question:
            return Response({"error": "Question is required"}, status=400)

        agent = DocumentAgent(
            user_id=str(request.user.id),
            session_id=session_id,
            doc_id=doc_id,
        )
        result = agent.ask(question)
        return Response(result)
