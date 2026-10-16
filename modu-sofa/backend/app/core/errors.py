from fastapi import HTTPException, status


class UserFacingError(Exception):
    """화면에 그대로 보여줄 수 있는 한국어 메시지를 가진 오류."""

    def __init__(self, message: str, code: str = "error"):
        super().__init__(message)
        self.message = message
        self.code = code


def not_found() -> HTTPException:
    # 다른 사용자의 리소스도 404로 응답해 존재 여부를 노출하지 않는다.
    return HTTPException(status.HTTP_404_NOT_FOUND, detail="찾을 수 없어요.")


def bad_request(message: str, code: str = "bad_request") -> HTTPException:
    return HTTPException(status.HTTP_400_BAD_REQUEST, detail={"code": code, "message": message})


def conflict(message: str, code: str = "conflict") -> HTTPException:
    return HTTPException(status.HTTP_409_CONFLICT, detail={"code": code, "message": message})


# 11장 오류 문구
MSG_UNSUPPORTED_FORMAT = "지원하지 않는 형식이에요. MP3, WAV, M4A 파일만 올릴 수 있어요."
MSG_TOO_LONG = "90분까지 올릴 수 있어요. 파일을 나눠서 올려 주세요."
MSG_TOO_LARGE = "500MB까지 올릴 수 있어요."
MSG_UNPLAYABLE = "파일을 재생할 수 없어요. 내용이 손상되었을 수 있어요."
MSG_NO_SPEECH = "음성을 찾지 못했어요."
MSG_SERVER_RESTART = "서버 재시작으로 작업이 중단되었습니다"
MSG_CANCELLED = "분석을 취소했어요."
