"""
Barcode Label Generator for Warehouse Operations.

Generates Code-128 barcode labels optimized for Citizen CL-E300 thermal printer.
Label size: 68mm × 38mm @ 203 DPI

Label Layout (Split Design):
┌────────────────────────────────────────┐
│ #12│x5│DE│TAG │       |||||||||||     │  ← Info left, barcode right
│ ORDER-001234   │       |||||||||||     │
│ DHL 16/01/26   │       |||||||||||     │
└────────────────────────────────────────┘

Fields:
- Sequential number (#12)
- Item count (x5 = 5 items total)
- Country code (DE or N/A)
- Internal tag (URGENT, BOX, N/A)
- Order number (ORDER-001234)
- Courier (DHL, PostOne, DPD)
- Generation date (DD/MM/YY)
- Code-128 barcode
"""

import io
import logging
from pathlib import Path
from typing import Dict, List, Any, Optional, Callable
from datetime import datetime
import json

import pandas as pd
import barcode
from barcode.writer import ImageWriter
from PIL import Image, ImageDraw, ImageFont
from reportlab.pdfgen import canvas
from reportlab.lib.pagesizes import mm

logger = logging.getLogger(__name__)


# === LABEL SPECIFICATIONS ===
# Optimized for Citizen CL-E300 thermal printer
DPI = 203
LABEL_WIDTH_MM = 68
LABEL_HEIGHT_MM = 38
LABEL_WIDTH_PX = int((LABEL_WIDTH_MM / 25.4) * DPI)   # 543px
LABEL_HEIGHT_PX = int((LABEL_HEIGHT_MM / 25.4) * DPI)  # 303px

# Layout zones (split design) - adjusted for better text visibility
INFO_SECTION_WIDTH = 340  # Left side for text info (increased from 260px)
BARCODE_SECTION_WIDTH = LABEL_WIDTH_PX - INFO_SECTION_WIDTH  # Right side for barcode (~203px)
BARCODE_SECTION_X = INFO_SECTION_WIDTH  # X position where barcode starts

# Font sizes - reduced for long text support
FONT_SIZE_SMALL = 11   # For compact info line (#12 | x5 | DE | TAG)
FONT_SIZE_MEDIUM = 14  # For order number
FONT_SIZE_LARGE = 16   # For courier name (bold)


# === EXCEPTIONS ===
class BarcodeProcessorError(Exception):
    """Base exception for barcode processor."""
    pass


class InvalidOrderNumberError(BarcodeProcessorError):
    """Invalid order number for barcode encoding."""
    pass


class BarcodeGenerationError(BarcodeProcessorError):
    """Error during barcode generation."""
    pass


# === UTILITY FUNCTIONS ===

def sanitize_order_number(order_number: str) -> str:
    """
    Clean order number for Code-128 barcode encoding.

    Removes non-alphanumeric characters except hyphens and underscores.
    Code-128 supports alphanumeric content for reliable scanning.

    Args:
        order_number: Raw order number

    Returns:
        Sanitized order number safe for barcode

    Raises:
        InvalidOrderNumberError: If order number is empty after sanitization
    """
    if not order_number:
        raise InvalidOrderNumberError("Order number cannot be empty")

    # Remove non-alphanumeric except hyphen and underscore
    clean = ''.join(c for c in order_number if c.isalnum() or c in ['-', '_'])

    if not clean:
        raise InvalidOrderNumberError(f"Order number '{order_number}' contains no valid characters")

    return clean


def load_font(size: int, bold: bool = False) -> ImageFont.FreeTypeFont:
    """
    Load font with fallback strategy.

    Tries to load Arial, falls back to DejaVu Sans if not available.

    Args:
        size: Font size in points
        bold: Whether to load bold variant

    Returns:
        PIL ImageFont object
    """
    font_name = "arialbd.ttf" if bold else "arial.ttf"

    try:
        # Try Windows fonts
        return ImageFont.truetype(font_name, size)
    except OSError:
        pass

    try:
        # Try system fonts (Linux/Mac)
        fallback = "DejaVuSans-Bold.ttf" if bold else "DejaVuSans.ttf"
        return ImageFont.truetype(fallback, size)
    except OSError:
        # Last resort: default font
        logger.warning(f"Could not load font {font_name}, using default")
        return ImageFont.load_default()


