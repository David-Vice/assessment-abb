from abb_scraper.extraction import compute_content_hash, extract_content, extract_rendered

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


_TABLE_HTML = """
<!DOCTYPE html><html lang="en"><head><title>Requisites | ABB</title></head>
<body>
  <nav>Individuals Business About</nav>
  <h1>Requisites</h1>
  <table>
    <tr><td>Full name</td><td>"ABB" Open Joint Stock Company</td></tr>
    <tr><td>Head Office</td><td>67 Nizami street, AZ1005, Baku, Azerbaijan</td></tr>
    <tr><td>Telephone</td><td>994 (012) 493 00 91</td></tr>
    <tr><td>TIN</td><td>9900001881</td></tr>
    <tr><td>Bank code</td><td>805250</td></tr>
    <tr><td>SWIFT code</td><td>IBAZAZ2X</td></tr>
    <tr><td>Correspondent account at Central Bank</td><td>AZ03NABZ01350100000000002944</td></tr>
    <tr><td>Reuters</td><td>AZBB</td></tr>
  </table>
  <footer>Copyright ABB</footer>
</body></html>
"""


def test_extract_rendered_recovers_structured_table_via_fallback() -> None:
    # Arrange — a thin-prose page whose real content is a key/value table
    # (trafilatura would discard it); the lxml visible-text fallback must recover it.
    # Act
    content = extract_rendered(_TABLE_HTML)

    # Assert
    assert content is not None
    assert "IBAZAZ2X" in content.markdown
    assert "9900001881" in content.markdown


def test_compute_content_hash_is_deterministic_and_prefixed() -> None:
    # Arrange & Act
    first = compute_content_hash("hello")
    second = compute_content_hash("hello")
    other = compute_content_hash("world")

    # Assert
    assert first == second
    assert first.startswith("sha256:")
    assert first != other
