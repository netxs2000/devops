"""统一异常体系。

遵循 contexts.md 第 10 章规范。
"""


class BusinessException(Exception):
    """基础业务异常类。"""

    def __init__(self, message: str, code: str = "ERROR", status_code: int = 400):
        self.message = message
        self.code = code
        self.status_code = status_code
        super().__init__(self.message)


class ValidationException(BusinessException):
    """参数校验异常。"""

    def __init__(self, message: str):
        super().__init__(message, code="VALIDATION_ERROR", status_code=400)


class NotFoundException(BusinessException):
    """资源不存在异常。"""

    def __init__(self, message: str):
        super().__init__(message, code="NOT_FOUND", status_code=404)


class PermissionException(BusinessException):
    """权限不足异常。"""

    def __init__(self, message: str):
        super().__init__(message, code="FORBIDDEN", status_code=403)
