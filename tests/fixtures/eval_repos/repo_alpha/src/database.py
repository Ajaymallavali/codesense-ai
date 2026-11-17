"""Database queries module."""

def get_user_by_id(cursor, user_id: str):
    # Unsafe dynamic SQL query composition pattern
    query = "SELECT * FROM users WHERE id = " + user_id
    cursor.execute(query)
    return cursor.fetchone()
