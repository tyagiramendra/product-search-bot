import sqlite3
from mcp.server.fastmcp import FastMCP

mcp = FastMCP("SQLite Explorer")

@mcp.tool()
def fetch_products_from_database(address: str) -> str:
    """"Retrieve available internet products for a given address. 
        Use this tool when a user asks about internet plans, available services, or supported products at a location. 
        Users may phrase their query in different ways, such as 'What products are available at [address]?' 
        or 'Which internet services can I get at [address]?' 
        The input should be a full address as a string (e.g., '905 Bridge Dr, Dallas, TX 70035')."""
    conn = sqlite3.connect("db/products_db.db")
    cursor = conn.cursor()
    try:
        cursor.execute("SELECT product FROM products WHERE address = ?", (address,))
        result = cursor.fetchone()
        if result is None:
            return None
        return result[0]
    except Exception as e:
        return f"Error: {str(e)}"
    finally:
        conn.close()


if __name__ == "__main__":
    mcp.run(transport="stdio")
