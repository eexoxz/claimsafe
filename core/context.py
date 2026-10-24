def shell(request):
    return {"section": request.resolver_match.url_name if request.resolver_match else ""}
