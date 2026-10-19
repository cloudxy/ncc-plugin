class DomainError(Exception):
    def __init__(self, code, detail, status=422, **extra):
        super().__init__(detail)
        self.code, self.detail, self.status, self.extra = code, detail, status, extra


def require(condition, code, detail, status=422, **extra):
    if not condition:
        raise DomainError(code, detail, status, **extra)
