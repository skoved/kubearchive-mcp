import inflect, os
from typing import Any, Optional

import httpx
from mcp.server.fastmcp import FastMCP

mcp = FastMCP("mcp-server")

engine = inflect.engine()

API_BASE_URL = os.environ["API_BASE_URL"]


async def make_request(
    url: str, method: str = "GET", data: dict[str, Any] = None, stream: Optional[bool] = False
) -> dict[str, Any] | None:
    api_key = os.environ.get("API_KEY")
    if api_key:
        if stream:
            headers = {
                "Authorization": f"Bearer {api_key}",
                "Accept": "text/plain",
            }
        else:
            headers = {
                "Authorization": f"Bearer {api_key}",
                "Accept": "application/json",
            }
    else:
        headers = {}

    async with httpx.AsyncClient(verify=False) as client:
        if method.upper() == "GET":
            response = await client.request(method, url, headers=headers, params=data)
        else:
            response = await client.request(method, url, headers=headers, json=data)
        response.raise_for_status()
        if stream:
            return response.text
        return response.json()

@mcp.tool()
async def logs(apiGroup: str, apiVersion: str, resourceType: str, name: str, namespace: str):
    """Get the logs of a Kubernetes resource from KubeArchive given the api group, api version, resource type, name and namespace"""
    if not resourceType.endswith("s"):
        resourceType = engine.plural(resourceType.lower())
    else:
        resourceType = resourceType.lower()

    apiGroupVersion = f"apis/{apiGroup.lower()}/{apiVersion.lower()}"
    if (apiGroup.lower() == "core" or apiGroup == "") and apiVersion.lower() == "v1":
        apiGroupVersion = "api/v1"

    url = f"{API_BASE_URL}/{apiGroupVersion}/namespaces/{namespace.lower()}/{resourceType}/{name.lower()}/log"
    response = await make_request(url, stream=True)
    return response

@mcp.tool()
async def resources(apiGroup: str, apiVersion: str, resourceType: str, namespace: Optional[str] = None, limit: int = 100, labelSelector: Optional[str] = None):
    """List the names in a Kubernetes namespace given the api group, api version, resource type and namespace from KubeArchive"""
    if not resourceType.endswith("s"):
        resourceType = engine.plural(resourceType.lower())
    else:
        resourceType = resourceType.lower()

    apiGroupVersion = f"apis/{apiGroup.lower()}/{apiVersion.lower()}"
    if (apiGroup.lower() == "core" or apiGroup == "") and apiVersion.lower() == "v1":
        apiGroupVersion = "api/v1"

    url = ""
    if namespace is not None:
        url = f"{API_BASE_URL}/{apiGroupVersion}/namespaces/{namespace.lower()}/{resourceType}"
    else:
        url = f"{API_BASE_URL}/{apiGroupVersion}/{resourceType}"

    params = {"limit": limit}
    if labelSelector is not None:
        params["labelSelector"] = labelSelector

    response = await make_request(url, data=params)
    names = [{"name": x["metadata"]["name"], "namespace": x["metadata"]["namespace"], "owner": x["metadata"]["ownerReferences"][0]["name"]} for x in response["items"]]
    return names

if __name__ == "__main__":
    mcp.run(transport=os.environ.get("MCP_TRANSPORT", "stdio"))
