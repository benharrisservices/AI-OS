"""Register all built-in extractors."""

from ai_os.knowledge.extractors import register_extractor
from ai_os.knowledge.extractors.docx import DocxExtractor
from ai_os.knowledge.extractors.html import HtmlExtractor
from ai_os.knowledge.extractors.markdown import MarkdownExtractor
from ai_os.knowledge.extractors.pdf import PdfExtractor
from ai_os.knowledge.extractors.plaintext import PlainTextExtractor


def register_builtin_extractors() -> None:
    for extractor in (
        MarkdownExtractor(),
        PlainTextExtractor(),
        PdfExtractor(),
        DocxExtractor(),
        HtmlExtractor(),
    ):
        register_extractor(extractor)
