import io
import pytest
from unittest.mock import AsyncMock, patch, MagicMock


def _real_png_bytes() -> bytes:
    """Gera um PNG real pequeno para exercitar o pipeline OpenCV/NumPy de verdade."""
    from PIL import Image
    buffer = io.BytesIO()
    Image.new("RGB", (20, 20), color="white").save(buffer, format="PNG")
    return buffer.getvalue()


@pytest.fixture
def mock_easyocr():
    import sys
    mock_ocr = MagicMock()
    mock_reader = MagicMock()
    mock_reader.readtext.return_value = [
        ([[0, 0], [10, 0], [10, 10], [0, 10]], "ARAMIS", 0.99),
        ([[0, 0], [10, 0], [10, 10], [0, 10]], "12345", 0.99)
    ]
    mock_ocr.Reader.return_value = mock_reader

    with patch.dict(sys.modules, {"easyocr": mock_ocr}):
        # Mock the OCR_AVAILABLE flag as well
        with patch("services.ocr_service.OCR_AVAILABLE", True):
            with patch("services.ocr_service.easyocr", mock_ocr, create=True):
                yield mock_ocr

@pytest.fixture
def mock_aiohttp():
    # Entrega um PNG real para que o pré-processamento (cv2/numpy) rode como em produção;
    # apenas o leitor OCR (easyocr) é mockado.
    with patch("aiohttp.ClientSession.get") as mock_get:
        mock_resp = AsyncMock()
        mock_resp.status = 200
        mock_resp.read.return_value = _real_png_bytes()
        mock_get.return_value.__aenter__.return_value = mock_resp
        yield mock_get

@pytest.mark.asyncio
async def test_extract_text_from_url(mock_easyocr, mock_aiohttp):
    from services.ocr_service import ocr_service
    # Reset reader so it initializes our mock
    ocr_service.reader = None

    text = await ocr_service.extract_text_from_url("http://example.com/image.jpg")

    assert text == "aramis 12345"

def test_compare_image_texts():
    from services.ocr_service import ocr_service
    
    ref = "aramis 12345 azul"
    target = "aramis manga longa 12345"
    
    score = ocr_service.compare_image_texts(ref, target)
    
    # ref words: aramis, 12345, azul (3)
    # target words: aramis, manga, longa, 12345 (4)
    # intersection: aramis, 12345 (2)
    # union: aramis, 12345, azul, manga, longa (5)
    # score: 2 / 5 = 0.4
    
    assert score == 0.4
