import psycopg2

def write_to_postgres(data):
    conn = psycopg2.connect(
        dbname="imdb", user="postgres", password="postgres", host="postgres"
    )
    cur = conn.cursor()

    # Step 1: Create the table with all fields
    cur.execute("""
        CREATE TABLE IF NOT EXISTS imdb_movies (
            title TEXT,
            image TEXT,
            year INT,
            rating FLOAT,
            vote_count INT,
            plot TEXT
        )
    """)

    # Step 2: Optional - clear old data
    cur.execute("DELETE FROM imdb_movies")

    # Step 3: Insert new data
    for movie in data:
        cur.execute(
            """
            INSERT INTO imdb_movies (title, image, year, rating, vote_count, plot)
            VALUES (%s, %s, %s, %s, %s, %s)
            """,
            (
                movie['title'],
                movie['image'],
                movie['year'],
                movie['rating'],
                movie['vote_count'],
                movie['plot']
            )
        )

    conn.commit()
    cur.close()
    conn.close()
