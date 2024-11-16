use pyo3::prelude::*;
use std::sync::OnceLock;

mod models;
mod datetime;

pub fn get_version() -> &'static str {
    static VERSION: OnceLock<String> = OnceLock::new();

    VERSION.get_or_init(|| {
        let _version = env!("CARGO_PKG_VERSION");
        _version.replace("-alpha", "a").replace("-beta", "b")
    })
}

#[pymodule(name = "_harp")]
fn py_init(module: &Bound<'_, PyModule>) -> PyResult<()> {
    module.add("__version__", get_version())?;
    models::py_init(module)?;
    Ok(())
}
