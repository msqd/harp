//! Native components for HARP. Each `#[pyfunction]` is the exact counterpart of a pure Python implementation selected
//! through `harp._native.select`.

use pyo3::prelude::*;
use sha1::{Digest, Sha1};

/// Below this size, releasing and re-acquiring the GIL costs more than the hashing it unblocks.
const RELEASE_GIL_THRESHOLD: usize = 64 * 1024;

fn digest_hex(content_type: &str, data: &[u8]) -> String {
    let mut hasher = Sha1::new();
    hasher.update(content_type.as_bytes());
    hasher.update(b"\n");
    hasher.update(data);
    hex::encode(hasher.finalize())
}

/// Hex sha1 of `content_type`, a newline, then `data`. `None` hashes like an empty content type.
#[pyfunction]
#[pyo3(signature = (data, content_type=None))]
fn blob_id(py: Python<'_>, data: &[u8], content_type: Option<&str>) -> String {
    let content_type = content_type.unwrap_or("");
    if data.len() < RELEASE_GIL_THRESHOLD {
        digest_hex(content_type, data)
    } else {
        py.detach(|| digest_hex(content_type, data))
    }
}

#[pymodule]
fn harp_native(m: &Bound<'_, PyModule>) -> PyResult<()> {
    m.add_function(wrap_pyfunction!(blob_id, m)?)
}
