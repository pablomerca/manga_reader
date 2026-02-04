#!/usr/bin/env python3
"""
Tests for VolumeIngestor - validates volume ingestion from Mokuro format.
"""

from pathlib import Path

from manga_reader.io import VolumeIngestor


def test_volume_ingestor_loads_mokuro_volume():
    """Test that VolumeIngestor successfully loads a Mokuro volume."""
    # Path to test volume
    test_vol_path = Path(__file__).parent.parent / "test_assets" / "testVol"
    
    assert test_vol_path.exists(), f"Test volume not found at: {test_vol_path}"
    
    # Create ingestor and ingest volume
    ingestor = VolumeIngestor()
    volume = ingestor.ingest_volume(test_vol_path)
    
    assert volume is not None, "Failed to ingest volume"
    assert volume.title is not None, "Volume should have a title"
    assert volume.total_pages > 0, "Volume should have at least one page"


def test_volume_ingestor_loads_first_page():
    """Test that VolumeIngestor correctly loads the first page with OCR data."""
    test_vol_path = Path(__file__).parent.parent / "test_assets" / "testVol"
    
    ingestor = VolumeIngestor()
    volume = ingestor.ingest_volume(test_vol_path)
    
    assert volume is not None, "Failed to ingest volume"
    assert volume.total_pages > 0, "Volume should have pages"
    
    # Get first page
    first_page = volume.get_page(0)
    assert first_page is not None, "First page should be accessible"
    
    # Verify page properties
    assert first_page.image_path is not None, "Page should have an image path"
    assert first_page.width > 0, "Page should have a valid width"
    assert first_page.height > 0, "Page should have a valid height"
    assert len(first_page.ocr_blocks) > 0, "Page should have OCR blocks"
    assert len(first_page.ocr_blocks[0].full_text) > 0, "OCR block should contain text"
