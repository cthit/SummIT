import psycopg2
from psycopg2 import pool
import os
from flask import g, Flask


class Database:
    """Database connection pool manager"""

    def __init__(self):
        self._connection_pool = None

    def init_app(self, app: Flask):
        """Initialize database connection pool with Flask app"""
        try:
            self._connection_pool = pool.SimpleConnectionPool(
                minconn=1,
                maxconn=10,
                host=os.getenv("DB_HOST", "summit_db"),
                port=os.getenv("DB_PORT", "5432"),
                database=os.getenv("POSTGRES_DB", "summit_db"),
                user=os.getenv("POSTGRES_USER", "postgres"),
                password=os.getenv("POSTGRES_PASSWORD", ""),
            )
            app.logger.info("Database connection pool created")
        except Exception as e:
            app.logger.error(f"Failed to create database pool: {e}")
            raise
        app.teardown_appcontext(self.close_all_connections)

    def get_connection(self):
        """Get a connection from the pool"""
        return self._connection_pool.getconn()

    def put_connection(self, conn: psycopg2.extensions.connection):
        """Put connection back to the pool"""
        self._connection_pool.putconn(conn)

    def close_all_connections(self):
        """Close all connections in the pool"""
        if self._connection_pool:
            self._connection_pool.closeall()


db = Database()


def get_db() -> psycopg2.extensions.connection:
    """Get database connection for current request"""
    if "db_conn" not in g:
        g.db_conn = db.get_connection()
    return g.db_conn


def close_db():
    """Close database connection at end of request"""
    conn = g.pop("db_conn", None)
    if conn is not None:
        db.put_connection(conn)
