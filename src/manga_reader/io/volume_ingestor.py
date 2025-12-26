"""Volume Ingestor - parses Mokuro JSON and validates image files."""

import json
from pathlib import Path
from typing import Optional

from manga_reader.core import MangaVolume, MangaPage, OCRBlock


class VolumeIngestor:
    """Data Factory responsible for parsing Mokuro JSON files and validating images."""
    
    def ingest_volume(self, volume_path: Path) -> Optional[MangaVolume]:
        """
        Parse a Mokuro volume directory and create a MangaVolume entity.
        
        Args:
            volume_path: Path to the directory containing .mokuro file and images
            
        Returns:
            MangaVolume object if successful, None if parsing fails
        """
        try:
            # Find the .mokuro file
            mokuro_files = list(volume_path.glob("*.mokuro"))
            if not mokuro_files:
                raise FileNotFoundError(f"No .mokuro file found in {volume_path}")
            
            mokuro_file = mokuro_files[0]
            
            # Parse JSON
            with open(mokuro_file, 'r', encoding='utf-8') as f:
                data = json.load(f)
            
            # Extract volume title (use directory name or from JSON if available)
            title = data.get("title", volume_path.name)
            
            # Create the volume
            volume = MangaVolume(title=title, volume_path=volume_path)
            
            # Process each page
            pages_data = data.get("pages", [])
            for page_idx, page_data in enumerate(pages_data):
                page = self._parse_page(page_idx, page_data, volume_path)
                if page:
                    volume.add_page(page)
            
            return volume
            
        except Exception as e:
            print(f"Error ingesting volume: {e}")
            return None
    
    def _parse_page(self, page_number: int, page_data: dict, volume_path: Path) -> Optional[MangaPage]:
        """
        Parse a single page from Mokuro JSON.
        
        Args:
            page_number: The page index
            page_data: Dictionary containing page information
            volume_path: Path to the volume directory
            
        Returns:
            MangaPage object if successful, None otherwise
        """
        try:
            # Get image filename
            image_filename = page_data.get("img_path", page_data.get("image", ""))
            if not image_filename:
                raise ValueError(f"No image path found for page {page_number}")
            
            image_path = volume_path / image_filename
            
            # Validate image exists
            if not image_path.exists():
                raise FileNotFoundError(f"Image not found: {image_path}")
            
            # Get page dimensions
            width = page_data.get("img_width", 0)
            height = page_data.get("img_height", 0)
            
            # Create page
            page = MangaPage(
                page_number=page_number,
                image_path=image_path,
                width=width,
                height=height
            )
            
            # Parse OCR blocks
            blocks_data = page_data.get("blocks", [])
            for block_data in blocks_data:
                block = self._parse_block(block_data)
                if block:
                    page.ocr_blocks.append(block)
            
            return page
            
        except Exception as e:
            print(f"Error parsing page {page_number}: {e}")
            return None
    
    def _parse_block(self, block_data: dict) -> Optional[OCRBlock]:
        """
        Parse a single OCR block from Mokuro JSON.
        
        Args:
            block_data: Dictionary containing block information
            
        Returns:
            OCRBlock object if successful, None otherwise
        """
        try:
            # Extract bounding box coordinates
            box = block_data.get("box", [])
            if len(box) < 4:
                return None
            
            x, y, width, height = box[0], box[1], box[2] - box[0], box[3] - box[1]
            
            # Extract text lines
            lines_data = block_data.get("lines", [])
            text_lines = [line for line in lines_data if isinstance(line, str)]
            
            return OCRBlock(
                x=x,
                y=y,
                width=width,
                height=height,
                text_lines=text_lines,
                orientation="vertical"
            )
            
        except Exception as e:
            print(f"Error parsing block: {e}")
            return None
