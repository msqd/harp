//! Static-response HTTP/1.1 origin for the macro benchmarks: every request gets 200 and a fixed body.
//!
//! Paths under `/cache/` also carry `Cache-Control: max-age=60`, so a caching proxy can hit on them.
//!
//! Usage: harp-bench-origin <port> [body-size-bytes]   (default size: 1024)
//! std only, thread per connection, keep-alive: far cheaper than the proxy it sits behind.

use std::io::{Read, Write};
use std::net::{TcpListener, TcpStream};
use std::sync::Arc;
use std::thread;

fn serve(mut stream: TcpStream, plain: &[u8], cacheable: &[u8]) {
    let _ = stream.set_nodelay(true);
    let mut buf = [0u8; 8192];
    let mut pending: Vec<u8> = Vec::new();
    loop {
        match stream.read(&mut buf) {
            Ok(0) | Err(_) => return,
            Ok(n) => pending.extend_from_slice(&buf[..n]),
        }
        // Requests carry no body (GET): answer once per complete header block.
        while let Some(end) = pending.windows(4).position(|w| w == b"\r\n\r\n") {
            let response = if pending.starts_with(b"GET /cache/") { cacheable } else { plain };
            let written = stream.write_all(response);
            pending.drain(..end + 4);
            if written.is_err() {
                return;
            }
        }
    }
}

fn main() {
    let mut args = std::env::args().skip(1);
    let port: u16 = args.next().and_then(|a| a.parse().ok()).expect("usage: harp-bench-origin <port> [size]");
    let size: usize = args.next().map(|a| a.parse().expect("size must be an integer")).unwrap_or(1024);

    let build = |extra: &str| {
        let mut response = format!(
            "HTTP/1.1 200 OK\r\nContent-Type: application/octet-stream\r\nContent-Length: {size}\r\n{extra}\r\n"
        )
        .into_bytes();
        response.extend(std::iter::repeat(b'x').take(size));
        Arc::new(response)
    };
    let plain = build("");
    let cacheable = build("Cache-Control: max-age=60\r\n");

    let listener = TcpListener::bind(("127.0.0.1", port)).expect("bind");
    for stream in listener.incoming().flatten() {
        let (plain, cacheable) = (Arc::clone(&plain), Arc::clone(&cacheable));
        thread::spawn(move || serve(stream, &plain, &cacheable));
    }
}
