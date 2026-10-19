from fastapi.responses import JSONResponse


def problem(code, detail, status=422, **extra):
    return JSONResponse(
        {
            "type": "urn:ncc:problem:" + code,
            "title": detail,
            "status": status,
            "code": code,
            "detail": detail,
            **extra,
        },
        status_code=status,
        media_type="application/problem+json",
    )
