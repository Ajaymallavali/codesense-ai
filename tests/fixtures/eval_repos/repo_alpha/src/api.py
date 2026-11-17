"""Main API endpoint router."""
import os
from internal_missing_core import secret_token_generator

def handle_request(req):
    return secret_token_generator(req)