def format_tags_for_barcode(internal_tag: str) -> str:
    """
    Format internal tags for barcode label display.

    Takes first tag if multiple, truncates if too long.

    Args:
        internal_tag: Internal tag string (may be pipe-separated)

    Returns:
        Formatted tag string (max 15 chars)

    Examples:
        >>> format_tags_for_barcode("Priority|VIP")
        "Priority"
        >>> format_tags_for_barcode("URGENT-CUSTOMER-FRAGILE-GLASS")
        "URGENT-CUSTOMER"
    """
    if not internal_tag:
        return ""

    # Split by pipe and take first tag
    tags = internal_tag.split('|')
    first_tag = tags[0].strip()

    # Truncate if too long
    if len(first_tag) > 15:
        first_tag = first_tag[:15]

    return first_tag


# === MAIN BARCODE GENERATION FUNCTIONS ===

def generate_barcode_label(
    order_number: str,
    sequential_num: int,
    courier: str,
    country: str,
    tag: str,
    item_count: int,
    output_dir: Path,
    label_width_mm: float = LABEL_WIDTH_MM,
    label_height_mm: float = LABEL_HEIGHT_MM
) -> Dict[str, Any]:
    """
    Generate single barcode label with complex layout.

    Creates 68x38mm label with:
    - Left section: Sequential#, item count, country, tag, order#, courier, date
    - Right section: Code-128 barcode

    Args:
        order_number: Order number (will be sanitized)
        sequential_num: Sequential order number (1, 2, 3, ...)
        courier: Courier name (DHL, PostOne, DPD, etc.)
        country: 2-letter country code (or empty)
        tag: Internal tag (or empty)
        item_count: Total quantity of items in order
        output_dir: Directory to save PNG file
        label_width_mm: Label width (default: 68mm)
        label_height_mm: Label height (default: 38mm)

    Returns:
        Dict with keys:
            - order_number: Original order number
            - sequential_num: Sequential number used
            - courier: Courier name
            - country: Country code (or "N/A")
            - tag: Tag used (or "N/A")
            - item_count: Item count
            - file_path: Path to generated PNG
            - file_size_kb: File size in KB
            - success: True if successful
            - error: Error message if failed (None if success)

    Raises:
        InvalidOrderNumberError: If order number invalid
        BarcodeGenerationError: If barcode generation fails
    """
    try:
        # === STEP 1: Sanitize and validate ===
        safe_order_number = sanitize_order_number(order_number)

        if not output_dir.exists():
            output_dir.mkdir(parents=True, exist_ok=True)

        # Prepare display values
        country_display = country if country else "N/A"
        tag_display = format_tags_for_barcode(tag) if tag else "N/A"
        date_str = datetime.now().strftime("%d/%m/%y")

        # Calculate dimensions
        dpi = DPI
        label_width_px = int((label_width_mm / 25.4) * dpi)
        label_height_px = int((label_height_mm / 25.4) * dpi)

        # === STEP 2: Generate Code-128 barcode ===
        barcode_class = barcode.get_barcode_class('code128')

        writer = ImageWriter()
        writer.set_options({
            'module_width': 0.30,    # Bar width (mm) - reduced for narrower section
            'module_height': 15.0,   # Bar height (mm) - reduced to fit better
            'dpi': dpi,
            'quiet_zone': 0,         # No quiet zone (we add manually)
            'write_text': False,     # We add text manually
        })

        barcode_instance = barcode_class(safe_order_number, writer=writer)

        # Generate barcode to BytesIO
        barcode_buffer = io.BytesIO()
        barcode_instance.write(barcode_buffer)
        barcode_buffer.seek(0)

        # Load barcode as PIL Image
        barcode_img = Image.open(barcode_buffer)

        # === STEP 3: Create label canvas ===
        label_img = Image.new('RGB', (label_width_px, label_height_px), 'white')
        draw = ImageDraw.Draw(label_img)

        # Resize barcode to fit right section (more compact)
        barcode_target_width = BARCODE_SECTION_WIDTH - 15  # More margin for safety
        barcode_target_height = label_height_px - 40       # More top/bottom margin

        barcode_img_resized = barcode_img.resize(
            (barcode_target_width, barcode_target_height),
            Image.Resampling.LANCZOS
        )

        # Paste barcode on right side (centered vertically)
        barcode_x = BARCODE_SECTION_X + 8  # Margin from text section
        barcode_y = (label_height_px - barcode_target_height) // 2  # Center vertically
        label_img.paste(barcode_img_resized, (barcode_x, barcode_y))

        # === STEP 4: Add text info on left side ===
        font_small = load_font(10, bold=False)        # For labels (SUM, COU, TAG)
        font_medium = load_font(13, bold=False)       # For values
        font_header = load_font(16, bold=False)       # For seq# and date
        font_courier = load_font(18, bold=True)       # For courier (bold)
        font_barcode_num = load_font(20, bold=True)   # Large font for barcode number

        left_margin = 10
        y_pos = 15  # Start from top

        # === TOP SECTION: Seq#, Courier, Date ===
        # Line 1: Sequential number
        draw.text((left_margin, y_pos), f"#{sequential_num}", font=font_header, fill='black')
        y_pos += 22

        # Line 2: Courier (bold, larger)
        courier_display = courier[:25] if len(courier) <= 25 else courier[:22] + "..."
        draw.text((left_margin, y_pos), courier_display, font=font_courier, fill='black')
        y_pos += 26

        # Line 3: Date
        draw.text((left_margin, y_pos), date_str, font=font_small, fill='black')
        y_pos += 18

        # === SEPARATOR LINE ===
        line_y = y_pos
        draw.line([(left_margin, line_y), (INFO_SECTION_WIDTH - 10, line_y)], fill='black', width=1)
        y_pos += 8

        # === INFO SECTIONS (3 rows with labels and values) ===
        section_height = 22  # Height for each section

        # Section 1: SUM (items count)
        draw.text((left_margin, y_pos), "SUM:", font=font_small, fill='black')
        draw.text((left_margin + 80, y_pos), str(item_count), font=font_medium, fill='black')
        y_pos += section_height

        # Separator line
        draw.line([(left_margin, y_pos - 4), (INFO_SECTION_WIDTH - 10, y_pos - 4)], fill='black', width=1)

        # Section 2: COU (country)
        draw.text((left_margin, y_pos), "COU:", font=font_small, fill='black')
        draw.text((left_margin + 80, y_pos), country_display, font=font_medium, fill='black')
        y_pos += section_height

        # Separator line
        draw.line([(left_margin, y_pos - 4), (INFO_SECTION_WIDTH - 10, y_pos - 4)], fill='black', width=1)

        # Section 3: TAG (internal tag)
        tag_display_short = tag_display[:12] if len(tag_display) <= 12 else tag_display[:9] + "..."
        draw.text((left_margin, y_pos), "TAG:", font=font_small, fill='black')
        draw.text((left_margin + 80, y_pos), tag_display_short, font=font_medium, fill='black')

        # === Add order number below barcode (right side) ===
        # Get text size to center it
        barcode_num_text = safe_order_number
        bbox = draw.textbbox((0, 0), barcode_num_text, font=font_barcode_num)
        text_width = bbox[2] - bbox[0]

        # Center text under barcode
        text_x = barcode_x + (barcode_target_width - text_width) // 2
        text_y = barcode_y + barcode_target_height + 8  # 8px below barcode

        draw.text((text_x, text_y), barcode_num_text, font=font_barcode_num, fill='black')

        # === STEP 5: Save PNG with DPI metadata ===
        output_file = output_dir / f"{safe_order_number}.png"
        label_img.save(output_file, dpi=(dpi, dpi))

        # Get file size
        file_size_kb = output_file.stat().st_size / 1024

        logger.info(f"Generated barcode label: {output_file}")

        return {
            "order_number": order_number,
            "sequential_num": sequential_num,
            "courier": courier,
            "country": country_display,
            "tag": tag_display,
            "item_count": item_count,
            "file_path": output_file,
            "file_size_kb": round(file_size_kb, 1),
            "success": True,
            "error": None
        }

    except InvalidOrderNumberError as e:
        logger.error(f"Invalid order number '{order_number}': {e}")
        return {
            "order_number": order_number,
            "sequential_num": 0,
            "courier": "",
            "country": "N/A",
            "tag": "N/A",
            "item_count": 0,
            "file_path": None,
            "file_size_kb": 0,
            "success": False,
            "error": str(e)
        }

    except Exception as e:
        logger.error(f"Failed to generate barcode for '{order_number}': {e}", exc_info=True)
        return {
            "order_number": order_number,
            "sequential_num": 0,
            "courier": "",
            "country": "N/A",
            "tag": "N/A",
            "item_count": 0,
            "file_path": None,
            "file_size_kb": 0,
            "success": False,
            "error": str(e)
        }


