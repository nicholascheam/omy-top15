import logging
from django.shortcuts import render

logger = logging.getLogger("core") # <-- Add this

def home(request):
    logger.info("test log message!") # <-- Add this
    return render(request, "home.html")