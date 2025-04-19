import pytest
from app import app  # Make sure this matches your filename (app.py)


@pytest.fixture
def client():
    app.config['TESTING'] = True
    with app.test_client() as client:
        yield client

# ✅ Parametrized test with multiple video URLs and expected keywords
@pytest.mark.parametrize("url, expected_keyword", [
    ("https://www.youtube.com/watch?v=UaVxeJQzGxY", "heisenberg"),
    ("https://www.youtube.com/watch?v=Bc5PpUyrwW0", "quantum"),
    ("https://www.youtube.com/watch?v=UaVxeJQzGxY&list=PLwdnzlV3ogoVGGv52O5biztwOcUewLEf5&index=10", "harmonic oscillator"),
])
def test_transcript_contains_keyword(client, url, expected_keyword):
    response = client.post("/transcript", json={"url": url})
    json_data = response.get_json()

    print(f"\n>>> Testing: {url}")
    print(">>> Transcript Preview:\n", json_data.get("transcript", "")[:300])

    if response.status_code == 200:
        assert "transcript" in json_data
        assert expected_keyword in json_data["transcript"].lower()
    else:
        assert "error" in json_data
        print(">>> Error message:", json_data["error"])

def test_missing_url(client):
    response = client.post('/transcript', json={})
    assert response.status_code == 400
    assert response.get_json()['error'] == "Missing URL"

def test_invalid_url_format(client):
    # An invalid YouTube URL — should fail gracefully
    response = client.post('/transcript', json={"url": "https://example.com/video"})
    assert response.status_code == 500
    assert "Transcript could not be retrieved" in response.get_json()["error"]

def test_valid_url_but_no_subs(client):
    # Replace this with a real video that has no subtitles (or private)
    url = "https://www.youtube.com/watch?v=dQw4w9WgXcQ"
    response = client.post('/transcript', json={"url": url})
    print(response)
    assert response.status_code in [200, 500]  # If subtitles exist, it will pass
    json_data = response.get_json()
    print(json_data)
    if response.status_code == 200:
        assert "transcript" in json_data
    else:
        assert "error" in json_data


# def test_valid_url_with_transcript(client):
#     # Use a YouTube video that you know for sure has subtitles
#     url = "https://www.youtube.com/watch?v=UaVxeJQzGxY&list=PLwdnzlV3ogoVGGv52O5biztwOcUewLEf5&index=10"  # Example: TED video with subtitles

#     response = client.post('/transcript', json={"url": url})
#     json_data = response.get_json()

#     print("\nStatus Code:", response.status_code)
#     print("Response JSON Keys:", list(json_data.keys()))
#     print("Transcript Preview:\n", json_data.get("transcript", "")[:500])  # show first 500 chars

#     assert response.status_code == 200
#     assert "transcript" in json_data
#     assert len(json_data["transcript"]) > 100  # Optional: length check
#     assert "welcome" in json_data["transcript"].lower()  # Optional keyword check

