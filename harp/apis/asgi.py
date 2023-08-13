from blacksheep import Application, json

from harp.services.database.fake import fake_db

app = Application()

app.use_cors(
    allow_methods="*",
    allow_origins="*",
    allow_headers="* Authorization",
    max_age=300,
)


@app.router.get("/")
async def home(request):
    return json({"items": [transaction.asdict() for transaction in fake_db.rows]})
