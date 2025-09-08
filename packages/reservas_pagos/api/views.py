from django.http import JsonResponse

def health(request):
    return JsonResponse({"ok": True, "module": "reservas_pagos"})
