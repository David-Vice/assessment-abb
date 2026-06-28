from abb_scraper.extraction import compute_content_hash, extract_content

_RICH_HTML = """
<!DOCTYPE html>
<html lang="en">
  <head><title>Wire transfers | ABB</title></head>
  <body>
    <nav>Home Individuals Business About</nav>
    <article>
      <h1>Wire transfers</h1>
      <p>ABB offers fast and secure domestic and international wire transfers for
      individual customers. You can send money to accounts in Azerbaijan and abroad
      through the ABB mobile app or any branch. Transfers are processed quickly with
      transparent fees and competitive exchange rates.</p>
      <p>To send a wire transfer you need the recipient's account number, the bank
      identifier, and a valid form of identification. International transfers use the
      SWIFT network and typically settle within one to three business days.</p>
    </article>
    <footer>Copyright ABB</footer>
  </body>
</html>
"""

_EMPTY_HTML = "<html><head><title>x</title></head><body><nav>menu</nav></body></html>"


def test_extract_content_returns_markdown_and_title() -> None:
    # Arrange & Act
    content = extract_content(_RICH_HTML)

    # Assert
    assert content is not None
    assert "transfer" in content.markdown.lower()
    assert content.title == "Wire transfers | ABB"


def test_extract_content_drops_boilerplate_only_pages() -> None:
    # Arrange & Act & Assert
    assert extract_content(_EMPTY_HTML) is None


def test_compute_content_hash_is_deterministic_and_prefixed() -> None:
    # Arrange & Act
    first = compute_content_hash("hello")
    second = compute_content_hash("hello")
    other = compute_content_hash("world")

    # Assert
    assert first == second
    assert first.startswith("sha256:")
    assert first != other
