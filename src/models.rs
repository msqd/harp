use crate::datetime;
use pyo3::prelude::*;
use pyo3::types::PyDateTime;

#[pyclass(module = "harp._harp", name = "HttpRequest")]
struct PyHttpRequest {
    #[pyo3(get)]
    created_at: Py<PyDateTime>,
}

#[pymethods]
#[allow(non_upper_case_globals)]
impl PyHttpRequest {
    #[new]
    #[pyo3(signature = (created_at=None))]
    fn __new__(py: Python, created_at: Option<Py<PyDateTime>>) -> PyResult<Self> {
        Ok(PyHttpRequest {
            created_at: created_at.unwrap_or_else(|| datetime::py_now(py).unwrap())
        })
    }

    #[classattr]
    const kind: &'static str = "request";

    #[classattr]
    const protocol: &'static str = "http";
}

pub fn py_init(module: &Bound<'_, PyModule>) -> PyResult<()> {
    module.add_class::<PyHttpRequest>()?;
    Ok(())
}
