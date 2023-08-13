from harp import Harp

proxy = Harp()

"""
@proxy.get('/')
async def homepage(scope, receive, send):
    await send(
        {
            "type": "http.response.start",
            "status": 200,
        }
    )

    await send(
        {
            "type": "http.response.body",
            "body": "Hello, world.",
        }
    )
"""


proxy.mount("/httpbin/", "http://localhost:8080/")
# proxy.mount("/", "http://localhost:5173/")

if __name__ == "__main__":
    proxy.run()
