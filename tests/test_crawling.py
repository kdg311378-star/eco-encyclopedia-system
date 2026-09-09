import pytest

from src.eco_encyclopedia.crawling import crawl_species


def test_crawl_species_mock(mocker):
    # 1. Mock requests.get to prevent real HTTP calls
    class MockResponse:
        def __init__(self, status_code, text):
            self.status_code = status_code
            self.text = text

    def mock_get(url, *args, **kwargs):
        if "wikipedia.org" in url:
            return MockResponse(200, "<html>Mock Wikipedia Content</html>")
        elif "wikimedia.org" in url:
            return MockResponse(200, '{"query": {"pages": {}}}')
        return MockResponse(404, "")

    mocker.patch("src.eco_encyclopedia.crawling.requests.get", side_effect=mock_get)
    
    # 2. Mock save_to_s3 to prevent real S3 uploads
    mock_s3 = mocker.patch("src.eco_encyclopedia.crawling.save_to_s3")
    
    # Run the function
    try:
        crawl_species("Panthera tigris", "test_batch_001")
        
        # Verify save_to_s3 was called twice (once for HTML, once for JSON)
        assert mock_s3.call_count == 2
    except Exception as e:
        pytest.fail(f"Test failed with {e}")
