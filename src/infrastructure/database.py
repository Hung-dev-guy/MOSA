import os
from contextlib import contextmanager

import pyodbc


def _odbc_value(value: str) -> str:
    return "{" + value.replace("}", "}}") + "}"


class SqlServerConnectionFactory:
    def __init__(self) -> None:
        driver = os.getenv("DB_DRIVER", "ODBC Driver 18 for SQL Server")
        server = os.getenv("DB_SERVER", "localhost")
        database = os.getenv("DB_NAME", "ECommerceMultimodalV1")
        user = os.getenv("DB_USER", "").strip()
        password = os.getenv("DB_PASSWORD", "")
        encrypt = os.getenv("DB_ENCRYPT", "no")
        auth = (
            f"UID={_odbc_value(user)};PWD={_odbc_value(password)};"
            if user
            else "Trusted_Connection=yes;"
        )
        self.connection_string = (
            f"DRIVER={{{driver}}};SERVER={_odbc_value(server)};"
            f"DATABASE={_odbc_value(database)};{auth}"
            f"Encrypt={encrypt};TrustServerCertificate=yes;"
        )

    @contextmanager
    def connect(self):
        connection = pyodbc.connect(
            self.connection_string,
            timeout=int(os.getenv("DB_CONNECT_TIMEOUT", "5")),
        )
        try:
            yield connection
        finally:
            connection.close()

