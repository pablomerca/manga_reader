#!/usr/bin/env python3
"""
Quick test script to verify basic functionality without launching the full GUI.
Tests the VolumeIngestor with the testVol directory.
"""

from pathlib import Path
from manga_reader.io import VolumeIngestor


def test_basic_ingestion():
    """Test basic volume ingestion with the testVol directory."""
    
    # Path to test volume
    test_vol_path = Path(__file__).parent / "testVol"
    
    if not test_vol_path.exists():
        print(f"❌ Test volume not found at: {test_vol_path}")
        return False
    
    print(f"📁 Testing with volume at: {test_vol_path}")
    
    # Create ingestor
    ingestor = VolumeIngestor()
    
    # Try to ingest the volume
    volume = ingestor.ingest_volume(test_vol_path)
    
    if volume is None:
        print("❌ Failed to ingest volume")
        return False
    
    print(f"✓ Successfully loaded volume: {volume.title}")
    print(f"✓ Total pages: {volume.total_pages}")
    
    # Check pages
    if volume.total_pages > 0:
        first_page = volume.get_page(0)
        if first_page:
            print(f"✓ First page loaded: {first_page.image_path.name}")
            print(f"  - Dimensions: {first_page.width}x{first_page.height}")
            print(f"  - OCR blocks: {len(first_page.ocr_blocks)}")
            
            if first_page.ocr_blocks:
                print(f"  - Sample text: {first_page.ocr_blocks[0].full_text[:50]}...")
    
    print("\n✅ All basic tests passed!")
    return True


if __name__ == "__main__":
    test_basic_ingestion()
