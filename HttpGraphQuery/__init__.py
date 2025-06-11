import logging
import requests
import azure.functions as func
import os
import json
from jinja2 import Template

HTML_TEMPLATE = Template("""
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <title>Azure AD User Groups</title>
    <link href="https://cdn.jsdelivr.net/npm/bootstrap@5.3.3/dist/css/bootstrap.min.css" rel="stylesheet">
</head>
<body class="bg-light">
    <div class="container py-5">
        <div class="card shadow-lg">
            <div class="card-body">
                <h1 class="card-title mb-4">Azure AD User Group Lookup</h1>
                <form method="GET" action="{{ action_url }}" class="row g-3 mb-4">
                    <div class="col-md-8">
                        <input type="email" name="upn" class="form-control" placeholder="Enter UPN">
                    </div>
                    <div class="col-md-4">
                        <button type="submit" class="btn btn-primary w-100">Lookup Groups</button>
                    </div>
                </form>

                {% if error %}
                    <div class="alert alert-danger">{{ error }}</div>
                {% elif groups %}
                    <h5>Groups for <code>{{ upn }}</code></h5>
                    <ul class="list-group">
                        {% for group in groups %}
                            <li class="list-group-item">{{ group.displayName }}</li>
                        {% endfor %}
                    </ul>
                {% elif upn %}
                    <div class="alert alert-warning">No groups found for <code>{{ upn }}</code>.</div>
                {% endif %}
            </div>
        </div>
    </div>
</body>
</html>
""")

def main(req: func.HttpRequest) -> func.HttpResponse:
    logging.info("Processing HTML group lookup")

    upn = req.params.get("upn")
    error = None
    groups = []

    if upn:
        tenant_id = os.getenv("TENANT_ID")
        client_id = os.getenv("CLIENT_ID")
        client_secret = os.getenv("CLIENT_SECRET")
        client_code = os.getenv("CLIENT_CODE")
        action_url = f"/api/HttpGraphQuery?code={client_code}&upn={upn}"

        # Token
        token_resp = requests.post(
            f"https://login.microsoftonline.com/{tenant_id}/oauth2/v2.0/token",
            data={
                "grant_type": "client_credentials",
                "client_id": client_id,
                "client_secret": client_secret,
                "scope": "https://graph.microsoft.com/.default"
            }
        )
        if not token_resp.ok:
            error = "Failed to acquire token"
        else:
            token = token_resp.json().get("access_token")
            headers = {"Authorization": f"Bearer {token}"}

            # Get user
            user_resp = requests.get(f"https://graph.microsoft.com/v1.0/users/{upn}", headers=headers)
            if user_resp.status_code != 200:
                error = f"User not found: {upn}"
            else:
                user_id = user_resp.json().get("id")
                group_resp = requests.get(f"https://graph.microsoft.com/v1.0/users/{user_id}/memberOf", headers=headers)
                if group_resp.ok:
                    groups = group_resp.json().get("value", [])
                else:
                    error = "Failed to fetch group memberships"


    html = HTML_TEMPLATE.render(upn=upn, groups=groups, error=error)
    return func.HttpResponse(html, mimetype="text/html")
