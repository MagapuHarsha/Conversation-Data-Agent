def nl_to_sql(question: str):
    q = question.lower()

    if "average" in q:
        return "SELECT AVG(column1) AS avg_value FROM table1 LIMIT 100"

    if "count" in q:
        return "SELECT COUNT(*) AS total FROM table1"

    if "max" in q:
        return "SELECT MAX(column1) FROM table1"

    return "SELECT * FROM table1 LIMIT 100"
