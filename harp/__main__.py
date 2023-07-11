import uvicorn

if __name__ == "__main__":
    config = uvicorn.Config("harp.subm.main:app", port=5000, log_level="debug", reload=True)
    server = uvicorn.Server(config)
    server.run()


