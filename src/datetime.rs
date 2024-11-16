use chrono::{DateTime, Datelike, Timelike, Utc};
use pyo3::types::PyDateTime;
use pyo3::{Py, PyResult, Python};

pub fn py_now(py: Python) -> PyResult<Py<PyDateTime>> {
    let now: DateTime<Utc> = Utc::now();
    let py_datetime = PyDateTime::new_bound(
        py,
        now.year(),
        now.month() as u8,
        now.day() as u8,
        now.hour() as u8,
        now.minute() as u8,
        now.second() as u8,
        now.timestamp_subsec_micros(),
        None,
    )?;
    Ok(py_datetime.into())
}
