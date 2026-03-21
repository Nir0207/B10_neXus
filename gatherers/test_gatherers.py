import pytest
from unittest.mock import AsyncMock, Mock, patch

from uniprot import UniProtGatherer
from opentargets import OpenTargetsGatherer
from ncbi import NCBIGatherer

@pytest.fixture
def temp_dir(tmp_path):
    return tmp_path

@pytest.mark.asyncio
async def test_uniprot_gatherer(temp_dir):
    gatherer = UniProtGatherer(base_dir=str(temp_dir))
    
    mock_response = Mock()
    mock_response.json.return_value = {"results": [{"primaryAccession": "P38398"}]}
    
    with patch("httpx.AsyncClient.get", new_callable=AsyncMock) as mock_get:
        mock_get.return_value = mock_response
        data = await gatherer.fetch("BRCA1")
        
        # Check if the data is returned
        assert "results" in data
        assert data["results"][0]["primaryAccession"] == "P38398"
        
        # Check if the file was saved
        output_file = temp_dir / "BRCA1.json"
        assert output_file.exists()


@pytest.mark.asyncio
async def test_uniprot_gatherer_sanitizes_filename(temp_dir):
    gatherer = UniProtGatherer(base_dir=str(temp_dir))

    mock_response = Mock()
    mock_response.json.return_value = {"results": []}

    with patch("httpx.AsyncClient.get", new_callable=AsyncMock) as mock_get:
        mock_get.return_value = mock_response
        await gatherer.fetch("BRCA1/../bad")

        output_file = temp_dir / "BRCA1_.._bad.json"
        assert output_file.exists()
        
@pytest.mark.asyncio
async def test_opentargets_gatherer(temp_dir):
    gatherer = OpenTargetsGatherer(base_dir=str(temp_dir))
    
    mock_response = Mock()
    mock_response.json.return_value = {"data": {"disease": {"id": "EFO_0000572"}}}
    
    with patch("httpx.AsyncClient.post", new_callable=AsyncMock) as mock_post:
        mock_post.return_value = mock_response
        data = await gatherer.fetch_liver_evidence("EFO_0000572")
        
        assert "data" in data
        assert data["data"]["disease"]["id"] == "EFO_0000572"
        
        output_file = temp_dir / "EFO_0000572_evidence.json"
        assert output_file.exists()


@pytest.mark.asyncio
async def test_opentargets_gatherer_raises_on_graphql_errors(temp_dir):
    gatherer = OpenTargetsGatherer(base_dir=str(temp_dir))

    mock_response = Mock()
    mock_response.json.return_value = {"errors": [{"message": "Rate limit exceeded"}]}

    with patch("httpx.AsyncClient.post", new_callable=AsyncMock) as mock_post:
        mock_post.return_value = mock_response
        with pytest.raises(RuntimeError, match="GraphQL error"):
            await gatherer.fetch_liver_evidence("EFO_0000572")
        
@pytest.mark.asyncio
async def test_ncbi_gatherer(temp_dir):
    gatherer = NCBIGatherer(base_dir=str(temp_dir))
    
    # Mock for two consecutive calls: esearch.fcgi and esummary.fcgi
    search_response = Mock()
    search_response.json.return_value = {"esearchresult": {"idlist": ["123", "456"]}}
    
    summary_response = Mock()
    summary_response.json.return_value = {"result": {"123": {"title": "Test Study"}}}
    
    with patch("httpx.AsyncClient.get", new_callable=AsyncMock) as mock_get:
        mock_get.side_effect = [search_response, summary_response]
        data = await gatherer.fetch_geo_studies("BRCA1")
        
        assert "result" in data
        assert "123" in data["result"]
        
        output_file = temp_dir / "BRCA1_studies.json"
        assert output_file.exists()
        
@pytest.mark.asyncio
async def test_ncbi_gatherer_empty(temp_dir):
    gatherer = NCBIGatherer(base_dir=str(temp_dir))
    
    search_response = Mock()
    search_response.json.return_value = {"esearchresult": {"idlist": []}}
    
    with patch("httpx.AsyncClient.get", new_callable=AsyncMock) as mock_get:
        mock_get.return_value = search_response
        data = await gatherer.fetch_geo_studies("EMPTY_GENE")
        
        assert data == []
        
        output_file = temp_dir / "EMPTY_GENE_studies.json"
        assert output_file.exists()
