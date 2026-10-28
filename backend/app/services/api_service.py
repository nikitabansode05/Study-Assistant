
import httpx

from app.config import JAVA_API_BASE_URL


class StudentAPIError(Exception):
    """Raised when student data cannot be fetched."""


async def get_student_tests(student_id: str) -> dict:
    """Fetch test results from the Java REST API."""

    headers = {}
 
    # Replace this example path with your real endpoint.
    url = (f"{JAVA_API_BASE_URL}/api/Assessment/performance/{student_id}")
    print(url)
    try:
        async with httpx.AsyncClient(timeout=10.0) as client:
            response = await client.get(url,headers=headers)

            response.raise_for_status()
            data = response.json()
            print(data)
        # if not isinstance(data, dict):
        #     raise StudentAPIError("Unexpected response format from Java API.")

        return data

    except httpx.HTTPStatusError as exc:
        raise StudentAPIError(f"Java API returned HTTP {exc.response.status_code}.") from exc

    except (httpx.RequestError, ValueError) as exc:
        raise StudentAPIError("Could not connect to the Java API or parse its response.") from exc