def generate_barcodes_batch(
    df: pd.DataFrame,
    output_dir: Path,
    sequential_start: int = 1,
    progress_callback: Optional[Callable[[int, int, str], None]] = None
) -> List[Dict[str, Any]]:
    """
    Generate barcodes for multiple orders with progress tracking.

    Args:
        df: DataFrame with columns:
            - Order_Number (required)
            - Shipping_Provider (required, courier name)
            - Destination_Country (required, may be empty)
            - Internal_Tag (required, may be empty)
            - item_count (preferred) or Quantity (fallback): number of items in order
        output_dir: Directory to save PNG files
        sequential_start: Starting sequential number (default: 1)
        progress_callback: Optional callback(current, total, message) for progress updates

    Returns:
        List of result dicts (one per order), same format as generate_barcode_label()

    Example:
        >>> results = generate_barcodes_batch(
        ...     df=filtered_orders,
        ...     output_dir=Path("session/barcodes/DHL_Orders"),
        ...     sequential_start=1
        ... )
        >>> successful = sum(r['success'] for r in results)
        >>> print(f"Generated {successful}/{len(results)} barcodes")
    """
    results = []
    total_orders = len(df)

    logger.info(f"Starting batch barcode generation: {total_orders} orders")

    for idx, row in df.iterrows():
        sequential_num = sequential_start + len(results)

        # Progress callback
        if progress_callback:
            progress_callback(
                len(results) + 1,
                total_orders,
                f"Generating barcode {len(results) + 1} of {total_orders}..."
            )

        # Extract data from row
        order_number = str(row['Order_Number'])
        courier = str(row['Shipping_Provider'])
        country = str(row.get('Destination_Country', ''))
        tag = str(row.get('Internal_Tag', ''))

        # Get item count (number of unique items/SKUs in order)
        # Use 'item_count' column if available, otherwise fall back to 'Quantity'
        item_count = int(row.get('item_count', row.get('Quantity', 1)))

        # Generate barcode
        try:
            result = generate_barcode_label(
                order_number=order_number,
                sequential_num=sequential_num,
                courier=courier,
                country=country,
                tag=tag,
                item_count=item_count,
                output_dir=output_dir
            )

            results.append(result)

        except Exception as e:
            logger.error(f"Failed to generate barcode for {order_number}: {e}", exc_info=True)

            results.append({
                "order_number": order_number,
                "sequential_num": 0,
                "courier": "",
                "country": "N/A",
                "tag": "N/A",
                "item_count": 0,
                "file_path": None,
                "file_size_kb": 0,
                "success": False,
                "error": str(e)
            })

    logger.info(
        f"Batch generation complete: {sum(r['success'] for r in results)}/{total_orders} successful"
    )

    return results


