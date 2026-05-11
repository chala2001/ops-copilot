try:
    from langchain.schema import Document
    print("Import from langchain.schema successful")
except ImportError as e:
    print(f"Import from langchain.schema failed: {e}")

try:
    from langchain_core.documents import Document
    print("Import from langchain_core.documents successful")
except ImportError as e:
    print(f"Import from langchain_core.documents failed: {e}")
