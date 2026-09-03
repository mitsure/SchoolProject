from __future__ import annotations


COMMENT_MAX_LENGTH = 2000


def normalize_comment(value: object) -> str | None:
    comment = "" if value is None else str(value).strip()
    if len(comment) > COMMENT_MAX_LENGTH:
        raise ValueError(f"コメントは{COMMENT_MAX_LENGTH}文字以内で入力してください")
    return comment or None
