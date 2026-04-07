"""Create test PDF files for upload testing"""
from reportlab.lib.pagesizes import letter
from reportlab.pdfgen import canvas
from reportlab.lib.styles import getSampleStyleSheet
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer
import io

def create_text_based_pdf(filename):
    """Create a text-based PDF with extractable text."""
    doc = SimpleDocTemplate(filename, pagesize=letter)
    styles = getSampleStyleSheet()
    story = []
    
    # Add content
    story.append(Paragraph("Construction Invoice", styles['Heading1']))
    story.append(Spacer(1, 12))
    story.append(Paragraph("Invoice #: INV-2024-001", styles['Normal']))
    story.append(Paragraph("Date: March 15, 2024", styles['Normal']))
    story.append(Paragraph("Vendor: ABC Construction Co.", styles['Normal']))
    story.append(Spacer(1, 12))
    story.append(Paragraph("Description: Foundation work for Project Alpha", styles['Normal']))
    story.append(Paragraph("Amount: $15,000.00", styles['Normal']))
    story.append(Spacer(1, 12))
    story.append(Paragraph("This is a text-based PDF document for testing text extraction.", styles['Normal']))
    
    doc.build(story)
    print(f"Created: {filename}")

def create_contract_pdf(filename):
    """Create a contract-style PDF."""
    doc = SimpleDocTemplate(filename, pagesize=letter)
    styles = getSampleStyleSheet()
    story = []
    
    story.append(Paragraph("CONSTRUCTION CONTRACT AGREEMENT", styles['Heading1']))
    story.append(Spacer(1, 12))
    story.append(Paragraph("Contract #: C-2024-0456", styles['Normal']))
    story.append(Spacer(1, 12))
    story.append(Paragraph("This agreement is made between:", styles['Normal']))
    story.append(Paragraph("Party A: XYZ Builders Ltd.", styles['Normal']))
    story.append(Paragraph("Party B: MegaCorp Development", styles['Normal']))
    story.append(Spacer(1, 12))
    story.append(Paragraph("Terms and Conditions:", styles['Heading2']))
    story.append(Paragraph("1. Project commencement date: April 1, 2024", styles['Normal']))
    story.append(Paragraph("2. Total contract value: $450,000.00", styles['Normal']))
    story.append(Paragraph("3. Payment terms: Net 30 days from invoice date", styles['Normal']))
    story.append(Spacer(1, 12))
    story.append(Paragraph("Signed on this 15th day of March, 2024", styles['Normal']))
    
    doc.build(story)
    print(f"Created: {filename}")

if __name__ == "__main__":
    import sys
    sys.path.insert(0, '/root/.openclaw/workspace/cerebrum-fix/backend')
    
    create_text_based_pdf("/root/.openclaw/workspace/test_pdfs/test_invoice.pdf")
    create_contract_pdf("/root/.openclaw/workspace/test_pdfs/test_contract.pdf")
    print("Test PDFs created successfully!")
