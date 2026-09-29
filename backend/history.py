from .database import db_run


def save_message(
    user_id,
    role,
    content
):

    db_run(
        """
        INSERT INTO chat_history
        (user_id, role, content)

        VALUES (?, ?, ?)
        """,
        (
            user_id,
            role,
            content
        )
    )


def load_history(user_id):

    return db_run(
        """
        SELECT
            role,
            content

        FROM chat_history

        WHERE user_id = ?

        ORDER BY id ASC
        """,
        (user_id,),
        fetch=True
    )