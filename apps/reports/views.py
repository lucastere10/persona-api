from django.shortcuts import render

# views.py
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from resend import Resend
from resend.services.emails.models import CreateEmailOptions
from resend.core.exception import ResendException

class SendEmailView(APIView):
    def post(self, request):
        resend = Resend(api_key=__import__("os").environ["RESEND_API_KEY"])
        opts = CreateEmailOptions(
            from_="Equipe <no-reply@seudominio.com>",
            to=["cliente@exemplo.com"],
            subject="Olá do Django!",
            html="<p>Este é um e‑mail enviado via Resend 🚀</p>"
        )
        try:
            resp = resend.emails.send(opts)
            return Response({"message_id": resp.id}, status=status.HTTP_202_ACCEPTED)
        except ResendException as e:
            return Response({"error": str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
