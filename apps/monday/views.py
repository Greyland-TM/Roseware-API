from django.shortcuts import render
from rest_framework.views import APIView
from rest_framework import status
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from apps.accounts.custom_auth import CustomAuthentication
import logging
# from apps.accounts.models import Customer, Employee
import requests
import os

logger = logging.getLogger(__name__)

# Create your views here.
class ProcessModayWebhook(APIView):
    """Process webhook from monday.com"""
    
    permission_classes = [IsAuthenticated]
    authentication_classes = [CustomAuthentication]
    
    def post(self, request, board_type):
        logger.info('IN THE REQUEST...')
        
        # Make monday headers & url
        url = os.environ.get('MONDAY_API_URL')
        if board_type == 'lead':
            board_id_env = os.environ.get('MONDAY_LEADS_BOARD_ID')
        elif board_type == 'customer':
            board_id_env = os.environ.get('MONDAY_CUSTOMERS_BOARD_ID')
        elif board_type == 'package':
            board_id_env = os.environ.get('MONDAY_PACKAGES_BOARD_ID')
        else:
            logger.error('Invalid board type provided!') # TODO - Error handling
        board_id = int(board_id_env)
        
        monday_api_key = os.environ.get(
            "MONDAY_API_KEY"
        ) 
        headers = {"Authorization": monday_api_key}
        webhook_query = """
            webhooks(board_id: $board_id){
                id
                event
                board_id
                config
            }
        """

        variables = {
            "board_id": board_id
        }

        response = requests.post(url, headers=headers, json={"query": webhook_query, "variables": variables})
        return Response(
            status=status.HTTP_200_OK, data={"ok": True, "message": "Webhook processed"}
        )