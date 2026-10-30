import sqlite3


DATABASE = "authentication.db"


def view_logs():

    connection = sqlite3.connect(DATABASE)

    cursor = connection.cursor()

    cursor.execute("""
        SELECT
            id,
            timestamp,
            status,
            similarity,
            failed_attempts
        FROM authentication_logs
        ORDER BY id DESC
    """)

    records = cursor.fetchall()

    connection.close()

    print()
    print("=" * 90)
    print("              CONTINUOUS BIOMETRIC AUTHENTICATION LOGS")
    print("=" * 90)

    if not records:

        print("No authentication records found.")

    else:

        print(
            f"{'ID':<5}"
            f"{'TIMESTAMP':<22}"
            f"{'STATUS':<20}"
            f"{'SIMILARITY':<15}"
            f"{'FAILURES':<10}"
        )

        print("-" * 90)

        for record in records:

            record_id = record[0]
            timestamp = record[1]
            status = record[2]
            similarity = record[3]
            failures = record[4]

            print(
                f"{record_id:<5}"
                f"{timestamp:<22}"
                f"{status:<20}"
                f"{similarity:<15.4f}"
                f"{failures:<10}"
            )

    print("=" * 90)


view_logs()