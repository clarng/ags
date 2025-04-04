import os

import pymupdf  # PyMuPDF
from typing import Any
from mcp.server.fastmcp import FastMCP

# Initialize FastMCP server
mcp = FastMCP("pdf")


def parse_pdf(pdf_path: str) -> str:
    """Parse a PDF file and return its text content."""
    try:
        doc = pymupdf.open(pdf_path)
        text = ""
        for page in doc:
            text += page.get_text()
        doc.close()
        return text
    except Exception as e:
        return f"Error parsing PDF: {str(e)}"

@mcp.tool()
async def extract_text(pdf_path: str) -> str:
    """Extract text from a PDF file.
    
    Args:
        pdf_path: Path to the PDF file to parse
        
    Returns:
        The extracted text from the PDF
    """
    return parse_pdf(pdf_path)

if __name__ == "__main__":
    # Initialize and run the server
    mcp.run(transport='stdio')

