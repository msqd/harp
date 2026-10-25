"""Decoding of ``Content-Encoding`` that never expands more than ``step`` bytes at once.

httpx decodes each chunk whole: a few kilobytes of gzip can expand to gigabytes in memory before anything is passed on.
Here gzip and deflate (zlib) are decoded with a maximum output size per step, so a decompression bomb streams through
in constant memory. Other codings (brotli, zstd) are optional dependencies of httpx with no such bound; they are
decoded by httpx's own decoders, whole.
"""

import typing as tp
import zlib

import httpx

MAX_DECODED_STEP = 64 * 1024


class _Stage(tp.Protocol):
    def decode(self, data: bytes) -> tp.Iterator[bytes]: ...

    def flush(self) -> tp.Iterator[bytes]: ...


class _ZlibStage:
    def __init__(self, wbits: int, step: int, *, raw_fallback: bool = False):
        self._step = step
        self._decompressor = zlib.decompressobj(wbits)
        self._raw_fallback = raw_fallback

    def decode(self, data: bytes) -> tp.Iterator[bytes]:
        try:
            yield from self._drain(data)
        except zlib.error as exc:
            raise httpx.DecodingError(str(exc)) from exc

    def _drain(self, data: bytes) -> tp.Iterator[bytes]:
        if self._raw_fallback:
            # Some servers send raw deflate: tell from the first bytes, like httpx.
            self._raw_fallback = False
            try:
                piece = self._decompressor.decompress(data, self._step)
            except zlib.error:
                self._decompressor = zlib.decompressobj(-zlib.MAX_WBITS)
                piece = self._decompressor.decompress(data, self._step)
        else:
            piece = self._decompressor.decompress(data, self._step)
        while True:
            if piece:
                yield piece
            pending = self._decompressor.unconsumed_tail
            if not pending:
                return
            piece = self._decompressor.decompress(pending, self._step)

    def flush(self) -> tp.Iterator[bytes]:
        try:
            piece = self._decompressor.flush()
        except zlib.error as exc:  # pragma: no cover
            raise httpx.DecodingError(str(exc)) from exc
        if piece:
            yield piece


class _HttpxStage:
    """A coding httpx knows how to decode, and this module cannot bound."""

    def __init__(self, decoder):
        self._decoder = decoder

    def decode(self, data: bytes) -> tp.Iterator[bytes]:
        if piece := self._decoder.decode(data):
            yield piece

    def flush(self) -> tp.Iterator[bytes]:
        if piece := self._decoder.flush():
            yield piece


def _stage(coding: str, step: int) -> tp.Optional[_Stage]:
    if coding == "gzip":
        return _ZlibStage(zlib.MAX_WBITS | 16, step)
    if coding == "deflate":
        return _ZlibStage(zlib.MAX_WBITS, step, raw_fallback=True)
    decoder = httpx.Response(200, headers=[("content-encoding", coding)])._get_content_decoder()
    if isinstance(decoder, httpx._decoders.IdentityDecoder):
        return None
    return _HttpxStage(decoder)


class BoundedDecoder:
    """Decodes a body sent with this ``Content-Encoding``, yielding pieces of at most ``step`` bytes.

    ``decode`` takes the body as it arrives, in chunks of any size; ``flush`` is called once at its end. Corrupt data
    raises :class:`httpx.DecodingError`.
    """

    def __init__(self, content_encoding: tp.Optional[str], *, step: int = MAX_DECODED_STEP):
        codings = [coding.strip().lower() for coding in (content_encoding or "").split(",")]
        # The codings were applied in the order listed: they are undone in reverse.
        stages = (_stage(coding, step) for coding in reversed(codings) if coding)
        self._stages: tp.List[_Stage] = [stage for stage in stages if stage is not None]

    def decode(self, data: bytes) -> tp.Iterator[bytes]:
        return self._through(self._stages, data)

    def flush(self) -> tp.Iterator[bytes]:
        for index, stage in enumerate(self._stages):
            for piece in stage.flush():
                yield from self._through(self._stages[index + 1 :], piece)

    @classmethod
    def _through(cls, stages: tp.Sequence[_Stage], data: bytes) -> tp.Iterator[bytes]:
        if not stages:
            if data:
                yield data
            return
        for piece in stages[0].decode(data):
            yield from cls._through(stages[1:], piece)