def generate_barcodes_pdf(
    barcode_files: List[Path],
    output_pdf: Path,
    label_width_mm: float = LABEL_WIDTH_MM,
    label_height_mm: float = LABEL_HEIGHT_MM
) -> Path:
    """
    Generate PDF from barcode PNG files.

    Creates a PDF with one barcode per page (68mm × 38mm pages).
    Optimized for direct printing on label stock.

    Args:
        barcode_files: List of PNG file paths to include
        output_pdf: Output PDF path
        label_width_mm: Label width (default: 68mm)
        label_height_mm: Label height (default: 38mm)

    Returns:
        Path to generated PDF

    Raises:
        ValueError: If barcode_files is empty
        BarcodeGenerationError: If PDF generation fails

    Example:
        >>> barcode_files = [
        ...     Path("barcodes/ORDER-001.png"),
        ...     Path("barcodes/ORDER-002.png")
        ... ]
        >>> pdf_path = generate_barcodes_pdf(
        ...     barcode_files,
        ...     Path("barcodes/DHL_Orders_barcodes.pdf")
        ... )
    """
    if not barcode_files:
        raise ValueError("Cannot generate PDF: no barcode files provided")

    try:
        # Create PDF with label-sized pages
        page_width = label_width_mm * mm
        page_height = label_height_mm * mm

        c = canvas.Canvas(str(output_pdf), pagesize=(page_width, page_height))

        for barcode_file in barcode_files:
            if not barcode_file.exists():
                logger.warning(f"Barcode file not found: {barcode_file}")
                continue

            # Draw barcode image to fill entire page (no margins)
            c.drawImage(
                str(barcode_file),
                0, 0,
                width=page_width,
                height=page_height,
                preserveAspectRatio=True
            )

            # Create new page for next barcode
            c.showPage()

        c.save()

        logger.info(f"Generated PDF: {output_pdf} ({len(barcode_files)} pages)")

        return output_pdf

    except Exception as e:
        raise BarcodeGenerationError(f"Failed to generate PDF: {e}") from e
