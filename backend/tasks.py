from .database import db_run


def get_tasks(user_id):
    """
    Read-only operation used by the
    dashboard and task board.
    """

    return db_run(
        """
        SELECT
            task_no,
            title,
            description,
            status,
            created_at

        FROM tasks

        WHERE user_id = ?

        ORDER BY task_no ASC
        """,
        (user_id,),
        fetch=True
    )